"""mrag/vine/alibaba_client.py: Qwen3.8-Max over Model Studio, with the network
faked. Made-up prompts and replies only."""
import json
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import requests  # noqa: E402

from mrag.vine import alibaba_client as al  # noqa: E402


# --------------------------------------------------------------------------- #
# A fake server: each POST takes the next planned answer
# --------------------------------------------------------------------------- #
def sse(*events, done=True):
    """The lines of a server-sent event stream."""
    lines = [": a comment line", ""]
    for e in events:
        lines += [f"data: {json.dumps(e)}", ""]
    if done:
        lines.append("data: [DONE]")
    return [x.encode() for x in lines]


def chunk(content=None, reasoning=None, finish=None, rid="chatcmpl-1"):
    delta = {}
    if content is not None:
        delta["content"] = content
    if reasoning is not None:
        delta["reasoning_content"] = reasoning
    return {"id": rid, "model": "qwen3.8-max", "choices": [{"index": 0, "delta": delta,
                                                             "finish_reason": finish}]}


USAGE = {"prompt_tokens": 1000, "completion_tokens": 300, "total_tokens": 1300,
         "completion_tokens_details": {"reasoning_tokens": 250},
         "prompt_tokens_details": {"cached_tokens": 400}}


def good_stream(text='{"ok": true}', finish="stop"):
    return sse(chunk(reasoning="Let me think. "), chunk(reasoning="Done."),
               chunk(content=text[:5]), chunk(content=text[5:], finish=finish),
               {"id": "chatcmpl-1", "choices": [], "usage": USAGE})


class Resp:
    def __init__(self, status=200, lines=(), body=None, kind="text/event-stream", headers=None,
                 broken_after=None, page=None):
        self.status_code, self._lines, self._body, self._page = status, list(lines), body, page
        self.headers = {"content-type": kind, "x-request-id": "req-9", **(headers or {})}
        self.broken_after, self.closed = broken_after, False

    @property
    def text(self):
        if self._page is not None:
            return self._page
        return json.dumps(self._body) if self._body is not None else "error text"

    def json(self):
        return self._body

    def iter_lines(self):
        for i, x in enumerate(self._lines):
            if self.broken_after is not None and i >= self.broken_after:
                raise requests.exceptions.ChunkedEncodingError("connection broken")
            yield x

    def close(self):
        self.closed = True


class Server:
    def __init__(self, *answers):
        self.answers, self.posts = list(answers), []

    def session(self):
        server = self

        class S:
            def post(self, url, headers=None, json=None, stream=False, timeout=None):
                server.posts.append({"url": url, "headers": headers, "json": json, "stream": stream,
                                     "timeout": timeout})
                a = server.answers.pop(0)
                if isinstance(a, Exception):
                    raise a
                return a
        return S()


class Env:
    """Set environment variables and module attributes; put them back after."""

    def __init__(self, env=None, attrs=()):
        self.env, self.attrs, self.saved, self.saved_attrs = dict(env or {}), list(attrs), {}, []

    def __enter__(self):
        for k, v in self.env.items():
            self.saved[k] = os.environ.get(k)
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        for obj, name, value in self.attrs:
            self.saved_attrs.append((obj, name, getattr(obj, name)))
            setattr(obj, name, value)
        return self

    def __exit__(self, *exc):
        for k, v in self.saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        for obj, name, value in reversed(self.saved_attrs):
            setattr(obj, name, value)


def make(server, **kw):
    sleeps = []
    with Env(attrs=[(al.requests, "Session", server.session)]):
        ask = al.make_ask_alibaba(say=lambda m: None, **kw)
    return ask, sleeps


def quiet_sleep(store):
    return [(al.time, "sleep", lambda s: store.append(s))]


