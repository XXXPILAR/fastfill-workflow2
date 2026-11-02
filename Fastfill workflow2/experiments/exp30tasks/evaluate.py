"""exp30tasks evaluation (no LLM, no money): the task mode against the workflow before it on the 30 rooms of
test30tasks (required and expansion furniture from each room's tasks), beside the ground truth and FastFill alone.

Checks are the independent ones exp150 uses, not the workflow's own critic: collisions (fastfill.validate on box
meshes, the objects in one), out of bounds (more than 1 % of the footprint outside the floor), door zones blocked
(layout_quality's door zones), constraints (Geometry.relation_issue), and the robot checker for a 0.5 m robot with
the task's objects (robot.RobotChecker with simple.task_robot: every work furniture reachable and openable furniture
free to open, plus the required objects reached and the articulation objects free to open); supports are inferred
from the boxes (robot.infer_parents), as for any method. SceneEval, EmbodiedGen and the rectangular base as in exp150.
A layout is scored on the objects it holds (the task mode may remove expansion objects); removed objects count as not
kept, never as a failure of a required object, and a missing required object counts as one.

Per required object: kept, legal (in no collision, inside, not blocking a door), reached (the robot reaches it: the
furniture it stands on for an object on furniture; within arm's reach for an object on furniture; free to open when
the task opens it). A task is doable when every object it uses is kept, legal and reached, and the doors are linked.

    ../.venv/bin/python experiments/exp30tasks/evaluate.py [workers]
    EVAL_ROOMS=experiments/exp30tasks/rooms10.json EVAL_OUT=eval_rooms10 ../.venv/bin/python experiments/exp30tasks/evaluate.py
        (only those rooms, into experiments/exp30tasks/<EVAL_OUT>; a run folder with no room of them is left out)
"""
import copy, json, os, statistics, sys, time
from multiprocessing import Pool
from pathlib import Path

from shapely.geometry import Polygon

HERE = Path(__file__).resolve().parent
W2 = HERE.parents[1]
sys.path[:0] = [str(W2 / "experiments" / "exp150"), str(W2 / "experiments"), str(W2)]
import evaluate as ev  # noqa: E402  (exp150's independent checks; sets up their paths)
import robot_check as rc  # noqa: E402
from fastfill.v2.ops import layout_quality as lq  # noqa: E402
from fastfill.v2.schema import migrate_legacy_row  # noqa: E402
from workflow.geometry import Geometry  # noqa: E402
from workflow.planning import Plan  # noqa: E402
from workflow.robot import Robot, RobotChecker, infer_parents  # noqa: E402
from workflow.simple import task_robot, without  # noqa: E402

ROWS_FILE = W2.parent / "test30tasks" / "rows.jsonl"
FF_FILE = HERE / "fastfill" / "1.7b-all-full" / "predictions_spread.jsonl"
RUNS = {"workflow before (old_mode)": "old_mode", "task mode (task_mode)": "task_mode",
        "task mode v2: required first + fallback (task_mode_v2)": "task_mode_v2"}
EVAL_ROOMS = json.loads(Path(os.environ["EVAL_ROOMS"]).read_text()) if os.environ.get("EVAL_ROOMS") else None
RUNS = {m: r for m, r in RUNS.items()
        if any((HERE / r / f"room_{k:03d}.json").exists() for k in (EVAL_ROOMS or range(30)))}
METHODS = ["ground truth", "FastFill alone (1.7B full)"] + list(RUNS)
COMBINED: list = []


def rows():
    return [migrate_legacy_row(json.loads(l)) for l in open(ROWS_FILE) if l.strip()]


def load(base):
    """method -> {room: (layout or None, seconds, usd, record)}"""
    ff = [json.loads(l) for l in open(FF_FILE)]
    out = {m: {} for m in METHODS}
    for k, row in enumerate(base):
        if EVAL_ROOMS is not None and k not in EVAL_ROOMS:
            continue
        out["ground truth"][k] = (row["target"], None, None, None)
        out["FastFill alone (1.7B full)"][k] = (ff[k]["layout"], ff[k]["latency_s"], 0., None)
        for name, run in RUNS.items():
            f = HERE / run / f"room_{k:03d}.json"
            if f.exists():
                r = json.loads(f.read_text())
                out[name][k] = (r.get("layout"), (r.get("wall_s") or 0) + (ff[k]["latency_s"] or 0), r.get("cost_usd"), r)
    return out


