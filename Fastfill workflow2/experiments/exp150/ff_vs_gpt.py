"""Where FastFill alone falls behind GPT alone on exp150 (and where it does not): both scored on the 149 rooms where both
returned a layout (room 162 is over FastFill's object budget), the ground truth alongside as the reference.

  out of bounds      objects with more than 1 % of their footprint outside the floor
  colliding          objects in a collision (lq.col); door blocked: door zones covered by floor furniture (lq.opc)
  constraints        by type, as robot_check.legality counts them
  facing             floor furniture >= 0.3 m tall with its back or its front edge at a wall (within 0.15 m): right
                     when the back is the edge at the wall and the front points into the room (within 45 deg of the
                     wall's inward normal), wrong when it faces the wall; front-aware, unlike the symmetric yaw
                     error FastFill is trained and scored with
  size error         mean |log(predicted / ground-truth)| over the three box dimensions, per object
  position error     distance of each object's centre to its ground-truth centre (the ground truth is one human
                     layout of many possible: a hint, not a score)
  floating / sunk    objects off the floor that stand on nothing and hang on no wall (bottom more than 5 cm above
                     the floor, no supporting box under them, more than 0.3 m from every wall) / boxes that start
                     inside the box they should stand on
  by room size       legal rooms for small (<= 10 objects), medium (11-30), large (> 30) rooms

    ../.venv/bin/python experiments/exp150/ff_vs_gpt.py      # writes eval/ff_vs_gpt.md and .json
"""
import collections, json, math, statistics, sys
from pathlib import Path

import numpy as np
from shapely.geometry import LineString, Point, Polygon

HERE = Path(__file__).resolve().parent
W2 = HERE.parents[1]
sys.path[:0] = [str(W2), str(W2 / "experiments")]
import workflow.contract  # noqa: E402,F401
from fastfill.v2.ops import layout_quality as lq  # noqa: E402
from fastfill.v2.schema import migrate_legacy_row  # noqa: E402
from workflow.contract import fill_room_defaults  # noqa: E402
from workflow.geometry import Geometry  # noqa: E402
from workflow.robot import infer_parents  # noqa: E402

ROOT = W2.parent
METHODS = ("ground truth", "GPT alone", "FastFill alone")


def layouts(k, rows, ff):
    g = json.loads((HERE / f"gpt_pure/room_{k:03d}.json").read_text())
    return {"ground truth": rows[k]["target"], "GPT alone": None if g.get("error") else g.get("layout"),
            "FastFill alone": ff[k]["layout"]}


def walls(floor):
    ring = list(floor.exterior.coords)
    inward = 1. if floor.exterior.is_ccw else -1.
    out = []
    for a, b in zip(ring, ring[1:]):
        d = np.subtract(b, a)
        n = np.linalg.norm(d)
        if n > 1e-6:
            u = d / n
            out.append((LineString([a, b]), inward * np.array((-u[1], u[0]))))
    return out


def score(row, layout, gt):
    condition = fill_room_defaults(row["condition"])[0]
    floor = Polygon(condition["room"]["floor_polygon_xy_m"]).buffer(0)
    bs = lq.boxes(row, layout)
    by = {b["id"]: b for b in bs}
    gt_by = {o["id"]: o for o in gt["objects"]}
    parents = infer_parents(bs)
    rec = {"n": len(condition["objects"])}
    rec["oob"] = (sum(1 for b in bs if b["poly"].area > 0 and b["poly"].difference(floor).area
                      > max(.01 * b["poly"].area, 5e-3)), len(bs))
    try:
        rec["col"] = lq.col(row, layout)
    except Exception:
        rec["col"] = (0, len(bs))
    rec["door"] = lq.opc(row, bs)
    given = {o["id"]: o["support_parent"] for o in condition["objects"] if o.get("support_parent")}
    geometry = Geometry(condition, {**parents, **given}, [])
    placed = {o["id"]: o for o in layout["objects"]}
    cons = collections.defaultdict(lambda: [0, 0])
    for r in condition["constraints"]:
        if r["type"] == "keepout":
            continue
        ids = [r.get("object_id"), r.get("target_id"), r.get("parent_id"), *(r.get("target_ids") or [])]
        present = all(i is None or i in placed or i in geometry.fixed for i in ids)
        cons[r["type"]][1] += 1
        cons[r["type"]][0] += present and geometry.relation_issue(r, placed) is None
    rec["cons"] = dict(cons)
    ws = walls(floor) if floor.geom_type == "Polygon" else []
    face = [0, 0]
    for b in bs:
        if not lq.obstacle(b) or b["size"][2] < .3:
            continue
        back = Point(b["centre"] - b["front"] * b["size"][0] / 2)
        front = Point(b["centre"] + b["front"] * b["size"][0] / 2)
        d_back = min((w.distance(back) for w, _n in ws), default=math.inf)
        d_front = min((w.distance(front) for w, _n in ws), default=math.inf)
        if min(d_back, d_front) > .15:  # neither its back nor its front edge is at a wall
            continue
        face[1] += 1
        if d_back <= d_front:
            line, normal = min(ws, key=lambda w: w[0].distance(back))
            face[0] += float(np.dot(b["front"], normal)) >= math.cos(math.radians(45))
    rec["face"] = face
    sizes, dists = [], []
    for o in layout["objects"]:
        g = gt_by.get(o["id"])
        if g is None:
            continue
        sizes.append(statistics.mean(abs(math.log(max(p, 1e-3) / max(q, 1e-3)))
                                     for p, q in zip(o["target_size_local_m"], g["target_size_local_m"])))
        dists.append(math.dist(o["bottom_center_m"][:2], g["bottom_center_m"][:2]))
    rec["size"], rec["dist"] = sizes, dists
    floating = sunk = 0
    for b in bs:
        if b["bottom"] <= .05:
            continue
        p = parents.get(b["id"])
        if p in by:
            sunk += b["bottom"] < by[p]["bottom"] + by[p]["size"][2] - .05
        elif all(w.distance(Point(b["centre"])) > .3 + b["size"][0] / 2 for w, _n in ws):
            floating += 1
    rec["float"], rec["sunk"] = (floating, len(bs)), (sunk, len(bs))
    rec["legal"] = rec["oob"][0] == 0 and rec["col"][0] == 0 and rec["door"][0] == 0
    return rec


