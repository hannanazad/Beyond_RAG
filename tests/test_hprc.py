"""hprc/: the FASTER run. Made-up data only."""
import importlib
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def test_local_data_path_finds_colab_files_under_this_base():
    from mrag.config import CFG
    with tempfile.TemporaryDirectory() as d:
        old = CFG.base_dir
        CFG.base_dir = Path(d)
        try:
            (Path(d) / "figures").mkdir()
            (Path(d) / "figures" / "f.png").write_bytes(b"x")
            colab = "/content/drive/MyDrive/Beyond_RAG/figures/f.png"
            assert CFG.local_data_path(colab) == str(Path(d) / "figures" / "f.png")
            # a path that exists, a path elsewhere, and an empty one are unchanged
            here = str(Path(d) / "figures" / "f.png")
            assert CFG.local_data_path(here) == here
            assert CFG.local_data_path("/elsewhere/f.png") == "/elsewhere/f.png"
            assert CFG.local_data_path("") == ""
        finally:
            CFG.base_dir = old


def test_launch_can_leave_other_servers_running():
    from mrag.vine import vllm_client as vc
    calls = []
    saved = (vc.stop_servers, vc.start_server, vc.wait_until_ready)

    class P:
        pid, returncode = 12345, None
        def poll(self): return None

    try:
        vc.stop_servers = lambda *a, **k: calls.append("stop_all")
        vc.start_server = lambda cmd, log, env=None: P()
        vc.wait_until_ready = lambda *a, **k: 1.0
        vc.launch("vllm", "M", "/tmp/none.log", port=8001, say=lambda m: None, stop_others=False)
        assert calls == []
        vc.launch("vllm", "M", "/tmp/none.log", port=8001, say=lambda m: None)
        assert calls == ["stop_all"]           # the Colab default is unchanged
    finally:
        vc.stop_servers, vc.start_server, vc.wait_until_ready = saved


def test_vllm_pids_are_only_this_users():
    from mrag.vine import vllm_client as vc
    uid = os.getuid()
    for pid in vc._vllm_pids():
        assert Path(f"/proc/{pid}").stat().st_uid == uid


def test_sample_questions_come_from_the_notebook_text_only():
    sys.path.insert(0, str(REPO / "hprc"))
    sys.path.insert(0, str(REPO / "evaluation"))
    V = importlib.import_module("vine_hprc")
    s = V.sample_questions()
    assert sorted(s) == [f"SAMPLE{i:03d}" for i in range(2, 22)]
    assert all(isinstance(v, str) and len(v) > 100 for v in s.values())
