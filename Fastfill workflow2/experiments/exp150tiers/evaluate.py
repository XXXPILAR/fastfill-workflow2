"""exp150tiers evaluation (no LLM, no money): every method on the easy / medium / hard versions of the same 40 rooms
(test150tiers, after EmbodiedGen's complexity levels; see its README), scored with exp150's checks (exp150/evaluate.py:
legality, constraints, our robot checker, SceneEval, EmbodiedGen, rectangular base) and the size error
(mean |log(size / ground-truth size)| over the three dimensions, per object).

A method's easy and medium layouts come from its run on test150tiers/rows.jsonl; its hard layouts are its run on
test150detail (the hard version is that row), so the main experiment's results are reused. A method is shown when
its results exist; the summary compares levels only on the rooms a method has all three versions of ("paired").

    ../.venv/bin/python experiments/exp150tiers/evaluate.py [workers]
"""
import json, math, statistics, sys, time
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
W2 = HERE.parents[1]
sys.path[:0] = [str(W2 / "experiments" / "exp150"), str(W2)]
import evaluate as ev  # noqa: E402  (exp150's checks; sets up the checkers' paths)
from fastfill.v2.schema import migrate_legacy_row  # noqa: E402

ROOT = W2.parent
TIERS = ROOT / "test150tiers"
BASE_ROWS = ROOT / "test150detail" / "rows.jsonl"
DETAIL = W2 / "experiments" / "exp150detail"
LEVELS = ("easy", "medium", "hard")
VERSIONS = json.loads((TIERS / "MANIFEST.json").read_text())["versions"]
OFFSET = 1000  # tier row r is room OFFSET + r in the combined row list; hard is the test150detail index

# name -> (kind, easy/medium source on test150tiers, hard source on test150detail)
FASTFILL = [("FastFill 8B base", "8b-base"), ("FastFill 1.7B full", "1.7b-all-full"),
            ("FastFill 1.7B LoRA r64a128", "1.7b-all-r64a128"), ("FastFill 1.7B LoRA r8a32", "1.7b-all-r8a32"),
            ("FastFill 4B full", "4b-all-full"), ("FastFill 4B LoRA r64a128", "4b-all-r64a128"),
            ("FastFill 4B LoRA r8a32", "4b-all-r8a32")]
METHODS = {"ground truth": ("truth", None, None),
           **{name: ("predictions", HERE / f"fastfill/{run}/predictions_spread.jsonl",
                     DETAIL / f"fastfill/{run}/predictions_spread.jsonl") for name, run in FASTFILL},
           "GPT alone": ("gpt_pure", HERE / "gpt_pure", DETAIL / "gpt_pure"),
           "ours, FastFill sizes": ("run_draft", HERE / "ff_sizes", DETAIL / "ff_sizes"),
           "ours, GPT draft (no FastFill)": ("run_draft", HERE / "gpt_draft", DETAIL / "gpt_draft")}


def rows():
    base = [migrate_legacy_row(json.loads(l)) for l in open(BASE_ROWS) if l.strip()]
    tier = [migrate_legacy_row(json.loads(l)) for l in open(TIERS / "rows.jsonl") if l.strip()]
    return base, tier


def init():
    base, tier = rows()
    combined = base + [None] * (OFFSET - len(base)) + tier
    ev.ie.ROWS = combined


def key(v):
    return v["base_index"] if v["row"] is None else OFFSET + v["row"]


def load():
    """method -> {(level, base room): (layout or None, seconds or None, usd or None, calls or None)}"""
    cache, out = {}, {}
    for name, (kind, tier_src, hard_src) in METHODS.items():
        got = {}
        for v in VERSIONS:
            k, src = key(v), (hard_src if v["row"] is None else tier_src)
            index = v["base_index"] if v["row"] is None else v["row"]
            if kind == "truth":
                got[(v["level"], v["base_index"])] = (ev.ie.ROWS[k]["target"], None, None, None)
            elif kind == "predictions":
                if src.exists():
                    lines = cache.setdefault(src, [json.loads(l) for l in open(src)])
                    p = lines[index]
                    got[(v["level"], v["base_index"])] = (p.get("layout"), p.get("latency_s"), 0., 0)
            else:
                f = src / f"room_{index:03d}.json"
                if f.exists():
                    r = json.loads(f.read_text())
                    if kind == "gpt_pure":
                        usage = r.get("usage") or []
                        got[(v["level"], v["base_index"])] = (None if r.get("error") else r.get("layout"),
                                                              r.get("latency_s"), ev.usd(usage), len(usage))
                    else:
                        log = src / "llm_calls" / f"room_{index:03d}.jsonl"
                        calls = sum(1 for l in open(log) if l.strip()) if log.exists() else None
                        got[(v["level"], v["base_index"])] = (r.get("layout"), r.get("wall_s"), r.get("cost_usd"), calls)
        if got:
            out[name] = got
    return out


