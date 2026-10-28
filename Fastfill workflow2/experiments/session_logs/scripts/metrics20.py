import json, sys, os
from pathlib import Path
sys.path.insert(0, ".")
from workflow.contract import check_request, fill_room_defaults  # noqa
from fastfill.v2.ops import layout_quality as lq
from fastfill.v2.schema import migrate_legacy_row
from workflow.critic import Critic, load_templates
from workflow.orders import critic_geometry
from workflow.planning import Plan
rows = [json.loads(l) for l in open("../test300/rows.jsonl")]
idx = [15,129,197,200,22,43,70,109,29,61,68,79,63,66,81,84,86,103,108,110]
T = json.loads(Path("experiments/quality50/eval_templates_odd.json").read_text())["templates"]
B = Path("../related work code/baselines/runs/full_agentsize")
def jl(p): return [json.loads(l).get("layout") for l in open(p)]
gpt = jl("../test300/gpt56/predictions.jsonl"); ff = jl("../server_runs/test300-v4/test300_base/predictions_spread.jsonl")
def base(m, i):
    p = B / m / f"room_{i:03d}" / "result.json"
    return json.loads(p.read_text()).get("layout") if p.exists() else None
def ours(d, i):
    for dd in d:
        p = Path("experiments") / dd / f"room_{i:03d}.json"
        if p.exists(): return json.loads(p.read_text()).get("layout")
methods = {
    "FastFill base (spread)": lambda i: ff[i],
    "GPT-5.6 one-shot": lambda i: gpt[i],
    "LayoutGPT": lambda i: base("layoutgpt", i),
    "Holodeck": lambda i: base("holodeck", i),
    "LayoutVLM": lambda i: base("layoutvlm", i),
    "C_final (server, old)": lambda i: ours(["orders_test50_server/C_final", "orders_AC_rest30_server/C_final"], i),
    "staged (local, old budget)": lambda i: ours(["local_staged20"], i),
}
mig = [migrate_legacy_row(rows[i]) for i in idx]
def hard_ok(lay, i):
    if not lay: return False
    cond = check_request(fill_room_defaults(rows[i]["condition"])[0])
    ids = {o["id"] for o in cond["objects"]}
    if {b["id"] for b in lay["objects"]} != ids: return False
    parents = {b["id"]: b.get("support_parent") or "floor" for b in lay["objects"]}
    plan = Plan(parents=parents); g = critic_geometry(cond, plan)
    try:
        return not Critic.for_plan(g, plan, []).hard({b["id"]: b for b in lay["objects"]})
    except Exception:
        return False
print("| method | layouts | hard-valid | NAV↑ | ACC↑ | REL↑ | SG↑ | COL↓ | OPC↓ |")
print("|---|---|---|---|---|---|---|---|---|")
q = lq.score_method(mig, [r["target"] for r in mig], T)
f = lambda v: "–" if v is None else f"{100*v:.1f}"
print(f"| ground truth | 20 | – | {f(q['NAV'])} | {f(q['ACC'])} | {f(q['REL'])} | {f(q['SG'])} | {f(q['COL'])} | {f(q['OPC'])} |")
for name, get in methods.items():
    lays = [get(i) for i in idx]
    q = lq.score_method(mig, lays, T)
    hv = sum(hard_ok(l, i) for l, i in zip(lays, idx))
    print(f"| {name} | {sum(l is not None for l in lays)} | {hv} | {f(q['NAV'])} | {f(q['ACC'])} | {f(q['REL'])} | {f(q['SG'])} | {f(q['COL'])} | {f(q['OPC'])} |")