# --------------------------------------------------------------------------- #
def test_a_streamed_reply_is_joined_and_saved_with_its_reasoning():
    server = Server(Resp(lines=good_stream('{"plan": 1}')))
    with tempfile.TemporaryDirectory() as d, Env({"DASHSCOPE_API_KEY": "sk-test"}):
        ask, _ = make(server, cache_dir=d, base_url=al.BASE_URLS["us"])
        out = ask("PROMPT A", [])
        assert out == '{"plan": 1}'                              # the answer only, no reasoning
        post = server.posts[0]
        assert post["url"] == "https://dashscope-us.aliyuncs.com/compatible-mode/v1/chat/completions"
        assert post["headers"]["Authorization"] == "Bearer sk-test" and post["stream"] is True
        body = post["json"]
        assert body["model"] == "qwen3.8-max" and body["messages"] == [{"role": "user", "content": "PROMPT A"}]
        assert body["stream"] is True and body["stream_options"] == {"include_usage": True}
        assert body["enable_thinking"] is True and body["thinking_budget"] == 131072
        assert body["max_completion_tokens"] == 131072 + 32768 and body["seed"] == 42
        for k in ("temperature", "top_p", "top_k", "extra_body", "max_tokens", "reasoning_effort"):
            assert k not in body, k     # the model's own sampling; never effort AND budget
        files = list(Path(d).glob("*.json"))
        assert len(files) == 1
        rec = json.loads(files[0].read_text())
        assert rec["content"] == '{"plan": 1}' and rec["reasoning"] == "Let me think. Done."
        assert rec["finish_reason"] == "stop" and rec["usage"] == USAGE and rec["prompt"] == "PROMPT A"
        assert rec["response_id"] == "chatcmpl-1" and rec["request_id"] == "req-9"
        assert rec["base_url"].startswith("https://dashscope-us") and rec["sampling"] == "server default"
        assert rec["model_returned"] == "qwen3.8-max" and rec["attempts"] == 1
        assert ask.last["cached"] is False and ask.last["prompt_tokens"] == 1000
        assert ask.last["finish_reason"] == "stop" and ask.last["reasoning_chars"] == len("Let me think. Done.")


def test_the_same_prompt_is_read_back_from_the_cache_without_a_key():
    server = Server(Resp(lines=good_stream('{"plan": 2}')))
    with tempfile.TemporaryDirectory() as d:
        with Env({"DASHSCOPE_API_KEY": "sk-test"}):
            ask, _ = make(server, cache_dir=d)
            assert ask("PROMPT B", []) == '{"plan": 2}'
        with Env({"DASHSCOPE_API_KEY": None}):
            again, _ = make(Server(), cache_dir=d)               # no answers: any POST would fail
            assert again("PROMPT B", []) == '{"plan": 2}' and again.last["cached"] is True
            only, _ = make(Server(), cache_dir=d, cache_only=True)
            assert only("PROMPT B", []) == '{"plan": 2}'
            try:
                only("PROMPT C", [])
            except al.NotInCache:
                pass
            else:
                raise AssertionError("cache_only asked the API")
            # a changed setting is a new key: never read from another setting's reply
            other, _ = make(Server(), cache_dir=d, cache_only=True, thinking_budget=65536)
            try:
                other("PROMPT B", [])
            except al.NotInCache:
                pass
            else:
                raise AssertionError("a reply made with another thinking budget was reused")
        assert len(server.posts) == 1


def test_two_writers_of_one_reply_never_share_a_temporary_file():
    """Two workers (threads) get the same prompt at the same time: each saves
    the reply through a temporary file of its own, and both calls succeed."""
    import threading
    barrier = threading.Barrier(2, timeout=30)
    server = Server(Resp(lines=good_stream('{"same": 1}')), Resp(lines=good_stream('{"same": 1}')))
    session = server.session

    def both_at_the_api():
        s = session()
        real = s.post

        def post(*a, **k):
            barrier.wait()                        # both have missed the cache before either saves
            return real(*a, **k)
        s.post = post
        return s
    server.session = both_at_the_api
    moved, real_replace = [], al.os.replace

    def replace(src, dst):
        moved.append(str(src))
        return real_replace(src, dst)
    out, errors = [], []
    with tempfile.TemporaryDirectory() as d, Env({"DASHSCOPE_API_KEY": "k"}, [(al.os, "replace", replace)]):
        asks = [make(server, cache_dir=d)[0] for _ in range(2)]

        def run(a):
            try:
                out.append(a("SAME PROMPT", []))
            except Exception as e:                # noqa: BLE001
                errors.append(e)
        threads = [threading.Thread(target=run, args=(a,)) for a in asks]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == [] and out == ['{"same": 1}'] * 2, errors
        assert len(moved) == 2 and len(set(moved)) == 2, moved
        assert [p.name for p in Path(d).iterdir() if p.suffix == ".tmp"] == []


