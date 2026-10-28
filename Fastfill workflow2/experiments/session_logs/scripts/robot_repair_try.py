"""Offline: the 17 workflow2 final layouts, robot checks (0.5 m) as hard, one program repair pass (no LLM)."""
import json, math, sys, time, glob
sys.path.insert(0, ".")
from workflow.catalog import SizeCatalog
from workflow.contract import check_request
from workflow.critic import Critic, load_templates
from workflow.loop import Loop, LoopBudget
from workflow.orders import critic_geometry
from workflow.planning import Plan, _required_parents
from workflow.robot import Robot, RobotChecker
from fastfill.v2.schema import migrate_legacy_row
rows = [migrate_legacy_row(json.loads(l)) for l in open("../test300/rows.jsonl")]
W = float(sys.argv[1]) if len(sys.argv) > 1 else .5
tot = {"before": 0, "after": 0, "rooms_fixed": 0, "rooms_bad": 0}
for f in sorted(glob.glob("experiments/simple20/room_*.json")):
    i = int(f[-8:-5]); r = json.load(open(f)); d = r["diagnostics"]
    cond = check_request(rows[i]["condition"])
    plan = Plan(dict(d["support_parents"]), d["plan_relations"], d["functional_groups"])
    geometry = critic_geometry(cond, plan)
    critic = Critic.for_plan(geometry, plan, load_templates())
    critic.robot = RobotChecker.for_critic(Robot(width_m=W), critic)
    placed = {o["id"]: o for o in r["layout"]["objects"]}
    a0 = critic.assess(placed)
    rb0 = [v for v in a0.hard if v.code.startswith("robot_")]
    if not a0.hard:
        print(i, "clean"); continue
    t = time.time()
    loop = Loop(geometry, plan, d["sizes"], SizeCatalog(None), critic, locked_parents=_required_parents(cond),
                budget=LoopBudget(gpt_repairs=0, min_soft_cost=math.inf))
    new, info = loop.run(placed)
    a1 = critic.assess(new)
    rb1 = [v for v in a1.hard if v.code.startswith("robot_")]
    moved = max(math.dist(placed[k]["bottom_center_m"][:2], new[k]["bottom_center_m"][:2]) for k in placed)
    tot["before"] += len(rb0); tot["after"] += len(rb1); tot["rooms_bad"] += 1; tot["rooms_fixed"] += not a1.hard
    print(i, "hard", a0.hard_count, "->", a1.hard_count, "| robot", [v.code[6:] for v in rb0], "->", [v.code[6:] for v in rb1],
          f"| other hard after {[v.code for v in a1.hard if not v.code.startswith('robot_')]} | max move {moved:.2f} m | {time.time()-t:.0f} s")
print(tot, flush=True)