def size_errors(layout, row):
    if not layout:
        return []
    truth = {o["id"]: o["target_size_local_m"] for o in row["target"]["objects"]}
    return [statistics.mean(abs(math.log(s / t)) for s, t in zip(o["target_size_local_m"], truth[o["id"]]))
            for o in layout["objects"] if o["id"] in truth and min(truth[o["id"]]) > 0 and min(o["target_size_local_m"]) > 0]


KEY = [("usable", "complete+legal+constraints rooms %"), ("robot_ok", "…and robot ok %"), ("legal", "legal rooms %"),
       ("se_col", "SceneEval colliding %"), ("se_oob", "SceneEval out of bounds %"),
       ("rect_ok", "rect base: all reached %"), ("size", "size error (mean)")]


def main():
    t0 = time.perf_counter()
    init()
    src = load()
    names = list(src)
    rooms = sorted({v["base_index"] for v in VERSIONS})
    paired = {m: [b for b in rooms if all((lvl, b) in src[m] for lvl in LEVELS)] for m in names}
    names = [m for m in names if paired[m]]  # a method without one room in all three versions is not shown yet
    jobs = [(f"{m}|{v['level']}", key(v), src[m][(v["level"], v["base_index"])][0])
            for m in names for v in VERSIONS if v["base_index"] in paired[m]]
    recs = {}
    with Pool(int(sys.argv[1]) if len(sys.argv) > 1 else 8, initializer=init) as pool:
        for r in pool.imap_unordered(ev.job, jobs):
            recs.setdefault(r["name"], []).append(r)
    table = {}
    for m in names:
        for lvl in LEVELS:
            name = f"{m}|{lvl}"
            info = {b: src[m][(lvl, b)] for b in paired[m]}
            s = ev.summarise(recs.get(name, []), info)
            errs = [e for v in VERSIONS if v["level"] == lvl and v["base_index"] in paired[m]
                    for e in size_errors(src[m][(lvl, v["base_index"])][0], ev.ie.ROWS[key(v)])]
            s["size"] = statistics.mean(errs) if errs and m != "ground truth" else None
            s["paired_rooms"] = len(paired[m])
            table[name] = s
    f = lambda v, fmt="{:.1f}": "–" if v is None else fmt.format(v)  # noqa: E731
    n_obj = {lvl: sum(v["objects"] for v in VERSIONS if v["level"] == lvl) for lvl in LEVELS}
    lines = ["| method | rooms | " + " | ".join(f"{label}: easy / medium / hard" for _k, label in KEY) + " |",
             "|---|---|" + "---|" * len(KEY)]
    for m in names:
        cells = [" / ".join(f(table[f"{m}|{lvl}"][k], "{:.3f}" if k == "size" else "{:.1f}") for lvl in LEVELS)
                 for k, _label in KEY]
        lines.append(f"| {m} | {len(paired[m])} | " + " | ".join(cells) + " |")
    detail = []
    for lvl in LEVELS:
        cols = names
        detail += [f"\n### {lvl} ({n_obj[lvl]} objects in all 40 rooms)\n",
                   "| metric | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]
        for k, label, fmt in ev.COLS:
            detail.append(f"| {label} | " + " | ".join(f(table[f'{m}|{lvl}'][k], fmt if k != 's_median' else '{:.3f}')
                                                     for m in cols) + " |")
    text = (f"# exp150tiers: easy / medium / hard versions of 40 rooms\n\n" + __doc__.split("\n\n    ../")[0]
            + f"\n\nObjects in all 40 rooms: easy {n_obj['easy']}, medium {n_obj['medium']}, hard {n_obj['hard']}. "
            + "Each method is scored on the rooms it has all three versions of (column rooms).\n\n## Summary\n\n"
            + "\n".join(lines) + "\n\n## All metrics by level\n" + "\n".join(detail) + "\n")
    out = HERE / "eval"
    out.mkdir(exist_ok=True)
    (out / "table.md").write_text(text)
    (out / "table.json").write_text(json.dumps({"paired_rooms": paired, "table": table}, indent=1))
    (out / "per_room.json").write_text(json.dumps(recs))
    print(text)
    print(f"{time.perf_counter() - t0:.0f} s", file=sys.stderr)


if __name__ == "__main__":
    main()
