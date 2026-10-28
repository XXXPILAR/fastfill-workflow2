import json, sys, time
sys.path.insert(0, ".")
from workflow.pipeline import run_draft_workflow
from workflow.loop import LoopBudget
rows = [json.loads(l) for l in open("../test300/rows.jsonl")]
picked = sorted(range(len(rows)), key=lambda i: -len(rows[i]["condition"]["objects"]))[:3] + list(range(0, 300, 60))
for i in picked:
    c = rows[i]["condition"]; t = time.perf_counter()
    try:
        r = run_draft_workflow(c, None, llm=False, loop_budget=LoopBudget(gpt_repairs=0, search_seconds=20))
        d = r["diagnostics"]; st = d["stages"]
        print(i, len(c["objects"]), "floor", len(st["stage_ids"]["floor"]), "small", len(st["stage_ids"]["small"]),
              "hard", d["critic"]["final"]["hard_count"], "escape", st["stage_two"]["escape"].get("result"),
              st["safeguard"], f"{time.perf_counter()-t:.1f}s", flush=True)
    except Exception as e:
        import traceback; traceback.print_exc(); print(i, "ERROR", e)
