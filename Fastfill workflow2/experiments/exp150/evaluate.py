"""Evaluation of exp150 (no LLM, no money): every method on the same 150 rooms, gpt-6.1-sol medium for all LLM calls.

Per room and method (a missing layout counts as a failed room in every room-level rate):
  objects placed %   objects of the input that the layout contains
  legal %            no collision, nothing out of bounds, no blocked door (robot_check.legality)
  constraints %      the input's constraints that hold
  ours: robot 0.5 m  RobotChecker (our program checker, the one g1 repairs against: not independent evidence)
  SceneEval          its own metric code on box meshes: navigability (0.5 m), collision, out of bounds
  EmbodiedGen        RoamTrajectoryGenerator, clearance 0.25 m: largest free component's share, roam generated
  rect base          a 0.5 x 0.7 m base that must turn, 3D arm (independent code, never optimised against)
Time: wall seconds per room as run (all groups ran at once on one 30 RPM relay, so it includes waiting for the shared
limit and the relay's retries); our groups add FastFill's own GPU seconds for the sizes (fastfill_server/timing).
Cost: tokens at gpt-5.6-sol prices (gpt-6.1-sol's relay price is not known: an estimate, the same for every method).

    ../.venv/bin/python experiments/exp150/evaluate.py [workers]
"""
import json, statistics, sys, time
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
W2 = HERE.parents[1]
SE = W2 / "experiments/session_logs/third_party/sceneeval_subset"  # SceneEval's metric code, as indep_eval ran it
sys.path[:0] = [str(W2), str(W2 / "experiments"), str(W2 / "experiments/session_logs/scripts"), str(SE),
                str(SE / "scenes_stub")]
import indep_eval as ie  # noqa: E402  (SceneEval, EmbodiedGen, rectangular base)
ie.SCR = Path("/tmp") / "exp150_eval"  # SceneEval's scratch output (debug images are not written)
import robot_check as rc  # noqa: E402  (legality, constraints, our robot checker)
from workflow.credentials import PRICES_USD  # noqa: E402

ROOT = W2.parent
BASE = ROOT / "related work code/baselines/runs/exp150_g61"
ROOMS = json.loads((HERE / "rooms.json").read_text())
PRICE_IN, PRICE_CACHED, PRICE_OUT = PRICES_USD["gpt-6.1-sol"]
METHODS = ["ground truth", "FastFill alone", "GPT alone", "LayoutGPT", "Holodeck", "LayoutVLM",
           "ours: GPT + robot prompt, no repair (g2)", "ours without robot (g3)", "ours (g1)"]


def usd(usages):
    total = 0.
    for u in usages:
        cached = ((u.get("prompt_tokens_details") or {}).get("cached_tokens") or 0)
        total += ((u.get("prompt_tokens", 0) - cached) * PRICE_IN + cached * PRICE_CACHED
                  + u.get("completion_tokens", 0) * PRICE_OUT) / 1e6
    return total


def load():
    """method -> {room: (layout or None, seconds or None, usd or None, calls or None)}"""
    ff = [json.loads(l) for l in open(HERE / "fastfill_server/predictions_spread.jsonl")]
    out = {m: {} for m in METHODS}
    for k in ROOMS:
        out["ground truth"][k] = (ie.ROWS[k]["target"], None, None, None)
        out["FastFill alone"][k] = (ff[k]["layout"], ff[k]["latency_s"], 0., 0)
        g = json.loads((HERE / f"gpt_pure/room_{k:03d}.json").read_text())
        out["GPT alone"][k] = (None if g.get("error") else g.get("layout"), g.get("latency_s"), usd(g.get("usage") or []),
                               len(g.get("usage") or []))
        for m, name in (("layoutgpt", "LayoutGPT"), ("holodeck", "Holodeck"), ("layoutvlm", "LayoutVLM")):
            r = json.loads((BASE / m / f"room_{k:03d}/result.json").read_text())
            calls = r.get("calls") or []
            out[name][k] = (r.get("layout"), r.get("seconds"), usd([c["usage"] for c in calls if c.get("usage")]),
                            len(calls))
        for d, name in (("g2_gpt_robot_prompt", METHODS[6]), ("g3_no_robot", METHODS[7]), ("g1_main", METHODS[8])):
            r = json.loads((HERE / d / f"room_{k:03d}.json").read_text())
            t = r.get("tokens") or {}
            log = HERE / d / "llm_calls" / f"room_{k:03d}.jsonl"
            calls = sum(1 for l in open(log) if l.strip()) if log.exists() else None
            out[name][k] = (r.get("layout"), (r.get("wall_s") or 0) + (ff[k]["latency_s"] or 0), r.get("cost_usd"), calls)
    return out


def job(args):
    name, k, layout = args
    row = ie.ROWS[k]
    rec = {"name": name, "room": k, "objects": len(row["condition"]["objects"])}
    if not layout:
        return rec
    placed = {o["id"] for o in layout["objects"]}
    rec["placed"] = sum(o["id"] in placed for o in row["condition"]["objects"])
    try:
        rec["check"] = rc.check_room(row, layout)
    except Exception as e:
        rec["check"] = {"error": f"{type(e).__name__}: {e}"[:200]}
    rec.update(ie.job((name, k, layout)))
    return rec


def init():
    ie.init()


def pct(h, n):
    return 100 * h / n if n else None