def kept_row(row, layout):
    """The row reduced to the objects the layout holds (their constraints), the target likewise."""
    ids = {o["id"] for o in layout["objects"]}
    gone = {o["id"] for o in row["condition"]["objects"]} - ids
    condition, _plan = without(row["condition"], Plan(parents={}), gone)
    out = copy.deepcopy(row)
    out["condition"] = condition
    out["target"] = {**row["target"], "objects": [o for o in row["target"]["objects"] if o["id"] in ids]}
    return out


def illegal_ids(row, layout, bs):
    """Ids of objects in a collision, out of bounds, or blocking a door zone (the independent checks, per object)."""
    from fastfill.v2.ops.v3_metrics import ir_room, placements
    from fastfill.scene import apply
    from fastfill.validate import check
    out = set()
    room, declared, z0 = ir_room(row)
    got = placements(room, declared, layout, z0)
    if got:
        pl, size = got
        c = check(apply({**room, "objects": [{**o, "size": size[o["id"]]} for o in room["objects"]]}, pl))
        out |= {i for kind in ("main", "contained") for pair in c["collisions"][kind] for i in pair}
    floor = Polygon(row["condition"]["room"]["floor_polygon_xy_m"]).buffer(0)
    out |= {b["id"] for b in bs if b["poly"].area > 0 and b["poly"].difference(floor).area > max(.01 * b["poly"].area, 5e-3)}
    zones = [Polygon(z) for z in lq.door_zones(row["condition"]["room"], lq.DOOR_ZONE_DEPTH_M)]
    out |= {b["id"] for b in bs if lq.obstacle(b) and any(z.intersection(b["poly"]).area > .01 for z in zones)}
    return out


def score(row, layout):
    """Per-room task metrics for one layout (None: no layout)."""
    task = row["task"]
    required, articulation = set(task["required_ids"]), set(task["articulation_ids"])
    expansion = set(task["expansion_ids"])
    if not layout:
        return {"layout": False, "required": len(required), "expansion": len(expansion),
                "tasks": len(task["tasks"]), "tasks_doable": 0}
    sub = kept_row(row, layout)
    kept = {o["id"] for o in layout["objects"]}
    bs = lq.boxes(sub, layout)
    parents = infer_parents(bs)
    bad = illegal_ids(sub, layout, bs)
    robot = task_robot(Robot(width_m=.5), required & kept, articulation & kept)
    report = RobotChecker(robot, sub["condition"]).report(layout, parents)
    fails = report["failures"]
    unreached = {f["object_ids"][0] for k in ("robot_reach", "robot_arm") for f in fails[k]}
    shut = {f["object_ids"][0] for f in fails["robot_openable"]}
    by_id = {b["id"]: b for b in bs}

    def floor_root(i):  # the floor furniture an object stands on (itself for floor furniture)
        seen = set()
        while i in by_id and not lq.obstacle(by_id[i]) and i not in seen:
            seen.add(i)
            i = parents.get(i, "?")
        return i
    reached = {i for i in kept if i not in unreached and floor_root(i) not in unreached
               and (i not in articulation or i not in shut)}
    doors_ok = not fails["robot_door"]
    geometry = Geometry(sub["condition"], {**parents, **{o["id"]: o["support_parent"] for o in sub["condition"]["objects"]
                                                          if o.get("support_parent")}}, [])
    placed = {o["id"]: o for o in layout["objects"]}
    req_constraints = [row["condition"]["constraints"][n] for n in task["required_constraints"]]
    met = sum(all(i in placed or i in geometry.fixed for i in
                  {r.get("object_id"), r.get("target_id"), r.get("parent_id"), *(r.get("target_ids") or [])} - {None})
              and geometry.relation_issue(r, placed) is None for r in req_constraints)
    good = {i for i in required & kept if i not in bad and i in reached}
    doable = sum(doors_ok and all(i in good for i in t["uses"]) for t in task["tasks"])
    exp_kept = expansion & kept
    return {"layout": True, "required": len(required), "required_kept": len(required & kept),
            "required_legal": len((required & kept) - bad), "required_reached": len((required & kept) & reached),
            "required_good": len(good), "required_constraints": (met, len(req_constraints)),
            "expansion": len(expansion), "expansion_kept": len(exp_kept), "expansion_legal": len(exp_kept - bad),
            "work_furniture": report["required"], "work_furniture_unreached": report["required_unreached"],
            "openable": report["openable"], "openable_blocked": report["openable_blocked"],
            "items": report["items"], "items_unreached": report["items_unreached"],
            "doors_linked": doors_ok, "room_legal": not bad, "robot_ok": report["ok"],
            "tasks": len(task["tasks"]), "tasks_doable": doable}


