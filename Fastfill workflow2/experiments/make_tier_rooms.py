"""Easy / medium / hard versions of the same rooms, after EmbodiedGen's scene complexity levels (its solver places
large furniture, then mid-scale objects on their supporting surfaces, then tabletop clutter, and the level sets how
many of those stages run: room_gen/gen_room.py, Simple / Medium / Detail).

Every object to place gets a layer from the request and its ground-truth size (benchmark metadata; no method sees it):
  1 furniture   stands on the floor or hangs on a wall (support_parent "floor", "wall" or none)
  2 medium      stands on another object to place and its largest ground-truth dimension is at least --mid-m
  3 clutter     stands on another object to place and is smaller
A version keeps the objects of its layers whose support is kept (an object on a removed one goes with it), the
constraints whose objects are all kept, and drops the rest from the condition, the target and every per-object list
(validity, provenance.target_source_ids / field_evidence); everything else (room, openings, fixed objects, the
descriptions) is copied unchanged:
  easy    layer 1           medium  layers 1-2           hard    layers 1-3 = the room as given
Only rooms with all three layers are used (in test150detail: the SAGE-10k rooms; the IL3D rooms hold furniture only).
The hard version is the input row itself, so it is not written again: rows.jsonl holds the easy and medium versions,
and MANIFEST.json maps every version to its room (``base_index`` in --rows) so the hard results come from the run on
--rows.

    python3 experiments/make_tier_rooms.py --rows ../test150detail/rows.jsonl --output ../test150tiers
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

LEVELS = ("easy", "medium", "hard")
PROVENANCE_PER_OBJECT = ("target_source_ids", "field_evidence")


def layers(row: dict, mid_m: float) -> dict[str, int]:
    ids = {o["id"] for o in row["condition"]["objects"]}
    size = {o["id"]: o["target_size_local_m"] for o in row["target"]["objects"]}
    return {o["id"]: 1 if o.get("support_parent") not in ids else 2 if max(size[o["id"]]) >= mid_m else 3
            for o in row["condition"]["objects"]}


def kept(row: dict, layer: dict[str, int], level: int) -> set[str]:
    """Ids of the objects of layers <= level whose support (when it is an object to place) is kept too."""
    parent = {o["id"]: o.get("support_parent") for o in row["condition"]["objects"]}
    keep: dict[str, bool] = {}

    def ok(i: str, seen=()) -> bool:
        if i not in keep:
            p = parent[i]
            keep[i] = layer[i] <= level and (p not in parent or (p not in seen and ok(p, seen + (i,))))
        return keep[i]
    return {i for i in parent if ok(i)}


def constraint_ids(c: dict) -> set[str]:
    ids = {c.get("object_id"), c.get("target_id"), c.get("parent_id"), *(c.get("target_ids") or ())}
    return {i for i in ids if i is not None}


def version(row: dict, keep: set[str]) -> dict:
    """``row`` with only the objects in ``keep`` (condition, target, constraints, per-object lists)."""
    out = copy.deepcopy(row)
    target_order = [o["id"] for o in row["target"]["objects"]]
    take = [n for n, i in enumerate(target_order) if i in keep]
    out["condition"]["objects"] = [o for o in row["condition"]["objects"] if o["id"] in keep]
    out["condition"]["constraints"] = [c for c in row["condition"]["constraints"] if constraint_ids(c) <= keep]
    out["target"]["objects"] = [row["target"]["objects"][n] for n in take]
    for key, values in row.get("validity", {}).items():
        if isinstance(values, list) and len(values) == len(target_order):
            out["validity"][key] = [values[n] for n in take]
    for key in PROVENANCE_PER_OBJECT:
        values = row["provenance"].get(key)
        if isinstance(values, list) and len(values) == len(target_order):
            out["provenance"][key] = [values[n] for n in take]
    return out


def tier_rows(rows: list[dict], mid_m: float = .3) -> tuple[list[dict], list[dict]]:
    """(easy and medium rows, manifest entries for all three levels of every room used)."""
    written, manifest = [], []
    for k, row in enumerate(rows):
        layer = layers(row, mid_m)
        if set(layer.values()) != {1, 2, 3}:
            continue
        for level, name in enumerate(LEVELS, 1):
            keep = kept(row, layer, level)
            entry = {"base_index": k, "level": name, "scene_id": row["provenance"].get("scene_id"),
                     "objects": len(keep), "of": len(layer),
                     "constraints": sum(constraint_ids(c) <= keep for c in row["condition"]["constraints"]),
                     "layer_counts": {str(n): sum(v == n for v in layer.values()) for n in (1, 2, 3)}}
            if name == "hard":
                entry["row"] = None  # the input row itself
            else:
                v = version(row, keep)
                v["provenance"]["tier"] = {"level": name, "base_index": k, "rule": f"layers 1-{level}, mid_m {mid_m}",
                                           "objects_kept": len(keep), "objects_in_room": len(layer)}
                entry["row"] = len(written)
                written.append(v)
            manifest.append(entry)
    return written, manifest


def check(rows: list[dict], base: list[dict], manifest: list[dict]) -> None:
    """Every version is a valid request with a valid target, every object keeps its description, and nothing but the
    dropped objects and constraints changed."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from workflow.contract import check_request, validate_layout
    for e in manifest:
        if e["row"] is None:
            continue
        v, b = rows[e["row"]], base[e["base_index"]]
        check_request(v["condition"])
        validate_layout(v["target"], v["condition"])
        assert v["condition"]["room"] == b["condition"]["room"]
        assert {o["id"] for o in v["condition"]["objects"]} == {o["id"] for o in v["target"]["objects"]}
        assert all(len(x) == len(v["target"]["objects"]) for x in v["validity"].values() if isinstance(x, list))
        objects = {o["id"]: o for o in b["condition"]["objects"]}
        assert all(o == objects[o["id"]] for o in v["condition"]["objects"])


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--rows", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--mid-m", type=float, default=.3, help="largest ground-truth dimension from which an object on "
                   "another object counts as medium, not clutter")
    a = p.parse_args(argv)
    lines = [l for l in a.rows.read_text().splitlines() if l.strip()]
    base = [json.loads(l) for l in lines]
    rows, manifest = tier_rows(base, a.mid_m)
    check(rows, base, manifest)
    a.output.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    (a.output / "rows.jsonl").write_text(text)
    rooms = sorted({e["base_index"] for e in manifest})
    summary = {lvl: {"versions": sum(e["level"] == lvl for e in manifest),
                     "objects": sum(e["objects"] for e in manifest if e["level"] == lvl),
                     "constraints": sum(e["constraints"] for e in manifest if e["level"] == lvl)} for lvl in LEVELS}
    (a.output / "MANIFEST.json").write_text(json.dumps({
        "base_rows": str(a.rows), "base_sha256": hashlib.sha256(a.rows.read_bytes()).hexdigest(),
        "rows_sha256": hashlib.sha256(text.encode()).hexdigest(), "mid_m": a.mid_m, "rooms": rooms,
        "summary": summary, "versions": manifest}, indent=1) + "\n")
    print(json.dumps({"rooms": len(rooms), "rows_written": len(rows), **summary}))


if __name__ == "__main__":
    main()
