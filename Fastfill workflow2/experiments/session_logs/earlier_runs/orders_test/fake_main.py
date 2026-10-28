import json, math, sys, shutil
from pathlib import Path
W = Path("/Users/zhangyang/Downloads/fastfill-v4/Fastfill workflow")
sys.path.insert(0, str(W)); sys.path.insert(0, str(W / "experiments"))
import workflow.llm as llm
from workflow.drafting import ALL_OBJECTS_RULE
import run_orders
ROWS = "/Users/zhangyang/Downloads/fastfill-v4/test300/rows.jsonl"
rows = [json.loads(l) for l in open(ROWS)]
GT = {o["id"]: o for r in rows for o in r["target"]["objects"]}  # ids repeat across rooms: keep per room below
BYROOM = [{o["id"]: o for o in r["target"]["objects"]} for r in rows]
sizes = Path("gt_sizes.jsonl"); sizes.write_text("".join(json.dumps({"layout": r["target"]}) + "\n" for r in rows))
SEEN = {"partial_with_all_rule": 0, "partial": 0}
def fake_ask(instructions, prompt, **k):
    call = {"model": "fake", "usage": {"prompt_tokens": 100, "completion_tokens": 10}, "cost_usd": 0.001, "latency_s": 0., "failed_attempts": 0}
    if "You place furniture" in instructions:
        p = json.loads(prompt)
        statuses = {o.get("status") for o in p["objects"]}
        if statuses - {None}:
            SEEN["partial"] += 1; SEEN["partial_with_all_rule"] += ALL_OBJECTS_RULE in instructions
        ids = {o["id"] for o in p["objects"]}
        room = next(r for r in BYROOM if set(r) == ids)
        now = [o["id"] for o in p["objects"] if o.get("status", "place_now") == "place_now"]
        return json.dumps({"objects": {i: {"x": room[i]["bottom_center_m"][0] + .3, "y": room[i]["bottom_center_m"][1],
                                           "yaw_deg": math.degrees(room[i]["yaw_rad"])} for i in now}}), call
    if "You repair part" in instructions:
        return json.dumps({"objects": {}}), call
    return "{}", call
llm.ask = fake_ask
run_orders.official_api = lambda: {"model": "fake", "base_url": "https://api.openai.com/v1", "api_key": "x"}
run_orders.preflight = lambda s: None
out = Path("out_main"); shutil.rmtree(out, ignore_errors=True)
base = ["run_orders.py", "--rows", ROWS, "--sizes-file", str(sizes), "--out", str(out), "--budget-usd", "5",
        "--indices", "29", "22", "--workers", "1", "--mp-start", "fork", "--quality", "--search-seconds", "30"]
sys.argv = base; run_orders.main()
print("partial prompts:", SEEN)
b, bf = (json.load(open(out / n / "room_029.json")) for n in ("B", "B_final"))
print("B and B_final share the steps:", b["diagnostics"]["steps"] == bf["diagnostics"]["steps"],
      "| B final loop:", b["diagnostics"]["final_loop"] is None, "B_final final loop attempts:", len((bf["diagnostics"]["final_loop"] or {}).get("attempts", [])))
print("ledger:", json.load(open(out / "ledger.json"))["rooms"]["29"])
sys.argv = base + ["--batch", "2"]
try:
    run_orders.main(); print("ERROR: changed settings were accepted")
except SystemExit as e:
    print("changed settings refused:", str(e)[:160])
