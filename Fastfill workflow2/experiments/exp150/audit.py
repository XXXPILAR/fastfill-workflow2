"""Completeness check of exp150: every group, every room. A room is

  ok       finished with every LLM answer it asked for
  gap      an LLM call failed (busy relay, dropped connection, no answer) or the room was not finished: it must be
           run again (``--fix`` deletes its record so that a restart of run_all.sh redoes it)
  model    finished, but what the model returned is the result itself (unparseable answer, objects the method
           could not place): kept, it is the method's outcome, not a missing value

Our groups (g1/g2/g3): a gap is a room file that is missing, has status "error", a plan that fell back to rules
because the LLM failed ("rules (llm failed)"), a draft call that errored, or a review that errored (g1/g3). FastFill
over its context budget (room 162) is not a gap: that room uses the size catalog in every run, in-process or not.
gpt_pure: a gap is a missing room or a transport error (no reply); an unparseable reply is "model".
Baselines: a gap is a missing room or a result without a layout.

    ../.venv/bin/python experiments/exp150/audit.py            # report
    ../.venv/bin/python experiments/exp150/audit.py --fix      # and delete the gap rooms' records
"""
import argparse, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[2] / "related work code" / "baselines" / "runs" / "exp150_g61"
TRANSPORT = ("URLError", "Connection", "relay gave no", "busy", "KeyError: 'choices'", "LLM request failed",
             "timed out", "Timeout", "HTTP 5", "HTTP 429", "upstream")


def ours(group: str, k: int):
    f = HERE / group / f"room_{k:03d}.json"
    if not f.exists():
        return "gap", "not run", f
    r = json.loads(f.read_text())
    if r.get("status") == "error" or not r.get("layout"):
        return "gap", f"status {r.get('status')}: {str(r.get('error'))[:80]}", f
    d = r["diagnostics"]
    if "llm failed" in str(d.get("plan_source")):
        return "gap", "plan fell back to rules (LLM failed)", f
    draft = d.get("draft") or {}
    errors = [draft.get("error")] + [c.get("error") for c in draft.get("candidates") or []]
    if any(errors):
        return "gap", f"draft error: {str([e for e in errors if e][0])[:80]}", f
    review = d.get("semantic") or {}
    if review.get("result") == "error":
        return "gap", f"review error: {str(review.get('error'))[:80]}", f
    return "ok", "", f


def gpt_pure(k: int):
    f = HERE / "gpt_pure" / f"room_{k:03d}.json"
    if not f.exists():
        return "gap", "not run", f
    r = json.loads(f.read_text())
    if r.get("error"):
        if r.get("reply") is None or any(t in r["error"] for t in TRANSPORT):
            return "gap", r["error"][:80], f
        return "model", r["error"][:80], f
    return ("ok", "", f) if r.get("layout") else ("gap", "no layout", f)


def baseline(method: str, k: int):
    f = BASE / method / f"room_{k:03d}" / "result.json"
    if not f.exists():
        return "gap", "not run", f
    r = json.loads(f.read_text())
    return ("ok", "", f) if r.get("layout") else ("gap", str(r.get("error"))[:80], f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true", help="delete the records of gap rooms that were run")
    a = ap.parse_args()
    rooms = json.loads((HERE / "rooms.json").read_text())
    checks = {g: (lambda k, g=g: ours(g, k)) for g in ("g1_main", "g2_gpt_robot_prompt", "g3_no_robot")}
    checks["gpt_pure"] = gpt_pure
    for m in ("layoutgpt", "holodeck", "layoutvlm"):
        checks[m] = lambda k, m=m: baseline(m, k)
    total_gap = 0
    for group, check in checks.items():
        verdicts = {k: check(k) for k in rooms}
        count = {v: sum(x[0] == v for x in verdicts.values()) for v in ("ok", "gap", "model")}
        run_gaps = [(k, why, f) for k, (v, why, f) in verdicts.items() if v == "gap" and why != "not run"]
        total_gap += count["gap"]
        print(f"{group:22} ok {count['ok']:3}  model {count['model']:3}  gap {count['gap']:3}"
              f"  (not run yet {count['gap'] - len(run_gaps)}, failed {len(run_gaps)})")
        for k, why, f in run_gaps[:8]:
            print(f"    room {k}: {why}")
        if a.fix:
            for k, why, f in run_gaps:
                f.unlink()
            if run_gaps:
                print(f"    deleted {len(run_gaps)} failed room records: a restart of run_all.sh redoes them")
    print("COMPLETE: no gaps" if total_gap == 0 else f"gaps left: {total_gap}")


if __name__ == "__main__":
    main()
