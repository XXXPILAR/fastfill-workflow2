"""Offline step ④ as run_simple does it now (zones, tiered critic, resize fallback) on a saved run's drafts."""
import json, math, sys, time, glob
sys.path[:0] = [".", "experiments"]
from big_table import ROOT
from workflow.catalog import SizeCatalog
from workflow.contract import check_request, fill_room_defaults
from workflow.critic import Critic, load_templates
from workflow.loop import Loop, LoopBudget
from workflow.orders import critic_geometry
from workflow.planning import Plan, _required_parents
from workflow.robot import Robot, RobotChecker, RobotZones
from fastfill.v2.schema import migrate_legacy_row
rows = [migrate_legacy_row(json.loads(l)) for l in open(ROOT / "test300/rows.jsonl") if l.strip()]
src, rooms, resize = sys.argv[1], [int(x) for x in sys.argv[2].split(",")], "resize" in sys.argv
for i in rooms:
    f = glob.glob(f"experiments/{src}*/room_{i:03d}.json")[0]
    d = json.load(open(f))["diagnostics"]
    cond = check_request(fill_room_defaults(rows[i]["condition"])[0])
    plan = Plan(dict(d["support_parents"]), d["plan_relations"], d["functional_groups"])
    g = critic_geometry(cond, plan); critic = Critic.for_plan(g, plan, load_templates())
    robot = Robot(width_m=.5); critic.robot = RobotChecker.for_critic(robot, critic); g.robot_zones = RobotZones(robot, g)
    placed = {o["id"]: o for o in d["stages"]["draft"]["objects"]}
    a0 = critic.assess(placed); t = time.time()
    kw = dict(locked_parents=_required_parents(cond), budget=LoopBudget(gpt_repairs=0, min_soft_cost=math.inf))
    new, _ = Loop(g, plan, d["sizes"], SizeCatalog(None), critic, **kw).run(placed)
    if resize and critic.assess(new).legality:
        new, _ = Loop(g, plan, d["sizes"], SizeCatalog(None), critic, resize=True, **kw).run(new)
    a1 = critic.assess(new)
    rep = critic.robot.report({"objects": list(new.values())}, dict(plan.parents))
    resized = {k: [round(a / b, 2) for a, b in zip(new[k]["target_size_local_m"], d["sizes"][k])]
               for k in new if new[k]["target_size_local_m"] != d["sizes"][k]}
    print(json.dumps({"room": i, "legal0": len(a0.legality), "legal1": len(a1.legality), "robot0": len(a0.robot),
                      "robot1": len(a1.robot), "items": [rep["items"] - rep["items_unreached"], rep["items"]],
                      "resized": resized, "s": round(time.time() - t, 1)}), flush=True)
