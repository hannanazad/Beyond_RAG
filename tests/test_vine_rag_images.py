"""compare40/run_vine_rag.py --max-images and its launcher: offline tests.

Every question, piece and figure here is invented ("zorb markers"). Nothing comes from a
benchmark question or its answer. No GPU, no API (the answer model is replaced by a stub
that only counts the pictures it is given), no data files of the project.

Run:  $RETR_ENV/bin/python tests/test_vine_rag_images.py   ->  "all vine_rag picture checks passed"
"""
import json
import os
import random
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
from PIL import Image  # noqa: E402

sys.path.insert(0, str(ROOT / "compare40"))
import run_vine_rag as rvr  # noqa: E402

TMP = Path(tempfile.mkdtemp(prefix="vine_rag_images_"))
random.seed(20261124)

# ---- 1. fit_sizes: small pictures stay as they are; a big one, or a big set, goes as a JPEG copy
small = []
for i in range(3):
    p = TMP / f"small_{i}.png"
    Image.new("RGB", (300, 200), (10 * i, 20, 30)).save(p)
    small.append({"figure_id": f"Figure 9Z-{i}", "image_path": str(p)})
big = TMP / "big.png"
Image.frombytes("RGB", (1400, 1400), os.urandom(1400 * 1400 * 3)).save(big)
assert big.stat().st_size > rvr.MAX_IMAGE_BYTES, "the test picture must be over 3.7 MB"
jdir = TMP / "jpeg"
out = rvr.fit_sizes(small, jdir)
assert [o["image_path"] for o in out] == [s["image_path"] for s in small] and {o["form"] for o in out} == {"png"}
assert not jdir.exists(), "no JPEG folder when nothing needs it"
out = rvr.fit_sizes(small + [{"figure_id": "Figure 9Z-9", "image_path": str(big)}], jdir)
assert [o["form"] for o in out] == ["png", "png", "png", "jpeg"] and out[3]["why_jpeg"] == "over 3.7 MB"
assert out[3]["source_image"] == str(big) and Path(out[3]["image_path"]).parent == jdir
assert Path(out[3]["image_path"]).stat().st_size < rvr.MAX_IMAGE_BYTES
assert big.exists() and big.suffix == ".png", "the figure file itself is never changed"
assert not list(jdir.glob("*.part")), "no half-written picture left"
first = Path(out[3]["image_path"]).stat().st_mtime_ns
again = rvr.fit_sizes([{"figure_id": "Figure 9Z-9", "image_path": str(big)}], jdir)
assert Path(again[0]["image_path"]).stat().st_mtime_ns == first, "a JPEG copy is made once"
saved = rvr.MAX_REQUEST_IMAGE_BYTES
rvr.MAX_REQUEST_IMAGE_BYTES = 1                  # a set over the request limit: every picture as JPEG
try:
    out = rvr.fit_sizes(small, jdir)
    assert {o["form"] for o in out} == {"jpeg"} and {o["why_jpeg"] for o in out} == {"the request would pass 24 MB"}
finally:
    rvr.MAX_REQUEST_IMAGE_BYTES = saved
print("1. fit_sizes: ok")

# ---- 2. the whole script, with the answer model replaced by a stub (no API)
H = TMP / "run"
bd = H / "scratch" / "Beyond_RAG"
figdir = bd / "mmrag_cache_v3" / "figs"
figdir.mkdir(parents=True)
(bd / "gems_rag").mkdir()
meta, Q, K = [], {}, {}
counts = {"VQ901": 0, "VQ902": 3, "VQ903": 6, "VQ904": 13, "VQ905": 9}
for qid, n in counts.items():
    Q[qid] = f"Zorb question {qid}: how wide must zorb markers be?"
    figs = []
    for j in range(n):
        p = figdir / f"{qid}_{j}.png"
        if qid == "VQ905" and j == 0:
            Image.frombytes("RGB", (1400, 1400), os.urandom(1400 * 1400 * 3)).save(p)
        else:
            Image.new("RGB", (200 + j, 100), (j, j, j)).save(p)
        meta.append({"image_path": str(p), "figure_id": f"Figure 9Z-{j}", "caption": f"zorb sheet {j}",
                     "page_printed": str(100 + j)})
        figs.append({"figure_id": f"Figure 9Z-{j}", "caption": f"zorb figure {j}", "image_paths": [str(p)]})
    chunks = [{"chunk_id": f"vine:{qid}:{k}", "content_type": ["Standard", "Guidance", "Option", "Support"][k % 4],
               "section_id": "9Z.01", "ordinal": k, "section_title": "Zorb Markers", "page_printed": "130",
               "text": f"Zorb markers shall be at least {30 + k} inches wide."} for k in range(4)]
    K[qid] = {"question": Q[qid], "chunks": chunks, "figures": figs}
