"""compare40/qwen_local.py -- the answer model on our own vLLM server (Qwen3.8-27B on FASTER).

Used by run_vine_rag.py only when it is given --local-server (run_qwen_rag.py does that).
Without --local-server this file is not imported, and run_vine_rag.py runs as before.

GEMS-RAG's answer step sends every model whose name does not start with "claude",
"gemini" or "gemma" to an OpenAI-style server (its "dashscope" provider). Here that
server is our own vLLM server on the same node. This is set in memory only: no file
of GEMS-RAG is changed, and nothing is sent off the node.

The request is GEMS-RAG's own for this kind of server: its prompt and images as one user
message, text first, then the images. (For Claude, GEMS-RAG puts the images first; the
prompt text and the image files are the same.) This file adds only the settings the model runs
with -- the same ones the VINE parser uses with this model (hprc/vine_hprc.py):
  - thinking on, reasoning effort "xhigh" (also the model's own default);
  - the model card's sampling for thinking (vllm_client.QWEN_THINKING);
  - seed 42.
The output limit is all the room the server's window leaves after the prompt, so the
limit never cuts the model's thinking short. (Claude's limit of 16,000, then 32,000,
was never reached: its longest VINE-as-RAG answer used 2,748 tokens.) The prompt is
measured by the server first (a 1-token request), so the limit is exact.

A reply cut off at the window is not asked again: the same seed gives the same reply.
GEMS-RAG's own retry with a larger limit is switched off for the same reason.
"""
from __future__ import annotations

import importlib.util
import re
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
EFFORT = "xhigh"
SEED = 42
MARGIN = 512                 # tokens left free under the window
MIN_ROOM = 8192              # less room than this for thinking and the answer: not asked
TIMEOUT_S = 2 * 3600         # one reply may take long (about 39 tokens a second on an A100;
                             # a full 80,000-token window is about 35 minutes)


def vine_vllm_client():
    """VINE's mrag/vine/vllm_client.py, loaded from its file (in this process the name
    `mrag` is GEMS-RAG's package, so VINE's cannot be imported by name)."""
    name = "vine_vllm_client"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, REPO / "mrag" / "vine" / "vllm_client.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def settings() -> Dict[str, Any]:
    """What is sent with every request, besides GEMS-RAG's prompt and images."""
    return {"sampling": dict(vine_vllm_client().QWEN_THINKING), "seed": SEED,
            "chat_template_kwargs": {"enable_thinking": True, "reasoning_effort": EFFORT},
            "max_tokens": "the room the window leaves after the prompt (window - prompt - "
                          f"{MARGIN}); not asked if under {MIN_ROOM}",
            "gems_rag_truncation_retry": False, "max_inline_image_bytes": "256 MB (GEMS-RAG's 18 MB is DashScope's)",
            "timeout_s": TIMEOUT_S}


class PromptTooLong(RuntimeError):
    """The prompt leaves too little room in the server's window."""


_INPUT_TOKENS = (re.compile(r"(\d+)\s+in the messages"), re.compile(r"(\d+)\s+input tokens"),
                 re.compile(r"prompt \(length (\d+)\)"), re.compile(r"(\d+)\s+prompt tokens"))


def input_tokens_from_error(text: str) -> Optional[int]:
    """The prompt's length in tokens, from a vLLM 'too long' error message (several forms)."""
    for rx in _INPUT_TOKENS:
        m = rx.search(text or "")
        if m:
            return int(m.group(1))
    return None


def _reasoning_text(message: Any) -> str:
    for k in ("reasoning_content", "reasoning"):
        v = getattr(message, k, None)
        if isinstance(v, str) and v:
            return v
    extra = getattr(message, "model_extra", None) or {}
    for k in ("reasoning_content", "reasoning"):
        v = extra.get(k)
        if isinstance(v, str) and v:
            return v
    return ""


def _usage(resp: Any) -> Dict[str, Any]:
    u = getattr(resp, "usage", None)
    if u is None:
        return {}
    if isinstance(u, dict):
        return dict(u)
    dump = getattr(u, "model_dump", None)
    if callable(dump):
        try:
            return dict(dump())
        except Exception:                                   # noqa: BLE001
            pass
    return {k: getattr(u, k) for k in ("prompt_tokens", "completion_tokens", "total_tokens")
            if getattr(u, k, None) is not None}


