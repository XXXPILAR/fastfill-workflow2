import json, sys, time
from collections import Counter, defaultdict
from pathlib import Path
sys.path.insert(0, '.')
from workflow.contract import check_request, fill_room_defaults
from workflow.critic import Critic, load_templates
from workflow.orders import critic_geometry, plan_from_dict
from workflow.planning import Plan
rows = [json.loads(l) for l in open('../fastfill-main/fastfill/v2/ops/test300/rows.jsonl')]
templates = load_templates()
counts = defaultdict(Counter); objs = defaultdict(Counter); rooms_with = defaultdict(Counter); times = defaultdict(list)
n = Counter()
for run in ['experiments/orders_test50_server', 'experiments/orders_AC_rest30_server']:
    for f in sorted(Path(run, 'C_final').glob('room_*.json')):
        i = int(f.stem.split('_')[1])
        plan_file = Path(run, 'plans', f.name)
        cond, _ = fill_room_defaults(rows[i]['condition']); cond = check_request(cond)
        cond_cat = {o["id"]: o.get("category") for o in cond["objects"]}
        plan = plan_from_dict(json.loads(plan_file.read_text())['plan']) if plan_file.is_file() else None
        layouts = {}
        for v in ('A', 'C_final'):
            p = Path(run, v, f.name)
            lay = json.loads(p.read_text()).get('layout') if p.is_file() else None
            if lay:
                layouts[v] = {o['id']: o for o in lay['objects']}
        gt = rows[i].get('target') or {}
        if gt.get('objects'):
            layouts['GT'] = {o['id']: {**o, 'support_parent': o.get('support_parent', 'floor')} for o in gt['objects']}
        if len(layouts) < 3:
            continue
        for v, placed in layouts.items():
            parents = {k: b.get('support_parent') or 'floor' for k, b in placed.items()}
            pl = plan or Plan(parents=parents)
            pl = Plan(parents=parents, groups=pl.groups, relations=pl.relations, priority=pl.priority)
            g = critic_geometry(cond, pl)
            c = Critic.for_plan(g, pl, templates)
            t = time.perf_counter(); a = c.assess(placed); times[v].append(time.perf_counter() - t)
            n[v] += 1; seen = set()
            for s in a.soft:
                counts[v][s.code] += s.cost; objs[v][s.code] += 1; seen.add(s.code)
                if s.code in ("wall_back", "reach") and v != "A": print(v, i, s.code, [cond_cat.get(x) for x in s.ids], round(s.magnitude, 2), s.detail)
            for code in seen: rooms_with[v][code] += 1
            objs[v]['_objects'] += len(placed)
codes = ['template_faces', 'wall_back', 'reach', 'access', 'template_near', 'relation_plan']
print('variant rooms objs  ' + '  '.join(f'{c}(n/rooms/cost)' for c in codes) + '  assess ms (median/max)')
for v in ('GT', 'A', 'C_final'):
    ts = sorted(times[v])
    print(v, n[v], objs[v]['_objects'], '  '.join(f'{objs[v][c]}/{rooms_with[v][c]}/{counts[v][c]:.1f}' for c in codes),
          f'{1000*ts[len(ts)//2]:.0f}/{1000*ts[-1]:.0f}')
