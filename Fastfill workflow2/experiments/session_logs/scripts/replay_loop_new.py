"""Program-only loop + polish from the saved C_final layouts under the new critic (no API)."""
import json, sys, time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
sys.path.insert(0, '.')
from workflow.catalog import SizeCatalog
from workflow.contract import check_request, fill_room_defaults
from workflow.critic import Critic, load_templates
from workflow.loop import Loop, LoopBudget
from workflow.orders import critic_geometry, plan_from_dict
from workflow.planning import _required_parents
from workflow.refine import refine

ROWS = '../fastfill-main/fastfill/v2/ops/test300/rows.jsonl'


def job(args):
    run, name = args
    i = int(name.split('_')[1].split('.')[0])
    row = json.loads(open(ROWS).read().splitlines()[i])
    rec = json.loads(Path(run, 'C_final', name).read_text())
    if not rec.get('layout'):
        return None
    cond, _ = fill_room_defaults(row['condition']); cond = check_request(cond)
    plan = plan_from_dict(json.loads(Path(run, 'plans', name).read_text())['plan'])
    plan.parents.clear(); plan.parents.update(rec['diagnostics']['support_parents'])
    placed = {o['id']: o for o in rec['layout']['objects']}
    sizes = {k: list(v) for k, v in rec['diagnostics']['sizes'].items()}
    g = critic_geometry(cond, plan)
    critic = Critic.for_plan(g, plan, load_templates())
    before = critic.assess(placed)
    t = time.perf_counter()
    loop = Loop(g, plan, sizes, SizeCatalog('size_catalog.json'), critic, locked_parents=_required_parents(cond),
                ask=None, budget=LoopBudget(gpt_repairs=0, search_seconds=120))
    placed, info = loop.run(placed)
    placed, _ = refine(g, plan, placed, critic=critic)
    after = critic.assess(placed)
    count = lambda a: Counter(v.code for v in a.soft)
    return {"room": i, "s": round(time.perf_counter() - t, 1), "hard": (before.hard_count, after.hard_count),
            "soft": (round(before.soft_total, 3), round(after.soft_total, 3)), "before": count(before), "after": count(after)}


if __name__ == '__main__':
    jobs = [(run, f.name) for run in ['experiments/orders_test50_server', 'experiments/orders_AC_rest30_server']
            for f in sorted(Path(run, 'C_final').glob('room_*.json'))]
    out = []
    with ProcessPoolExecutor(8) as pool:
        for r in pool.map(job, jobs):
            if r:
                out.append(r)
    json.dump(out, open(sys.argv[1], 'w'), indent=1)
    b, a = Counter(), Counter()
    for r in out:
        b.update(r['before']); a.update(r['after'])
    print(len(out), 'rooms; hard-valid before/after', sum(r['hard'][0] == 0 for r in out), sum(r['hard'][1] == 0 for r in out))
    print('new hard on valid:', sum(r['hard'][0] == 0 and r['hard'][1] > 0 for r in out))
    print('soft total before/after %.1f %.1f' % (sum(r['soft'][0] for r in out), sum(r['soft'][1] for r in out)))
    for c in sorted(set(b) | set(a)):
        print(f'  {c:<16} {b[c]:>4} -> {a[c]:>4}')
    s = sorted(r['s'] for r in out); print('seconds median/max', s[len(s)//2], s[-1])
