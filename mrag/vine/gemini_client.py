"""The parser's `ask(prompt, images) -> str` on Google's Gemini API (the
gemini_test branch: Gemini 4 Argon writes the plans instead of Qwen).

The same interface as mrag/vine/vllm_client.make_ask_vllm, so the parser,
its repair loop and the plan records are unchanged:
  - `ask(prompt, [])` returns the reply's text (the model's thinking kept out);
  - `ask.last` is a record of the call (cache key, cached or not, finish
    reason, token usage, seconds); `ask.calls` keeps them all.

Every reply is saved in `cache_dir`, one JSON file per prompt (with the
prompt, the reply, the thought summary, the usage, the response id and the
model version), so a plan can be read back and audited exactly as it was.
Gemini 4 takes no temperature, top_p or seed (they are accepted and ignored),
so nothing of the kind is sent.

Plain HTTPS with `requests`: no new package. The key is read from the
GEMINI_API_KEY environment variable and sent in a header, never in a URL, a
log or a cache file.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Sequence

API_ROOT = "https://generativelanguage.googleapis.com/v1beta"
# HTTP answers worth asking again: rate limit and passing server trouble
RETRY_STATUS = (429, 500, 502, 503, 504)
# a lost connection or a timeout on our side: Google may have finished (and billed)
# the call, so it is asked again only this many times in all
MAX_TRIES_NO_ANSWER = 3


def _refuses_output_cap(status, text) -> bool:
    """A 400 about the output cap, in either spelling Google uses."""
    t = (text or "").lower()
    return status == 400 and ("maxoutputtokens" in t or "max_output_tokens" in t)


def _wait_asked(r, text) -> float:
    """Seconds the API asks us to wait: the Retry-After header, or the
    RetryInfo "retryDelay" ("45s") in the error body; 0 when neither."""
    try:
        after = float((getattr(r, "headers", None) or {}).get("Retry-After") or 0)
    except (TypeError, ValueError):
        after = 0.0
    m = re.search(r'"retryDelay"\s*:\s*"([0-9.]+)s"', text or "")
    if m:
        after = max(after, float(m.group(1)))
    return after


def output_token_limit(model: str = "gemini-4-argon", api_key: Optional[str] = None,
                       get: Optional[Callable[..., Any]] = None, timeout: float = 60) -> Optional[int]:
    """The model's own output limit (`outputTokenLimit` of GET models/MODEL), or
    None when it cannot be read."""
    key = api_key if api_key is not None else os.environ.get("GEMINI_API_KEY", "")
    if get is None:
        import requests
        get = requests.get
    try:
        r = get(f"{API_ROOT}/models/{model}", headers={"x-goog-api-key": key}, timeout=timeout)
        if r.status_code != 200:
            return None
        n = (r.json() or {}).get("outputTokenLimit")
        return int(n) if n else None
    except Exception:                                            # noqa: BLE001
        return None
FINISH = {"STOP": "stop", "MAX_TOKENS": "length"}


class GeminiError(RuntimeError):
    pass


def _key(d: Dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(d, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def request_body(prompt: str, thinking_level: str, max_tokens: int) -> Dict[str, Any]:
    """The generateContent body: the prompt as one user turn, the thinking
    level, the output cap (thinking counts in it) and the thought summary."""
    return {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": int(max_tokens),
            "thinkingConfig": {"thinkingLevel": thinking_level, "includeThoughts": True},
        },
    }


def read_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """{content, reasoning, finish_reason, usage, response_id, model_version}
    from a generateContent reply. A refused prompt raises GeminiError."""
    cands = data.get("candidates") or []
    if not cands:
        fb = data.get("promptFeedback") or {}
        raise GeminiError(f"Gemini returned no answer (prompt feedback: {json.dumps(fb)[:400]})")
    c = cands[0] or {}
    parts = ((c.get("content") or {}).get("parts")) or []
    text = "".join(p.get("text") or "" for p in parts if isinstance(p, dict) and not p.get("thought"))
    thoughts = "".join(p.get("text") or "" for p in parts if isinstance(p, dict) and p.get("thought"))
    raw_finish = str(c.get("finishReason") or "")
    um = data.get("usageMetadata") or {}
    out_tokens = int(um.get("candidatesTokenCount") or 0)
    think_tokens = int(um.get("thoughtsTokenCount") or 0)
    usage = {"prompt_tokens": int(um.get("promptTokenCount") or 0),
             # as the Qwen records count it: thinking and reply together
             "completion_tokens": out_tokens + think_tokens,
             "thinking_tokens": think_tokens, "reply_tokens": out_tokens,
             "cached_tokens": int(um.get("cachedContentTokenCount") or 0),
             "total_tokens": int(um.get("totalTokenCount") or 0)}
    return {"content": text, "reasoning": thoughts,
            "finish_reason": FINISH.get(raw_finish, raw_finish.lower() or None),
            "finish_reason_raw": raw_finish, "usage": usage,
            "response_id": data.get("responseId"), "model_version": data.get("modelVersion")}


def make_ask_gemini(model: str = "gemini-4-argon", *, thinking_level: str = "high",
                    max_tokens: int = 65536, fallback_max_tokens: int = 32768,
                    cache_dir: Optional[str] = None, api_key: Optional[str] = None,
                    timeout: float = 1800, max_tries: int = 8,
                    post: Optional[Callable[..., Any]] = None, sleep: Callable[[float], None] = time.sleep,
                    cache_only: bool = False):
    """`ask(prompt, images) -> str` on Gemini. `post` and `sleep` are for tests."""
    key = api_key if api_key is not None else os.environ.get("GEMINI_API_KEY", "")
    if not key and not cache_only:
        raise GeminiError("no Gemini key: set GEMINI_API_KEY (the job reads it from $VINE_HOME/gemini_key)")
    if post is None:
        import requests
        session = requests.Session()
        post = session.post
    cache = Path(cache_dir) if cache_dir else None
    if cache:
        cache.mkdir(parents=True, exist_ok=True)
    url = f"{API_ROOT}/models/{model}:generateContent"
    state = {"max_tokens": int(max_tokens)}

    def cache_key(prompt: str) -> str:
        # the output cap in force is part of the key: a reply made with a smaller cap
        # is never reused for a larger one
        return _key({"api": "gemini", "model": model, "prompt": prompt,
                     "thinking_level": thinking_level, "max_tokens": state["max_tokens"]})

    def ask(prompt: str, images: Optional[Sequence[str]] = None) -> str:
        if images:
            raise GeminiError("the Gemini parser takes text only (the parser never passes images)")
        ckey = cache_key(prompt)
        path = cache / f"{ckey}.json" if cache else None
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
            raise GeminiError(f"no cached reply for this prompt (key {ckey[:12]}...)")

        t0 = time.time()
        note = ""
        tries = no_answer = 0
        while True:
            tries += 1
            body = request_body(prompt, thinking_level, state["max_tokens"])
            r = None
            try:
                r = post(url, json=body, timeout=timeout,
                         headers={"x-goog-api-key": key, "Content-Type": "application/json"})
                status, text = r.status_code, r.text
            except Exception as e:                                # noqa: BLE001
                status, text = None, type(e).__name__ + ": " + str(e)[:300]
            if status == 200:
                break
            if _refuses_output_cap(status, text) and state["max_tokens"] > fallback_max_tokens:
                note = (f"an output cap of {state['max_tokens']} was refused; "
                        f"using {fallback_max_tokens} from now on")
                state["max_tokens"] = int(fallback_max_tokens)
                continue
            if status is None:
                no_answer += 1
            if ((status in RETRY_STATUS and tries < max_tries)
                    or (status is None and no_answer < MAX_TRIES_NO_ANSWER and tries < max_tries)):
                wait = min(300.0, 15.0 * (2 ** (tries - 1))) * (0.8 + 0.4 * random.random())
                after = _wait_asked(r, text)
                sleep(min(600.0, max(wait, after)))
                continue
            raise GeminiError(f"Gemini answered {status} after {tries} tries: {(text or '')[:800]}")

        data = r.json()
        got = read_response(data)
        ckey = cache_key(prompt)                 # the cap in force now (after any fallback)
        path = cache / f"{ckey}.json" if cache else None
        rec = {"key": ckey, "api": "gemini", "model": model, "thinking_level": thinking_level,
               "max_tokens": state["max_tokens"], "max_tokens_asked": int(max_tokens),
               "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(), "prompt": prompt,
               **got, "seconds": round(time.time() - t0, 2), "tries": tries,
               "created": time.strftime("%Y-%m-%d %H:%M:%S"), "note": note}
        if path is not None:
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(rec))
            os.replace(tmp, path)                # never a half-written cache file
        ask.last = _summary(rec, cached=False)
        ask.calls.append(ask.last)
        return rec["content"]

    ask.last = None
    ask.calls = []
    return ask


def _summary(rec: Dict[str, Any], cached: bool) -> Dict[str, Any]:
    return {"cache_key": rec.get("key"), "cached": cached, "model": rec.get("model"),
            "model_version": rec.get("model_version"), "response_id": rec.get("response_id"),
            "finish_reason": rec.get("finish_reason"), "finish_reason_raw": rec.get("finish_reason_raw"),
            "usage": rec.get("usage") or {}, "seconds": rec.get("seconds"), "tries": rec.get("tries"),
            "max_tokens": rec.get("max_tokens"),
            "prompt_tokens": (rec.get("usage") or {}).get("prompt_tokens"), "prompt_tokens_how": "gemini",
            "reasoning_chars": len(rec.get("reasoning") or ""),
            "content_chars": len(rec.get("content") or ""),
            "prompt_sha256": rec.get("prompt_sha256"), "note": rec.get("note", "")}
