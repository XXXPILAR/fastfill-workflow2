"""A task dataset: rooms of a rows file, each with household robot tasks and its objects split into the required
furniture (what the tasks need) and the expansion furniture (everything else), as the upstream task agent would send
them (room type, room shell, required furniture with relations, articulation, expansion furniture).

--tasks (JSON, written by hand: test30tasks/tasks_source.json) gives per room its tasks; each task names the ids it
uses and the ids it must open (articulation). Here:
  required     the ids the tasks use, plus every object a required object stands on (a cup on a table needs the
               table), recursively; the ones added that way are listed in ``supports_added``
  expansion    every other object of the room
  articulation the ids the tasks open (all required)
  constraints  the room's constraints whose objects are all required are the required relations
               (``required_constraints``, indices into condition.constraints); the others touch expansion objects
Each output row is the input row unchanged plus a ``task`` field with the above. The condition is not changed, so
every existing runner reads the rows as they are; the required / expansion split is in ``task`` until the request
format carries it.

    python3 experiments/make_task_rooms.py --rows ../test150detail/rows.jsonl --tasks ../test30tasks/tasks_source.json \\
        --output ../test30tasks [--review]
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def constraint_ids(c: dict) -> set[str]:
    return {i for i in (c.get("object_id"), c.get("target_id"), c.get("parent_id"), *(c.get("target_ids") or ())) if i}


def task_row(row: dict, spec: dict, base_index: int, author: str) -> dict:
    objects = {o["id"]: o for o in row["condition"]["objects"]}
    used = [i for t in spec["tasks"] for i in t["uses"]]
    articulation = sorted({i for t in spec["tasks"] for i in t["articulation"]})
    unknown = sorted(set(used + articulation) - set(objects))
    if unknown:
        raise ValueError(f"room {base_index}: unknown ids {unknown}")
    for t in spec["tasks"]:
        if not set(t["articulation"]) <= set(t["uses"]):
            raise ValueError(f"room {base_index}: articulation ids not used by the task: {t['text']}")
    required, added = set(used), []
    frontier = list(required)
    while frontier:
        parent = objects[frontier.pop()].get("support_parent")
        if parent in objects and parent not in required:
            required.add(parent)
            added.append(parent)
            frontier.append(parent)
    order = [o["id"] for o in row["condition"]["objects"]]
    constraints = row["condition"]["constraints"]
    out = dict(row)
    out["task"] = {
        "base_index": base_index, "author": author,
        "room_type": row["condition"]["room"].get("room_type"),
        "tasks": spec["tasks"],
        "required_ids": [i for i in order if i in required],
        "expansion_ids": [i for i in order if i not in required],
        "articulation_ids": articulation,
        "supports_added": sorted(added),
        "required_constraints": [n for n, c in enumerate(constraints) if constraint_ids(c) <= required],
        "expansion_constraints": [n for n, c in enumerate(constraints) if not constraint_ids(c) <= required]}
    return out


def review(row: dict) -> str:
    """The tasks with the category and the first words of the description of every object they use."""
    objects = {o["id"]: o for o in row["condition"]["objects"]}
    t = row["task"]
    lines = [f"### room {t['base_index']} ({t['room_type']}, {len(objects)} objects): required {len(t['required_ids'])}, "
             f"expansion {len(t['expansion_ids'])}, articulation {t['articulation_ids']}, supports added {t['supports_added']}"]
    for task in t["tasks"]:
        lines.append(f"  - {task['text']}")
        for i in task["uses"]:
            o = objects[i]
            lines.append(f"      {i} {o['category']} [{o.get('support_parent')}] {' '.join(o['description'].split()[:10])}"
                         + ("  (open)" if i in task["articulation"] else ""))
    return "\n".join(lines)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--rows", type=Path, required=True)
    p.add_argument("--tasks", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--review", action="store_true", help="print every task with the objects it uses")
    a = p.parse_args(argv)
    base = [json.loads(l) for l in a.rows.read_text().splitlines() if l.strip()]
    spec = json.loads(a.tasks.read_text())
    rows = [task_row(base[r["room"]], r, r["room"], spec["author"]) for r in spec["rooms"]]
    if a.review:
        print("\n".join(review(r) for r in rows))
    a.output.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    (a.output / "rows.jsonl").write_text(text)
    (a.output / "rooms.json").write_text(json.dumps(list(range(len(rows)))))
    summary = {"rooms": len(rows), "tasks": sum(len(r["task"]["tasks"]) for r in rows),
               "objects": sum(len(r["condition"]["objects"]) for r in rows),
               "required": sum(len(r["task"]["required_ids"]) for r in rows),
               "expansion": sum(len(r["task"]["expansion_ids"]) for r in rows),
               "articulation": sum(len(r["task"]["articulation_ids"]) for r in rows),
               "supports_added": sum(len(r["task"]["supports_added"]) for r in rows),
               "required_constraints": sum(len(r["task"]["required_constraints"]) for r in rows),
               "expansion_constraints": sum(len(r["task"]["expansion_constraints"]) for r in rows)}
    (a.output / "MANIFEST.json").write_text(json.dumps({
        "base_rows": str(a.rows), "base_sha256": hashlib.sha256(a.rows.read_bytes()).hexdigest(),
        "tasks_sha256": hashlib.sha256(a.tasks.read_bytes()).hexdigest(),
        "rows_sha256": hashlib.sha256(text.encode()).hexdigest(), "summary": summary,
        "rooms": [{"row": n, "base_index": r["task"]["base_index"], "source": r["provenance"].get("source"),
                   "room_type": r["task"]["room_type"], "objects": len(r["condition"]["objects"]),
                   "required": len(r["task"]["required_ids"]), "expansion": len(r["task"]["expansion_ids"]),
                   "tasks": len(r["task"]["tasks"])} for n, r in enumerate(rows)]}, indent=1) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
