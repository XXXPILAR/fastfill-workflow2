"""Cross-check workflow/robot.py (exact polygons) against an independent grid implementation, and measure how often a
1 cm / 0.5 deg jitter flips a verdict. Same definitions (obstacles, door strips, approach sides, sweep), different
computation: 2 cm raster, Euclidean distance transform, connected components (EmbodiedGen RoamTrajectoryGenerator style).
"""
import json, math, random, sys, time, collections
from pathlib import Path
import numpy as np
from scipy import ndimage
from matplotlib.path import Path as MPath
from shapely.geometry import Polygon, Point

W2 = Path("/Users/zhangyang/Downloads/fastfill-v4/Fastfill workflow2")
sys.path.insert(0, str(W2)); sys.path.insert(0, str(W2 / "experiments"))
from big_table import ROOT, sources  # noqa
from fastfill.v2.ops import layout_quality as lq  # noqa
from fastfill.v2.schema import migrate_legacy_row  # noqa
from workflow.robot import Robot, RobotChecker, infer_parents, openable, sweep, OPEN_BLOCKED_SHARE  # noqa
from workflow.critic import approach_sides  # noqa

RES = .02
WIDTH = float(sys.argv[1]) if len(sys.argv) > 1 else .5
MAX_LAYOUTS = int(sys.argv[2]) if len(sys.argv) > 2 else 400


def raster(poly, x0, y0, nx, ny):
    """cells whose centre lies in poly (Polygon or MultiPolygon)."""
    xs = x0 + (np.arange(nx) + .5) * RES
    ys = y0 + (np.arange(ny) + .5) * RES
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    pts = np.column_stack([X.ravel(), Y.ravel()])
    out = np.zeros(nx * ny, bool)
    geoms = getattr(poly, "geoms", [poly])
    for g in geoms:
        if g.is_empty:
            continue
        m = MPath(np.asarray(g.exterior.coords)).contains_points(pts)
        for hole in g.interiors:
            m &= ~MPath(np.asarray(hole.coords)).contains_points(pts)
        out |= m
    return out.reshape(nx, ny)


def grid_check(checker, bs, parents):
    robot = checker.robot
    floor = checker.floor
    minx, miny, maxx, maxy = floor.bounds
    x0, y0 = minx - .1, miny - .1
    nx, ny = int(math.ceil((maxx - minx + .2) / RES)), int(math.ceil((maxy - miny + .2) / RES))
    if nx * ny > 4e6:
        return None
    obstacles = [b for b in bs if lq.obstacle(b)]
    free = raster(floor, x0, y0, nx, ny)
    for o in [b["poly"] for b in obstacles] + list(checker.fixed):
        free &= ~raster(o, x0, y0, nx, ny)
    dist = ndimage.distance_transform_edt(free) * RES  # distance to the nearest blocked cell centre
    centre_ok = dist > robot.half_width + RES / 2      # cell-centre to cell-edge correction
    lab, n = ndimage.label(centre_ok)
    near = lambda mask: ndimage.binary_dilation(mask, iterations=2)  # "touching" within 2 cells
    doors = [near(raster(z, x0, y0, nx, ny)) for z in checker.door_zones]
    if n == 0:
        main = None
    else:
        best, key = None, None
        for k in range(1, n + 1):
            comp = lab == k
            t = sum(bool((comp & d).any()) for d in doors)
            kk = (t, comp.sum())
            if key is None or kk > key:
                best, key = comp, kk
        main = best
    out = {"door": [], "reach": {}, "arm": {}, "open": {}}
    for d in doors:
        out["door"].append(main is not None and bool((main & d).any()))
    by_id = {b["id"]: b for b in bs}
    reach = robot.half_width + robot.arm_m
    for ident in checker.required(bs, parents):
        b = by_id[ident]
        ok = False
        if main is not None:
            for dvec, hw, hd in approach_sides(b):
                a = np.array((-dvec[1], dvec[0]))
                nr, fr = b["centre"] + dvec * hd, b["centre"] + dvec * (hd + reach)
                z = Polygon([tuple(nr + a * hw), tuple(nr - a * hw), tuple(fr - a * hw), tuple(fr + a * hw)])
                if (main & near(raster(z, x0, y0, nx, ny))).any():
                    ok = True
                    break
        out["reach"][ident] = ok
    if main is not None:
        ii, jj = np.nonzero(main)
        cx, cy = x0 + (ii + .5) * RES, y0 + (jj + .5) * RES
    for ident, root in checker.items(bs, parents).items():
        c = by_id[ident]["centre"]
        out["arm"][ident] = main is not None and bool((np.hypot(cx - c[0], cy - c[1]) <= robot.arm_reach_m + RES).any())
    for b in obstacles:
        if not openable(b):
            continue
        z = sweep(b)
        zm = raster(z, x0, y0, nx, ny)
        if zm.sum() == 0:
            out["open"][b["id"]] = None
            continue
        blocked = zm & ~free
        out["open"][b["id"]] = blocked.sum() / zm.sum() <= OPEN_BLOCKED_SHARE
    return out