(bd / "mmrag_cache_v3" / "figures.jsonl").write_text("\n".join(json.dumps(m) for m in meta) + "\n")
(H / "q.json").write_text(json.dumps(Q))
(H / "kq.json").write_text(json.dumps(K))
DRIVER = H / "drive.py"
DRIVER.write_text(
    "import sys, os, importlib\n"
    "sys.dont_write_bytecode = True\n"
    "repo = sys.argv[1]\n"
    "sys.path.insert(0, repo + '/gems_rag'); sys.path.insert(0, repo + '/compare40')\n"
    "os.environ['MRAG_ENV'] = 'hprc'; os.environ['MRAG_BASE_DIR'] = os.environ['SCRATCH'] + '/Beyond_RAG/gems_rag'\n"
    "import mrag\n"
    "from mrag.vlm import VLM\n"
    "VLM.load = lambda self: self\n"
    "def stub(self, question, chunks, figs, pages, max_new_tokens=None):\n"
    "    self.last_api_debug = {'stub': True}\n"
    "    return 'zorb stub answer, %d pictures' % len(figs)\n"
    "VLM.answer = stub\n"
    "m = importlib.import_module('run_vine_rag')\n"
    "sys.argv = ['run_vine_rag'] + sys.argv[2:]\n"
    "sys.exit(m.main())\n")