def init(combined):
    global COMBINED
    COMBINED = combined
    ev.ie.ROWS = combined


def job(args):
    name, k, i, layout = args
    row = COMBINED[i]
    out = {"name": name, "room": k}
    try:
        out["task"] = score(row, layout)
    except Exception as e:
        out["task"] = {"error": f"{type(e).__name__}: {e}"[:200]}
    if layout:
        sub = kept_row(row, layout)
        COMBINED.append(sub)  # the worker's own copy: ie.job reads its row by index
        ie = ev.ie.job((name, len(COMBINED) - 1, layout))
        out.update({k2: ie[k2] for k2 in ("sceneeval", "embodiedgen", "rect")})
        COMBINED.pop()
    return out


def pct(a, b):
    return 100 * a / b if b else None


def summarise(recs, info):
    t = [r["task"] for r in recs if "error" not in r["task"]]
    lay = [x for x in t if x["layout"]]
    se = [r["sceneeval"] for r in recs if "sceneeval" in r and "error" not in r["sceneeval"]]
    rb = [r["rect"] for r in recs if "rect" in r and "error" not in r["rect"]]
    s = lambda key: sum(x.get(key, 0) for x in t)  # noqa: E731
    records = [v[3] for v in info.values() if v[3]]
    tasks_d = [((r.get("diagnostics") or {}).get("task") or {}) for r in records]
    secs = sorted(v[1] for v in info.values() if v[1] is not None)
    cost = [v[2] for v in info.values() if v[2] is not None]
    rc_met = sum(x["required_constraints"][0] for x in lay)
    rc_tot = sum(x["required_constraints"][1] for x in lay)
    return {
        "rooms": len(t), "layouts": len(lay),
        "required_kept": pct(s("required_kept"), s("required")), "required_legal": pct(s("required_legal"), s("required")),
        "required_reached": pct(s("required_reached"), s("required")), "required_good": pct(s("required_good"), s("required")),
        "required_rooms_all_good": pct(sum(x["layout"] and x["required_good"] == x["required"] for x in t), len(t)),
        "required_constraints": pct(rc_met, rc_tot),
        "tasks_doable": pct(s("tasks_doable"), s("tasks")),
        "expansion_kept": pct(s("expansion_kept"), s("expansion")),
        "expansion_legal": pct(s("expansion_legal"), s("expansion")),
        "room_legal": pct(sum(x["room_legal"] for x in lay), len(t)),
        "doors_linked": pct(sum(x["doors_linked"] for x in lay), len(t)),
        "work_furniture": pct(s("work_furniture") - s("work_furniture_unreached"), s("work_furniture")),
        "openable": pct(s("openable") - s("openable_blocked"), s("openable")),
        "items": pct(s("items") - s("items_unreached"), s("items")),
        "robot_ok": pct(sum(x["robot_ok"] for x in lay), len(t)),
        "se_col": pct(sum(x["col"][0] for x in se), sum(x["col"][1] for x in se)),
        "se_oob": pct(sum(x["oob"][0] for x in se), sum(x["oob"][1] for x in se)),
        "rect_ok": pct(sum(x["ok"] for x in rb), len(t)),
        "required_first_used": sum(bool((t.get("required_first") or {}).get("used")) for t in tasks_d) if records else None,
        "fallback_rooms": sum(r.get("status") == "fallback_required_only" for r in records) if records else None,
        "s_median": secs[len(secs) // 2] if secs else None,
        "usd_room": statistics.mean(cost) if cost else None}


COLS = [("required_kept", "required objects kept %", "{:.1f}"), ("required_legal", "required objects legal %", "{:.1f}"),
        ("required_reached", "required objects reached by the robot %", "{:.1f}"),
        ("required_good", "required objects kept + legal + reached %", "{:.1f}"),
        ("required_rooms_all_good", "rooms with every required object good %", "{:.1f}"),
        ("required_constraints", "required relations met %", "{:.1f}"),
        ("tasks_doable", "tasks doable (every object used good, doors linked) %", "{:.1f}"),
        ("expansion_kept", "expansion objects kept %", "{:.1f}"), ("expansion_legal", "expansion objects kept + legal %", "{:.1f}"),
        ("room_legal", "rooms legal (every object kept) %", "{:.1f}"), ("doors_linked", "rooms with doors linked %", "{:.1f}"),
        ("work_furniture", "work furniture reached %", "{:.1f}"), ("openable", "openable furniture free to open %", "{:.1f}"),
        ("items", "items within arm's reach %", "{:.1f}"), ("robot_ok", "rooms robot ok (task robot) %", "{:.1f}"),
        ("se_col", "SceneEval objects colliding %", "{:.1f}"), ("se_oob", "SceneEval out of bounds %", "{:.1f}"),
        ("rect_ok", "rect base: rooms all reached %", "{:.1f}"),
        ("required_first_used", "rooms where required first (④c) was used", "{:.0f}"),
        ("fallback_rooms", "rooms delivered as the required-only fallback", "{:.0f}"),
        ("s_median", "s / room (median)", "{:.1f}"),
        ("usd_room", "$ / room (est.)", "{:.3f}")]


def main():
    t0 = time.perf_counter()
    base = rows()
    src = load(base)
    combined = list(base)
    jobs = [(m, k, k, src[m][k][0]) for m in METHODS for k in src[m]]
    for m in METHODS:  # a room a run has not done counts as failed
        for k in (EVAL_ROOMS if EVAL_ROOMS is not None else range(len(base))):
            if k not in src[m]:
                jobs.append((m, k, k, None))
    recs = {m: [] for m in METHODS}
    with Pool(int(sys.argv[1]) if len(sys.argv) > 1 else 8, initializer=init, initargs=(combined,)) as pool:
        for r in pool.imap_unordered(job, jobs):
            recs[r["name"]].append(r)
    table = {m: summarise(recs[m], src[m]) for m in METHODS}
    f = lambda v, fmt: "–" if v is None else fmt.format(v)  # noqa: E731
    lines = ["| metric | " + " | ".join(f"{m} ({table[m]['rooms']})" for m in METHODS) + " |",
             "|---|" + "---|" * len(METHODS)]
    for key, label, fmt in COLS:
        lines.append(f"| {label} | " + " | ".join(f(table[m][key], fmt) for m in METHODS) + " |")
    removed = []
    for k, (_l, _s, _u, r) in sorted(src[list(RUNS)[-1]].items()):
        t = ((r or {}).get("diagnostics") or {}).get("task") or {}
        for d in t.get("removed", []):
            removed.append(f"- room row {k} ({base[k]['task']['base_index']}): {d['id']} {d['category']}"
                           + (f" with {d['with']}" if d["with"] else "") + f": {d['because'][0] if d['because'] else ''}")
    text = ("# exp30tasks: the task mode against the workflow before it\n\n"
            + (f"Rooms (rows of test30tasks): {EVAL_ROOMS}\n\n" if EVAL_ROOMS is not None else "")
            + __doc__.split("\n\n    ../")[0]
            + "\n\nColumn headers give the rooms scored; a method's missing rooms count as failed rooms.\n\n"
            + "\n".join(lines) + f"\n\n## Expansion objects removed by {list(RUNS)[-1]}\n\n" + ("\n".join(removed) or "none") + "\n")
    out = HERE / os.environ.get("EVAL_OUT", "eval")
    out.mkdir(exist_ok=True)
    (out / "table.md").write_text(text)
    (out / "table.json").write_text(json.dumps(table, indent=1))
    (out / "per_room.json").write_text(json.dumps(recs))
    print(text)
    print(f"{time.perf_counter() - t0:.0f} s", file=sys.stderr)


if __name__ == "__main__":
    main()
