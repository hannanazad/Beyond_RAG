"""Call a Claude model through the Anthropic API as `ask(prompt, images)`.

The checkers (the text and image verifiers) take one function,
`ask(prompt, images) -> str` (see `model_verifiers.py`). This file supplies it
for a Claude model. The parser keeps its own open model (`vllm_client.py`).

REPEATABLE BY CACHING, NOT BY TEMPERATURE
-----------------------------------------
Current Claude models reject any non-default temperature, top_p or top_k
(a 400 error), and their thinking is always adaptive. So a fresh call is not
guaranteed to give the same reply. What makes a run repeatable is the cache:
every reply is saved on disk under a key made from everything that could
change it (model, effort, token limit, prompt, the bytes of every image).
Running again reads the saved reply. The saved file holds the prompt, the
reply, any thinking text the API returns, the stop reason, token usage and
the request id, so every certificate can be traced to exactly what the model
was shown.

WHAT IS SENT
------------
    model, max_tokens (thinking plus reply), output_config.effort,
    one user message: the images first, then the text.
No temperature, top_p, top_k or thinking field is sent. Images larger than
`max_image_edge` pixels on their long side are shrunk to it before sending
(the model would shrink them to the same size itself), and the hash in the
key is of the bytes actually sent.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

import requests

from .vllm_client import NotInCache

__all__ = ["make_ask_anthropic", "cost_usd", "NotInCache", "PRICES_PER_MTOK"]

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
# Base price per million tokens (input, output), from the model's page.
PRICES_PER_MTOK = {"claude-sonnet-5-5": (2.0, 10.0)}
_RETRY_STATUS = {408, 429, 500, 502, 503, 504, 529}
_MIME = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp", "GIF": "image/gif"}
_MAX_IMAGE_BYTES = 4_500_000          # under the API's per-image size limit


def _key(parts: Dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest()


def _prepare_image(path: str, max_edge: int) -> Dict[str, Any]:
    """The image as it will be sent: shrunk if larger than `max_edge` on its
    long side, as PNG (or JPEG if a PNG would be too big)."""
    raw = Path(path).read_bytes()
    data, mime, size = raw, None, None
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(raw))
        size = img.size
        mime = _MIME.get(img.format or "")
        if max(img.size) > max_edge or mime is None or len(raw) > _MAX_IMAGE_BYTES:
            scale = min(1.0, max_edge / float(max(img.size)))
            if scale < 1.0:
                img = img.resize((max(1, round(img.size[0] * scale)),
                                  max(1, round(img.size[1] * scale))), Image.LANCZOS)
            size = img.size
            if img.mode not in ("RGB", "RGBA", "L", "LA"):
                img = img.convert("RGBA" if "transparency" in img.info else "RGB")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            data, mime = buf.getvalue(), "image/png"
            if len(data) > _MAX_IMAGE_BYTES:
                flat = img
                if img.mode in ("RGBA", "LA"):
                    # JPEG has no transparency: put the image on white
                    flat = Image.new("RGB", img.size, "white")
                    flat.paste(img.convert("RGBA"), mask=img.convert("RGBA").split()[-1])
                elif img.mode != "RGB":
                    flat = img.convert("RGB")
                buf = io.BytesIO()
                flat.save(buf, format="JPEG", quality=90)
                data, mime = buf.getvalue(), "image/jpeg"
    except Exception:                       # noqa: BLE001
        # no Pillow, or a file Pillow cannot read: send the bytes as they are
        data, size = raw, None
    if mime is None:
        suffix = Path(path).suffix.lower()
        mime = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
                ".gif": "image/gif"}.get(suffix, "image/png")
    return {"path": str(path), "sha256": hashlib.sha256(data).hexdigest(),
            "media_type": mime, "data": base64.b64encode(data).decode(),
            "sent_size": list(size) if size else None, "bytes": len(data)}


def make_ask_anthropic(model: str = "claude-sonnet-5-5", *, effort: str = "high",
                       max_tokens: int = 32000, cache_dir: Optional[str] = None,
                       cache_only: bool = False, api_key_env: str = "ANTHROPIC_API_KEY",
                       max_image_edge: int = 2576, timeout: float = 900,
                       max_retries: int = 6, say: Callable[[str], None] = print):
    """`ask(prompt, images) -> str`: the reply's text blocks joined.

    After every call `ask.last` holds a record of it (cache key, whether it
    came from the cache, stop reason, token usage, seconds); `ask.calls` keeps
    them all. cache_only=True never calls the API: a reply not in the cache
    raises `NotInCache`. The API key is read from `api_key_env` only when a
    call actually goes to the API, so reading back a cached run needs no key.
    """
    cache = Path(cache_dir) if cache_dir else None
    if cache:
        cache.mkdir(parents=True, exist_ok=True)
    session = requests.Session()

    def ask(prompt: str, images: Optional[Sequence[str]] = None) -> str:
        pictures = [_prepare_image(p, max_image_edge) for p in (images or [])]
        parts: Dict[str, Any] = {"provider": "anthropic", "model": model, "effort": effort,
                                 "max_tokens": max_tokens, "prompt": prompt}
        if pictures:
            parts["images"] = [pic["sha256"] for pic in pictures]
            parts["max_image_edge"] = max_image_edge
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

        api_key = os.environ.get(api_key_env, "")
        if not api_key:
            raise RuntimeError(f"{api_key_env} is not set: put the key in Colab's "
                               f"secrets and load it before calling the model")
        content: List[Dict[str, Any]] = [
            {"type": "image", "source": {"type": "base64", "media_type": pic["media_type"],
                                         "data": pic["data"]}}
            for pic in pictures]
        content.append({"type": "text", "text": prompt})
        body = {"model": model, "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": content}],
                "output_config": {"effort": effort}}
        headers = {"x-api-key": api_key, "anthropic-version": API_VERSION,
                   "content-type": "application/json"}

        t0 = time.time()
        attempt = 0
        while True:
            attempt += 1
            try:
                r = session.post(API_URL, headers=headers, json=body, timeout=timeout)
            except requests.RequestException as e:
                if attempt > max_retries:
                    raise RuntimeError(f"the API could not be reached: {e!r}") from e
                time.sleep(min(120, 5 * 2 ** (attempt - 1)))
                continue
            if r.status_code == 200:
                break
            if r.status_code in _RETRY_STATUS and attempt <= max_retries:
                wait = r.headers.get("retry-after")
                try:
                    pause = float(wait) if wait else min(120, 5 * 2 ** (attempt - 1))
                except ValueError:
                    pause = min(120, 5 * 2 ** (attempt - 1))
                say(f"  API answered {r.status_code}; trying again in {pause:.0f}s")
                time.sleep(pause)
                continue
            raise RuntimeError(f"the API answered {r.status_code}: {r.text[:800]}")

        data = r.json()
        blocks = data.get("content") or []
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        thinking = "\n".join(b.get("thinking", "") for b in blocks
                             if b.get("type") == "thinking" and b.get("thinking"))
        rec = {
            "key": key, "provider": "anthropic", "model": model,
            "model_returned": data.get("model"), "effort": effort, "max_tokens": max_tokens,
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "prompt": prompt,
            "images": [{k: pic[k] for k in ("path", "sha256", "media_type", "sent_size", "bytes")}
                       for pic in pictures],
            "content": text, "thinking": thinking,
            "stop_reason": data.get("stop_reason"),
            "stop_details": data.get("stop_details"),
            "usage": data.get("usage") or {},
            "request_id": r.headers.get("request-id", ""),
            "seconds": round(time.time() - t0, 2), "attempts": attempt,
            "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        if path is not None:
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(rec))
            os.replace(tmp, path)                # never a half-written cache file
        ask.last = _summary(rec, cached=False)
        ask.calls.append(ask.last)
        return text

    ask.last = None
    ask.calls = []
    ask.model = model
    return ask


def _summary(rec: Dict[str, Any], cached: bool) -> Dict[str, Any]:
    u = dict(rec.get("usage") or {})
    # the same field names the rest of the code reads from the vLLM client
    u.setdefault("prompt_tokens", u.get("input_tokens"))
    u.setdefault("completion_tokens", u.get("output_tokens"))
    return {"cache_key": rec.get("key"), "cached": cached,
            "finish_reason": rec.get("stop_reason"), "usage": u,
            "seconds": rec.get("seconds"), "model": rec.get("model_returned") or rec.get("model"),
            "images": len(rec.get("images") or []),
            "thinking_chars": len(rec.get("thinking") or ""),
            "content_chars": len(rec.get("content") or ""),
            "prompt_sha256": rec.get("prompt_sha256"),
            "request_id": rec.get("request_id", "")}


def cost_usd(calls: Sequence[Dict[str, Any]], model: str = "claude-sonnet-5-5",
             only_new: bool = True) -> float:
    """What these calls cost at the base price (cached replies cost nothing again)."""
    p_in, p_out = PRICES_PER_MTOK.get(model, (0.0, 0.0))
    total = 0.0
    for c in calls:
        if only_new and c.get("cached"):
            continue
        u = c.get("usage") or {}
        total += (int(u.get("input_tokens") or u.get("prompt_tokens") or 0) * p_in
                  + int(u.get("output_tokens") or u.get("completion_tokens") or 0) * p_out) / 1e6
    return round(total, 4)