def run(*extra):
    env = dict(os.environ, SCRATCH=str(H / "scratch"), PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([sys.executable, "-I", str(DRIVER), str(ROOT), "--kq", str(H / "kq.json"),
                        "--questions", str(H / "q.json"), "--models", "claude-sonnet-5-5",
                        "--out", str(H / "out"), *extra], capture_output=True, text=True, env=env)
    return r


def answers(tag):
    return {json.loads(l)["question_id"]: json.loads(l) for l in (H / "out" / f"answers_{tag}.jsonl").read_text().splitlines()}


r = run("--tag", "d")
assert r.returncode == 0, r.stdout + r.stderr
r = run("--tag", "i20", "--max-images", "20")
assert r.returncode == 0, r.stdout + r.stderr
assert "up to 20 images a question" in r.stdout
d, w = answers("d"), answers("i20")
for qid, n in counts.items():
    assert len(d[qid]["images"]) == min(n, 4), (qid, d[qid]["images"])
    assert len(w[qid]["images"]) == n, (qid, w[qid]["images"])
    assert "max_images" not in d[qid] and "image_forms" not in d[qid], "the default record is unchanged"
    assert w[qid]["max_images"] == 20 and len(w[qid]["image_forms"]) == n
    if qid != "VQ905":
        assert w[qid]["images"][:4] == d[qid]["images"], "the same pictures first, in VINE's order"
assert w["VQ905"]["image_forms"][0] == "jpeg" and Path(w["VQ905"]["images"][0]).parent == H / "out" / "figure_jpeg"
assert w["VQ905"]["images"][1:4] == d["VQ905"]["images"][1:4]
assert d["VQ904"]["prompt_sha256"] != w["VQ904"]["prompt_sha256"], "more pictures: a different prompt"
assert d["VQ902"]["prompt_sha256"] == w["VQ902"]["prompt_sha256"], "3 pictures either way: the same prompt"
assert not (H / "out" / "figure_jpeg").exists() or len(list((H / "out" / "figure_jpeg").iterdir())) == 1
r = run("--tag", "i20", "--max-images", "20")
assert r.returncode == 0 and r.stdout.count("SKIP") == len(counts), "a rerun skips what is done"
for bad in ("0", "21"):
    r = run("--tag", "bad", "--max-images", bad)
    assert r.returncode != 0 and "--max-images must be 1 to 20" in (r.stdout + r.stderr), bad
print("2. the script, default and 20: ok")

# ---- 3. the launcher and the job pass the number through, and the default is unchanged
L = (ROOT / "compare40" / "run_vine_rag_grace.sh").read_text()
J = (ROOT / "compare40" / "vine_rag_job.slurm").read_text()
assert 'IMAGES="${3:-4}"' in L and '[ "$IMAGES" -eq 4 ] || TAG="${TAG}_img$IMAGES"' in L
assert "VR_IMAGES=$IMAGES" in L and '"$IMAGES" -le 20' in L
assert 'VR_IMAGES="${VR_IMAGES:-4}"' in J and '--max-images "$VR_IMAGES"' in J
src = (ROOT / "compare40" / "run_vine_rag.py").read_text()
assert "MAX_IMAGES = 4 " in src and "if len(shown) < args.max_images:" in src
assert "if args.max_images > MAX_IMAGES and shown:" in src and "if args.max_images != MAX_IMAGES:" in src
print("3. launcher and job: ok")

# ---- 4. the launcher itself, with fake Slurm: tag, summary line and exported number
F = TMP / "launch"
(F / "bin").mkdir(parents=True)
(F / "bin" / "squeue").write_text("#!/bin/bash\nexit 0\n")
(F / "bin" / "sbatch").write_text("#!/bin/bash\necho \"$@\" > \"$FAKE_OUT\"\necho 4242\n")
for b in ("squeue", "sbatch"):
    (F / "bin" / b).chmod(0o755)
sc = F / "scratch"
(sc / "Beyond_RAG" / "parser_runs_faster").mkdir(parents=True)
(sc / "Beyond_RAG" / "gems_rag").mkdir()
(sc / "Beyond_RAG" / "mmrag_cache_v3").mkdir()
(sc / "Beyond_RAG" / "mmrag_cache_v3" / "figures.jsonl").write_text((bd / "mmrag_cache_v3" / "figures.jsonl").read_text())
(sc / "Beyond_RAG" / "parser_runs_faster" / "kq_r4299665_s0c3805.json").write_text((H / "kq.json").read_text())
(sc / "vine" / "envs" / "retrieval" / "bin").mkdir(parents=True)
(sc / "vine" / "envs" / "retrieval" / "bin" / "python").symlink_to(sys.executable)
(sc / "vine" / "anthropic_key").write_text("zorb-not-a-key\n")
(sc / "q").mkdir()
(sc / "q" / "questions_zorb.json").write_text((H / "q.json").read_text())
clone = F / "repo"
subprocess.run(["git", "clone", "-q", "--no-hardlinks", str(ROOT), str(clone)], check=True) if (ROOT / ".git").exists() else None
if not clone.exists():                          # a copy without .git: make a throwaway repository
    subprocess.run(["cp", "-r", str(ROOT), str(clone)], check=True)
    subprocess.run(["git", "init", "-q"], cwd=clone, check=True)
    subprocess.run(["git", "add", "-A"], cwd=clone, check=True)
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "t"], cwd=clone, check=True)
for n, tag in (("", "sonnet_questions_zorb"), ("20", "sonnet_questions_zorb_img20")):
    env = dict(os.environ, SCRATCH=str(sc), USER="tester", PATH=f"{F / 'bin'}:{os.environ['PATH']}",
               FAKE_OUT=str(F / "sbatch_args"), RETR_ENV=str(sc / "vine" / "envs" / "retrieval"))
    args = ["bash", str(clone / "compare40" / "run_vine_rag_grace.sh"), "132692299628", str(sc / "q" / "questions_zorb.json")]
    r = subprocess.run(args + ([n] if n else []), capture_output=True, text=True, env=env, cwd=clone)
    assert r.returncode == 0, r.stdout + r.stderr
    sb = (F / "sbatch_args").read_text()
    assert f"--job-name=vine_rag_{tag} " in sb and f"VR_IMAGES={n or 4}" in sb, sb
    assert ("figure pictures a question: 0 to 13 (median 6); more than 4 in 3, more than 20 in 0" in r.stdout) == bool(n), r.stdout
for bad in ("0", "21", "x"):
    r = subprocess.run(args + [bad], capture_output=True, text=True, env=env, cwd=clone)
    assert r.returncode != 0 and "MAX_IMAGES must be 1 to 20" in r.stdout, (bad, r.stdout)
print("4. launcher with fake Slurm: ok")

import shutil  # noqa: E402
shutil.rmtree(TMP, ignore_errors=True)          # the made-up files and the throwaway clone
print("\nall vine_rag picture checks passed")
