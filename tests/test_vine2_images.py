"""vine2 on VINE's evidence with more figure pictures (MAX_IMAGES): offline tests.

The writer (compare40/run_qwen_rag.py) and the checker (vine2/check.py) both take
--max-images; the launcher (vine2/run_vine2_grace.sh) passes one number to both jobs. With
the default (4) nothing changes. Every question, piece and figure here is invented ("zorb
markers"). No GPU, no API, no data files of the project.

Run:  $RETR_ENV/bin/python tests/test_vine2_images.py   ->  "all vine2 picture checks passed"
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
from PIL import Image  # noqa: E402

from vine2 import check  # noqa: E402

TMP = Path(tempfile.mkdtemp(prefix="vine2_images_"))
FIGS = TMP / "figs"
FIGS.mkdir()
paths = []
for j in range(13):
    p = FIGS / f"zorb_{j:02d}.png"
    Image.new("RGB", (120 + j, 80), (j, j, j)).save(p)
    paths.append(str(p))
ENTRY = {"question": "Zorb?",
         "chunks": [{"chunk_id": "MUTCD11e_9Z01_Standard_02", "content_type": "Standard", "section_id": "9Z.01",
                     "ordinal": 2, "section_title": "Zorb Markers", "page_printed": 12,
                     "text": "Zorb markers shall be at least 30 inches wide on blip lanes."}],
         "figures": [{"figure_id": f"Figure 9Z-{j}", "caption": f"zorb figure {j}", "image_paths": [p]}
                     for j, p in enumerate(paths)]}

# ---- 1. the checker sees the pictures the writer saw, up to the limit
assert check.MAX_IMAGES == 4
assert check.image_list(ENTRY, {"images": paths}) == paths[:4], "default: as before"
assert check.image_list(ENTRY, {"images": paths}, 20) == paths
assert check.image_list(ENTRY, {"images": paths[:6]}, 20) == paths[:6], "never more than the writer was shown"
assert check.image_list(ENTRY, None) == paths[:4] and check.image_list(ENTRY, None, 20) == paths
print("1. image_list: ok")

# ---- 2. a JPEG copy of a big figure picture (run_vine_rag.fit_sizes) keeps its figure's id
jdir = TMP / "out" / "figure_jpeg"
jpg = jdir / f"zorb_00_{'0123456789abcdef'}.jpg"
assert check.image_ids(ENTRY, [str(jpg), paths[1], paths[2]]) == ["Figure 9Z-0", "Figure 9Z-1", "Figure 9Z-2"]
assert check.image_ids(ENTRY, [str(TMP / "elsewhere" / "zorb_00_0123456789abcdef.jpg")]) == ["zorb_00_0123456789abcdef"]
assert check.image_ids(ENTRY, [str(jdir / "zorb_00.jpg")]) == ["zorb_00"], "only <stem>_<16 hex>.jpg is a copy"
print("2. image_ids: ok")


# ---- 3. one question: the pictures reach the checker's call
class Ask:
    def __init__(self):
        self.seen, self.calls, self.last = [], [], None

    def __call__(self, prompt, images=None):
        self.seen.append((prompt, list(images or [])))
        raise RuntimeError("no API in the tests")


class FakeChecker:
    model = "checker-x"

    def __init__(self):
        self.a = Ask()

    def ask(self):
        return self.a

    @staticmethod
    def cost_usd(calls, model):
        return 0.0


DRAFT = ("Direct Answer: Zorb markers must be at least 30 inches wide.\n\nStandards (shall):\n"
         "- Section 9Z.01 paragraph 2: Zorb markers shall be at least 30 inches wide on blip lanes.\n")
draft = {"answer": DRAFT, "model_id": "writer-x", "prompt_sha256": "p", "images": paths}
fc = FakeChecker()
rec = check.check_one("Z1", "Zorb?", ENTRY, draft, fc, True)
assert rec["images"] == paths[:4] and fc.a.seen[0][1] == paths[:4], "default: 4, as before"
assert "Attached images, in order: Figure 9Z-0, Figure 9Z-1, Figure 9Z-2, Figure 9Z-3." in fc.a.seen[0][0]
fc = FakeChecker()
rec = check.check_one("Z1", "Zorb?", ENTRY, draft, fc, True, 20)
assert rec["images"] == paths and fc.a.seen[0][1] == paths
assert "Attached images, in order: " + ", ".join(f"Figure 9Z-{j}" for j in range(13)) + "." in fc.a.seen[0][0]
print("3. check_one: ok")

# ---- 4. the checker's command line: bounds, the setting in its code fingerprint and manifest
d = TMP / "run"
d.mkdir()
(d / "kq.json").write_text(json.dumps({"Z1": ENTRY}))
(d / "q.json").write_text(json.dumps({"Z1": "Zorb?"}))
(d / "drafts.jsonl").write_text(json.dumps(dict(draft, question_id="Z1", question="Zorb?", status="ok",
                                                kq_file="kq.json")) + "\n")
real = check.Checker
check.Checker = lambda *a, **k: FakeChecker()
argv = sys.argv
try:
    base = ["check.py", "--kq", str(d / "kq.json"), "--questions", str(d / "q.json"), "--drafts",
            str(d / "drafts.jsonl"), "--workers", "1"]
    for bad in ("0", "21"):
        sys.argv = base + ["--tag", "bad", "--out", str(d / "bad"), "--max-images", bad]
        assert check.main() == 1 and not (d / "bad" / "final.jsonl").exists()
    sys.argv = base + ["--tag", "t4", "--out", str(d / "o4")]
    check.main()
    sys.argv = base + ["--tag", "t20", "--out", str(d / "o20"), "--max-images", "20"]
    check.main()
finally:
    check.Checker = real
    sys.argv = argv
r4 = json.loads((d / "o4" / "final.jsonl").read_text().splitlines()[-1])
r20 = json.loads((d / "o20" / "final.jsonl").read_text().splitlines()[-1])
m4, m20 = json.loads((d / "o4" / "manifest.json").read_text()), json.loads((d / "o20" / "manifest.json").read_text())
assert r4["images"] == paths[:4] and r20["images"] == paths
assert "max_images" not in m4 and m20["max_images"] == 20 and r4["code_sha"] != r20["code_sha"]
print("4. check.py main: ok")

# ---- 5. the writer: the servers' limit and the per-question command
sys.path.insert(0, str(ROOT / "compare40"))
import run_qwen_rag as rq  # noqa: E402

assert rq.MAX_IMAGES == 4 and rq.IMAGE_LIMIT == 4
src = (ROOT / "compare40" / "run_qwen_rag.py").read_text()
assert 'json.dumps({"image": IMAGE_LIMIT, "video": 0})' in src
assert 'if args.max_images != MAX_IMAGES:     # only then: the default command is as before' in src
assert 'cmd += ["--max-images", str(args.max_images)]' in src
assert "IMAGE_LIMIT = max(MAX_IMAGES, need)" in src
assert src.count('str(HERE / "run_vine_rag.py")') == 1        # run_qwen_pages.py swaps this one call


class VC:                                       # vllm_client, as with_vision wraps it
    @staticmethod
    def serve_command(vllm_bin, model, served_name="parser", port=8000, max_model_len=40960,
                      gpu_memory_utilization=0.90, seed=42, language_only="flag", extra=()):
        return list(extra)


vc = rq.with_vision(VC())
assert vc.serve_command("v", "m")[-1] == json.dumps({"image": 4, "video": 0}), "default: 4, as before"
rq.IMAGE_LIMIT = 13
assert vc.serve_command("v", "m")[-1] == json.dumps({"image": 13, "video": 0})
rq.IMAGE_LIMIT = rq.MAX_IMAGES
print("5. the writer's server limit: ok")

# ---- 6. the jobs pass the number on
A = (ROOT / "vine2" / "answer_job.slurm").read_text()
B = (ROOT / "vine2" / "check_job.slurm").read_text()
assert 'V2_IMAGES="${V2_IMAGES:-4}"' in A and '--tag "qwen_$V2_STEM" --max-images "$V2_IMAGES"' in A
assert 'V2_IMAGES="${V2_IMAGES:-4}"' in B and '--tag "$V2_STEM" --max-images "$V2_IMAGES"' in B
print("6. jobs: ok")

# ---- 7. the launcher, with fake Slurm: STEM, job names, exported number, the summary line
F = TMP / "launch"
(F / "bin").mkdir(parents=True)
(F / "bin" / "squeue").write_text("#!/bin/bash\nexit 0\n")
(F / "bin" / "sbatch").write_text("#!/bin/bash\necho \"$@\" >> \"$FAKE_OUT\"\necho $RANDOM\n")
for b in ("squeue", "sbatch"):
    (F / "bin" / b).chmod(0o755)
sc = F / "scratch"
bd = sc / "Beyond_RAG"
(bd / "parser_runs_faster").mkdir(parents=True)
(bd / "gems_rag").mkdir()
(bd / "mmrag_cache_v3").mkdir()
(bd / "mmrag_cache_v3" / "figures.jsonl").write_text(json.dumps({"image_path": paths[0]}) + "\n")
counts = {"Z1": 13, "Z2": 2, "Z3": 6}
kq = {q: dict(ENTRY, question=f"Zorb {q}?", figures=ENTRY["figures"][:n]) for q, n in counts.items()}
(bd / "parser_runs_faster" / "kq_r4299665_s0c3805.json").write_text(json.dumps(kq))
(sc / "q").mkdir()
(sc / "q" / "questions_zorb.json").write_text(json.dumps({q: v["question"] for q, v in kq.items()}))
venv = sc / "vine"
(venv / "envs" / "retrieval" / "bin").mkdir(parents=True)
(venv / "envs" / "retrieval" / "bin" / "python").symlink_to(sys.executable)
(venv / "envs" / "vllm" / "bin").mkdir(parents=True)
(venv / "envs" / "vllm" / "bin" / "vllm").write_text("#!/bin/bash\n")
(venv / "envs" / "vllm" / "bin" / "vllm").chmod(0o755)
(venv / ".done_models").write_text("")
(venv / "anthropic_key").write_text("zorb-not-a-key\n")
rev = re.search(r'^REVISION = "([0-9a-f]*)"$', (ROOT / "hprc" / "vine_hprc.py").read_text(), re.M).group(1)
snap = sc / "hf_cache" / "models--Qwen--Qwen3.8-27B-FP8" / "snapshots" / rev
snap.mkdir(parents=True)
(snap / "config.json").write_text("{}")
clone = F / "repo"
if (ROOT / ".git").exists():
    subprocess.run(["git", "clone", "-q", "--no-hardlinks", str(ROOT), str(clone)], check=True)
else:                                           # a copy without .git: make a throwaway repository
    shutil.copytree(ROOT, clone)
    subprocess.run(["git", "init", "-q"], cwd=clone, check=True)
    subprocess.run(["git", "add", "-A"], cwd=clone, check=True)
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "t"], cwd=clone, check=True)
env = dict(os.environ, SCRATCH=str(sc), USER="tester", PATH=f"{F / 'bin'}:{os.environ['PATH']}",
           FAKE_OUT=str(F / "sbatch_args"))
launch = ["bash", str(clone / "vine2" / "run_vine2_grace.sh"), "132692299628", str(sc / "q" / "questions_zorb.json")]
for extra, stem, n in (([], "questions_zorb", 4), (["2", "20"], "questions_zorb_img20", 20)):
    (F / "sbatch_args").unlink(missing_ok=True)
    r = subprocess.run(launch + extra, capture_output=True, text=True, env=env, cwd=clone)
    assert r.returncode == 0, r.stdout + r.stderr
    sb = (F / "sbatch_args").read_text().splitlines()
    assert len(sb) == 2, sb
    assert f"--job-name=vine2_answer_{stem} " in sb[0] and f"--job-name=vine2_check_{stem} " in sb[1], sb
    assert all(f"V2_STEM={stem},V2_KQ=" in x and x.split("V2_IMAGES=")[1].split()[0] == str(n) for x in sb), sb
    summary = "figure pictures a question: 2 to 13 (median 6); more than 4 in 2, more than 20 in 0"
    assert (summary in r.stdout) == (n != 4), r.stdout
    assert ("up to 20 pictures a question" in r.stdout) == (n != 4), r.stdout
for bad in (["2", "0"], ["2", "21"], ["2", "x"]):
    r = subprocess.run(launch + bad, capture_output=True, text=True, env=env, cwd=clone)
    assert r.returncode != 0 and "MAX_IMAGES must be 1 to 20" in r.stdout, (bad, r.stdout)
print("7. launcher with fake Slurm: ok")

shutil.rmtree(TMP, ignore_errors=True)
print("\nall vine2 picture checks passed")