def test_no_key_is_refused_before_any_call():
    server = Server(Resp(lines=good_stream()))
    with Env({"DASHSCOPE_API_KEY": None}):
        ask, _ = make(server)
        try:
            ask("PROMPT", [])
        except RuntimeError as e:
            assert "DASHSCOPE_API_KEY" in str(e)
        else:
            raise AssertionError("called without a key")
    assert server.posts == []


def test_busy_servers_and_broken_streams_are_tried_again():
    sleeps = []
    server = Server(Resp(status=429, headers={"retry-after": "3"}), Resp(status=503),
                    Resp(lines=good_stream(), broken_after=3),               # the connection drops
                    Resp(lines=sse(chunk(content='{"ok"'), done=True)),       # ends with no finish reason
                    requests.exceptions.ConnectionError("no route"),
                    Resp(lines=sse({"error": {"code": "Throttling", "message": "Requests rate limit exceeded"}})),
                    Resp(lines=good_stream('{"ok": 3}')))
    with Env({"DASHSCOPE_API_KEY": "k"}, quiet_sleep(sleeps)):
        ask, _ = make(server)
        assert ask("PROMPT", []) == '{"ok": 3}'
    assert len(server.posts) == 7 and sleeps[0] == 3.0 and len(sleeps) == 6
    assert ask.last["attempts"] == 7


def _next_job_asks_again(e):
    """What the next parse job does with a plan whose call failed with `e`
    (the parser records it as "the model call failed: <repr>")."""
    sys.path.insert(0, str(REPO / "evaluation"))
    import vine_run as vr
    rec = {"question": "Q", "outcome": "failed", "problems": [[f"the model call failed: {e!r}"]]}
    return vr.plan_needs_retry(rec, "Q")


ACCOUNT, REFUSED = "account or its settings", "refused by the API"


def test_refused_requests_and_account_errors_are_raised_at_once_and_marked_for_the_next_job():
    cases = (
        # the request itself: the next job does not ask again
        (Resp(status=400, body={"error": {"code": "InvalidParameter"}}), REFUSED, False),
        (Resp(status=400, body={"code": "InternalError.Algo.InvalidParameter", "message": "too long"}), REFUSED, False),
        (Resp(status=400, body={"error": {"code": "data_inspection_failed"}}), REFUSED, False),
        (Resp(lines=sse({"code": "InvalidParameter", "message": "bad seed", "request_id": "r"})), REFUSED, False),
        (Resp(lines=sse(chunk(reasoning="long think"),
                        {"code": "DataInspectionFailed", "message": "output inspection"})), REFUSED, False),
        # the account or its settings: fixed by a person, then the next job asks again
        (Resp(status=400, body={"code": "Arrearage", "message": "Access denied, please make sure your "
                                                               "account is in good standing."}), ACCOUNT, True),
        (Resp(status=400, body={"code": "isv.OUT_OF_SERVICE"}), ACCOUNT, True),
        (Resp(status=401, body={"error": {"code": "invalid_api_key"}}), ACCOUNT, True),
        (Resp(status=403, body={"code": "AccessDenied.Unpurchased"}), ACCOUNT, True),
        (Resp(status=404, body={"error": {"code": "model_not_found"}}), ACCOUNT, True),
        (Resp(lines=sse({"error": {"code": "Arrearage", "message": "overdue"}})), ACCOUNT, True),
        # a status not known as busy, with no known code: as it says
        (Resp(status=400, body={"error": {"code": "SomethingNew"}}), "answered 400", False),
        (Resp(status=413, body={"error": {"code": "SomethingNew"}}), "answered 413", True),
    )
    for answer, words, again in cases:
        sleeps = []
        server = Server(answer, Resp(lines=good_stream()))
        with Env({"DASHSCOPE_API_KEY": "k"}, quiet_sleep(sleeps)):
            ask, _ = make(server)
            try:
                ask("PROMPT", [])
            except RuntimeError as e:
                assert words in str(e), (words, str(e))
                assert _next_job_asks_again(e) is again, (words, str(e))
            else:
                raise AssertionError(f"accepted {words}")
        assert len(server.posts) == 1 and sleeps == [], words


