"""Run the semantic parser on a local open-weights model.

WHY THIS FILE EXISTS
--------------------
`parser.make_semantic_parser(ask)` already holds everything: the prompt, the
repair loop, the verifier assignment rule, the fallback. It needs one thing --
a function that sends a prompt to a model and returns the reply. This supplies
one backed by weights you download and run yourself.

That matters for three claims the paper makes or needs:

  reproducible   temperature 0 and a fixed seed, so the same question yields
                 the same specification on every run. Pin the model digest and
                 the server version and a reviewer can repeat it.
  open           Apache 2.0 or MIT weights, no API, no per-call cost, nothing
                 that can be withdrawn or silently updated underneath the
                 results.
  model-agnostic S3.3 says the framework does not depend on a particular model.
                 Swapping MODEL here is the whole change.

WHAT THIS DOES NOT DO
---------------------
It does not route. The section is chosen by `graph_parser`'s text similarity,
measured at 10/10 on real scenario questions, and handed in. The model is given
the question and that section's text, exactly as S3.1 describes, and asked only
what must be checked and how the checks relate.

It does not decide anything downstream. Everything the model emits passes
`NetworkSpec.problems()`, `instantiate()` and `Network.validate()` before it
reaches the executor, and a verifier it proposes is discarded in favour of the
rule in `parser.assign_verifier`.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Sequence

import requests

from .parser import make_semantic_parser

# Set to any model your server has pulled. gpt-oss-120b is the strongest that
# fits one 80 GB card; gpt-oss-20b is the same family at 16 GB.
MODEL = os.environ.get('VINE_PARSER_MODEL', 'gpt-oss:120b')
HOST = os.environ.get('VINE_OLLAMA_HOST', 'http://127.0.0.1:11434')
SEED = 42
NUM_CTX = 32768          # the prompt carries a whole section's text


def make_ask(model: str = None, host: str = None, seed: int = SEED,
             num_ctx: int = NUM_CTX, timeout: int = 900):
    """An `ask(prompt, images) -> str` for `make_semantic_parser`.

    Temperature is pinned at 0 and the seed is fixed, so two runs of the same
    question return the same text. That is deterministic on one stack; change
    the GPU, driver or server version and floating-point ordering can still
    shift a token, so the versions are what a reviewer must be given.
    """
    model = model or MODEL
    host = (host or HOST).rstrip('/')

    def ask(prompt: str, images: Sequence[str] = ()) -> str:
        body = {
            'model': model,
            'prompt': prompt,
            'stream': False,
            'options': {'temperature': 0, 'seed': seed, 'num_ctx': num_ctx,
                        'top_p': 1.0, 'top_k': 1},
        }
        if images:
            body['images'] = list(images)
        r = requests.post(f'{host}/api/generate', json=body, timeout=timeout)
        r.raise_for_status()
        return r.json().get('response', '')

    return ask


def section_chunks(gp, section_id: str, limit: int = 60) -> List[Dict[str, Any]]:
    """The section's text, shaped as the chunks the parser prompt expects.

    The parser only ever cites a chunk_id it was given -- `read_spec` rejects
    any evidence id outside `allowed` -- so this is also what bounds the
    model's citations to real provisions.
    """
    out: List[Dict[str, Any]] = []
    for nid in gp.by_section.get(section_id, [])[:limit]:
        node = gp.N[nid]
        if node.kind not in ('SENTENCE', 'NOTE'):
            continue
        out.append({'chunk_id': nid,
                    'section_id': node.section,
                    'rule_type': node.authority or 'SUPPORT',
                    'text': node.text or ''})
    return out


def parse_question(gp, question: str, ask=None, k_sections: int = 1):
    """Route with the graph, then parse with the model.

    Returns (spec, report, sections) so the caller can see which sections the
    router chose -- a wrong section makes a correct parse impossible, and the
    two failures should never be reported as one.
    """
    ranked, _ = gp.parse_ranked(question, k=k_sections)
    sections = [c.section for c in ranked]
    if not sections:
        return None, None, []
    chunks: List[Dict[str, Any]] = []
    for sec in sections[:k_sections]:
        chunks.extend(section_chunks(gp, sec))
    parse = make_semantic_parser(ask or make_ask())
    spec, report = parse(question, chunks, sections[0])
    return spec, report, sections


# ---------------------------------------------------------------------------
# API-backed parsers.
#
# Same contract as make_ask: a callable taking (prompt, images) and returning
# the reply as text. The point is not convenience -- it is S3.3. A framework
# that only works on one model family has not been shown to be model-agnostic,
# and two families agreeing is the evidence for that claim.
#
# These are not reproducible in the way the local path is. A hosted model can
# be updated underneath a result without notice, so record the date and the
# exact model string with any number taken from them.
# ---------------------------------------------------------------------------

def make_ask_anthropic(model: str = 'claude-sonnet-4-5', max_tokens: int = 4096,
                       timeout: int = 300):
    """An `ask` backed by the Anthropic API. Needs ANTHROPIC_API_KEY."""
    key = os.environ.get('ANTHROPIC_API_KEY')
    if not key:
        raise RuntimeError('ANTHROPIC_API_KEY is not set')

    def ask(prompt: str, images: Optional[Sequence] = None) -> str:
        r = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers={'x-api-key': key, 'anthropic-version': '2023-06-01',
                     'content-type': 'application/json'},
            json={'model': model, 'max_tokens': max_tokens,
                  'temperature': 0,
                  'messages': [{'role': 'user', 'content': prompt}]},
            timeout=timeout)
        r.raise_for_status()
        blocks = r.json().get('content', [])
        return '\n'.join(b.get('text', '') for b in blocks if b.get('type') == 'text')

    return ask


def make_ask_dashscope(model: str = 'qwen-max', max_tokens: int = 4096,
                       timeout: int = 300):
    """An `ask` backed by DashScope (Qwen). Needs DASHSCOPE_API_KEY.

    Uses the OpenAI-compatible endpoint, so the same function serves any
    provider that speaks that shape by changing `base`.
    """
    key = os.environ.get('DASHSCOPE_API_KEY')
    if not key:
        raise RuntimeError('DASHSCOPE_API_KEY is not set')
    base = os.environ.get(
        'VINE_DASHSCOPE_BASE',
        'https://dashscope-intl.aliyuncs.com/compatible-mode/v1')

    def ask(prompt: str, images: Optional[Sequence] = None) -> str:
        r = requests.post(
            f'{base}/chat/completions',
            headers={'Authorization': f'Bearer {key}',
                     'Content-Type': 'application/json'},
            json={'model': model, 'max_tokens': max_tokens,
                  'temperature': 0, 'seed': SEED,
                  'messages': [{'role': 'user', 'content': prompt}]},
            timeout=timeout)
        r.raise_for_status()
        return r.json()['choices'][0]['message']['content'] or ''

    return ask
