import json, math, sys, cProfile, pstats
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
i = 66; d = json.load(open(f"experiments/simple20_robot_b/room_{i:03d}.json"))["diagnostics"]
cond = check_request(fill_room_defaults(rows[i]["condition"])[0])
plan = Plan(dict(d["support_parents"]), d["plan_relations"], d["functional_groups"])
g = critic_geometry(cond, plan); critic = Critic.for_plan(g, plan, load_templates())
robot = Robot(width_m=.5); critic.robot = RobotChecker.for_critic(robot, critic); g.robot_zones = RobotZones(robot, g)
placed = {o["id"]: o for o in d["stages"]["draft"]["objects"]}
loop = Loop(g, plan, d["sizes"], SizeCatalog(None), critic, locked_parents=_required_parents(cond),
            budget=LoopBudget(gpt_repairs=0, min_soft_cost=math.inf, max_attempts=4))
cProfile.run("loop.run(placed)", "/tmp/p66" if False else sys.argv[1])
pstats.Stats(sys.argv[1]).sort_stats("cumulative").print_stats(28)
