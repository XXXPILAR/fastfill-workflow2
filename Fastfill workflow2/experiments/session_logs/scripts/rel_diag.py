import json, sys, collections
from pathlib import Path
sys.path.insert(0, ".")
from workflow.contract import check_request  # noqa
from fastfill.v2.ops import layout_quality as lq
from fastfill.v2.schema import migrate_legacy_row
rows = [json.loads(l) for l in open("../test300/rows.jsonl")]
idx = [15,129,197,200,22,43,70,109,29,61,68,79,63,66,81,84,86,103,108,110]
E = Path("experiments")
T = json.loads(Path("experiments/quality50/eval_templates_odd.json").read_text())["templates"]
def cf(i):
    for d in ("orders_test50_server", "orders_AC_rest30_server"):
        p = E / d / "C_final" / f"room_{i:03d}.json"
        if p.exists(): return json.loads(p.read_text())
fails = {"staged": collections.Counter(), "C_final": collections.Counter()}
print("room n  staged hits/total   C_final hits/total")
for i in idx:
    row = migrate_legacy_row(rows[i]); out = []
    for name, r in (("staged", json.loads((E/"local_staged20"/f"room_{i:03d}.json").read_text())), ("C_final", cf(i))):
        if not r.get("layout"): out.append("failed"); continue
        bs = lq.boxes(row, r["layout"]); st = lq.pair_stats(bs); h = t = 0
        for tp in T:
            for gap, faces in st.get((tp["a"], tp["b"]), ()):
                ok = (gap <= tp["max_gap_m"]) if tp["kind"] == "near" else faces
                h += ok; t += 1
                if not ok: fails[name][(tp["kind"], tp["a"], tp["b"])] += 1
        out.append(f"{h}/{t}")
    print(i, len(rows[i]["condition"]["objects"]), *out)
for name, c in fails.items():
    print(name, sum(c.values()), c.most_common(12))
