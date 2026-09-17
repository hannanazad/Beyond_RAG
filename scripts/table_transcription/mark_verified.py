"""Record that the transcriptions have been checked against the source.

Run ONCE, against the folder holding the batch scripts. Without this, the next
`build.py` would rewrite mutcd_tables.jsonl from the batch files and silently
put every record back to verified=false, because the SRC string in each file
still says "unverified".

    python mark_verified.py scripts/table_transcription

The script only rewrites the SRC assignment; it does not touch the repo paths
you have already edited, or anything else in the files.
"""
import re
import sys
from pathlib import Path

NEW = ('SRC = "transcribed from a PDF render; checked against the source by the '
       'project author"')
PATTERN = re.compile(r'^SRC\s*=\s*(?:"[^"]*"|\'[^\']*\')(?:\s*\n\s*(?:"[^"]*"|\'[^\']*\'))*',
                     re.MULTILINE)


MARK_BLOCK = """
# The whole set has been checked against the source by the project author.
# Recorded here rather than on each Table(...) call so one edit covers all 91
# records, and so the flag cannot drift out of step between batch files.
for _t in TABLES:
    _t.verified = True
"""


def patch_build(folder: str) -> bool:
    """Make build.py set verified=True before it saves.

    Updating the SRC strings alone is not enough: `verified` is a field on
    Table with a default of False, and the batch files never pass it, so a
    rebuild would still write verified=false for every record.
    """
    build = Path(folder) / "build.py"
    if not build.exists():
        print(f"no build.py in {folder}; skipping that step")
        return False
    text = build.read_text(encoding="utf-8")
    if "_t.verified = True" in text:
        print("build.py already marks the records verified")
        return False
    anchor = "crops = [json.loads(l)"
    if anchor not in text:
        print("could not find the save step in build.py; add this by hand:\n" + MARK_BLOCK)
        return False
    text = text.replace(anchor, MARK_BLOCK.strip() + "\n\n" + anchor, 1)
    build.write_text(text, encoding="utf-8")
    print("patched build.py to mark every record verified")
    return True


def main(folder: str) -> None:
    changed, skipped = [], []
    for path in sorted(Path(folder).glob("batch*.py")):
        text = path.read_text(encoding="utf-8")
        if "SRC" not in text:
            skipped.append(path.name)
            continue
        new_text, n = PATTERN.subn(NEW, text, count=1)
        if n and new_text != text:
            path.write_text(new_text, encoding="utf-8")
            changed.append(path.name)
        else:
            skipped.append(path.name)
    print(f"updated {len(changed)} batch files: {', '.join(changed)}")
    if skipped:
        print(f"no SRC assignment found in: {', '.join(skipped)}")
    patch_build(folder)
    print("\nNow re-run build.py; every record should come out verified=true.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
