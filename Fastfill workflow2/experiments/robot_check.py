"""Every saved run through the program checker, for robots of several widths (no rendering, no LLM).

Per method, pooled over the rooms it returned a layout for:
  rooms ok %         every check below passes (legality + constraints + the robot's checks at that width)
  legal %            no collision (lq.col), nothing out of bounds (> 1 % of a footprint), no blocked door (lq.opc)
  constraints %      the input's constraints that hold (Geometry.relation_issue; ``on`` reads the layout's supports
                     as given, else as inferred from the boxes: robot.infer_parents); a missing object fails its own
  doors linked %     rooms with doors whose doors are all linked for the robot (robot_door)
  required reached % furniture the robot works at (supports of other objects, openable furniture) it reaches
  openable free %    openable furniture whose doors / drawers can open (robot_openable; width-independent)
  items in reach %   objects on furniture within the arm's 0.85 m of where the robot can stand (robot_arm)
  furniture reached % every floor obstacle >= 0.3 m tall it reaches (as REACH0.5, but for the robot: nothing lets
                     it pass between a sofa and a table)
The ground truth is checked too: these are datasets' human rooms, not robot-checked ones.

    ../.venv/bin/python experiments/robot_check.py --out experiments/robot_check
"""
import argparse, json, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "experiments"))
from shapely.geometry import Polygon  # noqa: E402

from big_table import ROOT, sources  # noqa: E402  (the saved runs' loader)
from fastfill.v2.ops import layout_quality as lq  # noqa: E402
from fastfill.v2.schema import migrate_legacy_row  # noqa: E402
from workflow.contract import fill_room_defaults  # noqa: E402
from workflow.geometry import Geometry  # noqa: E402
from workflow.robot import Robot, RobotChecker, infer_parents  # noqa: E402

WIDTHS = (.4, .5, .6)


def legality(row, layout, parents):
    condition = fill_room_defaults(row["condition"])[0]
    bs = lq.boxes(row, layout)
    floor = Polygon(condition["room"]["floor_polygon_xy_m"]).buffer(0)
    oob = sum(1 for b in bs if b["poly"].area > 0 and b["poly"].difference(floor).area > max(.01 * b["poly"].area, 5e-3))
    try:
        col = lq.col(row, layout)[0]
    except Exception:
        col = None
    opc = lq.opc(row, bs)[0]
    given = {o["id"]: o["support_parent"] for o in condition["objects"] if o.get("support_parent")}
    geometry = Geometry(condition, {**parents, **given}, [])
    placed = {o["id"]: o for o in layout["objects"]}
    met = total = 0
    for r in condition["constraints"]:
        if r["type"] == "keepout":
            continue
        ids = [r.get("object_id"), r.get("target_id"), r.get("parent_id"), *(r.get("target_ids") or [])]
        present = all(i is None or i in placed or i in geometry.fixed for i in ids)
        total += 1
        met += present and geometry.relation_issue(r, placed) is None
    return {"col": col, "oob": oob, "opc": opc, "constraints": (met, total),
            "legal": col == 0 and oob == 0 and opc == 0}


def check_room(row, layout):
    parents = infer_parents(lq.boxes(row, layout))
    out = {"legality": legality(row, layout, parents), "robot": {}}
    for w in WIDTHS:
        rep = RobotChecker(Robot(width_m=w), row["condition"]).report(layout, parents)
        rep.pop("failures")
        out["robot"][str(w)] = rep
    return out


def pct(h, n):
    return 100 * h / n if n else None


def summarise(recs):
    leg = [r["legality"] for r in recs]
    met = sum(x["constraints"][0] for x in leg)
    tot = sum(x["constraints"][1] for x in leg)
    row = {"rooms": len(recs), "legal": pct(sum(x["legal"] for x in leg), len(leg)), "constraints": pct(met, tot),
           "all_constraints_rooms": pct(sum(x["constraints"][0] == x["constraints"][1] for x in leg), len(leg))}
    for w in WIDTHS:
        rs = [r["robot"][str(w)] for r in recs]
        door_rooms = [x for x in rs if x["doors"]]
        robot_ok = [x["ok"] for x in rs]
        row[str(w)] = {
            "rooms_ok": pct(sum(o and r["legality"]["legal"] and r["legality"]["constraints"][0] == r["legality"]["constraints"][1]
                                for o, r in zip(robot_ok, recs)), len(recs)),
            "robot_ok": pct(sum(robot_ok), len(rs)),
            "doors_linked": pct(sum(x["doors_unlinked"] == 0 for x in door_rooms), len(door_rooms)),
            "required_reached": pct(sum(x["required"] - x["required_unreached"] for x in rs), sum(x["required"] for x in rs)),
            "items_reached": pct(sum(x["items"] - x["items_unreached"] for x in rs), sum(x["items"] for x in rs)),
            "openable_free": pct(sum(x["openable"] - x["openable_blocked"] for x in rs), sum(x["openable"] for x in rs)),
            "furniture_reached": pct(sum(x["furniture_reached"] for x in rs), sum(x["furniture"] for x in rs))}
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=HERE / "experiments" / "robot_check")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    rows = [migrate_legacy_row(json.loads(l)) for l in open(ROOT / "test300/rows.jsonl") if l.strip()]
    src = sources(rows)
    src.pop("shuffled ground truth (anchor)", None)
    checked = {}
    for name, rooms in src.items():
        checked[name] = {i: check_room(rows[i], lay) for i, (lay, _s, _u) in rooms.items() if lay}
        print(f"{name}: {len(checked[name])} rooms, {time.perf_counter() - t0:.0f} s", flush=True)
    simple = sorted(checked["workflow2 simple (one place, one check, one review)"])
    sets = {"test300": list(range(len(rows))), f"workflow2's {len(simple)} rooms": simple}
    f = lambda v: "–" if v is None else f"{v:.1f}"  # noqa: E731
    lines, result = [], {}
    for set_name, rooms in sets.items():
        result[set_name] = {}
        lines += [f"\n## {set_name}\n", "| method | rooms | legal % | constraints % | " +
                  " | ".join(f"{h} @{w}" for w in WIDTHS for h in ("rooms ok %", "doors linked %", "required reached %",
                                                                   "items in reach %", "furniture reached %")) + " | openable free % |",
                  "|" + "---|" * (5 + 5 * len(WIDTHS))]
        for name, recs in checked.items():
            have = [recs[i] for i in rooms if i in recs]
            if not have:
                continue
            s = result[set_name][name] = summarise(have)
            cells = [f(s[str(w)][k]) for w in WIDTHS for k in ("rooms_ok", "doors_linked", "required_reached",
                                                              "items_reached", "furniture_reached")]
            lines.append(f"| {name} | {len(have)}/{len(rooms)} | {f(s['legal'])} | {f(s['constraints'])} | " +
                         " | ".join(cells) + f" | {f(s['0.5']['openable_free'])} |")
    text = "# Program checker: legality, constraints, robot checks\n\n" + (__doc__ or "").split("\n\n    ../")[0] + \
        "\n" + "\n".join(lines) + "\n"
    (a.out / "table.md").write_text(text)
    (a.out / "metrics.json").write_text(json.dumps(result, indent=1))
    (a.out / "rooms.json").write_text(json.dumps({k: {str(i): v for i, v in r.items()} for k, r in checked.items()}))
    print(text)


if __name__ == "__main__":
    main()
