import json, sys, time, collections
sys.path.insert(0, ".")
from workflow.contract import check_request, fill_room_defaults
from workflow.planning import Plan
from workflow.orders import sub_room
from workflow.critic import load_templates
from workflow.catalog import SizeCatalog
from workflow.loop import FocusedLoop, LoopBudget
from fastfill.v2.ops import layout_quality as lq
from fastfill.v2.schema import migrate_legacy_row
rows = [json.loads(l) for l in open("../test300/rows.jsonl")]
T = json.loads(open("experiments/quality50/eval_templates_odd.json").read())["templates"]
i = int(sys.argv[1]) if len(sys.argv) > 1 else 63
r = json.load(open(f"experiments/local_staged20/room_{i:03d}.json")); d = r["diagnostics"]
cond = check_request(fill_room_defaults(rows[i]["condition"])[0])
placed = {b["id"]: b for b in r["layout"]["objects"]}
def plan_():
    return Plan(parents=dict(d["support_parents"]), relations=list(d["plan_relations"]), groups=list(d["functional_groups"]),
                priority=dict(d["priority"]))
def rel(lay):
    row = migrate_legacy_row(rows[i]); h, t = lq.rel(lq.boxes(row, {"objects": list(lay.values())}), T); return f"{h}/{t}"
floor = {k: v for k, v in placed.items() if d["support_parents"][k] == "floor"}
for name, budget in (("old: 24 attempts, stale 4, this run's share of 180 s", LoopBudget(gpt_repairs=0, max_attempts=24, stale_limit=4, search_seconds=180 / 9)),
                     ("new default", LoopBudget(gpt_repairs=0))):
    plan = plan_()
    g, c = sub_room(cond, plan, floor, load_templates())
    before = c.assess(floor)
    t0 = time.perf_counter()
    loop = FocusedLoop(g, plan, d["sizes"], SizeCatalog(), c, locked_parents={}, budget=budget, movable=set(floor))
    out, info = loop.run(dict(floor))
    after = c.assess(out)
    by = lambda a: {k: v["count"] for k, v in a.summary()["soft_by_code"].items()}
    print(f"{name}: {info['termination']}, attempts {len(info['attempts'])}/{info['max_attempts']}, "
          f"{time.perf_counter()-t0:.0f} s, hard {before.hard_count}->{after.hard_count}, soft {before.soft_total:.2f}->{after.soft_total:.2f}")
    print("   soft by code", by(before), "->", by(after))
    print("   REL (floor objects)", rel(floor), "->", rel(out))