def pct(h, n):
    return 100 * h / n if n else float("nan")


def main():
    rows = [migrate_legacy_row(json.loads(l)) for l in open(ROOT / "test300/rows.jsonl") if l.strip()]
    ff = [json.loads(l) for l in open(HERE / "fastfill_server/predictions_spread.jsonl")]
    rooms = json.loads((HERE / "rooms.json").read_text())
    recs = {m: {} for m in METHODS}
    for k in rooms:
        lay = layouts(k, rows, ff)
        if not all(lay.values()):
            continue
        for m in METHODS:
            recs[m][k] = score(rows[k], lay[m], rows[k]["target"])
    common = sorted(recs["FastFill alone"])
    lines = [f"# FastFill alone vs GPT alone on exp150 ({len(common)} rooms both answered)\n",
             (__doc__ or "").split("\n\n    ../")[0], "", "| | " + " | ".join(METHODS) + " |", "|---|---|---|---|"]
    table = {}

    def add(label, fn, fmt="{:.1f}"):
        vals = [fn(list(recs[m].values())) for m in METHODS]
        table[label] = vals
        lines.append(f"| {label} | " + " | ".join(fmt.format(v) for v in vals) + " |")

    S = lambda rs, key: (sum(r[key][0] for r in rs), sum(r[key][1] for r in rs))  # noqa: E731
    add("legal rooms %", lambda rs: pct(sum(r["legal"] for r in rs), len(rs)))
    add("objects out of bounds %", lambda rs: pct(*S(rs, "oob")))
    add("rooms with an object out of bounds %", lambda rs: pct(sum(r["oob"][0] > 0 for r in rs), len(rs)))
    add("objects colliding %", lambda rs: pct(*S(rs, "col")))
    add("rooms with a collision %", lambda rs: pct(sum(r["col"][0] > 0 for r in rs), len(rs)))
    add("doors blocked %", lambda rs: pct(*S(rs, "door")))
    types = sorted({t for r in recs["ground truth"].values() for t in r["cons"]})
    for t in types:
        n = sum(r["cons"].get(t, [0, 0])[1] for r in recs["ground truth"].values())
        add(f"constraint {t} met % (n={n})", lambda rs, t=t: pct(sum(r["cons"].get(t, [0, 0])[0] for r in rs),
                                                                  sum(r["cons"].get(t, [0, 0])[1] for r in rs)))
    add("at a wall: back to the wall, front into the room %", lambda rs: pct(*S(rs, "face")))
    add("furniture at a wall (count)", lambda rs: S(rs, "face")[1], "{:.0f}")
    add("size error |log| (mean)", lambda rs: statistics.mean(x for r in rs for x in r["size"]), "{:.3f}")
    add("size error |log| (median)", lambda rs: statistics.median(x for r in rs for x in r["size"]), "{:.3f}")
    add("centre distance to ground truth m (median)", lambda rs: statistics.median(x for r in rs for x in r["dist"]),
        "{:.2f}")
    add("objects floating in the air %", lambda rs: pct(*S(rs, "float")))
    add("objects sunk into their support %", lambda rs: pct(*S(rs, "sunk")))
    for name, lo, hi in (("small <= 10", 0, 10), ("medium 11-30", 11, 30), ("large > 30", 31, 10 ** 6)):
        add(f"legal rooms %, {name} objects", lambda rs, lo=lo, hi=hi: pct(
            sum(r["legal"] for r in rs if lo <= r["n"] <= hi), sum(1 for r in rs if lo <= r["n"] <= hi)))
        add(f"objects out of bounds %, {name}", lambda rs, lo=lo, hi=hi: pct(
            sum(r["oob"][0] for r in rs if lo <= r["n"] <= hi), sum(r["oob"][1] for r in rs if lo <= r["n"] <= hi)))
    text = "\n".join(lines) + "\n"
    (HERE / "eval/ff_vs_gpt.md").write_text(text)
    (HERE / "eval/ff_vs_gpt.json").write_text(json.dumps({"rooms": common, "table": table,
                                                          "per_room": {m: {str(k): v for k, v in r.items()}
                                                                       for m, r in recs.items()}}))
    print(text)


if __name__ == "__main__":
    main()