class LocalServer:
    """Stands in for the OpenAI client GEMS-RAG makes for the "dashscope" provider:
    GEMS-RAG calls `.chat.completions.create(model=..., messages=..., max_tokens=...)`.
    Every call is kept in `.calls` (settings, tokens, finish reason, seconds) and its
    reasoning text in `.reasoning`."""

    def __init__(self, base_url: str, max_len: int) -> None:
        import openai
        self.openai = openai
        self.base_url = base_url.rstrip("/")
        self.max_len = int(max_len)
        self.client = openai.OpenAI(api_key="local-vllm", base_url=self.base_url,
                                    timeout=TIMEOUT_S, max_retries=0)
        self.sampling = dict(vine_vllm_client().QWEN_THINKING)
        self.calls: List[Dict[str, Any]] = []
        self.reasoning: List[str] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def _send(self, model: str, messages: list, max_tokens: int):
        s = self.sampling
        return self.client.chat.completions.create(
            model=model, messages=messages, max_tokens=int(max_tokens), seed=SEED,
            temperature=s["temperature"], top_p=s["top_p"], presence_penalty=s["presence_penalty"],
            extra_body={"top_k": s["top_k"], "min_p": s["min_p"],
                        "repetition_penalty": s["repetition_penalty"],
                        "chat_template_kwargs": {"enable_thinking": True, "reasoning_effort": EFFORT}})

    def create(self, **request: Any):
        request = dict(request)
        gems_max_tokens = request.pop("max_tokens", None)   # replaced by the room the window leaves
        model, messages = request.pop("model"), request.pop("messages")
        if request:
            raise ValueError(f"GEMS-RAG sent fields this stand-in does not know: {sorted(request)}")
        call: Dict[str, Any] = {"gems_rag_max_tokens": gems_max_tokens, "window": self.max_len,
                                "started": time.strftime("%Y-%m-%d %H:%M:%S")}
        self.calls.append(call)
        t0 = time.time()
        # 1. the prompt's exact length, images included, as the server counts it
        n = None
        try:
            n = int(_usage(self._send(model, messages, 1)).get("prompt_tokens") or 0) or None
            call["prompt_tokens_from"] = "server (1-token request)"
        except self.openai.BadRequestError as e:
            n = input_tokens_from_error(str(e))
            call["prompt_tokens_from"] = "server error message"
            if n is None:
                call["error"] = f"BadRequestError: {str(e)[:600]}"
                raise
        if n is None:
            raise RuntimeError("the server did not say how long the prompt is (no usage.prompt_tokens)")
        room = self.max_len - n - MARGIN
        call.update({"prompt_tokens": n, "max_tokens": room})
        if room < MIN_ROOM:
            call["error"] = "prompt too long for the window"
            raise PromptTooLong(f"the prompt has {n:,} tokens; the server's window of {self.max_len:,} leaves "
                                f"{max(room, 0):,} for thinking and the answer (at least {MIN_ROOM:,} needed)")
        # 2. the answer, with all the room that is left
        try:
            resp = self._send(model, messages, room)
        except self.openai.BadRequestError as e:          # the server counts differently: once more, exactly
            n2 = input_tokens_from_error(str(e))
            if n2 is None or n2 == n:
                call["error"] = f"BadRequestError: {str(e)[:600]}"
                raise
            room = self.max_len - n2 - MARGIN
            call.update({"prompt_tokens": n2, "max_tokens": room, "lowered_after_error": True})
            if room < MIN_ROOM:
                call["error"] = "prompt too long for the window"
                raise PromptTooLong(f"the prompt has {n2:,} tokens; too long for the window of {self.max_len:,}")
            resp = self._send(model, messages, room)
        choice = (getattr(resp, "choices", None) or [None])[0]
        message = getattr(choice, "message", None)
        text = _reasoning_text(message) if message is not None else ""
        call.update({"finish_reason": getattr(choice, "finish_reason", None), "usage": _usage(resp),
                     "reasoning_chars": len(text),
                     "answer_chars": len(getattr(message, "content", None) or "") if message is not None else 0,
                     "seconds": round(time.time() - t0, 1)})
        self.reasoning.append(text)
        return resp

    def transient(self, err: BaseException) -> bool:
        """Worth asking again: the server could not be reached or failed. Not a reply that
        was cut off, empty or too long -- the same seed would give the same again."""
        o = self.openai
        if isinstance(err, o.APITimeoutError):              # 2 hours on one reply: do not wait again
            return False
        return isinstance(err, (o.APIConnectionError, o.InternalServerError, o.RateLimitError))


def use_local_server(CFG, VLM_PROVIDERS: dict, provider_of_model, model: str, base_url: str) -> None:
    """Point GEMS-RAG's OpenAI-style provider at our server, in memory only. Called before
    the answer model is loaded."""
    import os
    assert provider_of_model(model) == "dashscope", \
        f"{model!r} would not go through GEMS-RAG's OpenAI-style path (a claude/gemini/gemma name)"
    VLM_PROVIDERS["dashscope"]["base_url"] = base_url
    os.environ["DASHSCOPE_API_KEY"] = "local-vllm"     # never a real key: nothing leaves the node
    CFG.api_base_url = base_url
    CFG.api_retry_on_truncation = False
    # GEMS-RAG's 18 MB limit on the images of one request is DashScope's; our own server
    # takes the same images Claude was sent (Claude's path has no such limit)
    CFG.api_max_inline_image_bytes = max(int(getattr(CFG, "api_max_inline_image_bytes", 0) or 0), 256 * 1024 * 1024)
