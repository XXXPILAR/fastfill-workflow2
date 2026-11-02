"""One HTML page to compare exp30tasks room by room in 3D, the same view as exp150's compare_view: ground truth,
FastFill alone, the workflow before the task mode (old_mode) and the task mode (task_mode), side by side, cameras
moving together. Colours: red the task's required furniture, blue other objects on the floor, orange on a wall,
green on another object, grey the room's fixed objects; doors brown, windows light blue. The room's tasks are shown
above the panes; each pane's head gives its task scores from eval/per_room.json (run evaluate.py first) and, for the
task mode, the expansion objects it removed and why. Hovering a box names it, with its size in that pane and its
description.

    ../.venv/bin/python experiments/exp30tasks/compare_view.py      # writes experiments/exp30tasks/compare_view.html
    CV_ROOMS=experiments/exp30tasks/rooms10.json CV_EVAL=eval_rooms10 CV_OUT=compare_view_rooms10.html \
        CV_PANES=v2 ../.venv/bin/python experiments/exp30tasks/compare_view.py
        (those rooms only, scores from that eval folder; v2: ground truth, the workflow before, the task mode, the task
        mode v2 with required first and the fallback)
"""
import html, json, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP150 = HERE.parent / "exp150"
sys.path.insert(0, str(EXP150))
import compare_view as cv  # noqa: E402  (boxes / r3, and the page template)
from fastfill.v2.schema import migrate_legacy_row  # noqa: E402

PANES = [("ground truth", "原始数据集布局"), ("FastFill alone (1.7B full)", "纯 FastFill（1.7B 全量）"),
         ("workflow before (old_mode)", "原流程（不分必须/扩充）"), ("task mode (task_mode)", "任务模式（必须家具优先）")]
RUNS = {"workflow before (old_mode)": "old_mode", "task mode (task_mode)": "task_mode",
        "task mode v2: required first + fallback (task_mode_v2)": "task_mode_v2"}
if os.environ.get("CV_PANES") == "v2":
    PANES = [("ground truth", "原始数据集布局"), ("workflow before (old_mode)", "原流程（不分必须/扩充）"),
             ("task mode (task_mode)", "任务模式（上一版）"),
             ("task mode v2: required first + fallback (task_mode_v2)", "任务模式（最新：必须优先 + 兜底）")]
REQUIRED_KIND = 3


def head(rec: dict | None, result: dict | None, why: str | None) -> str:
    """The pane's scores as HTML (the template shows it under the pane's title)."""
    if not rec or not rec.get("task", {}).get("layout"):
        return f'<span class="bad">没有布局：{html.escape((why or "")[:80])}</span>'
    t = rec["task"]
    ok = lambda good, text: f'<span class="{"ok" if good else "bad"}">{text}</span>'  # noqa: E731
    lines = [ok(t["required_good"] == t["required"], f"必须家具 合法+可达 {t['required_good']}/{t['required']}")
             + f" · 合法 {t['required_legal']} · 可达 {t['required_reached']} · "
             + ok(t["tasks_doable"] == t["tasks"], f"任务可完成 {t['tasks_doable']}/{t['tasks']}"),
             ok(t["room_legal"], "全屋合法" if t["room_legal"] else "全屋有不合法")
             + " · " + ok(t["doors_linked"], "门连通" if t["doors_linked"] else "门不连通")
             + f" · 扩充家具保留 {t['expansion_kept']}/{t['expansion']}（合法 {t['expansion_legal']}）"]
    se, rect = rec.get("sceneeval") or {}, rec.get("rect") or {}
    if "col" in se:
        lines.append(f"SceneEval 碰撞 {se['col'][0]}/{se['col'][1]} · 出界 {se['oob'][0]}/{se['oob'][1]}"
                     + (" · " + ok(rect.get("ok"), "矩形底盘：全部够到" if rect.get("ok") else "矩形底盘：有够不到")
                        if "ok" in rect else ""))
    task = ((result or {}).get("diagnostics") or {}).get("task") or {}
    if task.get("removed"):
        lines.append("删除：" + "；".join(
            html.escape(f"{d['id'][4:]} {d['category']}" + (f"（连同 {len(d['with'])} 件）" if d["with"] else "")
                        + (f" ← {d['because'][0].split(' (')[0]}" if d["because"] else "")) for d in task["removed"][:6])
            + (f" 等 {len(task['removed'])} 件" if len(task["removed"]) > 6 else ""))
    if task.get("moved"):
        lines.append(f"为必须家具挪开的扩充家具 {len(task['moved'])} 件")
    return "<br>".join(lines)


