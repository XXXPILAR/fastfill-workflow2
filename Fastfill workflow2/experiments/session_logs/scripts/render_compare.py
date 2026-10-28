import json, sys, math, hashlib
from pathlib import Path
sys.path.insert(0, ".")
import workflow.contract  # noqa (fastfill on path)
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly
from shapely.geometry import Polygon
from fastfill.v2.ops import layout_quality as lq
from fastfill.v2.cell_costs import door_zones
from fastfill.v2.schema import migrate_legacy_row
OUT = Path(sys.argv[1]); rooms = [int(x) for x in sys.argv[2:]]
rows = [json.loads(l) for l in open("../test300/rows.jsonl")]
gpt = [json.loads(l).get("layout") for l in open("../test300/gpt56/predictions.jsonl")]
def ours(d, i):
    p = Path("experiments") / d / f"room_{i:03d}.json"
    return json.loads(p.read_text()).get("layout") if p.exists() else None
def cfinal(i):
    for d in ("orders_test50_server/C_final", "orders_AC_rest30_server/C_final"):
        l = ours(d, i)
        if l: return l
def col(cat):
    h = hashlib.md5(cat.encode()).digest(); return tuple(.25 + .7 * b / 255 for b in h[:3])
def panel(ax, row, layout, title):
    room = row["condition"]["room"]; floor = Polygon(room["floor_polygon_xy_m"])
    ax.add_patch(MPoly(list(floor.exterior.coords), closed=True, fc="#eeeeee", ec="k", lw=1.5))
    for z in door_zones(room, .8):
        ax.add_patch(MPoly(z, closed=True, fc="#ffcccc", ec="r", lw=.8, alpha=.6))
    for p in lq.fixed_obstacles(row):
        ax.add_patch(MPoly(list(p.exterior.coords), closed=True, fc="#555555", ec="k"))
    if layout:
        bs = sorted(lq.boxes(row, layout), key=lambda b: (b["bottom"], b["size"][2]))
        for b in bs:
            raised = b["bottom"] > lq.FLOOR_M
            ax.add_patch(MPoly(list(b["poly"].exterior.coords), closed=True, fc=col(b["cat"]), ec="k",
                               lw=.6, alpha=.55 if raised else .9, ls="--" if raised else "-"))
            cx, cy = b["centre"]; L = min(b["size"][0], b["size"][1]) * .45 + .05
            ax.arrow(cx, cy, b["front"][0] * L, b["front"][1] * L, head_width=.07, color="k", lw=.6, length_includes_head=True)
            ax.text(cx, cy, b["head"][:10], fontsize=5.5, ha="center", va="center")
    x0, y0, x1, y1 = floor.bounds
    ax.set_xlim(x0 - .3, x1 + .3); ax.set_ylim(y0 - .3, y1 + .3); ax.set_aspect("equal"); ax.set_title(title, fontsize=8)
    ax.set_xticks([]); ax.set_yticks([])
for i in rooms:
    row = migrate_legacy_row(rows[i])
    staged = ours("local_room63_v2", i) if i == 63 else ours("local_staged20", i)
    panels = [("ground truth", row["target"]), ("ours: staged", staged), ("ours: C_final", cfinal(i)), ("GPT-5.6 one-shot", gpt[i])]
    fig, axs = plt.subplots(1, 4, figsize=(16, 4.6))
    for ax, (t, lay) in zip(axs, panels): panel(ax, row, lay, f"{t}" + ("" if lay else " (none)"))
    fig.suptitle(f"room {i} ({len(rows[i]['condition']['objects'])} objects, {rows[i]['condition']['room'].get('room_type')}); "
                 "red = door zone, dashed = on furniture/wall, arrow = front", fontsize=9)
    fig.tight_layout(); fig.savefig(OUT / f"room_{i:03d}.png", dpi=110); plt.close(fig)
    print("saved", i)