def test_a_busy_backend_answering_400_is_tried_again():
    sleeps = []
    # Model Studio sends it under the code InvalidParameter, its own way or the OpenAI way
    server = Server(Resp(status=400, body={"code": "InvalidParameter", "message": "No backend server available"}),
                    Resp(status=400, body={"error": {"code": "invalid_parameter_error",
                                                     "message": "No backend server available"}}),
                    Resp(status=429, headers={"retry-after": "9999"}, body={"code": "Throttling.RateQuota"}),
                    Resp(lines=good_stream('{"ok": 4}')))
    with Env({"DASHSCOPE_API_KEY": "k"}, quiet_sleep(sleeps)):
        ask, _ = make(server)
        assert ask("PROMPT", []) == '{"ok": 4}'
    assert len(server.posts) == 4 and sleeps[2] == 120.0                 # a long Retry-After is capped


def test_a_proxy_error_page_is_not_read_as_an_account_problem():
    """Only a JSON error's code and message are read: a proxy's HTML page that
    happens to say ERR_ACCESS_DENIED is an HTTP status, nothing more."""
    page = Resp(status=403, kind="text/html",
                page="<html><body>ERR_ACCESS_DENIED: access_denied by the proxy</body></html>")
    server = Server(page)
    with Env({"DASHSCOPE_API_KEY": "k"}):
        ask, _ = make(server)
        try:
            ask("PROMPT", [])
        except RuntimeError as e:
            assert "the API answered 403" in str(e) and ACCOUNT not in str(e), str(e)
            assert _next_job_asks_again(e) is True
        else:
            raise AssertionError("accepted a proxy page")


def test_it_gives_up_after_the_retries():
    sleeps = []
    for status, body in ((500, None), (400, {"code": "InvalidParameter", "message": "No backend server available"})):
        server = Server(*[Resp(status=status, body=body) for _ in range(3)])
        with Env({"DASHSCOPE_API_KEY": "k"}, quiet_sleep(sleeps)):
            ask, _ = make(server, max_retries=2)
            try:
                ask("PROMPT", [])
            except RuntimeError as e:
                assert f"stayed busy or failing after 3 tries (HTTP {status})" in str(e)
                assert _next_job_asks_again(e) is True                    # busy is not a refusal
            else:
                raise AssertionError("did not give up")
        assert len(server.posts) == 3
    # the same for a stream that keeps breaking
    server = Server(*[Resp(lines=good_stream(), broken_after=2) for _ in range(3)])
    with Env({"DASHSCOPE_API_KEY": "k"}, quiet_sleep(sleeps)):
        ask, _ = make(server, max_retries=2)
        try:
            ask("PROMPT", [])
        except RuntimeError as e:
            assert "did not complete after 3 tries" in str(e) and _next_job_asks_again(e) is True
        else:
            raise AssertionError("did not give up")
    assert len(server.posts) == 3


