"""Serve an open-weights model with vLLM and call it as `ask(prompt, images)`.

WHY A SEPARATE SERVER
---------------------
The pipeline has one model call site: a function `ask(prompt, images) -> str`
(see `run.make_ask`). This file supplies that function for a model served by
vLLM's OpenAI-compatible server.

The server runs from its OWN Python environment. vLLM needs a newer torch and
transformers than the retrieval stack (BGE-M3, the reranker) is pinned to, and
installing it into the notebook's environment would replace them. A separate
environment and an HTTP call keep the two apart.

REPRODUCIBLE BY CONSTRUCTION
----------------------------
  * one request at a time (`--max-num-seqs 1`), so a reply never depends on
    what else was in the batch;
  * a fixed seed on every request, and the sampling settings the model card
    gives for its thinking mode, written out in full;
  * every reply cached on disk, under a key made from everything that could
    change it: model, revision, prompt, seed, sampling, token limit, reasoning
    effort. Running the same prompt again returns the same reply from the
    cache; a changed prompt is a new key and is sent to the model.

The cache holds the prompt, the reply and the model's reasoning text, so any
plan can be traced back to exactly what the model was shown.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

import requests

__all__ = ["QWEN_THINKING", "serve_command", "start_server", "wait_until_ready",
           "launch", "stop_servers", "log_tail", "make_ask_vllm", "ServerFailed",
           "NotInCache"]

# The model card's settings for thinking mode (Qwen3.8-27B).
QWEN_THINKING: Dict[str, float] = {"temperature": 1.0, "top_p": 0.95, "top_k": 20,
                                   "min_p": 0.0, "presence_penalty": 0.0,
                                   "repetition_penalty": 1.0}


class ServerFailed(RuntimeError):
    """The server process exited or never became ready."""


class NotInCache(LookupError):
    """cache_only=True and the reply is not in the cache."""


# --------------------------------------------------------------------------- #
# 1. The server
# --------------------------------------------------------------------------- #
def serve_command(vllm_bin: str, model: str, served_name: str = "parser",
                  port: int = 8000, max_model_len: int = 40960,
                  gpu_memory_utilization: float = 0.90, seed: int = 42,
                  language_only: str = "flag",
                  extra: Sequence[str] = ()) -> List[str]:
    """The `vllm serve` command. `language_only` is "flag" for
    `--language-model-only` (skip the vision tower), "limits" for the older
    `--limit-mm-per-prompt` form, or "" to load the whole model."""
    cmd = [vllm_bin, "serve", model,
           "--served-model-name", served_name,
           "--host", "127.0.0.1", "--port", str(port),
           "--max-model-len", str(max_model_len),
           "--gpu-memory-utilization", str(gpu_memory_utilization),
           "--max-num-seqs", "1",
           "--seed", str(seed),
           "--reasoning-parser", "qwen3",
           # each request is computed whole: a repeat run must not reuse
           # stored work from an earlier request
           "--no-enable-prefix-caching"]
    if language_only == "flag":
        cmd.append("--language-model-only")
    elif language_only == "limits":
        cmd += ["--limit-mm-per-prompt", '{"image": 0, "video": 0}']
    return cmd + list(extra)


def start_server(cmd: Sequence[str], log_path: str,
                 env: Optional[Dict[str, str]] = None) -> subprocess.Popen:
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    log = open(log_path, "w")
    full_env = dict(os.environ)
    full_env.update(env or {})
    return subprocess.Popen(list(cmd), stdout=log, stderr=subprocess.STDOUT,
                            env=full_env, start_new_session=True)


def log_tail(log_path: str, n: int = 40) -> str:
    try:
        lines = Path(log_path).read_text(errors="replace").splitlines()
    except OSError:
        return "(no log)"
    return "\n".join(lines[-n:])


def wait_until_ready(base_url: str, proc: subprocess.Popen, log_path: str,
                     timeout: float = 2400, every: float = 10,
                     say: Callable[[str], None] = print) -> float:
    """Poll /health until the server answers. Raises ServerFailed, with the
    end of the log, if the process exits or the time runs out."""
    t0 = time.time()
    last = 0.0
    while time.time() - t0 < timeout:
        if proc.poll() is not None:
            raise ServerFailed(f"the vLLM server exited with code {proc.returncode}.\n"
                               f"--- end of {log_path} ---\n{log_tail(log_path)}")
        try:
            if requests.get(f"{base_url}/health", timeout=5).status_code == 200:
                return time.time() - t0
        except requests.RequestException:
            pass
        if time.time() - last > 120:
            last = time.time()
            lines = log_tail(log_path, 1).strip()
            say(f"  ... {time.time() - t0:4.0f}s  {lines[-150:]}")
        time.sleep(every)
    raise ServerFailed(f"the vLLM server was not ready after {timeout:.0f}s.\n"
                       f"--- end of {log_path} ---\n{log_tail(log_path)}")


def _vllm_pids() -> List[int]:
    """Processes that are a vLLM server: an argument list with the `vllm`
    program followed by `serve`, or a process titled `VLLM::...` (the engine
    worker vLLM starts). Matched on whole arguments, never on a substring of
    a command line, so a shell whose command merely mentions the server is
    left alone."""
    me, uid = os.getpid(), os.getuid()
    out: List[int] = []
    for d in Path("/proc").iterdir():
        if not d.name.isdigit() or int(d.name) == me:
            continue
        try:
            if d.stat().st_uid != uid:      # never another user's process (shared HPC nodes)
                continue
        except OSError:
            continue
        try:
            argv = (d / "cmdline").read_bytes().split(b"\0")
        except OSError:
            continue
        argv = [a.decode(errors="replace") for a in argv if a]
        if not argv:
            continue
        server = any((a == "vllm" or a.endswith("/vllm")) and i + 1 < len(argv)
                     and argv[i + 1] == "serve" for i, a in enumerate(argv))
        if server or argv[0].startswith("VLLM::"):
            out.append(int(d.name))
    return out


def stop_servers(say: Callable[[str], None] = print, wait: float = 120) -> None:
    """Stop every vLLM server on this machine and wait for it to go.

    The server runs in its own session so it outlives a cell; for the same
    reason a Colab session restart does not stop it, and it keeps the GPU.
    """
    import signal
    pids = _vllm_pids()
    if not pids:
        return
    say(f"stopping a vLLM server that is still running (pids {pids}) ...")
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
    t0 = time.time()
    while time.time() - t0 < wait and _vllm_pids():
        time.sleep(2)
    for pid in _vllm_pids():
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
    time.sleep(5)                     # let the driver release the memory


_MAX_LEN_RE = re.compile(r"estimated maximum model length is (\d+)")


def stop_server(server: Dict[str, Any], wait: float = 120) -> None:
    """Stop ONE server started by `launch` (and the engine processes it
    started), leaving any other server alone."""
    import signal
    proc = server.get("proc") if isinstance(server, dict) else server
    if proc is None or proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)    # the server runs in its own session
    except OSError:
        proc.terminate()
    try:
        proc.wait(timeout=wait)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            proc.kill()
        proc.wait(timeout=30)


def launch(vllm_bin: str, model: str, log_path: str, port: int = 8000,
           env: Optional[Dict[str, str]] = None, say: Callable[[str], None] = print,
           min_model_len: Optional[int] = None, stop_others: bool = True,
           **kw) -> Dict[str, Any]:
    """Start the server and wait for it. Any server already running is
    stopped first, so the one that answers is the one started here. If this
    vLLM does not know `--language-model-only`, start again with the older
    form of the same setting.

    min_model_len: if the server stops because its working memory cannot hold
    a request of `max_model_len` tokens, vLLM says the largest length that
    fits; the server is started again with that (rounded down to 1,024) as
    long as it is at least `min_model_len`. The length actually used is in the
    result. Returns {"proc", "base_url", "cmd", "seconds", "max_model_len"}.

    stop_others=False: leave other servers running (several servers, one per
    GPU, on one machine); only the server started here is stopped on a retry."""
    base_url = f"http://127.0.0.1:{port}"
    if stop_others:
        stop_servers(say)
    modes = ["flag", "limits"]
    max_len = int(kw.pop("max_model_len", 40960))
    i = 0
    while i < len(modes):
        mode = modes[i]
        cmd = serve_command(vllm_bin, model, port=port, language_only=mode,
                            max_model_len=max_len, **kw)
        say("starting: " + " ".join(cmd))
        proc = start_server(cmd, log_path, env)
        try:
            secs = wait_until_ready(base_url, proc, log_path, say=say)
            if proc.poll() is not None:
                raise ServerFailed("something answered on the port, but the server "
                                   "started here has exited.\n" + log_tail(log_path))
            return {"proc": proc, "base_url": base_url, "cmd": cmd, "seconds": secs,
                    "max_model_len": max_len}
        except ServerFailed as e:
            if not stop_others:
                stop_server({"proc": proc})
            elif proc.poll() is None:
                proc.terminate()
            text = str(e) + "\n" + log_tail(log_path, 400)
            unknown_flag = ("--language-model-only" in text
                            and ("unrecognized" in text or "no such option" in text))
            if mode == "flag" and unknown_flag:
                say("this vLLM has no --language-model-only; using --limit-mm-per-prompt")
                i += 1
                continue
            m = _MAX_LEN_RE.search(text)
            if m and min_model_len:
                fits = (int(m.group(1)) // 1024) * 1024
                if min_model_len <= fits < max_len:
                    say(f"the working memory holds {m.group(1)} tokens, not {max_len}; "
                        f"starting again with max_model_len {fits}")
                    max_len = fits
                    if stop_others:
                        stop_servers(say)
                    continue
            raise
    raise ServerFailed("unreachable")


# --------------------------------------------------------------------------- #
# 2. The call
# --------------------------------------------------------------------------- #
def _key(parts: Dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest()


def make_ask_vllm(base_url: str, served_name: str = "parser", *,
                  model_id: str = "", revision: str = "", engine: str = "",
                  seed: int = 42, max_tokens: int = 16384,
                  sampling: Optional[Dict[str, float]] = None,
                  reasoning_effort: Optional[str] = "medium",
                  enable_thinking: bool = True,
                  cache_dir: Optional[str] = None, timeout: float = 3600,
                  cache_only: bool = False):
    """`ask(prompt, images) -> str`: the reply's content, with the model's
    reasoning kept out of it (the server's reasoning parser separates them).

    After every call `ask.last` holds a record of it (cache key, whether it
    came from the cache, token usage, finish reason, seconds); `ask.calls`
    keeps them all. Images are not sent: the server runs the language model
    only, and the parser never passes any.

    cache_only=True: never call the server. A reply not in the cache raises
    `NotInCache`. Used to read back plans made earlier, exactly as they were.
    """
    sampling = dict(QWEN_THINKING if sampling is None else sampling)
    session = requests.Session()
    cache = Path(cache_dir) if cache_dir else None
    if cache:
        cache.mkdir(parents=True, exist_ok=True)

    def ask(prompt: str, images: Optional[Sequence[str]] = None) -> str:
        key = _key({"model": model_id or served_name, "revision": revision,
                    "engine": engine,
                    "prompt": prompt, "seed": seed, "sampling": sampling,
                    "max_tokens": max_tokens, "reasoning_effort": reasoning_effort,
                    "enable_thinking": enable_thinking})
        path = cache / f"{key}.json" if cache else None
        if path is not None and path.exists():
            try:
                rec = json.loads(path.read_text())
            except (OSError, ValueError):
                rec = None                    # a half-written file: ask again
            if rec is not None:
                ask.last = _summary(rec, cached=True)
                ask.calls.append(ask.last)
                return rec.get("content") or ""

        if cache_only:
            raise NotInCache(f"no cached reply for this prompt (key {key[:12]}...)")
        kwargs: Dict[str, Any] = {"enable_thinking": enable_thinking}
        body: Dict[str, Any] = {
            "model": served_name,
            "messages": [{"role": "user", "content": prompt}],
            "seed": seed, "max_tokens": max_tokens, **sampling,
            "chat_template_kwargs": kwargs,
        }
        if reasoning_effort:
            body["reasoning_effort"] = reasoning_effort
            kwargs["reasoning_effort"] = reasoning_effort

        t0 = time.time()
        r = session.post(f"{base_url}/v1/chat/completions", json=body, timeout=timeout)
        dropped = ""
        if r.status_code == 400 and "reasoning_effort" in r.text and "reasoning_effort" in body:
            # an older server that does not take the top-level field: the
            # template keyword still carries it
            body.pop("reasoning_effort")
            dropped = "top-level reasoning_effort refused by the server; sent in the template only"
            r = session.post(f"{base_url}/v1/chat/completions", json=body, timeout=timeout)
        if r.status_code != 200:
            raise RuntimeError(f"the model server answered {r.status_code}: {r.text[:800]}")
        data = r.json()
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        rec = {
            "key": key, "model": model_id or served_name, "revision": revision,
            "engine": engine,
            "seed": seed, "sampling": sampling, "max_tokens": max_tokens,
            "reasoning_effort": reasoning_effort, "enable_thinking": enable_thinking,
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "prompt": prompt,
            "content": msg.get("content") or "",
            "reasoning": msg.get("reasoning_content") or msg.get("reasoning") or "",
            "finish_reason": choice.get("finish_reason"),
            "usage": data.get("usage") or {},
            "seconds": round(time.time() - t0, 2),
            "created": time.strftime("%Y-%m-%d %H:%M:%S"),
            "note": dropped,
        }
        if path is not None:
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(rec))
            os.replace(tmp, path)             # never a half-written cache file
        ask.last = _summary(rec, cached=False)
        ask.calls.append(ask.last)
        return rec["content"]

    ask.last = None
    ask.calls = []
    return ask


def _summary(rec: Dict[str, Any], cached: bool) -> Dict[str, Any]:
    return {"cache_key": rec.get("key"), "cached": cached,
            "finish_reason": rec.get("finish_reason"),
            "usage": rec.get("usage") or {}, "seconds": rec.get("seconds"),
            "reasoning_chars": len(rec.get("reasoning") or ""),
            "content_chars": len(rec.get("content") or ""),
            "prompt_sha256": rec.get("prompt_sha256"),
            "note": rec.get("note", "")}