def summarise(recs, info):
    n = len(recs)
    have = [r for r in recs if "check" in r and "error" not in r["check"]]
    leg = [r["check"]["legality"] for r in have]
    rob = [r["check"]["robot"]["0.5"] for r in have]
    se = [r["sceneeval"] for r in have if "error" not in r["sceneeval"]]
    eg = [r["embodiedgen"] for r in have if "error" not in r["embodiedgen"]]
    rb = [r["rect"] for r in have if "error" not in r["rect"]]
    complete = [r for r in have if r["placed"] == r["objects"]]
    legal_full = [r for r in complete if r["check"]["legality"]["legal"]
                  and r["check"]["legality"]["constraints"][0] == r["check"]["legality"]["constraints"][1]]
    secs = sorted(s for _l, s, _u, _c in info.values() if s is not None)
    cost = [u for _l, _s, u, _c in info.values() if u is not None]
    calls = [c for _l, _s, _u, c in info.values() if c is not None]
    return {
        "layouts": len(have), "rooms": n,
        "placed": pct(sum(r["placed"] for r in have), sum(r["objects"] for r in recs)),
        "legal": pct(sum(x["legal"] for x in leg), n),
        "constraints": pct(sum(x["constraints"][0] for x in leg), sum(x["constraints"][1] for x in leg)),
        "usable": pct(len(legal_full), n),
        "robot_ok": pct(sum(r["check"]["robot"]["0.5"]["ok"] for r in legal_full), n),
        "doors_linked": pct(sum(x["doors_unlinked"] == 0 for x in rob if x["doors"]), sum(1 for x in rob if x["doors"])),
        "required": pct(sum(x["required"] - x["required_unreached"] for x in rob), sum(x["required"] for x in rob)),
        "items": pct(sum(x["items"] - x["items_unreached"] for x in rob), sum(x["items"] for x in rob)),
        "openable": pct(sum(x["openable"] - x["openable_blocked"] for x in rob), sum(x["openable"] for x in rob)),
        "se_nav": 100 * statistics.mean(x["nav0.5"] for x in se) if se else None,
        "se_col": pct(sum(x["col"][0] for x in se), sum(x["col"][1] for x in se)),
        "se_oob": pct(sum(x["oob"][0] for x in se), sum(x["oob"][1] for x in se)),
        "eg_share": 100 * statistics.mean(x["largest_share"] for x in eg) if eg else None,
        "eg_roam": pct(sum(x["roam_ok"] for x in eg), n),
        "rect_furniture": pct(sum(x["furniture_reached"] for x in rb), sum(x["furniture"] for x in rb)),
        "rect_items": pct(sum(x["items_reached"] for x in rb), sum(x["items"] for x in rb)),
        "rect_ok": pct(sum(x["ok"] for x in rb), n),
        "s_median": secs[len(secs) // 2] if secs else None, "s_p90": secs[int(.9 * (len(secs) - 1))] if secs else None,
        "usd_room": statistics.mean(cost) if cost else None, "calls_room": statistics.mean(calls) if calls else None}


COLS = [("layouts", "layouts", "{:.0f}"), ("placed", "objects placed %", "{:.1f}"), ("legal", "legal rooms %", "{:.1f}"),
        ("constraints", "constraints %", "{:.1f}"), ("usable", "complete+legal+constraints rooms %", "{:.1f}"),
        ("robot_ok", "…and robot ok (ours 0.5 m) %", "{:.1f}"), ("doors_linked", "doors linked %", "{:.1f}"),
        ("required", "work furniture reached %", "{:.1f}"), ("items", "items in arm reach %", "{:.1f}"),
        ("openable", "doors/drawers open %", "{:.1f}"),
        ("se_nav", "SceneEval nav 0.5 m %", "{:.1f}"), ("se_col", "SceneEval objects colliding %", "{:.1f}"),
        ("se_oob", "SceneEval out of bounds %", "{:.1f}"), ("eg_share", "EmbodiedGen largest free %", "{:.1f}"),
        ("eg_roam", "EmbodiedGen roam ok rooms %", "{:.1f}"), ("rect_furniture", "rect base: furniture parked %", "{:.1f}"),
        ("rect_items", "rect base: items in 3D reach %", "{:.1f}"), ("rect_ok", "rect base: rooms all reached %", "{:.1f}"),
        ("s_median", "s / room (median)", "{:.0f}"), ("s_p90", "s / room (p90)", "{:.0f}"),
        ("calls_room", "LLM calls / room", "{:.1f}"), ("usd_room", "$ / room (est.)", "{:.3f}")]


def main():
    t0 = time.perf_counter()
    init()
    src = load()
    jobs = [(m, k, src[m][k][0]) for m in METHODS for k in ROOMS]
    recs = {m: [] for m in METHODS}
    with Pool(int(sys.argv[1]) if len(sys.argv) > 1 else 8, initializer=init) as pool:
        for n, r in enumerate(pool.imap_unordered(job, jobs)):
            recs[r["name"]].append(r)
            if (n + 1) % 50 == 0:
                print(f"{n + 1}/{len(jobs)} {time.perf_counter() - t0:.0f} s", file=sys.stderr, flush=True)
    table = {m: summarise(recs[m], src[m]) for m in METHODS}
    f = lambda v, fmt: "–" if v is None else fmt.format(v)  # noqa: E731
    lines = ["| metric | " + " | ".join(METHODS) + " |", "|---|" + "---|" * len(METHODS)]
    for key, label, fmt in COLS:
        lines.append(f"| {label} | " + " | ".join(f(table[m][key], fmt) for m in METHODS) + " |")
    text = "# exp150: 150 rooms, every method on gpt-6.1-sol medium\n\n" + __doc__.split("\n\n    ../")[0] + "\n\n" + \
        "\n".join(lines) + "\n"
    out = HERE / "eval"
    out.mkdir(exist_ok=True)
    (out / "table.md").write_text(text)
    (out / "table.json").write_text(json.dumps(table, indent=1))
    (out / "per_room.json").write_text(json.dumps(recs))
    print(text)
    print(f"{time.perf_counter() - t0:.0f} s", file=sys.stderr)


if __name__ == "__main__":
    main()
