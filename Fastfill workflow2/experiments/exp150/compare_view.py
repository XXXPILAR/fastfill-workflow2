"""One HTML page to compare exp150's layouts room by room in 3D: ground truth, GPT alone, FastFill alone and ours (g1),
side by side, the same boxes view as the earlier boxes_view pages (blue: on the floor, orange: on a wall, green: on
another object, grey: the room's fixed objects; doors brown, windows light blue). The cameras move together; hovering
a box names it; each pane shows that room's scores from eval/per_room.json (run evaluate.py first).

    ../.venv/bin/python experiments/exp150/compare_view.py      # writes experiments/exp150/compare_view.html
"""
import json, math, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
W2 = HERE.parents[1]
sys.path.insert(0, str(W2))
import workflow.contract  # noqa: E402,F401  (puts fastfill on sys.path)
from fastfill.v2.ops import layout_quality as lq  # noqa: E402
from fastfill.v2.schema import migrate_legacy_row  # noqa: E402
from workflow.robot import infer_parents  # noqa: E402

ROOT = W2.parent
PANES = [("ground truth", "原始数据集布局"), ("GPT alone", "纯 GPT"), ("FastFill alone", "纯 FastFill"),
         ("ours (g1)", "我们的方法 g1")]


def r3(v):
    return round(float(v), 3)


def boxes(row, layout):
    """[[id, kind, x, y, z, sx, sy, sz, yaw]] with kind 0 floor, 1 wall, 2 on an object."""
    if not layout:
        return None
    floor_z = row["condition"]["room"].get("floor_z_m") or 0.
    bs = lq.boxes(row, layout)
    parents = infer_parents(bs)
    given = {o["id"]: o.get("support_parent") for o in layout["objects"]}
    ids = {o["id"] for o in layout["objects"]}
    out = []
    for o in layout["objects"]:
        sx, sy, sz = o["target_size_local_m"]
        x, y, z = o["bottom_center_m"]
        parent = given.get(o["id"]) or parents.get(o["id"])
        kind = 2 if parent in ids else (1 if z - floor_z > .05 else 0)
        out.append([o["id"], kind, r3(x), r3(y), r3(z - floor_z), r3(sx), r3(sy), r3(sz), r3(o["yaw_rad"])])
    return out


def scores(rec):
    if not rec or "check" not in rec:
        return None
    leg, rob, rect = rec["check"]["legality"], rec["check"]["robot"]["0.5"], rec.get("rect") or {}
    return {"legal": leg["legal"], "col": leg["col"], "oob": leg["oob"], "opc": leg["opc"],
            "cons": list(leg["constraints"]), "placed": rec["placed"], "objects": rec["objects"],
            "robot": rob["ok"], "items": [rob["items"] - rob["items_unreached"], rob["items"]],
            "rect": rect.get("ok"), "rect_items": [rect.get("items_reached"), rect.get("items")],
            "rect_furn": [rect.get("furniture_reached"), rect.get("furniture")]}


def main():
    sys.path.insert(0, str(HERE))
    rows = [migrate_legacy_row(json.loads(l)) for l in open(ROOT / "test300/rows.jsonl") if l.strip()]
    rooms = json.loads((HERE / "rooms.json").read_text())
    per_room = json.loads((HERE / "eval/per_room.json").read_text())
    by = {m: {r["room"]: r for r in recs} for m, recs in per_room.items()}
    ff = [json.loads(l) for l in open(HERE / "fastfill_server/predictions_spread.jsonl")]
    data = []
    for k in rooms:
        row = rows[k]
        room = row["condition"]["room"]
        gpt = json.loads((HERE / f"gpt_pure/room_{k:03d}.json").read_text())
        g1 = json.loads((HERE / f"g1_main/room_{k:03d}.json").read_text())
        layouts = {"ground truth": row["target"], "GPT alone": None if gpt.get("error") else gpt.get("layout"),
                   "FastFill alone": ff[k]["layout"], "ours (g1)": g1.get("layout")}
        why = {"GPT alone": gpt.get("error"), "FastFill alone": ff[k].get("error")}
        fixed = []
        for f in room.get("fixed_objects") or []:
            sx, sy, sz = f["size_local_m"]
            x, y, z = f["bottom_center_m"]
            fixed.append([r3(x), r3(y), r3(z - (room.get("floor_z_m") or 0.)), r3(sx), r3(sy), r3(sz), r3(f["yaw_rad"])])
        openings = [[o["type"], o["wall_index"], r3(o["position_on_wall"]), r3(o["width_m"]), r3(o.get("height_m") or 2.),
                     r3(o.get("sill_height_m") or 0.)] for o in room.get("openings") or []
                    if "wall_index" in o and "position_on_wall" in o]
        data.append({"k": k, "type": room.get("room_type") or "", "n": len(row["condition"]["objects"]),
                     "floor": [[r3(x), r3(y)] for x, y in room["floor_polygon_xy_m"]],
                     "h": r3(room.get("height_m") or 2.8), "openings": openings, "fixed": fixed,
                     "cat": {o["id"]: o["category"] for o in row["condition"]["objects"]},
                     "panes": {m: {"boxes": boxes(row, layouts[m]), "scores": scores(by[m].get(k)),
                                   "why": None if layouts[m] else (why.get(m) or "no layout")} for m, _ in PANES}})
    page = (HERE / "compare_view.template.html").read_text()
    page = page.replace("__PANES__", json.dumps(PANES, ensure_ascii=False)).replace(
        "__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    out = HERE / "compare_view.html"
    out.write_text(page)
    print(f"{out} ({out.stat().st_size / 1e6:.1f} MB, {len(data)} rooms)")


if __name__ == "__main__":
    main()
