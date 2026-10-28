import json, math, sys
from pathlib import Path
W = Path("/Users/zhangyang/Downloads/fastfill-v4/Fastfill workflow")
sys.path.insert(0, str(W)); sys.path.insert(0, str(W / "experiments"))
import workflow.llm as llm
import run_draft
rows = [json.loads(l) for l in open("/Users/zhangyang/Downloads/fastfill-v4/test300/rows.jsonl")]
row = rows[29]; gt = {o["id"]: o for o in row["target"]["objects"]}
N = {"draft": 0, "repair": 0, "plan": 0}
def fake(instructions, prompt, **k):
    call = {"model": "gpt-5.6-sol", "usage": {"prompt_tokens": 1000, "completion_tokens": 100}, "cost_usd": 0.01, "latency_s": 0, "failed_attempts": 0}
    if "You place furniture" in instructions:
        N["draft"] += 1
        p = json.loads(prompt); now = [o["id"] for o in p["objects"] if o.get("status", "place_now") == "place_now"]
        return json.dumps({"objects": {i: {"x": gt[i]["bottom_center_m"][0] + .2, "y": gt[i]["bottom_center_m"][1], "yaw_deg": math.degrees(gt[i]["yaw_rad"])} for i in now}}), call
    if "You repair part" in instructions:
        N["repair"] += 1; return json.dumps({"objects": {}}), call
    N["plan"] += 1; return "{}", call
llm.ask = fake
settings = {"model": "gpt-5.6-sol", "base_url": "https://api.openai.com/v1", "api_key": "x"}
result, cost, tokens, ncalls = run_draft.run_room(row["condition"], None, None, None, str(W / "size_catalog.json"), settings, "prompt")
d = result["diagnostics"]
print("status", result["status"], "| placement", d["placement"], "| groups", [len(g) for g in d["draft"]["groups"]])
print("calls made:", N, "| ledger calls", ncalls, "cost", round(cost, 3), "| timing", result["timing_s"])
