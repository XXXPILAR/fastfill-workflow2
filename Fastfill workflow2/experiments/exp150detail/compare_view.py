"""One HTML page to compare the exp150detail size ablation room by room in 3D, the same view as exp150's
compare_view (boxes: blue on the floor, orange on a wall, green on another object, grey fixed objects; doors brown,
windows light blue; cameras move together): ground truth, FastFill alone (1.7B full), ours with FastFill's sizes and
ours with GPT's complete draft (no FastFill), on the rooms scored in eval/ (run evaluate.py first). Hovering a box
gives its category, size in that pane and description; each pane's head adds the room's mean size error
(|log(size / ground-truth size)| over the three dimensions, averaged over the objects).

    ../.venv/bin/python experiments/exp150detail/compare_view.py      # writes experiments/exp150detail/compare_view.html
"""
import json, math, statistics, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP150 = HERE.parent / "exp150"
sys.path.insert(0, str(EXP150))
import compare_view as cv  # noqa: E402  (boxes / scores / r3, and the page template)
from fastfill.v2.schema import migrate_legacy_row  # noqa: E402

PANES = [("ground truth", "原始数据集布局"), ("FastFill alone (1.7B full)", "纯 FastFill（1.7B 全量）"),
         ("ours, FastFill sizes", "A：FastFill 尺寸 + GPT"), ("ours, GPT draft (no FastFill)", "B：GPT 完整初稿（不用 FastFill）")]
RUNS = {"ours, FastFill sizes": "ff_sizes", "ours, GPT draft (no FastFill)": "gpt_draft"}


def size_error(row, layout):
    if not layout:
        return None
    truth = {o["id"]: o["target_size_local_m"] for o in row["target"]["objects"]}
    errs = [statistics.mean(abs(math.log(s / t)) for s, t in zip(o["target_size_local_m"], truth[o["id"]]))
            for o in layout["objects"] if o["id"] in truth and min(truth[o["id"]]) > 0 and min(o["target_size_local_m"]) > 0]
    return round(statistics.mean(errs), 3) if errs else None


def page_template():
    page = (EXP150 / "compare_view.template.html").read_text()
    edits = [("<title>exp150 布局对比</title>", "<title>exp150detail 尺寸对照</title>"),
             ("'exp150_room'", "'exp150detail_room'"),
             ("`${id} · ${r.cat[id] || '?'}`",
              "`${id} · ${r.cat[id] || '?'} · 宽 ${b[4].toFixed(2)} × 深 ${b[3].toFixed(2)} × 高 ${b[5].toFixed(2)} m"
              " · ${(r.desc[id] || '').slice(0, 140)}`"),
             ("<br>${fmt(p.scores, p.why)}`;",
              "<br>${fmt(p.scores, p.why)}${p.size_err == null ? '' : `<br>尺寸误差（与原始数据比）${p.size_err.toFixed(3)}`}`;")]
    for old, new in edits:
        assert page.count(old) >= 1, old
        page = page.replace(old, new)
    return page


def main():
    rows = [migrate_legacy_row(json.loads(l)) for l in open(cv.ROOT / "test150detail/rows.jsonl") if l.strip()]
    rooms = json.loads((HERE / "eval/table.json").read_text())["rooms"]
    per_room = json.loads((HERE / "eval/per_room.json").read_text())
    by = {m: {r["room"]: r for r in recs} for m, recs in per_room.items()}
    ff = [json.loads(l) for l in open(HERE / "fastfill/1.7b-all-full/predictions_spread.jsonl")]
    data = []
    for k in rooms:
        row = rows[k]
        room = row["condition"]["room"]
        layouts = {"ground truth": row["target"], "FastFill alone (1.7B full)": ff[k]["layout"]}
        why = {"FastFill alone (1.7B full)": ff[k].get("error")}
        for name, run in RUNS.items():
            r = json.loads((HERE / run / f"room_{k:03d}.json").read_text())
            layouts[name], why[name] = r.get("layout"), r.get("error")
        floor_z = room.get("floor_z_m") or 0.
        fixed = [[cv.r3(f["bottom_center_m"][0]), cv.r3(f["bottom_center_m"][1]), cv.r3(f["bottom_center_m"][2] - floor_z),
                  *map(cv.r3, f["size_local_m"]), cv.r3(f["yaw_rad"])] for f in room.get("fixed_objects") or []]
        openings = [[o["type"], o["wall_index"], cv.r3(o["position_on_wall"]), cv.r3(o["width_m"]),
                     cv.r3(o.get("height_m") or 2.), cv.r3(o.get("sill_height_m") or 0.)]
                    for o in room.get("openings") or [] if "wall_index" in o and "position_on_wall" in o]
        data.append({"k": k, "type": f"{row['provenance'].get('source')} {room.get('room_type') or ''}".strip(),
                     "n": len(row["condition"]["objects"]),
                     "floor": [[cv.r3(x), cv.r3(y)] for x, y in room["floor_polygon_xy_m"]],
                     "h": cv.r3(room.get("height_m") or 2.8), "openings": openings, "fixed": fixed,
                     "cat": {o["id"]: o["category"] for o in row["condition"]["objects"]},
                     "desc": {o["id"]: o.get("description", "") for o in row["condition"]["objects"]},
                     "panes": {m: {"boxes": cv.boxes(row, layouts[m]), "scores": cv.scores(by[m].get(k)),
                                   "size_err": None if m == "ground truth" else size_error(row, layouts[m]),
                                   "why": None if layouts[m] else (why.get(m) or "no layout")} for m, _ in PANES}})
    page = page_template().replace("__PANES__", json.dumps(PANES, ensure_ascii=False)).replace(
        "__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    out = HERE / "compare_view.html"
    out.write_text(page)
    print(f"{out} ({out.stat().st_size / 1e6:.1f} MB, {len(data)} rooms)")


if __name__ == "__main__":
    main()
