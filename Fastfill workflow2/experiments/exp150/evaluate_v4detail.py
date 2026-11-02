"""exp150, FastFill alone: the 8B base run (fastfill_server) against the six v4detail every-room models
(fastfill_v4detail/<run>, 2026-11-01: trained on SAGE-10k + IL3D only, every training row with its detailed descriptions)
on the same 150 rooms, with exp150's checks (evaluate.py: legality, constraints, our robot checker, SceneEval,
EmbodiedGen, rectangular base). No LLM, no money. Writes eval/v4detail_table.md, eval/v4detail_table.json and
eval/v4detail_per_room.json.

    ../.venv/bin/python experiments/exp150/evaluate_v4detail.py [workers]
"""
import json, sys, time
from multiprocessing import Pool

import evaluate as ev  # noqa: E402  (sits beside this file; sets up the checkers' paths)

RUNS = [("1.7B full", "1.7b-all-full"), ("1.7B LoRA r64 a128", "1.7b-all-r64a128"), ("1.7B LoRA r8 a32", "1.7b-all-r8a32"),
        ("4B full", "4b-all-full"), ("4B LoRA r64 a128", "4b-all-r64a128"), ("4B LoRA r8 a32", "4b-all-r8a32")]
METHODS = ["ground truth", "8B base (all sources)"] + [name for name, _ in RUNS]


def load():
    """method -> {room: (layout or None, seconds or None, usd, calls)}, as evaluate.load"""
    files = {"8B base (all sources)": ev.HERE / "fastfill_server/predictions_spread.jsonl",
             **{name: ev.HERE / f"fastfill_v4detail/{run}/predictions_spread.jsonl" for name, run in RUNS}}
    out = {m: {} for m in METHODS}
    for name, path in files.items():
        ff = [json.loads(l) for l in open(path)]
        for k in ev.ROOMS:
            out[name][k] = (ff[k]["layout"], ff[k]["latency_s"], 0., 0)
    for k in ev.ROOMS:
        out["ground truth"][k] = (ev.ie.ROWS[k]["target"], None, None, None)
    return out


def main():
    t0 = time.perf_counter()
    ev.init()
    src = load()
    jobs = [(m, k, src[m][k][0]) for m in METHODS for k in ev.ROOMS]
    recs = {m: [] for m in METHODS}
    with Pool(int(sys.argv[1]) if len(sys.argv) > 1 else 8, initializer=ev.init) as pool:
        for n, r in enumerate(pool.imap_unordered(ev.job, jobs)):
            recs[r["name"]].append(r)
            if (n + 1) % 100 == 0:
                print(f"{n + 1}/{len(jobs)} {time.perf_counter() - t0:.0f} s", file=sys.stderr, flush=True)
    table = {m: ev.summarise(recs[m], src[m]) for m in METHODS}
    f = lambda v, fmt: "–" if v is None else fmt.format(v)  # noqa: E731
    cols = [c for c in ev.COLS if c[0] not in ("calls_room", "usd_room", "s_p90")]
    lines = ["| metric | " + " | ".join(METHODS) + " |", "|---|" + "---|" * len(METHODS)]
    for key, label, fmt in cols:
        lines.append(f"| {label} | " + " | ".join(f(table[m][key], fmt if key != "s_median" else "{:.3f}") for m in METHODS) + " |")
    text = "# exp150, FastFill alone: 8B base against the v4detail models\n\n" + __doc__.split("\n\n    ../")[0] + "\n\n" + \
        "\n".join(lines) + "\n"
    out = ev.HERE / "eval"
    out.mkdir(exist_ok=True)
    (out / "v4detail_table.md").write_text(text)
    (out / "v4detail_table.json").write_text(json.dumps(table, indent=1))
    (out / "v4detail_per_room.json").write_text(json.dumps(recs))
    print(text)
    print(f"{time.perf_counter() - t0:.0f} s", file=sys.stderr)


if __name__ == "__main__":
    main()
