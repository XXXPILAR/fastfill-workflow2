"""exp150detail size ablation, evaluation (no LLM, no money): our main method on the rooms of rooms30.json (from
test150detail, every object with its detailed description), with FastFill's sizes (ff_sizes) and without FastFill,
GPT's placement call giving the complete draft with every size (gpt_draft), beside FastFill alone and the ground
truth. Only rooms both runs finished are scored.

Layout quality: exp150's checks (exp150/evaluate.py: legality, constraints, our robot checker, SceneEval,
EmbodiedGen, rectangular base), here on test150detail's rows.
Size error, per object: mean |log(size / ground-truth size)| over the three box dimensions, for
  input sizes    what each run placed with: FastFill 1.7B full's prediction / the sizes of GPT's chosen draft
                 (diagnostics.sizes); the train catalog's size (size_catalog.json) as the no-model reference
  final sizes    the boxes of the final layout (step ④'s resize may shrink an object by up to 20 %)
95 % intervals: 2,000 bootstrap resamples of the rooms (seed 0); "FastFill - GPT" is paired on the same objects.

    ../.venv/bin/python experiments/exp150detail/evaluate.py [workers]
"""
import json, math, random, statistics, sys, time
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
W2 = HERE.parents[1]
sys.path[:0] = [str(W2 / "experiments" / "exp150"), str(W2)]
import evaluate as ev  # noqa: E402  (exp150's checks; sets up the checkers' paths)
from fastfill.v2.schema import migrate_legacy_row  # noqa: E402
from workflow.catalog import SizeCatalog  # noqa: E402

ROWS_FILE = W2.parent / "test150detail" / "rows.jsonl"
ROOMS = json.loads((HERE / "rooms30.json").read_text())
FF_FILE = HERE / "fastfill" / "1.7b-all-full" / "predictions_spread.jsonl"
METHODS = ["ground truth", "FastFill alone (1.7B full)", "ours, FastFill sizes", "ours, GPT draft (no FastFill)"]
RUNS = {"ours, FastFill sizes": "ff_sizes", "ours, GPT draft (no FastFill)": "gpt_draft"}


def init():
    ev.ie.ROWS = [migrate_legacy_row(json.loads(l)) for l in open(ROWS_FILE) if l.strip()]


def done_rooms():
    return [k for k in ROOMS if all((HERE / run / f"room_{k:03d}.json").exists() for run in RUNS.values())]


def load(rooms):
    """method -> {room: (layout or None, seconds or None, usd or None, calls or None)}, as exp150's evaluate.load"""
    ff = [json.loads(l) for l in open(FF_FILE)]
    out = {m: {} for m in METHODS}
    for k in rooms:
        out["ground truth"][k] = (ev.ie.ROWS[k]["target"], None, None, None)
        out["FastFill alone (1.7B full)"][k] = (ff[k]["layout"], ff[k]["latency_s"], 0., 0)
        for name, run in RUNS.items():
            r = json.loads((HERE / run / f"room_{k:03d}.json").read_text())
            log = HERE / run / "llm_calls" / f"room_{k:03d}.jsonl"
            calls = sum(1 for l in open(log) if l.strip()) if log.exists() else None
            ff_s = (ff[k]["latency_s"] or 0) if run == "ff_sizes" else 0
            out[name][k] = (r.get("layout"), (r.get("wall_s") or 0) + ff_s, r.get("cost_usd"), calls)
    return out


def gpt_draft_sizes(k):
    """The sizes GPT's chosen draft gave in room k ({id: [depth, width, height]}); the catalog's sizes for objects
    it gave none are left out."""
    d = json.loads((HERE / "gpt_draft" / f"room_{k:03d}.json").read_text()).get("diagnostics") or {}
    sized = set((d.get("draft") or {}).get("sized_by_draft") or ())
    return {i: s for i, s in (d.get("sizes") or {}).items() if i in sized}


def err(size, truth):
    return statistics.mean(abs(math.log(s / t)) for s, t in zip(size, truth))