def test_a_stream_that_breaks_after_the_reply_started_is_tried_only_twice_more():
    """Each new try is paid for again: after 2, it gives up, even with retries left."""
    sleeps = []
    server = Server(*[Resp(lines=good_stream(), broken_after=4) for _ in range(5)])   # one event, then broken
    with Env({"DASHSCOPE_API_KEY": "k"}, quiet_sleep(sleeps)):
        ask, _ = make(server, max_retries=6)
        try:
            ask("PROMPT", [])
        except RuntimeError as e:
            assert "3 broke after the reply had started" in str(e) and _next_job_asks_again(e) is True
        else:
            raise AssertionError("did not give up")
    assert len(server.posts) == 3


def test_a_stream_that_breaks_after_the_finish_keeps_the_reply():
    lines = good_stream('{"ok": 5}')
    cut = next(i for i, x in enumerate(lines) if b'"usage"' in x)          # broken just before the usage
    server = Server(Resp(lines=lines, broken_after=cut), Resp(lines=good_stream()))
    with tempfile.TemporaryDirectory() as d, Env({"DASHSCOPE_API_KEY": "k"}):
        ask, _ = make(server, cache_dir=d)
        assert ask("PROMPT", []) == '{"ok": 5}' and ask.last["finish_reason"] == "stop"
        assert "broke after the reply finished" in ask.last["note"] and ask.last["usage"] == {}
    assert len(server.posts) == 1                                         # not asked (and paid) again


def test_a_reply_cut_off_by_the_token_limit_is_returned_and_marked():
    server = Server(Resp(lines=sse(chunk(reasoning="a long think"), chunk(content='{"obl', finish="length"),
                                   {"choices": [], "usage": USAGE})))
    with tempfile.TemporaryDirectory() as d, Env({"DASHSCOPE_API_KEY": "k"}):
        ask, _ = make(server, cache_dir=d)
        assert ask("PROMPT", []) == '{"obl'
        assert ask.last["finish_reason"] == "length"
    assert len(server.posts) == 1                                # not asked again: it is a result


def test_a_whole_reply_instead_of_a_stream_is_read_too():
    body = {"id": "x1", "model": "qwen3.8-max",
            "choices": [{"index": 0, "message": {"content": '{"ok": 1}', "reasoning_content": "hm"},
                         "finish_reason": "stop"}], "usage": USAGE}
    server = Server(Resp(body=body, kind="application/json"))
    with tempfile.TemporaryDirectory() as d, Env({"DASHSCOPE_API_KEY": "k"}):
        ask, _ = make(server, cache_dir=d)
        assert ask("PROMPT", []) == '{"ok": 1}'
        rec = json.loads(next(Path(d).glob("*.json")).read_text())
        assert rec["reasoning"] == "hm" and rec["response_id"] == "x1"


def test_a_reply_past_the_time_limit_stops_and_is_not_asked_again():
    sleeps = []
    # a server that only sends keep-alive comments: the clock is read on every line
    for lines in (good_stream(), [b": ping", b"", b": ping", b""]):
        server = Server(Resp(lines=lines), Resp(lines=good_stream()))
        with Env({"DASHSCOPE_API_KEY": "k"}, quiet_sleep(sleeps)):
            ask, _ = make(server, total_timeout=-1)
            try:
                ask("PROMPT", [])
            except RuntimeError as e:
                assert "did not finish within" in str(e)
            else:
                raise AssertionError("ran past the limit")
        assert len(server.posts) == 1


def test_thinking_off_sends_no_budget_and_sampling_is_sent_only_when_given():
    server = Server(Resp(lines=good_stream()), Resp(lines=good_stream()), Resp(lines=good_stream()))
    with Env({"DASHSCOPE_API_KEY": "k"}):
        ask, _ = make(server, enable_thinking=False, max_completion_tokens=512)
        ask("PROMPT", [])
        body = server.posts[0]["json"]
        assert body["enable_thinking"] is False and "reasoning_effort" not in body
        assert "thinking_budget" not in body and body["max_completion_tokens"] == 512
        effort, _ = make(server, thinking_budget=None, reasoning_effort="medium")
        effort("PROMPT", [])
        body = server.posts[1]["json"]
        assert body["reasoning_effort"] == "medium" and "thinking_budget" not in body
        try:
            make(server, thinking_budget=4096, reasoning_effort="low")
        except ValueError:
            pass
        else:
            raise AssertionError("sent a budget and an effort together: the API refuses that")
        ask2, _ = make(server, sampling={"temperature": 0.6, "top_p": 0.95})
        ask2("PROMPT", [])
        body = server.posts[2]["json"]
        assert body["temperature"] == 0.6 and body["top_p"] == 0.95


