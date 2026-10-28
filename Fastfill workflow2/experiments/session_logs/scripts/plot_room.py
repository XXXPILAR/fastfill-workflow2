import json,sys
sys.path.insert(0,'.')
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from workflow.robot import Robot, RobotChecker, sweep, openable
from fastfill.v2.ops import layout_quality as lq
from fastfill.v2.schema import migrate_legacy_row
rows=[migrate_legacy_row(json.loads(l)) for l in open("../test300/rows.jsonl")]
def draw(ax, i, layout, title, w=.5):
    r=rows[i]; ck=RobotChecker(Robot(width_m=w), r["condition"])
    bs=lq.boxes(ck.row, layout); obs=[b for b in bs if lq.obstacle(b)]
    regions, main = ck._space(obs)
    ax.plot(*ck.floor.exterior.xy,'k')
    for g in regions: ax.fill(*g.exterior.xy, color=('lightgreen' if g is main else 'khaki'))
    for d in ck.door_zones: ax.fill(*d.exterior.xy,color='blue',alpha=.3)
    for f in ck.fixed: ax.fill(*f.exterior.xy,color='gray')
    cats={o["id"]:o["category"] for o in r["condition"]["objects"]}
    for b in bs:
        ax.plot(*b["poly"].exterior.xy, 'r' if lq.obstacle(b) else 'm', lw=1)
        c=b["centre"]; ax.arrow(c[0],c[1],*(b["front"]*.25),head_width=.06,color='k')
        ax.text(c[0],c[1],b["id"][-2:]+" "+cats[b["id"]][:12],fontsize=6)
        if openable(b): ax.fill(*sweep(b).exterior.xy,color='orange',alpha=.35)
    ax.set_aspect('equal'); ax.set_title(title,fontsize=8)
if __name__=="__main__":
    idx=[int(x) for x in sys.argv[1].split(",")]
    fig,axs=plt.subplots(1,len(idx)*2,figsize=(7*len(idx),5))
    for k,i in enumerate(idx):
        draw(axs[2*k],i,json.load(open(f"experiments/simple20/room_{i:03d}.json"))["layout"],f"room {i} workflow2")
        draw(axs[2*k+1],i,rows[i]["target"],f"room {i} GT")
    plt.savefig(sys.argv[2],dpi=110,bbox_inches='tight')