def size_errors(rooms, src):
    """{source: {room: [(object id, error)]}}: step ② and final sizes, and the catalog, against the ground truth."""
    ff = [json.loads(l) for l in open(FF_FILE)]
    catalog = SizeCatalog(str(W2 / "size_catalog.json"))
    out = {s: {} for s in ("FastFill (input)", "GPT draft (input)", "catalog", "ours, FastFill sizes (final)",
                           "ours, GPT draft (final)")}
    for k in rooms:
        row = ev.ie.ROWS[k]
        truth = {o["id"]: o["target_size_local_m"] for o in row["target"]["objects"]}
        step2 = {"FastFill (input)": {o["id"]: o["target_size_local_m"] for o in (ff[k]["layout"] or {}).get("objects", [])},
                 "GPT draft (input)": gpt_draft_sizes(k),
                 "catalog": {o["id"]: catalog.candidates(o)[0][0] for o in row["condition"]["objects"]}}
        for name, short in (("ours, FastFill sizes", "ours, FastFill sizes"), ("ours, GPT draft (no FastFill)", "ours, GPT draft")):
            layout = src[name][k][0] or {}
            step2[f"{short} (final)"] = {o["id"]: o["target_size_local_m"] for o in layout.get("objects", [])}
        for source, sizes in step2.items():
            out[source][k] = [(i, err(sizes[i], t)) for i, t in truth.items()
                              if i in sizes and all(v > 0 for v in t) and all(v > 0 for v in sizes[i])]
    return out


def boot(rooms, stat, n=2000):
    rng, values = random.Random(0), []
    for _ in range(n):
        v = stat([rooms[rng.randrange(len(rooms))] for _ in rooms])
        if v is not None:
            values.append(v)
    values.sort()
    return values[int(.025 * len(values))], values[int(.975 * len(values)) - 1]


def size_table(rooms, errors):
    def mean_of(source):
        return lambda rs: statistics.mean([e for k in rs for _i, e in errors[source][k]] or [math.nan])
    lines = ["| size source | objects | mean error (95 % CI) | median error | objects within 20 % (error < log 1.2) |",
             "|---|---|---|---|---|"]
    for source in errors:
        es = [e for k in rooms for _i, e in errors[source][k]]
        lo, hi = boot(rooms, mean_of(source))
        lines.append(f"| {source} | {len(es)} | {statistics.mean(es):.3f} ({lo:.3f}–{hi:.3f}) | "
                     f"{statistics.median(es):.3f} | {100 * sum(e < math.log(1.2) for e in es) / len(es):.1f} % |")

    def paired(rs, a="FastFill (input)", b="GPT draft (input)"):
        d = []
        for k in rs:
            eb = dict(errors[b][k])
            d += [e - eb[i] for i, e in errors[a][k] if i in eb]
        return statistics.mean(d) if d else None
    lo, hi = boot(rooms, paired)
    n = sum(1 for k in rooms for i, _e in errors["FastFill (input)"][k] if i in dict(errors["GPT draft (input)"][k]))
    lines.append(f"\nFastFill - GPT draft (input sizes), paired on {n} objects: {paired(rooms):+.3f} (95 % CI {lo:+.3f} to {hi:+.3f}; "
                 "negative: FastFill closer to the ground truth)")
    return "\n".join(lines)


def main():
    t0 = time.perf_counter()
    init()
    rooms = done_rooms()
    src = load(rooms)
    jobs = [(m, k, src[m][k][0]) for m in METHODS for k in rooms]
    recs = {m: [] for m in METHODS}
    with Pool(int(sys.argv[1]) if len(sys.argv) > 1 else 8, initializer=init) as pool:
        for r in pool.imap_unordered(ev.job, jobs):
            recs[r["name"]].append(r)
    table = {m: ev.summarise(recs[m], src[m]) for m in METHODS}
    f = lambda v, fmt: "–" if v is None else fmt.format(v)  # noqa: E731
    lines = ["| metric | " + " | ".join(METHODS) + " |", "|---|" + "---|" * len(METHODS)]
    for key, label, fmt in ev.COLS:
        lines.append(f"| {label} | " + " | ".join(f(table[m][key], fmt if key != "s_median" else "{:.3f}")
                                                  for m in METHODS) + " |")
    errors = size_errors(rooms, src)
    n_obj = sum(len(ev.ie.ROWS[k]["condition"]["objects"]) for k in rooms)
    text = (f"# exp150detail size ablation: {len(rooms)} of {len(ROOMS)} rooms ({n_obj} objects)\n\n"
            + __doc__.split("\n\n    ../")[0] + "\n\n## Layout quality\n\n" + "\n".join(lines)
            + "\n\n## Size error\n\n" + size_table(rooms, errors) + "\n")
    out = HERE / "eval"
    out.mkdir(exist_ok=True)
    (out / "table.md").write_text(text)
    (out / "table.json").write_text(json.dumps({"rooms": rooms, "layout": table,
                                                "size_errors": {s: {str(k): v for k, v in e.items()}
                                                                for s, e in errors.items()}}, indent=1))
    (out / "per_room.json").write_text(json.dumps(recs))
    print(text)
    print(f"{time.perf_counter() - t0:.0f} s", file=sys.stderr)


if __name__ == "__main__":
    main()