def test_images_are_refused():
    with Env({"DASHSCOPE_API_KEY": "k"}):
        ask, _ = make(Server())
        try:
            ask("PROMPT", ["/x/fig.png"])
        except ValueError:
            pass
        else:
            raise AssertionError("sent an image")


def test_regions_and_cost():
    assert al.base_url_for("singapore") == "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    assert al.base_url_for(" US ") == "https://dashscope-us.aliyuncs.com/compatible-mode/v1"
    assert al.base_url_for("https://ws1.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1/") == \
        "https://ws1.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"
    for bad in ("", "europe", "http://dashscope-us.aliyuncs.com"):
        try:
            al.base_url_for(bad)
        except ValueError:
            continue
        raise AssertionError(f"accepted region {bad!r}")
    calls = [{"cached": False, "usage": USAGE}, {"cached": True, "usage": USAGE}]
    # (1000 - 400) x $2 + 400 x $0.25 + 300 x $6, per million; the cached reply costs nothing
    assert al.cost_usd(calls) == round((600 * 2.0 + 400 * 0.25 + 300 * 6.0) / 1e6, 4)
    assert al.cost_usd(calls, only_new=False) == round(2 * (600 * 2.0 + 400 * 0.25 + 300 * 6.0) / 1e6, 4)


def test_the_parser_reads_a_plan_from_this_client():
    """The real parser and plan record, with only the network faked: the plan
    comes from `content`, never from the reasoning, and the record keeps the
    token counts (thinking included)."""
    sys.path.insert(0, str(REPO / "evaluation"))
    import parser_check as pc
    from mrag.vine.parser import make_semantic_parser
    plan = {"terminal": "o1", "facts": [],
            "obligations": [{"id": "o1", "type": "classification", "claim": "The made-up panel meets the rule.",
                             "authority": "STANDARD", "requires": [], "evidence_hint": [], "source_chunk": "Z1"}],
            "merges": [], "asked": [{"id": "a1", "ask": "Is the made-up panel right?", "answered_by": ["o1"]}]}
    decoy = json.dumps({**plan, "terminal": "o9"})                          # a draft in the reasoning
    server = Server(Resp(lines=sse(chunk(reasoning="Draft: " + decoy), chunk(content=json.dumps(plan), finish="stop"),
                                   {"choices": [], "usage": USAGE})))
    chunks = [{"chunk_id": "Z1", "section_id": "9Z.01", "content_type": "Standard", "ordinal": 1,
               "text": "A made-up panel shall be blue."}]
    with Env({"DASHSCOPE_API_KEY": "k"}):
        ask, _ = make(server)
        parse = make_semantic_parser(ask, max_attempts=3, fall_back_to_baseline=False,
                                     check_ref=lambda kind, ident: True, tables={})
        spec, rep = parse("Is the made-up panel right?", chunks, "", [])
    assert spec is not None and spec.terminal == "o1" and rep.attempts == 1, rep.problems
    rec = pc.make_record("D1", "Is the made-up panel right?", {"chunks": chunks}, spec, rep, None, 1.0)
    assert rec["completion_tokens"] == 300 and rec["calls"][0]["finish_reason"] == "stop"
    assert rec["calls"][0]["prompt_tokens"] == 1000


if __name__ == "__main__":
    for _name, _f in sorted(globals().items()):
        if _name.startswith("test_") and callable(_f):
            _f()
            print("ok", _name)
    print("ALL ALIBABA CLIENT TESTS PASSED")
