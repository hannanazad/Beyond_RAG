"""Call a Qwen model on Alibaba Cloud Model Studio as `ask(prompt, images)`.

The parser takes one function, `ask(prompt, images) -> str` (see
`parser.make_semantic_parser`). This file supplies it for Qwen3.8-Max over
Model Studio's OpenAI-compatible endpoint. The checkers stay on Claude
(`anthropic_client.py`): the plan-writer and the checkers are different models
from different companies, so a mistake in a plan is not judged by the model
that made it (S2.2: "verification by an LLM is itself fallible"; S4.6 has
"a single LLM for all verification operations" as an ablation).

REPEATABLE BY CACHING, AND MEASURED
-----------------------------------
A hosted model does not promise the same reply twice, even with a seed. What
makes a run repeatable is the cache: every reply is saved on disk under a key
made from everything that could change it (model, thinking, thinking budget or
effort, token limit, seed, sampling, prompt). Running again reads the saved
reply. The saved file holds the prompt, the reply, the model's reasoning text,
the finish reason, the token usage, the response id and the address, so every
plan can be traced to exactly what the model was shown. How often a FRESH call
changes a plan is measured by the repeat run (hprc/run.sh ... repeat NAME
alibaba), not assumed.

WHAT IS SENT (plain HTTP; Model Studio's own fields go at the top level)
------------------------------------------------------------------------
    model, one user message (the prompt), stream: true with usage in the last
    chunk, enable_thinking, thinking_budget (or reasoning_effort: never both,
    the API refuses that), max_completion_tokens (thinking plus reply), seed,
    and the sampling settings only if given.
When the thinking reaches its budget the model stops thinking and answers; so
max_completion_tokens is the budget plus room for the answer, and a long think
can never use up the whole limit and leave no answer. With sampling=None no
temperature, top_p or top_k is sent: the server uses the model's own
defaults. Model Studio says a temperature of 0 is not recommended, and a
thinking model is not run greedily.

Streaming is used because a non-streamed call that runs past the server's
time limit is cut off and returned as if it were complete; a streamed call
has no such limit. Thinking tokens are billed as output tokens.

ERRORS, AND WHAT THE NEXT JOB DOES WITH THEM
--------------------------------------------
The parser records a failed call as "the model call failed: <message>", and
the next parse job asks again unless the message says the request itself was
refused (`evaluation/vine_run.py`, `_NO_RETRY`: "answered 400", "answered
422", "refused by the API"). So:
  busy or failing (429, 5xx, "No backend server available", a dropped
      connection, a broken stream): tried again here; if it lasts, the
      message names no refusal, and the next job asks again;
  the account or its settings (no balance, no access, wrong key, unknown
      model): raised at once, naming no refusal: fix it and submit again;
  the request itself (a bad parameter, an input too long, a refused
      content check), as an HTTP status or inside the stream: raised at
      once as a refusal; the next job does not ask again (the same request
      gets the same answer).

Model Studio's documentation (checked 18 Oct 2026):
  https://www.alibabacloud.com/help/en/model-studio/qwen-api-via-openai-chat-completions
  https://www.alibabacloud.com/help/en/model-studio/deep-thinking
  https://www.alibabacloud.com/help/en/model-studio/base-url  (API keys are per region)
  https://www.alibabacloud.com/help/en/model-studio/developer-reference/error-code
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import requests

from .vllm_client import NotInCache

__all__ = ["make_ask_alibaba", "cost_usd", "base_url_for", "error_kind", "BASE_URLS",
           "PRICES_PER_MTOK", "NotInCache"]

# The OpenAI-compatible address of each region (pay-as-you-go). A key works only
# in the region it was made in.
BASE_URLS = {
    "singapore": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    "us": "https://dashscope-us.aliyuncs.com/compatible-mode/v1",
    "beijing": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "hongkong": "https://cn-hongkong.dashscope.aliyuncs.com/compatible-mode/v1",
}
# Price per million tokens (input, cached input, output), Qwen3.8-Max's list
# price at release (The Batch, Aug 2026). The bill on the Model Studio console
# is what counts; this is only for the log.
PRICES_PER_MTOK = {"qwen3.8-max": (2.0, 0.25, 6.0)}
_RETRY_STATUS = {408, 429, 500, 502, 503, 504}
_MAX_PAUSE = 120.0

# What an error says (its code or message, lower case), from Model Studio's
# error-code page. Read in this order: "No backend server available" comes
# under the code InvalidParameter but is a passing outage; then the account;
# then the request (an InternalError.Algo.InvalidParameter is about the
# request, not the server); then the passing ones.
_PASSING_FIRST = ("no backend server",)
_ACCOUNT = ("arrearage", "out_of_service", "overdue", "accessdenied", "access_denied",
            "unpurchased", "freetieronly", "invalidapikey", "invalid_api_key",
            "modelnotfound", "model_not_found")
_REQUEST = ("invalidparameter", "invalid_parameter", "datainspection", "data_inspection")
_PASSING = ("throttl", "rate limit", "ratelimit", "rate_limit", "limit_requests", "limitrequests",
            "limit_burst", "too many requests", "insufficient_quota", "internalerror",
            "internal error", "internal_error", "no backend server", "unavailable", "overload",
            "resourceexhausted", "timeout", "timed out", "busy")


def error_kind(text: str) -> str:
    """"account", "request", "passing" or "" (not known) for an error's code
    and message (never a whole HTML page: see `_body_error`)."""
    t = (text or "").lower()
    for kind, words in (("passing", _PASSING_FIRST), ("account", _ACCOUNT), ("request", _REQUEST),
                        ("passing", _PASSING)):
        if any(w in t for w in words):
            return kind
    return ""


def _body_error(r) -> Tuple[str, str]:
    """(the code, type and message of a JSON error body, for `error_kind`;
    the body's start, for the message). A body that is not JSON (a proxy's
    error page, say) gives no code: its kind is not known."""
    text = r.text[:800]
    try:
        data = json.loads(r.text)
    except ValueError:
        return "", text
    if not isinstance(data, dict):
        return "", text
    e = data["error"] if isinstance(data.get("error"), dict) else data
    return " ".join(str(e.get(k) or "") for k in ("code", "type", "message")), text


def _account_error(detail: str) -> RuntimeError:
    return RuntimeError(f"the Model Studio account or its settings stopped the call ({detail[:600]}); "
                        f"fix that (balance, access, key, region, model name), then submit the "
                        f"parse stage again")


def _refused(detail: str) -> RuntimeError:
    return RuntimeError(f"the request was refused by the API: {detail[:600]}")


class _StreamBroke(RuntimeError):
    """The stream stopped before the model finished, or reported a passing
    (or unknown) error: worth trying again."""


def base_url_for(region: str) -> str:
    """The address for a region name (singapore, us, beijing, hongkong), or
    an address given in full."""
    r = (region or "").strip()
    if r.startswith("https://"):
        return r.rstrip("/")
    if r.lower() not in BASE_URLS:
        raise ValueError(f"unknown Model Studio region {region!r}: use one of "
                         f"{', '.join(BASE_URLS)}, or the full https:// address")
    return BASE_URLS[r.lower()]


def _key(parts: Dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest()


def _events(lines: Iterable[Any], check: Callable[[], None] = lambda: None
            ) -> Iterable[Dict[str, Any]]:
    """The JSON objects of a server-sent event stream, until [DONE]. `check()`
    runs on every line the server sends, keep-alive comments included."""
    for raw in lines:
        check()
        if raw is None:
            continue
        line = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
        line = line.strip()
        if not line.startswith("data:"):
            continue                           # blank lines, comments, event:/id: lines
        data = line[5:].strip()
        if data == "[DONE]":
            return
        try:
            yield json.loads(data)
        except ValueError as e:
            raise _StreamBroke(f"the stream sent something that is not JSON: {data[:200]!r}") from e


def _error_in(event: Dict[str, Any]) -> str:
    """The error an event reports, or ''. Model Studio reports one either the
    OpenAI way ({"error": {...}}) or its own way ({"code", "message"} with no
    choices)."""
    if isinstance(event.get("error"), dict):
        e = event["error"]
        return f"{e.get('code') or e.get('type') or ''}: {e.get('message') or ''}".strip(": ")
    if event.get("code") and event.get("message") and "choices" not in event:
        return f"{event['code']}: {event['message']}"
    return ""


class _Reply:
    """One reply, joined from its chunks as they come: the answer, the
    reasoning, the finish reason, the usage (in the last chunk), the id."""

    def __init__(self) -> None:
        self.content: List[str] = []
        self.reasoning: List[str] = []
        self.finish: Optional[str] = None
        self.usage: Dict[str, Any] = {}
        self.id = ""
        self.model = ""
        self.events = 0

    def add(self, ev: Dict[str, Any]) -> None:
        err = _error_in(ev)
        if err:
            kind = error_kind(err)
            if kind == "account":
                raise _account_error(err)
            if kind == "request":
                raise _refused(f"(in the stream) {err}")
            raise _StreamBroke(f"the stream reported an error: {err[:600]}")
        self.events += 1
        self.id = self.id or str(ev.get("id") or "")
        self.model = self.model or str(ev.get("model") or "")
        if ev.get("usage"):
            self.usage = ev["usage"]
        for ch in ev.get("choices") or []:
            delta = ch.get("delta") or ch.get("message") or {}
            if delta.get("reasoning_content"):
                self.reasoning.append(str(delta["reasoning_content"]))
            if delta.get("content"):
                self.content.append(str(delta["content"]))
            if ch.get("finish_reason"):
                self.finish = ch["finish_reason"]

    def result(self, note: str = "") -> Dict[str, Any]:
        return {"content": "".join(self.content), "reasoning": "".join(self.reasoning),
                "finish_reason": self.finish, "usage": self.usage, "id": self.id,
                "model_returned": self.model, "note": note}


def make_ask_alibaba(model: str = "qwen3.8-max", *, base_url: str = BASE_URLS["singapore"],
                     enable_thinking: bool = True, thinking_budget: Optional[int] = 131072,
                     reasoning_effort: Optional[str] = None,
                     max_completion_tokens: int = 163840, seed: Optional[int] = 42,
                     sampling: Optional[Dict[str, float]] = None,
                     cache_dir: Optional[str] = None, cache_only: bool = False,
                     api_key_env: str = "DASHSCOPE_API_KEY", connect_timeout: float = 30,
                     read_timeout: float = 600, total_timeout: float = 7200,
                     max_retries: int = 6, max_stream_retries: int = 2,
                     say: Callable[[str], None] = print):
    """`ask(prompt, images) -> str`: the reply's answer, with the model's
    reasoning kept out of it (it is saved in the cache file).

    thinking_budget or reasoning_effort, not both (the API refuses both).
    After every call `ask.last` holds a record of it (cache key, whether it
    came from the cache, finish reason, token usage, seconds); `ask.calls`
    keeps them all. cache_only=True never calls the API: a reply not in the
    cache raises `NotInCache`. The key is read from `api_key_env` only when a
    call actually goes out, so reading back a cached run needs no key.

    A reply cut off by the token limit (finish reason "length") is returned
    as it is; the parser treats a reply with no complete plan as a failed
    attempt, and the finish reason is in the record. Busy or failing servers
    and a connection that drops before any of the reply has come are tried
    again up to `max_retries` times; a stream that breaks after the reply has
    started only `max_stream_retries` times, since each new try is paid for
    again. A stream that breaks after the finish reason has come keeps the
    reply (only the usage may be missing). See ERRORS above for the rest. A
    reply still running after `total_timeout` seconds raises.
    """
    if enable_thinking and thinking_budget and reasoning_effort:
        raise ValueError("give thinking_budget or reasoning_effort, not both: the API refuses both")
    base = base_url.rstrip("/")
    sampling = dict(sampling) if sampling else None
    cache = Path(cache_dir) if cache_dir else None
    if cache:
        cache.mkdir(parents=True, exist_ok=True)
    session = requests.Session()

    def ask(prompt: str, images: Optional[Sequence[str]] = None) -> str:
        if images:
            raise ValueError("this client sends text only; the parser never passes images")
        parts = {"provider": "alibaba", "model": model, "enable_thinking": enable_thinking,
                 "thinking_budget": thinking_budget, "reasoning_effort": reasoning_effort,
                 "max_completion_tokens": max_completion_tokens, "seed": seed,
                 "sampling": sampling, "prompt": prompt}
        key = _key(parts)
        path = cache / f"{key}.json" if cache else None
        if path is not None and path.exists():
            try:
                rec = json.loads(path.read_text())
            except (OSError, ValueError):
                rec = None                       # a half-written file: ask again
            if rec is not None:
                ask.last = _summary(rec, cached=True)
                ask.calls.append(ask.last)
                return rec.get("content") or ""
        if cache_only:
            raise NotInCache(f"no cached reply for this prompt (key {key[:12]}...)")

        body: Dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True, "stream_options": {"include_usage": True},
            "enable_thinking": enable_thinking,
            "max_completion_tokens": max_completion_tokens,
        }
        if enable_thinking and thinking_budget:
            body["thinking_budget"] = thinking_budget
        elif enable_thinking and reasoning_effort:
            body["reasoning_effort"] = reasoning_effort
        if seed is not None:
            body["seed"] = seed
        if sampling:
            body.update(sampling)
        t0 = time.time()
        reply, attempts, request_id = _call(body, t0)
        rec = {
            "key": key, "provider": "alibaba", "model": model,
            "model_returned": reply.get("model_returned", ""), "base_url": base,
            "enable_thinking": enable_thinking, "thinking_budget": thinking_budget,
            "reasoning_effort": reasoning_effort,
            "max_completion_tokens": max_completion_tokens, "seed": seed,
            "sampling": sampling if sampling else "server default",
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "prompt": prompt,
            "content": reply.get("content") or "", "reasoning": reply.get("reasoning") or "",
            "finish_reason": reply.get("finish_reason"),
            "usage": reply.get("usage") or {},
            "response_id": reply.get("id", ""), "request_id": request_id,
            "seconds": round(time.time() - t0, 2), "attempts": attempts,
            "note": reply.get("note", ""),
            "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        if path is not None:
            # a name of its own per process and thread: two writers never share one
            tmp = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
            tmp.write_text(json.dumps(rec))
            os.replace(tmp, path)                # never a half-written cache file
        ask.last = _summary(rec, cached=False)
        ask.calls.append(ask.last)
        return rec["content"]

    def _pause(attempt: int, r=None) -> float:
        wait = r.headers.get("retry-after") if r is not None else None
        try:
            pause = float(wait) if wait else 5.0 * 2 ** (attempt - 1)
        except ValueError:
            pause = 5.0 * 2 ** (attempt - 1)
        return max(0.0, min(_MAX_PAUSE, pause))

    def _call(body: Dict[str, Any], t0: float) -> Tuple[Dict[str, Any], int, str]:
        """POST and read the whole reply, with retries. Returns (reply,
        attempts, request id)."""
        api_key = os.environ.get(api_key_env, "")
        if not api_key:
            raise RuntimeError(f"{api_key_env} is not set: save the Model Studio key "
                               f"(see hprc/README.md) before calling the model")
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json",
                   "Accept": "text/event-stream"}

        def check() -> None:
            if time.time() - t0 > total_timeout:
                raise RuntimeError(f"the reply did not finish within {total_timeout / 60:.0f} minutes")

        attempt, broken = 0, 0
        while True:
            attempt += 1
            r, request_id, rep = None, "", _Reply()
            try:
                r = session.post(f"{base}/chat/completions", headers=headers, json=body,
                                 stream=True, timeout=(connect_timeout, read_timeout))
                if r.status_code != 200:
                    fields, text = _body_error(r)
                    kind = error_kind(fields)
                    if kind == "account":
                        raise _account_error(f"HTTP {r.status_code}: {text}")
                    if kind == "request":
                        raise _refused(f"the API answered {r.status_code}: {text}")
                    busy = r.status_code in _RETRY_STATUS or kind == "passing"
                    if busy and attempt <= max_retries:
                        pause = _pause(attempt, r)
                        say(f"  API answered {r.status_code}; trying again in {pause:.0f}s")
                        time.sleep(pause)
                        continue
                    if busy:
                        raise RuntimeError(f"the API stayed busy or failing after {attempt} tries "
                                           f"(HTTP {r.status_code}): {text}")
                    raise RuntimeError(f"the API answered {r.status_code}: {text}")
                request_id = (r.headers.get("x-request-id")
                              or r.headers.get("x-dashscope-request-id") or "")
                if "text/event-stream" in r.headers.get("content-type", ""):
                    for ev in _events(r.iter_lines(), check):
                        rep.add(ev)
                else:                              # a whole reply, not a stream
                    rep.add(r.json())
                if rep.finish is None:
                    raise _StreamBroke("the stream ended before the model finished")
                return rep.result(), attempt, request_id
            except (requests.RequestException, _StreamBroke) as e:
                if rep.finish is not None:
                    # the reply was complete; only what comes after it was lost
                    return rep.result(f"the stream broke after the reply finished ({type(e).__name__}); "
                                      f"the usage may be missing"), attempt, request_id
                if rep.events:
                    broken += 1
                if attempt > max_retries or broken > max_stream_retries:
                    raise RuntimeError(f"the API call did not complete after {attempt} tries "
                                       f"({broken} broke after the reply had started): {e!r}") from e
                pause = _pause(attempt)
                say(f"  the API call broke ({type(e).__name__}: {str(e)[:160]}); "
                    f"trying again in {pause:.0f}s")
                time.sleep(pause)
                continue
            finally:
                if r is not None:
                    r.close()

    ask.last = None
    ask.calls = []
    return ask


def _summary(rec: Dict[str, Any], cached: bool) -> Dict[str, Any]:
    u = rec.get("usage") or {}
    return {"cache_key": rec.get("key"), "cached": cached,
            "finish_reason": rec.get("finish_reason"), "usage": u,
            "prompt_tokens": u.get("prompt_tokens"),
            "seconds": rec.get("seconds"), "model": rec.get("model"),
            "model_returned": rec.get("model_returned", ""),
            "reasoning_chars": len(rec.get("reasoning") or ""),
            "content_chars": len(rec.get("content") or ""),
            "prompt_sha256": rec.get("prompt_sha256"),
            "response_id": rec.get("response_id", ""), "attempts": rec.get("attempts"),
            "note": rec.get("note", "")}


def cost_usd(calls: Sequence[Dict[str, Any]], model: str = "qwen3.8-max",
             only_new: bool = True) -> float:
    """What these calls cost at the list price (replies read back from the
    reply cache cost nothing again). Input tokens the server read from its
    own cache are priced as cached input; thinking counts as output. A try
    that broke before it finished is billed too, and is not counted here."""
    p_in, p_cached, p_out = PRICES_PER_MTOK.get(model, (0.0, 0.0, 0.0))
    total = 0.0
    for c in calls:
        if only_new and c.get("cached"):
            continue
        u = c.get("usage") or {}
        prompt = int(u.get("prompt_tokens") or 0)
        cached = int((u.get("prompt_tokens_details") or {}).get("cached_tokens") or 0)
        out = int(u.get("completion_tokens") or 0)
        total += ((prompt - cached) * p_in + cached * p_cached + out * p_out) / 1e6
    return round(total, 4)
