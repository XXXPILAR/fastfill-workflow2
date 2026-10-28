import json, math, sys, shutil
from pathlib import Path
W = Path("/Users/zhangyang/Downloads/fastfill-v4/Fastfill workflow")
sys.path.insert(0, str(W)); sys.path.insert(0, str(W / "experiments"))
import workflow.llm as llm
import run_orders
rows = [json.loads(l) for l in open("/Users/zhangyang/Downloads/fastfill-v4/test300/rows.jsonl")]
# a room with objects on other objects and several groups-to-be, plus a small one
def n_on(r): return sum(1 for o in r["condition"]["objects"] if str(o.get("support_parent", "")).startswith("obj_"))
idx_on = next(i for i, r in enumerate(rows) if n_on(r) >= 3 and 10 <= len(r["condition"]["objects"]) <= 16)
idx_small = next(i for i, r in enumerate(rows) if 4 <= len(r["condition"]["objects"]) <= 6)
LOG = []
def fake_ask(instructions, prompt, **k):
    call = {"model": "fake", "usage": {"prompt_tokens": 100, "completion_tokens": 10}, "cost_usd": 0.001,
            "latency_s": 0., "failed_attempts": 0}
    if "You place furniture" in instructions:
        p = json.loads(prompt)
        statuses = [o.get("status") for o in p["objects"]]
        now = [o["id"] for o in p["objects"] if o.get("status", "place_now") == "place_now"]
        LOG.append(("draft", len(now), statuses.count("placed"), statuses.count("later"), "Some objects are already placed" in instructions))
        gt = {o["id"]: o for o in CUR["target"]["objects"]}
        out = {i: {"x": gt[i]["bottom_center_m"][0], "y": gt[i]["bottom_center_m"][1],
                   "yaw_deg": math.degrees(gt[i]["yaw_rad"])} for i in now}
        return json.dumps({"objects": out}), call
    if "You repair part" in instructions:
        LOG.append(("repair",))
        return json.dumps({"objects": {}}), call
    LOG.append(("plan",))
    return "{}", call
llm.ask = fake_ask
settings = {"model": "fake", "base_url": "https://api.openai.com/v1", "api_key": "x"}
out = Path("out"); shutil.rmtree(out, ignore_errors=True)
for i in (idx_small, idx_on):
    CUR = rows[i]; LOG.clear()
    spent = run_orders.run_room(i, rows[i]["condition"], None, None, None, str(W / "size_catalog.json"), settings,
                                ["A", "B", "C"], str(out), 2, 1, False, 60.)
    n = len(rows[i]["condition"]["objects"])
    print(f"room {i}: {n} objects, {n_on(rows[i])} on other objects")
    for m in ("A", "B", "C"):
        r = json.load(open(out / m / f"room_{i:03d}.json"))
        d = r["diagnostics"]
        print(f"  {m}: status {r['status']} steps {d['step_count']} draft calls {len(d['draft_calls'])} gpt repairs {len(d['gpt_repair_calls'])} "
              f"llm_calls {r['llm_calls']} cost {r['cost_usd']} final {d['final']['hard_count']},{d['final']['soft_total']} wall {r['wall_s']}s")
        if m == "C": print("     groups:", [len(s["ids"]) for s in d["steps"]])
    print("  spent:", {k: (round(v[0], 4), v[1]) for k, v in spent.items()})
    drafts = [x for x in LOG if x[0] == "draft"]
    print("  partial-draft prompts (place_now, placed, later, partial rules):", drafts[:3], "...", drafts[-1])
# resume: nothing re-run, plan reused
LOG.clear(); spent = run_orders.run_room(idx_on, rows[idx_on]["condition"], None, None, None, str(W / "size_catalog.json"), settings, ["A", "B", "C"], str(out), 2, 1, False, 60.)
print("resume calls:", LOG, spent)
