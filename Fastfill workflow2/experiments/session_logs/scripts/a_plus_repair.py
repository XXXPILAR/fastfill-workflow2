"""Control: A's final layout + one more whole-room critic loop (A's budget, no GPT) + polish, on the rooms where
every variant succeeded. Compares with C_final, which had per-group repairs plus one whole-room loop."""
import json, sys, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
W = Path("/Users/zhangyang/Downloads/fastfill-v4/Fastfill workflow")
sys.path.insert(0, str(W))
from workflow.catalog import SizeCatalog
from workflow.contract import check_request, fill_room_defaults
from workflow.critic import Critic, load_templates
from workflow.loop import Loop, LoopBudget
from workflow.orders import critic_geometry, plan_from_dict
from workflow.planning import _required_parents
from workflow.refine import refine
O = W / "experiments/orders_test50_server"
ROWS = open("/Users/zhangyang/Downloads/fastfill-v4/test300/rows.jsonl").read().splitlines()

def run(i):
    a = json.load(open(O / "A" / f"room_{i:03d}.json"))
    cond = check_request(fill_room_defaults(json.loads(ROWS[i])["condition"])[0])
    plan = plan_from_dict(json.load(open(O / "plans" / f"room_{i:03d}.json"))["plan"])
    plan.parents.clear(); plan.parents.update(a["diagnostics"]["support_parents"])
    g = critic_geometry(cond, plan); critic = Critic.for_plan(g, plan, load_templates())
    placed = {b["id"]: b for b in a["layout"]["objects"]}
    t0 = time.perf_counter()
    loop = Loop(g, plan, a["diagnostics"]["sizes"], SizeCatalog(W / "size_catalog.json"), critic,
                locked_parents=_required_parents(cond), ask=None, budget=LoopBudget(gpt_repairs=0, search_seconds=180))
    placed, info = loop.run(placed)
    placed, _ = refine(g, plan, placed, critic=critic)
    final = critic.assess(placed)
    return i, {"layout": {"schema_version": "fastfill.v2", "objects": [placed[o["id"]] for o in cond["objects"]]},
               "hard": final.hard_count, "soft": final.soft_total, "extra_s": round(time.perf_counter() - t0, 1)}

if __name__ == "__main__":
    V = ["A", "B", "B_final", "C", "C_final"]
    common = sorted(set.intersection(*[{int(p.stem[5:]) for p in (O / v).glob("room_*.json")} for v in V]))
    ok = [i for i in common if all("diagnostics" in json.load(open(O / v / f"room_{i:03d}.json")) for v in V)]
    with ProcessPoolExecutor(8) as pool:
        res = dict(pool.map(run, ok))
    out = O / "A_plus_repair"; out.mkdir(exist_ok=True)
    for i, r in res.items():
        (out / f"room_{i:03d}.json").write_text(json.dumps(r))
    print("done", len(res))
