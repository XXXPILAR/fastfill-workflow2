import json, sys
sys.path.insert(0, ".")
from workflow.pipeline import run_draft_workflow
from workflow.loop import LoopBudget
rows = [json.loads(l) for l in open("../test300/rows.jsonl")]
sizes = []
def ask(instructions, prompt):
    sizes.append((len(instructions), len(prompt)))
    return json.dumps({"issues": []}), {"usage": {}}
for i in (163, 180, 120):
    sizes.clear()
    run_draft_workflow(rows[i]["condition"], None, llm=False, semantic_ask=ask,
                       loop_budget=LoopBudget(gpt_repairs=0, search_seconds=10))
    print(i, len(rows[i]["condition"]["objects"]), "objects; review prompts (chars):", [p for _, p in sizes],
          "~tokens", [p // 4 for _, p in sizes])
