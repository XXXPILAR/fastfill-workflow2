"""Offline A/B of step ④ on simple20_robot2's saved drafts: robot margin x hard zones (no LLM, no review).
Evaluates at the nominal robot (0.4/0.5/0.6 m): legality, rooms ok, per-object reach, 1 cm jitter robustness, touching.
    ../.venv/bin/python <this> [workers]
"""
import glob, json, math, random, sys, time
from dataclasses import replace
from multiprocessing import Pool
sys.path[:0] = [".", "experiments"]
import numpy as np

CONFIGS = {"now (no margin, soft zones)": (0.0, False), "margin 0.1": (0.1, False),
           "hard zones": (0.0, True), "margin 0.1 + hard zones": (0.1, True)}
RUN = "experiments/simple20_robot2"


def one(job):
    name, f = job
    margin, hard = CONFIGS[name]
    from big_table import ROOT
    from workflow.catalog import SizeCatalog
    from workflow.contract import check_request, fill_room_defaults
    from workflow.critic import Critic, load_templates
    from workflow.loop import Loop, LoopBudget
    from workflow.orders import critic_geometry
    from workflow.planning import Plan, _required_parents
    from workflow.robot import Robot, RobotChecker, RobotZones
    from fastfill.v2.schema import migrate_legacy_row
    r = json.load(open(f)); i = r["room"]; d = r["diagnostics"]
    row = migrate_legacy_row(json.loads(open(ROOT / "test300/rows.jsonl").readlines()[i]))
    cond = check_request(fill_room_defaults(row["condition"])[0])
    plan = Plan(dict(d["support_parents"]), d["plan_relations"], d["functional_groups"])
    g = critic_geometry(cond, plan); critic = Critic.for_plan(g, plan, load_templates())
    robot = Robot(width_m=.5); planned = replace(robot, width_m=.5 + margin)
    critic.robot = RobotChecker.for_critic(planned, critic); g.robot_zones = RobotZones(planned, g, hard=hard)
    placed = {o["id"]: o for o in d["stages"]["draft"]["objects"]}
    if hard:
        g.robot_zones.reserve(placed)
    t = time.time()
    kw = dict(locked_parents=_required_parents(cond), budget=LoopBudget(gpt_repairs=0, min_soft_cost=math.inf))
    if critic.assess(placed).hard:
        placed, _ = Loop(g, plan, d["sizes"], SizeCatalog(None), critic, **kw).run(placed)
        if critic.assess(placed).legality:
            placed, _ = Loop(g, plan, d["sizes"], SizeCatalog(None), critic, resize=True, **kw).run(placed)
    return name, i, {"objects": list(placed.values())}, round(time.time() - t, 1)


def evaluate(results):
    import robot_check as R
    from big_table import ROOT
    from fastfill.v2.ops import layout_quality as lq
    from fastfill.v2.schema import migrate_legacy_row
    from workflow.robot import Robot, RobotChecker, infer_parents
    rows = [migrate_legacy_row(json.loads(l)) for l in open(ROOT / "test300/rows.jsonl") if l.strip()]
    rng = random.Random(0)

    def jit(lay):
        return {"objects": [{**o, "bottom_center_m": [o["bottom_center_m"][0] + rng.gauss(0, .01),
                                                      o["bottom_center_m"][1] + rng.gauss(0, .01), o["bottom_center_m"][2]],
                             "yaw_rad": o["yaw_rad"] + rng.gauss(0, math.radians(1))} for o in lay["objects"]]}
    for name in CONFIGS:
        recs = {i: R.check_room(rows[i], lay) for (n, i), (lay, _s) in results.items() if n == name}
        s = R.summarise(list(recs.values()))
        secs = sorted(v for (n, _i), (_l, v) in results.items() if n == name)
        flips = passed = 0; touch = n_fl = 0
        for (n, i), (lay, _s) in results.items():
            if n != name:
                continue
            ch = RobotChecker(Robot(width_m=.5), rows[i]["condition"])
            ok = recs[i]["robot"]["0.5"]["ok"]
            if ok:
                for _ in range(10):
                    passed += 1; flips += not ch.report(jit(lay))["ok"]
            fl = [b for b in lq.boxes(rows[i], lay) if lq.obstacle(b)]
            for a in fl:
                dmin = min([a["poly"].distance(b["poly"]) for b in fl if b is not a] or [9])
                touch += dmin < .05; n_fl += 1
        f = lambda v: "-" if v is None else f"{v:.1f}"
        print(f"| {name} | {f(s['legal'])} | {f(s['constraints'])} | {f(s['0.4']['rooms_ok'])} | {f(s['0.5']['rooms_ok'])} | "
              f"{f(s['0.6']['rooms_ok'])} | {f(s['0.5']['required_reached'])} | {f(s['0.5']['items_reached'])} | "
              f"{f(s['0.5']['furniture_reached'])} | {f(s['0.6']['required_reached'])} | {f(s['0.6']['furniture_reached'])} | "
              f"{100 * flips / max(passed, 1):.1f} | {100 * touch / n_fl:.0f} | {secs[len(secs) // 2]} / {secs[-1]} |", flush=True)


if __name__ == "__main__":
    files = sorted(glob.glob(f"{RUN}/room_*.json"))
    jobs = [(n, f) for n in CONFIGS for f in files]
    out = {}
    with Pool(int(sys.argv[1]) if len(sys.argv) > 1 else 8) as pool:
        for name, i, lay, secs in pool.imap_unordered(one, jobs):
            out[(name, i)] = (lay, secs)
            print(f"{name} room {i}: {secs} s", file=sys.stderr, flush=True)
    json.dump({f"{n}|{i}": v for (n, i), v in out.items()}, open(__file__.replace(".py", "_layouts.json"), "w"))
    print("| config | legal | constraints | ok@0.4 | ok@0.5 | ok@0.6 | required@0.5 | items@0.5 | furniture@0.5 | "
          "required@0.6 | furniture@0.6 | 1 cm jitter: pass->fail % | touching % | s median / max |")
    print("|" + "---|" * 14)
    evaluate(out)