def page_template() -> str:
    page = (EXP150 / "compare_view.template.html").read_text()
    edits = [("<title>exp150 布局对比</title>", "<title>任务模式对照</title>"),
             ("'exp150_room'", "'exp30tasks_room'"),
             ("const COLORS = [0x4d80cc, 0xe08a2e, 0x3aa35b];", "const COLORS = [0x4d80cc, 0xe08a2e, 0x3aa35b, 0xd6336c];"),
             ('<span id="legend" class="muted">', '<span id="legend" class="muted"><span style="background:#d6336c"></span>'
                                                  '<b>必须家具</b>'),
             ('<div id="grid"></div>', '<div id="tasks" class="muted" style="padding:4px 12px;line-height:1.5"></div>'
                                       '<div id="grid"></div>'),
             ("const r = DATA[+sel.value], panes = PANES.filter(([m]) => shown[m]);",
              "const r = DATA[+sel.value], panes = PANES.filter(([m]) => shown[m]);\n"
              "  document.getElementById('tasks').innerHTML = r.tasks;"),
             ("<br>${fmt(p.scores, p.why)}`;", "<br>${p.html}`;"),
             ("`${id} · ${r.cat[id] || '?'}`",
              "`${r.req[id] ? '【必须】' : ''}${id} · ${r.cat[id] || '?'} · 宽 ${b[4].toFixed(2)} × 深 ${b[3].toFixed(2)} × "
              "高 ${b[5].toFixed(2)} m · ${(r.desc[id] || '').slice(0, 120)}`"),
             ("o.textContent = `room ${r.k} · ${r.type} · ${r.n} 件`;",
              "o.textContent = `${r.k} · 原房间 ${r.base} · ${r.type} · ${r.n} 件（必须 ${r.nreq}）`;")]
    for old, new in edits:
        assert page.count(old) >= 1, old
        page = page.replace(old, new)
    return page


def main():
    rows = [migrate_legacy_row(json.loads(l)) for l in open(cv.ROOT / "test30tasks/rows.jsonl") if l.strip()]
    per_room = json.loads((HERE / os.environ.get("CV_EVAL", "eval") / "per_room.json").read_text())
    only = json.loads(Path(os.environ["CV_ROOMS"]).read_text()) if os.environ.get("CV_ROOMS") else None
    by = {m: {r["room"]: r for r in recs} for m, recs in per_room.items()}
    ff = [json.loads(l) for l in open(HERE / "fastfill/1.7b-all-full/predictions_spread.jsonl")]
    data = []
    for k, row in enumerate(rows):
        if only is not None and k not in only:
            continue
        room, task = row["condition"]["room"], row["task"]
        required = set(task["required_ids"])
        layouts, results, why = {"ground truth": row["target"], "FastFill alone (1.7B full)": ff[k]["layout"]}, {}, {}
        for name, run in RUNS.items():
            f = HERE / run / f"room_{k:03d}.json"
            results[name] = json.loads(f.read_text()) if f.exists() else None
            layouts[name] = (results[name] or {}).get("layout")
            why[name] = (results[name] or {}).get("error") or ("not run" if results[name] is None else None)
        floor_z = room.get("floor_z_m") or 0.
        fixed = [[cv.r3(f["bottom_center_m"][0]), cv.r3(f["bottom_center_m"][1]), cv.r3(f["bottom_center_m"][2] - floor_z),
                  *map(cv.r3, f["size_local_m"]), cv.r3(f["yaw_rad"])] for f in room.get("fixed_objects") or []]
        openings = [[o["type"], o["wall_index"], cv.r3(o["position_on_wall"]), cv.r3(o["width_m"]),
                     cv.r3(o.get("height_m") or 2.), cv.r3(o.get("sill_height_m") or 0.)]
                    for o in room.get("openings") or [] if "wall_index" in o and "position_on_wall" in o]

        def boxes(layout):
            out = cv.boxes(row, layout)
            return [[b[0], REQUIRED_KIND if b[0] in required else b[1], *b[2:]] for b in out] if out else out
        tasks = "<b>任务：</b>" + " ｜ ".join(
            f"{n + 1}. {html.escape(t['text'])}" + (f"（要打开：{', '.join(i[4:] for i in t['articulation'])}）"
                                                    if t["articulation"] else "") for n, t in enumerate(task["tasks"]))
        data.append({"k": k, "base": task["base_index"], "type": f"{row['provenance'].get('source')} {room.get('room_type') or ''}",
                     "n": len(row["condition"]["objects"]), "nreq": len(required), "tasks": tasks,
                     "floor": [[cv.r3(x), cv.r3(y)] for x, y in room["floor_polygon_xy_m"]],
                     "h": cv.r3(room.get("height_m") or 2.8), "openings": openings, "fixed": fixed,
                     "cat": {o["id"]: o["category"] for o in row["condition"]["objects"]},
                     "desc": {o["id"]: o.get("description", "") for o in row["condition"]["objects"]},
                     "req": {i: 1 for i in required},
                     "panes": {m: {"boxes": boxes(layouts[m]), "why": None if layouts[m] else (why.get(m) or "no layout"),
                                   "html": head(by.get(m, {}).get(k), results.get(m), why.get(m))} for m, _ in PANES}})
    page = page_template().replace("__PANES__", json.dumps(PANES, ensure_ascii=False)).replace(
        "__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    out = HERE / os.environ.get("CV_OUT", "compare_view.html")
    out.write_text(page)
    print(f"{out} ({out.stat().st_size / 1e6:.1f} MB, {len(data)} rooms)")


if __name__ == "__main__":
    main()
