import json, sys
from pathlib import Path
sys.path.insert(0, ".")
from workflow.contract import check_request, fill_room_defaults  # noqa (puts fastfill on sys.path)
from fastfill.v2.ops import layout_quality as lq
from fastfill.v2.schema import migrate_legacy_row
from workflow.critic import Critic, load_templates
from workflow.orders import critic_geometry
from workflow.planning import Plan
rows = [json.loads(l) for l in open("../test300/rows.jsonl")]
idx = [15,129,197,200,22,43,70,109,29,61,68,79,63,66,81,84,86,103,108,110]
E = Path("experiments")
def cfinal(i):
    for d in ("orders_test50_server", "orders_AC_rest30_server"):
        p = E / d / "C_final" / f"room_{i:03d}.json"
        if p.exists(): return json.loads(p.read_text())
runs = {"staged (now)": {i: json.loads((E / "local_staged20" / f"room_{i:03d}.json").read_text()) for i in idx},
        "C_final (server, older critic)": {i: cfinal(i) for i in idx}}
templates = json.loads(Path("experiments/quality50/eval_templates_odd.json").read_text())["templates"]
mig = [migrate_legacy_row(rows[i]) for i in idx]
def same_critic(r, i):
    """wall_back and reach (plan-independent terms) with the current critic, and hard violations"""
    if not r.get("layout"):
        return None
    cond = check_request(fill_room_defaults(rows[i]["condition"])[0])
    parents = {b["id"]: b["support_parent"] for b in r["layout"]["objects"]}
    plan = Plan(parents=dict(parents))
    g = critic_geometry(cond, plan)
    c = Critic.for_plan(g, plan, load_templates())
    placed = {b["id"]: b for b in r["layout"]["objects"]}
    a = c.assess(placed)
    by = lambda code: sum(1 for v in a.soft if v.code == code)
    return a.hard_count, by("wall_back"), by("reach"), by("template_faces"), by("template_near")
print("| variant | hard-valid (current critic) | wall_back | reach | faces | near | NAV | ACC | REL | COL | OPC |")
q = lq.score_method(mig, [r["target"] for r in mig], templates)
print("| ground truth | – | – | – | – | – |", " | ".join(f"{100*q[k]:.1f}" for k in ("NAV","ACC","REL","COL","OPC")), "|")
for name, res in runs.items():
    vals = [v for v in (same_critic(res[i], i) for i in idx) if v is not None]
    q = lq.score_method(mig, [res[i].get("layout") for i in idx], templates)
    print(f"| {name} | {sum(v[0]==0 for v in vals)}/20 ({20-len(vals)} failed) | " + " | ".join(str(sum(v[k] for v in vals)) for k in (1,2,3,4)),
          "|", " | ".join(f"{100*q[k]:.1f}" for k in ("NAV","ACC","REL","COL","OPC")), "|")
for name, res in runs.items():
    print(name, "USD", round(sum(r.get("cost_usd") or 0 for r in res.values()), 2) if "staged" in name else "")
