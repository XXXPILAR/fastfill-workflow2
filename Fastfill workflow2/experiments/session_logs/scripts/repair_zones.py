"""Offline step ④ on the saved drafts: robot checks hard in the critic, zones in the search on/off (no LLM)."""
import json, math, sys, time
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
zones = sys.argv[1] == "zones"
rooms = [int(x) for x in sys.argv[2].split(",")]
W = .5
for i in rooms:
    r = json.load(open(f"experiments/simple20/room_{i:03d}.json")); d = r["diagnostics"]
    cond = check_request(fill_room_defaults(rows[i]["condition"])[0])
    plan = Plan(dict(d["support_parents"]), d["plan_relations"], d["functional_groups"])
    geometry = critic_geometry(cond, plan)
    critic = Critic.for_plan(geometry, plan, load_templates())
    critic.robot = RobotChecker.for_critic(Robot(width_m=W), critic)
    if zones:
        geometry.robot_zones = RobotZones(Robot(width_m=W), geometry)
    placed = {o["id"]: o for o in d["stages"]["draft"]["objects"]}
    a0 = critic.assess(placed)
    t = time.time()
    new, info = placed, {"attempts": []}
    if a0.hard:
        loop = Loop(geometry, plan, d["sizes"], SizeCatalog(None), critic, locked_parents=_required_parents(cond),
                    budget=LoopBudget(gpt_repairs=0, min_soft_cost=math.inf))
        new, info = loop.run(placed)
    a1 = critic.assess(new)
    rep = critic.robot.report({"objects": list(new.values())}, dict(plan.parents))
    moved = max(math.dist(placed[k]["bottom_center_m"][:2], new[k]["bottom_center_m"][:2]) for k in placed)
    out = {"room": i, "zones": zones, "hard0": [v.code for v in a0.hard], "hard1": [v.code for v in a1.hard],
           "robot_ok": rep["ok"], "req": (rep["required"] - rep["required_unreached"], rep["required"]),
           "open": (rep["openable"] - rep["openable_blocked"], rep["openable"]),
           "items": (rep["items"] - rep["items_unreached"], rep["items"]), "move": round(moved, 2),
           "accepted": sum(a["accepted"] for a in info["attempts"]), "attempts": len(info["attempts"]),
           "s": round(time.time() - t, 1)}
    print(json.dumps(out), flush=True)
    if "-v" in sys.argv:
        for a in info["attempts"]: print("  ", a["target"]["code"], a["target"]["object_ids"], a["level"], a["scope"], a["accepted"], a["reason"], a["seconds"])
