"""Merge the full test300 baseline runs, score them like every other test300 method, and write the cost ledger.

Per method (runs/full/<method>/room_XXX/result.json, from adapters/launch_full.sh):
  * predictions.jsonl / rows.jsonl aligned with test300/rows.jsonl (``layout`` null for a failed or unfinished room)
  * ledger/room_XXX.json in llm_cost / method_figures' format: ``usage`` (one entry per answered request),
    ``latency_s``, ``error``, plus ``failed_attempts`` (relay errors retried, not billed usage) and ``missing``
  * eval/: fastfill.v2.evaluate's report (legality, constraints, sizes)
Then COST.md / cost.json (time, requests, tokens, optional USD with --price-in/--price-out per 1M tokens) and
figures/: method_figures' results table with FastFill, GPT-5.6, M1, M2 and the three baselines (REL, ACC, NAV, SG,
COL, OPC, clean rooms, constraints, size error, success, seconds and tokens per room).

    python adapters/merge_and_score.py [--price-in 1.25 --price-out 10]
"""
import argparse, json, shutil, statistics, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parents[1]          # related work code/baselines (the repos and runs)
FULL = BASE / "runs/full"
FF = ROOT / "fastfill-main"
PY = sys.executable
METHODS = {"layoutgpt": "LayoutGPT (k-similar ICL)", "holodeck": "Holodeck (constraints + DFS)",
           "layoutvlm": "LayoutVLM (VLM constraints + optimisation)"}


