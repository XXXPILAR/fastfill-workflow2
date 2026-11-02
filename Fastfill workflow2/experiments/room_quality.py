"""Room quality of a rows file, to pick high-quality rooms for a dataset (test30tasks). Per room:
  gt_legal        the ground-truth layout has no collision, nothing out of bounds and no blocked door
                  (experiments/robot_check.py legality, the check exp150 scores layouts with)
  mismatch        objects whose category names a kind of furniture (bed, seat, sofa, table, storage, lamp, plant) that
                  the first 14 words of the description do not mention while they mention another kind (IL3D has
                  e.g. a "drawer chest" described as a bed); examples are kept
  support_none    objects that do not declare what they stand on
  doors, objects  counts
  robot           for the rooms passing every check: the robot checker on the ground truth (0.5 m robot): ok, share
                  of work furniture reached, share of items in arm reach
A room passes when gt_legal, no mismatch, no missing support, at least --min-doors doors and --min-objects objects.
--pick N keeps the N passing rooms whose ground truth the robot reaches best (fewest unreached furniture, then
items), in row order.

    ../.venv/bin/python experiments/room_quality.py --rows ../test150detail/rows.jsonl --output ../test30tasks/room_quality.json --pick 30
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
import workflow.contract  # noqa: E402,F401  (puts fastfill on sys.path)
from fastfill.v2.schema import migrate_legacy_row  # noqa: E402
import robot_check as rc  # noqa: E402

KINDS = {"bed": ["bed", "beds", "mattress", "bunk"],
         "seat": ["chair", "chairs", "stool", "stools", "armchair", "seat", "bench", "ottoman", "footstool", "chaise",
                  "lounge", "recliner"],
         "sofa": ["sofa", "sectional", "couch", "loveseat", "settee"],
         "table": ["table", "desk", "workbench", "console", "counter", "countertop", "island", "vanity", "nightstand"],
         "storage": ["cabinet", "wardrobe", "chest", "dresser", "sideboard", "drawer", "drawers", "shelf", "shelves",
                     "bookcase", "bookshelf", "lowboard", "cupboard", "rack", "nightstand", "credenza", "armoire",
                     "hutch", "unit"],
         "lamp": ["lamp", "chandelier", "sconce", "fixture"],
         "plant": ["plant", "plants", "succulent", "orchid", "fig", "planter"]}


def kinds(text: str) -> set[str]:
    words = set(re.findall(r"[a-z]+", text.lower()))
    return {k for k, keys in KINDS.items() if words & set(keys)}


def category_kinds(category: str) -> set[str]:
    for word in reversed(re.findall(r"[a-z]+", category.lower())):
        if kinds(word):
            return kinds(word)
    return set()


def quality(row: dict, k: int) -> dict:
    c = row["condition"]
    mismatch = []
    for o in c["objects"]:
        named, described = category_kinds(o["category"]), kinds(" ".join(o["description"].split()[:14]))
        if named and described and not named & described:
            mismatch.append(f"{o['category']} -> {' '.join(o['description'].split()[:7])}")
    legality = rc.check_room(row, row["target"])["legality"]
    return {"room": k, "source": row["provenance"].get("source"), "type": c["room"].get("room_type"),
            "objects": len(c["objects"]), "doors": sum(o["type"] == "door" for o in c["room"].get("openings") or []),
            "support_none": sum(o.get("support_parent") is None for o in c["objects"]),
            "mismatch": len(mismatch), "mismatch_examples": mismatch[:3],
            "gt_legal": legality["legal"], "gt_col": legality["col"], "gt_oob": legality["oob"], "gt_opc": legality["opc"]}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--rows", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--min-doors", type=int, default=1)
    p.add_argument("--min-objects", type=int, default=6)
    p.add_argument("--pick", type=int)
    a = p.parse_args(argv)
    rows = [migrate_legacy_row(json.loads(l)) for l in a.rows.read_text().splitlines() if l.strip()]
    rooms = [quality(r, k) for k, r in enumerate(rows)]
    for q in rooms:
        q["passes"] = bool(q["gt_legal"] and not q["mismatch"] and not q["support_none"]
                           and q["doors"] >= a.min_doors and q["objects"] >= a.min_objects)
        if q["passes"]:
            rob = rc.check_room(rows[q["room"]], rows[q["room"]]["target"])["robot"]["0.5"]
            q["robot"] = {"ok": rob["ok"],
                          "furniture_reached": (rob["required"] - rob["required_unreached"]) / rob["required"] if rob["required"] else 1.,
                          "items_reached": (rob["items"] - rob["items_unreached"]) / rob["items"] if rob["items"] else 1.}
    passing = [q for q in rooms if q["passes"]]
    ranked = sorted(passing, key=lambda q: (-q["robot"]["furniture_reached"], -q["robot"]["items_reached"], q["room"]))
    picked = sorted(q["room"] for q in ranked[:a.pick]) if a.pick else [q["room"] for q in passing]
    a.output.write_text(json.dumps({"rows": str(a.rows), "min_doors": a.min_doors, "min_objects": a.min_objects,
                                    "passing": [q["room"] for q in passing], "picked": picked, "rooms": rooms}, indent=1) + "\n")
    print(json.dumps({"rooms": len(rooms), "passing": len(passing), "picked": picked}))


if __name__ == "__main__":
    main()
