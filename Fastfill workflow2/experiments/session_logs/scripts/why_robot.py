import json, sys, collections
from pathlib import Path
HERE = Path("/Users/zhangyang/Downloads/fastfill-v4/Fastfill workflow2")
sys.path[:0] = [str(HERE), str(HERE / "experiments")]
from shapely.geometry import Polygon
from big_table import ROOT, sources
from fastfill.v2.ops import layout_quality as lq
from fastfill.v2.schema import migrate_legacy_row
from workflow.robot import Robot, RobotChecker, infer_parents

rows = [migrate_legacy_row(json.loads(l)) for l in open(ROOT / "test300/rows.jsonl") if l.strip()]
src = sources(rows)
rooms = sorted(src["workflow2 simple (one place, one check, one review)"])
rooms = [i for i in rooms if src["workflow2 simple (one place, one check, one review)"][i][0]]
W = float(sys.argv[1]) if len(sys.argv) > 1 else .5

def rep(i, lay):
    bs = lq.boxes(rows[i], lay)
    return RobotChecker(Robot(width_m=W), rows[i]["condition"]).report(lay, infer_parents(bs)), bs

def fill(i, lay):
    floor = Polygon(rows[i]["condition"]["room"]["floor_polygon_xy_m"]).buffer(0)
    bs = lq.boxes(rows[i], lay)
    return sum(b["poly"].area for b in bs if b.get("obstacle", True) and b["poly"].area > 0) / floor.area

methods = {"GT": lambda i: src["ground truth"][i][0], "GPT": lambda i: src["GPT-5.6 one-shot"][i][0]}
for st in ("draft", "after_check", "final"):
    methods["wf2 " + st] = (lambda st: lambda i: json.load(open(HERE / f"experiments/simple20/room_{i:03d}.json"))["diagnostics"]["stages"][st])(st)

tot = collections.defaultdict(lambda: collections.Counter())
per = {}
for name, get in methods.items():
    for i in rooms:
        lay = get(i)
        if not lay: continue
        r, bs = rep(i, lay)
        c = tot[name]
        c["rooms"] += 1; c["ok"] += r["ok"]
        for k in ("required", "required_unreached", "openable", "openable_blocked", "items", "items_unreached", "doors_unlinked"):
            c[k] += r[k]
        c["fill"] += fill(i, lay)
        for code, fs in r["failures"].items():
            for f in fs:
                c["n_" + code] += 1
                if code == "robot_openable":
                    c["open_wall" if "wall" in f["detail"] else "open_obj"] += 1
        per[(name, i)] = r
print(f"width {W}")
print("method        rooms ok  req_reach  open_free  items  fill  door  | open: wall/obj")
for n, c in tot.items():
    p = lambda a, b: 100 * (c[b] - c[a]) / c[b] if c[b] else 0
    print(f"{n:12s} {c['rooms']:3d} {c['ok']:3d}  {p('required_unreached','required'):6.1f}  {p('openable_blocked','openable'):6.1f}  {p('items_unreached','items'):6.1f}  {c['fill']/c['rooms']:.2f}  {c['doors_unlinked']}  | {c['open_wall']}/{c['open_obj']}  req={c['required']} open={c['openable']}")

# failure provenance: final failures present in the draft?
print("\nfinal failures by provenance (same code + same first id in draft / after_check)")
prov = collections.Counter()
for i in rooms:
    keys = lambda st: {(code, (f["object_ids"] or ["-"])[0]) for code, fs in per.get((st, i), {"failures": {}})["failures"].items() for f in fs}
    d, a, fi = keys("wf2 draft"), keys("wf2 after_check"), keys("wf2 final")
    for k in fi:
        prov[(k[0], "in draft" if k in d else ("added by check/repair" if k in a else "added by review"))] += 1
    for k in d - fi:
        prov[(k[0], "draft fail fixed")] += 1
for k, v in sorted(prov.items()): print(k, v)

# blockers / details for final
print("\nfinal failure details")
for i in rooms:
    r = per[("wf2 final", i)]
    cat = {o["id"]: o["category"] for o in rows[i]["condition"]["objects"]}
    for code, fs in r["failures"].items():
        for f in fs:
            print(i, code, [cat.get(x, x) for x in f["object_ids"]], f["detail"][:110])

print("\nper room: GPT vs wf2 final  (req_unreached/req, open_blocked/open, items_unreached/items, fill)")
for i in rooms:
    g, f = per[("GPT", i)], per[("wf2 final", i)]
    t = per[("GT", i)]
    s = lambda r: f"{r['required_unreached']}/{r['required']} {r['openable_blocked']}/{r['openable']} {r['items_unreached']}/{r['items']}"
    print(i, rows[i]["condition"]["room"].get("room_type", ""), len(rows[i]["condition"]["objects"]), "| GT", s(t), "| GPT", s(g), "| wf2", s(f),
          f"| fill GPT {fill(i, methods['GPT'](i)):.2f} wf2 {fill(i, methods['wf2 final'](i)):.2f}")
# sizes: wf2 vs GPT vs GT footprint per object
import statistics as st
ratios = collections.defaultdict(list)
for i in rooms:
    a = {b["id"]: b["poly"].area for b in lq.boxes(rows[i], methods["GT"](i))}
    for n in ("GPT", "wf2 final"):
        for b in lq.boxes(rows[i], methods[n](i)):
            if a.get(b["id"]) and b["poly"].area: ratios[n].append(b["poly"].area / a[b["id"]])
for n, v in ratios.items(): print(n, "footprint / GT median", round(st.median(v), 2), "mean", round(st.mean(v), 2))