def merge(method, rows):
    d = FULL / method
    ledger = d / "ledger"; ledger.mkdir(exist_ok=True)
    stats = {"rooms": len(rows), "finished": 0, "with_layout": 0, "errors": 0, "requests": 0, "failed_attempts": 0,
             "prompt_tokens": 0, "cached_tokens": 0, "completion_tokens": 0, "reasoning_tokens": 0, "missing_objects": 0,
             "objects": 0, "seconds": []}
    with open(d / "predictions.jsonl", "w") as p, open(d / "rows.jsonl", "w") as r:
        for i, row in enumerate(rows):
            r.write(json.dumps(row) + "\n")
            f = d / f"room_{i:03d}" / "result.json"
            rec = json.loads(f.read_text()) if f.exists() else None
            p.write(json.dumps({"layout": rec.get("layout") if rec else None}) + "\n")
            if rec is None:
                continue
            calls = rec.get("calls") or []
            usage = [c["usage"] for c in calls if c.get("usage")]
            (ledger / f"room_{i:03d}.json").write_text(json.dumps({
                "usage": usage, "latency_s": rec.get("seconds"), "error": rec.get("error"),
                "failed_attempts": sum(c.get("failed_attempts") or 0 for c in calls), "missing": rec.get("missing")}))
            stats["finished"] += 1
            stats["with_layout"] += rec.get("layout") is not None
            stats["errors"] += bool(rec.get("error"))
            stats["requests"] += len(usage)
            stats["failed_attempts"] += sum(c.get("failed_attempts") or 0 for c in calls)
            for u in usage:
                stats["prompt_tokens"] += u.get("prompt_tokens") or 0
                stats["completion_tokens"] += u.get("completion_tokens") or 0
                stats["cached_tokens"] += (u.get("prompt_tokens_details") or {}).get("cached_tokens") or 0
                stats["reasoning_tokens"] += (u.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0
            stats["missing_objects"] += rec.get("missing") or 0
            stats["objects"] += len(row["condition"]["objects"])
            if rec.get("seconds") is not None:
                stats["seconds"].append(rec["seconds"])
    return stats


def evaluate(method):
    d = FULL / method
    shutil.rmtree(d / "eval", ignore_errors=True)  # evaluate refuses an existing output
    res = subprocess.run([PY, "-m", "fastfill.v2.evaluate", "--data", str(d / "rows.jsonl"), "--predictions",
                          str(d / "predictions.jsonl"), "--output", str(d / "eval")], cwd=FF, capture_output=True, text=True)
    (d / "eval.log").write_text(res.stdout + res.stderr)
    return res.returncode == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--price-in", type=float, help="USD per 1M input tokens")
    ap.add_argument("--price-out", type=float, help="USD per 1M output tokens (reasoning included)")
    ap.add_argument("--no-figures", action="store_true")
    a = ap.parse_args()
    rows = [json.loads(l) for l in open(ROOT / "test300/rows.jsonl")]
    out, lines = {}, []
    for m in METHODS:
        if not (FULL / m).exists():
            continue
        s = merge(m, rows)
        s["evaluate_ok"] = evaluate(m)
        sec = s.pop("seconds")
        n = max(s["finished"], 1)
        s.update(sum_room_seconds=round(sum(sec), 1), mean_s=round(statistics.mean(sec), 1) if sec else None,
                 median_s=round(statistics.median(sec), 1) if sec else None,
                 p90_s=round(sorted(sec)[int(.9 * (len(sec) - 1))], 1) if sec else None,
                 total_tokens=s["prompt_tokens"] + s["completion_tokens"],
                 tokens_per_room=round((s["prompt_tokens"] + s["completion_tokens"]) / n), requests_per_room=round(s["requests"] / n, 2))
        if a.price_in is not None and a.price_out is not None:
            s["cost_usd"] = round((s["prompt_tokens"] * a.price_in + s["completion_tokens"] * a.price_out) / 1e6, 2)
            s["cost_usd_per_room"] = round(s["cost_usd"] / n, 4)
        out[m] = s
    (FULL / "cost.json").write_text(json.dumps(out, indent=1) + "\n")
    head = ["method", "finished", "with layout", "errors", "missing objects", "requests", "relay retries", "input tok", "cached",
            "output tok", "reasoning", "tokens/room", "s/room (median)", "mean", "p90", "sum of room s"] + (["USD", "USD/room"] if a.price_in is not None else [])
    lines += ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for m, s in out.items():
        vals = [METHODS[m], s["finished"], s["with_layout"], s["errors"], f"{s['missing_objects']}/{s['objects']}", s["requests"], s["failed_attempts"],
                f"{s['prompt_tokens']:,}", f"{s['cached_tokens']:,}", f"{s['completion_tokens']:,}", f"{s['reasoning_tokens']:,}",
                f"{s['tokens_per_room']:,}", s["median_s"], s["mean_s"], s["p90_s"], s["sum_room_seconds"]]
        if a.price_in is not None:
            vals += [s.get("cost_usd"), s.get("cost_usd_per_room")]
        lines.append("| " + " | ".join(str(v) for v in vals) + " |")
    started = ", ".join(f"{m} {(FULL / f'STARTED_{m}').read_text().strip()}" for m in out if (FULL / f"STARTED_{m}").exists()) or "?"
    text = (f"# test300 baselines: time, tokens, cost\n\nModel gpt-5.6-sol, reasoning medium, via the relay. Run started {started}.\n"
            "Tokens are the API's reported usage of answered requests; relay retries (errors with no answer) are counted "
            "separately and returned no usage. Reasoning tokens are part of the output tokens. Seconds per room include "
            "relay retries and the method's own solver / rendering.\n\n" + "\n".join(lines) + "\n")
    (FULL / "COST.md").write_text(text)
    print(text)
    if a.no_figures:
        return
    base = json.loads((ROOT / "server_runs/figures_final/methods.json").read_text())
    for m in out:
        base["methods"].append({"name": METHODS[m], "predictions": str(FULL / m / "predictions.jsonl"),
                                "report": str(FULL / m / "eval/report.json"), "llm_runs": str(FULL / m / "ledger"), "rooms": True})
    cfg = FULL / "methods.json"; cfg.write_text(json.dumps(base, indent=1))
    res = subprocess.run([PY, "-m", "fastfill.v2.ops.method_figures", "--config", str(cfg), "--out", str(FULL / "figures")],
                         cwd=FF, capture_output=True, text=True)
    print(res.stdout[-4000:], res.stderr[-2000:])


if __name__ == "__main__":
    main()