def exact_check(checker, bs, parents):
    found = checker._check(bs, parents, blockers=False)
    out = {"door": [True] * len(checker.door_zones), "reach": {}, "arm": {}, "open": {}, "gap": {}}
    failed_doors = {int(d.split()[1]) for _ids, _g, d in found["robot_door"]}
    for k in failed_doors:
        out["door"][k] = False
    bad_reach = {ids[0]: g for ids, g, _ in found["robot_reach"]}
    for ident in checker.required(bs, parents):
        out["reach"][ident] = ident not in bad_reach
        out["gap"][("reach", ident)] = bad_reach.get(ident, 0.)
    bad_arm = {ids[0]: g for ids, g, _ in found["robot_arm"]}
    for ident in checker.items(bs, parents):
        out["arm"][ident] = ident not in bad_arm
        out["gap"][("arm", ident)] = bad_arm.get(ident, 0.)
    bad_open = {ids[0]: g for ids, g, _ in found["robot_openable"]}
    for b in bs:
        if lq.obstacle(b) and openable(b):
            out["open"][b["id"]] = b["id"] not in bad_open
            out["gap"][("open", b["id"])] = bad_open.get(b["id"], 0.)
    return out


def jitter(layout, rng):
    objs = []
    for o in layout["objects"]:
        x, y, z = o["bottom_center_m"]
        objs.append({**o, "bottom_center_m": [x + rng.gauss(0, .01), y + rng.gauss(0, .01), z],
                     "yaw_rad": o["yaw_rad"] + rng.gauss(0, math.radians(.5))})
    return {**layout, "objects": objs}


def main():
    rows = [migrate_legacy_row(json.loads(l)) for l in open(ROOT / "test300/rows.jsonl") if l.strip()]
    src = sources(rows)
    src.pop("shuffled ground truth (anchor)", None)
    jobs = []
    for name, rooms in src.items():
        for i, (lay, _s, _u) in rooms.items():
            if lay:
                jobs.append((name, i, lay))
    rng = random.Random(0)
    rng.shuffle(jobs)
    ours = [j for j in jobs if j[0].startswith("workflow2")]
    jobs = ours + [j for j in jobs if not j[0].startswith("workflow2")][:max(0, MAX_LAYOUTS - len(ours))]
    agree = collections.defaultdict(collections.Counter)  # check -> (exact, grid) counts
    flips = collections.Counter(); totals = collections.Counter()
    disagreements = []
    t0 = time.time()
    for n, (name, i, lay) in enumerate(jobs):
        checker = RobotChecker(Robot(width_m=WIDTH), rows[i]["condition"])
        bs = lq.boxes(checker.row, lay)
        parents = infer_parents(bs)
        e = exact_check(checker, bs, parents)
        g = grid_check(checker, bs, parents)
        if g is None:
            continue
        for k, (a, b) in enumerate(zip(e["door"], g["door"])):
            agree["door"][(a, b)] += 1
            if a != b:
                disagreements.append((name, i, "door", k, None))
        for check in ("reach", "arm", "open"):
            for ident, a in e[check].items():
                b = g[check].get(ident)
                if b is None:
                    continue
                agree[check][(a, b)] += 1
                if a != b:
                    disagreements.append((name, i, check, ident, e["gap"].get((check, ident))))
        # jitter stability of the exact checker
        bs2 = lq.boxes(checker.row, jitter(lay, rng))
        e2 = exact_check(checker, bs2, infer_parents(bs2))
        for k, (a, b) in enumerate(zip(e["door"], e2["door"])):
            totals["door"] += 1; flips["door"] += a != b
        for check in ("reach", "arm", "open"):
            for ident, a in e[check].items():
                if ident in e2[check]:
                    totals[check] += 1; flips[check] += a != e2[check][ident]
        if (n + 1) % 50 == 0:
            print(f"{n + 1}/{len(jobs)} layouts, {time.time() - t0:.0f} s", flush=True)
    print(f"\nrobot width {WIDTH} m, {len(jobs)} layouts\n")
    print("check   | both pass | both fail | exact pass, grid fail | exact fail, grid pass | agreement | 1 cm jitter flips")
    for check in ("door", "reach", "arm", "open"):
        c = agree[check]; tot = sum(c.values())
        print(f"{check:7} | {c[(True, True)]:9} | {c[(False, False)]:9} | {c[(True, False)]:21} | {c[(False, True)]:21} | "
              f"{100 * (c[(True, True)] + c[(False, False)]) / max(tot, 1):8.2f}% | {flips[check]}/{totals[check]} "
              f"({100 * flips[check] / max(totals[check], 1):.2f}%)")
    json.dump([list(map(str, d)) for d in disagreements], open(Path(__file__).with_name(f"crosscheck_disagree_{WIDTH}.json"), "w"))
    gaps = [d[4] for d in disagreements if d[4] is not None]
    print(f"\ndisagreements {len(disagreements)}; with exact gap (m): "
          + ", ".join(f"{g:.3f}" for g in sorted(gaps)[:40]))


if __name__ == "__main__":
    main()
