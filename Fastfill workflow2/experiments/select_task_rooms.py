"""Pick the rooms of a task dataset from a quality report (experiments/room_quality.py): every passing room of the
small-room sources, the rooms of an earlier task dataset kept (``--keep``), the rest drawn at random (seed) from the
passing rooms of the large-room source, so that small and large rooms are both there. Writes <output>/base_rows.jsonl
(the chosen rows of --rows, unchanged, in --rows order) and <output>/selection.json (what was chosen and how).

    python3 experiments/select_task_rooms.py --rows ../data_v4_detail/test.jsonl --quality ../test150tasks/room_quality.json \\
        --keep ../test30tasks/rows.jsonl --keep-manifest ../test150detail/MANIFEST.json --rooms 150 --output ../test150tasks
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

LARGE = "SAGE-10k"  # the source drawn from; every passing room of the other sources is taken


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--rows", type=Path, required=True)
    p.add_argument("--quality", type=Path, required=True)
    p.add_argument("--keep", type=Path, help="an earlier task dataset whose rooms are kept (rows with task.base_index)")
    p.add_argument("--keep-manifest", type=Path, help="the manifest mapping those base indices to --rows lines")
    p.add_argument("--rooms", type=int, default=150)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args(argv)
    lines = [l for l in a.rows.read_text().splitlines() if l.strip()]
    quality = json.loads(a.quality.read_text())
    passing = [q for q in quality["rooms"] if q["passes"]]
    small = sorted(q["room"] for q in passing if q["source"] != LARGE)
    large = sorted(q["room"] for q in passing if q["source"] == LARGE)
    kept = []
    if a.keep:
        base = json.loads(a.keep_manifest.read_text())["test_line_indices"]
        kept = sorted(base[json.loads(l)["task"]["base_index"]] for l in a.keep.read_text().splitlines() if l.strip())
        missing = set(kept) - {q["room"] for q in passing}
        if missing:
            raise SystemExit(f"kept rooms that do not pass: {sorted(missing)}")
    chosen = set(small) | set(kept)
    need = a.rooms - len(chosen)
    if need < 0:
        raise SystemExit(f"{len(chosen)} rooms already chosen, more than --rooms {a.rooms}")
    pool = [r for r in large if r not in chosen]
    drawn = sorted(random.Random(a.seed).sample(pool, need))
    chosen = sorted(chosen | set(drawn))
    a.output.mkdir(parents=True, exist_ok=True)
    text = "".join(lines[i] + "\n" for i in chosen)
    (a.output / "base_rows.jsonl").write_text(text)
    by = {q["room"]: q for q in quality["rooms"]}
    (a.output / "selection.json").write_text(json.dumps({
        "rows": str(a.rows), "rows_sha256": hashlib.sha256(a.rows.read_bytes()).hexdigest(),
        "quality": str(a.quality), "criteria": {k: quality[k] for k in ("min_doors", "min_objects")},
        "seed": a.seed, "passing": len(passing), "small_sources_taken": len(small), "kept": kept, "drawn": drawn,
        "base_rows_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "line_indices": chosen,
        "rooms": [{"row": n, "line": i, "source": by[i]["source"], "type": by[i]["type"], "objects": by[i]["objects"],
                   "doors": by[i]["doors"], "why": "kept" if i in kept else "small source" if i in small else "drawn"}
                  for n, i in enumerate(chosen)]}, indent=1) + "\n")
    print(json.dumps({"rooms": len(chosen), "small": len(small), "kept": len(kept), "drawn": len(drawn),
                      "objects": sum(by[i]["objects"] for i in chosen)}))


if __name__ == "__main__":
    main()
