"""Independent evaluation of saved layouts (no LLM, no money): metrics we did NOT optimise.

  A. SceneEval (3dlg-hcvc/SceneEval, MIT), its own metric code on box meshes: NavigabilityMetric (PhyScene's walkable
     rate, robot 0.2 m = their default, and 0.5 m), CollisionMetric (fcl, 5 mm double check), OutOfBoundMetric (rays).
  B. EmbodiedGen's RoamTrajectoryGenerator (its own code): clearance 0.25 m (a 0.5 m robot), components, share of the
     navigable floor in the largest, and whether its roam trajectory can be generated.
  C. A different robot (new code): a 0.5 x 0.7 m rectangular base that must turn (16 headings), connected states from
     the doors; furniture counts as reached when the base can park facing it (front within 0.30 m, heading within 30
     deg); items on furniture count as reached when a 0.85 m arm on a 0.9 m shoulder 0.2 m ahead of the base centre
     reaches the item's top (3D) from a reachable state facing it within 60 deg.
"""
import importlib.util, json, math, sys, types
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import shapely
import trimesh
from matplotlib.path import Path as MPath
from scipy import ndimage
from scipy.signal import fftconvolve
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

W2 = Path("/Users/zhangyang/Downloads/fastfill-v4/Fastfill workflow2")
SCR = Path(__file__).parent
sys.path[:0] = [str(W2), str(W2 / "experiments"), str(SCR / "sceneeval"), str(SCR / "sceneeval" / "scenes_stub")]
from big_table import ROOT, sources  # noqa
from fastfill.v2.ops import layout_quality as lq  # noqa
from fastfill.v2.schema import migrate_legacy_row  # noqa
from workflow.robot import infer_parents, openable  # noqa

import matplotlib  # noqa
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa
plt.savefig = lambda *a, **k: None  # SceneEval saves debug images on every run: computation unchanged, nothing written
from metrics.navigability import NavigabilityMetric, NavigabilityMetricConfig  # noqa
from metrics.collision import CollisionMetric, CollisionMetricConfig  # noqa
from metrics.out_of_bound import OutOfBoundMetric, OutOfBoundMetricConfig  # noqa

_spec = importlib.util.spec_from_file_location("eg_traj", ROOT / "related work code/EmbodiedGen-master/embodied_gen/skills/spatial-computing/core/trajectory.py")
eg_traj = importlib.util.module_from_spec(_spec)
sys.modules["eg_traj"] = eg_traj
_spec.loader.exec_module(eg_traj)

METHODS = {"ground truth": "ground truth", "GPT-5.6 one-shot": "GPT-5.6 one-shot", "Holodeck": "Holodeck",
           "LayoutVLM": "LayoutVLM", "LayoutGPT": "LayoutGPT", "FastFill base": "FastFill base (spread)",
           "ours C_final": "ours C_final: by group + whole-room loop",
           "workflow2 (no robot)": "workflow2 simple (one place, one check, one review)",
           "workflow2 + robot": "workflow2 simple + robot 0.5 m (prompt, search zones, tiered critic)",
           "workflow2 + robot + 2 drafts": "workflow2 simple + robot 0.5 m + 2 drafts + resize"}
ROWS = None


class BoxScene:
    """What SceneEval's three geometric metrics read from a scene, built from a layout's boxes."""

    def __init__(self, row, layout):
        room = row["condition"]["room"]
        floor_z = room.get("floor_z_m") or 0.0
        poly = Polygon(room["floor_polygon_xy_m"]).buffer(0)
        tris = shapely.constrained_delaunay_triangles(poly)
        verts, faces = [], []
        for t in tris.geoms:
            k = len(verts)
            verts += [(x, y, floor_z) for x, y in list(t.exterior.coords)[:3]]
            faces.append((k, k + 1, k + 2))
        self.t_architecture = {"floor_0": trimesh.Trimesh(np.array(verts), np.array(faces), process=False)}
        self.boxes, self.t_objs = {}, {}
        for o in layout["objects"]:
            sx, sy, sz = o["target_size_local_m"]
            x, y, z = o["bottom_center_m"]
            if min(sx, sy, sz) <= 0:
                continue
            T = trimesh.transformations.rotation_matrix(o["yaw_rad"], (0, 0, 1))
            T[:3, 3] = (x, y, z + sz / 2)
            self.t_objs[o["id"]] = trimesh.creation.box((sx, sy, sz), transform=T)
            self.boxes[o["id"]] = o

    def get_obj_ids(self):
        return list(self.t_objs)

    def get_obj_bbox_center(self, i):
        o = self.boxes[i]
        x, y, z = o["bottom_center_m"]
        return np.array([x, y, z + o["target_size_local_m"][2] / 2])

    def get_default_pose_obj_bbox_extents(self, i):
        return np.array(self.boxes[i]["target_size_local_m"])

    def get_obj_z_rotation(self, i):
        return self.boxes[i]["yaw_rad"]


def sceneeval(row, layout):
    import contextlib, io
    sc = BoxScene(row, layout)
    out = {}
    with contextlib.redirect_stdout(io.StringIO()):
        for w in (.2, .5):
            m = NavigabilityMetric(sc, SCR / "se_out", NavigabilityMetricConfig(robot_width=w)).run()
            out[f"nav{w}"] = m.data["navigability"]
        c = CollisionMetric(sc, CollisionMetricConfig(move_direction_amount=.005)).run()
        out["col"] = (c.data["num_obj_in_collision"], len(sc.t_objs))
        b = OutOfBoundMetric(sc, OutOfBoundMetricConfig(threshold=.99, volume_sample_multiplier=5000., min_sample_points=1000)).run()
        out["oob"] = (sum(v["out_of_bound"] for v in b.data.values()), len(b.data))
    return out


def floor_obstacles(row, layout):
    floor_z = row["condition"]["room"].get("floor_z_m") or 0.0
    polys = []
    for o in layout["objects"]:
        sx, sy, sz = o["target_size_local_m"]
        if o["bottom_center_m"][2] - floor_z > .05 or sz < .05:   # on something / on a wall / a rug
            continue
        c, s = math.cos(o["yaw_rad"]), math.sin(o["yaw_rad"])
        x, y = o["bottom_center_m"][:2]
        polys.append(Polygon([(x + c * a * sx / 2 - s * b * sy / 2, y + s * a * sx / 2 + c * b * sy / 2)
                              for a, b in ((1, 1), (1, -1), (-1, -1), (-1, 1))]))
    fixed = [Polygon(f["footprint"]) for f in []]
    for f in row["condition"]["room"].get("fixed_objects", []):
        sx, sy, sz = f["size_local_m"]
        if f["bottom_center_m"][2] - floor_z > .05:
            continue
        c, s = math.cos(f["yaw_rad"]), math.sin(f["yaw_rad"])
        x, y = f["bottom_center_m"][:2]
        polys.append(Polygon([(x + c * a * sx / 2 - s * b * sy / 2, y + s * a * sx / 2 + c * b * sy / 2)
                              for a, b in ((1, 1), (1, -1), (-1, -1), (-1, 1))]))
    return polys


def embodiedgen(row, layout):
    floor = Polygon(row["condition"]["room"]["floor_polygon_xy_m"]).buffer(0)
    obstacles = unary_union(floor_obstacles(row, layout))
    gen = eg_traj.RoamTrajectoryGenerator(floor, obstacles, clearance=.25, resolution=.05)
    sizes = np.bincount(gen.labels.ravel())[1:]
    out = {"components": int(len(sizes)), "largest_share": float(sizes.max() / sizes.sum()) if len(sizes) else 0.}
    try:
        gen.generate(seed=0)
        out["roam_ok"] = True
    except Exception:
        out["roam_ok"] = False
    return out


# ----------------------------------------------------------------------------- C: rectangular robot
RES, K, BL, BW = .05, 16, .7, .5          # grid, headings, base length (forward) and width
SHOULDER_Z, SHOULDER_AHEAD, ARM = .9, .2, .85
ANY_SIDE = ("table", "desk", "counter", "bed", "island", "bench")


def raster(poly, x0, y0, nx, ny):
    xs, ys = x0 + (np.arange(nx) + .5) * RES, y0 + (np.arange(ny) + .5) * RES
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    pts = np.column_stack([X.ravel(), Y.ravel()])
    m = np.zeros(nx * ny, bool)
    for g in getattr(poly, "geoms", [poly]):
        if g.is_empty:
            continue
        mm = MPath(np.asarray(g.exterior.coords)).contains_points(pts)
        for h in g.interiors:
            mm &= ~MPath(np.asarray(h.coords)).contains_points(pts)
        m |= mm
    return m.reshape(nx, ny)


def rect_kernel(theta):
    r = math.hypot(BL, BW) / 2
    n = int(math.ceil(r / RES))
    a = np.arange(-n, n + 1) * RES
    X, Y = np.meshgrid(a, a, indexing="ij")
    c, s = math.cos(theta), math.sin(theta)
    u, v = c * X + s * Y, -s * X + c * Y
    return ((np.abs(u) <= BL / 2) & (np.abs(v) <= BW / 2)).astype(float)


KERNELS = [rect_kernel(2 * math.pi * k / K) for k in range(K)]


def door_points(room):
    poly = room["floor_polygon_xy_m"]
    pts = []
    for o in room.get("openings", []):
        if o.get("type") != "door":
            continue
        a, b = np.array(poly[o["wall_index"]]), np.array(poly[(o["wall_index"] + 1) % len(poly)])
        p = a + (b - a) * o["position_on_wall"]
        n = np.array([-(b - a)[1], (b - a)[0]]) / np.linalg.norm(b - a)
        if not Polygon(poly).buffer(0).contains(Point(*(p + n * .1))):
            n = -n
        pts.append(p + n * .45)
    return pts


def rect_robot(row, layout):
    room = row["condition"]["room"]
    floor = Polygon(room["floor_polygon_xy_m"]).buffer(0)
    minx, miny, maxx, maxy = floor.bounds
    x0, y0 = minx - .5, miny - .5
    nx, ny = int(math.ceil((maxx - minx + 1) / RES)), int(math.ceil((maxy - miny + 1) / RES))
    occ = ~raster(floor, x0, y0, nx, ny)
    for p in floor_obstacles(row, layout):
        occ |= raster(p, x0, y0, nx, ny)
    occf = occ.astype(float)
    free = np.stack([fftconvolve(occf, k, mode="same") < .5 for k in KERNELS], -1)  # nx, ny, K
    lab, n = ndimage.label(free, structure=np.ones((3, 3, 3)))
    # heading wraps around: merge the labels of the first and last heading
    parent = list(range(n + 1))
    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    for a, b in zip(lab[..., 0].ravel(), lab[..., -1].ravel()):
        if a and b:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb
    roots = np.array([find(i) for i in range(n + 1)])
    lab = roots[lab]
    xs, ys = x0 + (np.arange(nx) + .5) * RES, y0 + (np.arange(ny) + .5) * RES
    starts = set()
    doors = door_points(room)
    for p in doors:
        i0, j0 = int((p[0] - x0) / RES), int((p[1] - y0) / RES)
        r = int(.35 / RES)
        sub = lab[max(i0 - r, 0):i0 + r + 1, max(j0 - r, 0):j0 + r + 1]
        starts |= set(np.unique(sub[sub > 0]).tolist())
    if not doors and n:
        counts = np.bincount(lab.ravel())
        counts[0] = 0
        starts = {int(counts.argmax())}
    reach = np.isin(lab, list(starts)) if starts else np.zeros_like(free)
    I, J, T = np.nonzero(reach)
    cx, cy, th = xs[I], ys[J], 2 * math.pi * T / K
    hx, hy = np.cos(th), np.sin(th)
    bs = lq.boxes(row, layout)
    parents = infer_parents(bs)
    by = {b["id"]: b for b in bs}
    carry = {}
    for c, p in parents.items():
        q = p
        while q in by and not lq.obstacle(by[q]):
            q = parents.get(q, "?")
        if q in by and c in by and not lq.obstacle(by[c]):
            carry.setdefault(q, []).append(c)
    targets = {b["id"] for b in bs if lq.obstacle(b) and b["size"][2] >= .3 and (b["id"] in carry or openable(b))}
    res = {"doors": len(doors), "furniture": 0, "furniture_reached": 0, "items": 0, "items_reached": 0}
    for t in targets:
        b = by[t]
        f, sd = b["front"], b["side"]
        sides = [(f, b["size"][1] / 2, b["size"][0] / 2)]
        if any(w in b["cat"] for w in ANY_SIDE):
            sides += [(-f, b["size"][1] / 2, b["size"][0] / 2), (sd, b["size"][0] / 2, b["size"][1] / 2),
                      (-sd, b["size"][0] / 2, b["size"][1] / 2)]
        ok = False
        for d, half_len, half_dep in sides:
            rel_x, rel_y = cx - b["centre"][0], cy - b["centre"][1]
            along = rel_x * d[0] + rel_y * d[1]                 # distance out from the centre along the side normal
            across = -rel_x * d[1] + rel_y * d[0]
            gap = along - half_dep - BL / 2
            facing = -(hx * d[0] + hy * d[1])                   # robot heading points back at the furniture
            if np.any((gap >= -1e-6) & (gap <= .30) & (np.abs(across) <= half_len) & (facing >= math.cos(math.radians(30)))):
                ok = True
                break
        res["furniture"] += 1
        res["furniture_reached"] += ok
    for t, items in carry.items():
        for c in items:
            it = by[c]
            px, py = it["centre"]
            pz = it["bottom"] + it["size"][2]
            sx, sy = cx + hx * SHOULDER_AHEAD, cy + hy * SHOULDER_AHEAD
            dist = np.sqrt((px - sx) ** 2 + (py - sy) ** 2 + (pz - SHOULDER_Z) ** 2)
            vx, vy = px - cx, py - cy
            facing = (vx * hx + vy * hy) / (np.hypot(vx, vy) + 1e-9)
            res["items"] += 1
            res["items_reached"] += bool(np.any((dist <= ARM) & (facing >= math.cos(math.radians(60)))))
    res["ok"] = res["furniture_reached"] == res["furniture"] and res["items_reached"] == res["items"] and bool(starts)
    return res


def job(args):
    name, i, layout = args
    row = ROWS[i]
    out = {"name": name, "room": i}
    for key, fn in (("sceneeval", sceneeval), ("embodiedgen", embodiedgen), ("rect", rect_robot)):
        try:
            out[key] = fn(row, layout)
        except Exception as e:
            out[key] = {"error": f"{type(e).__name__}: {e}"[:200]}
    return out


def init():
    global ROWS
    ROWS = [migrate_legacy_row(json.loads(l)) for l in open(ROOT / "test300/rows.jsonl") if l.strip()]


if __name__ == "__main__":
    init()
    src = sources(ROWS)
    rooms = sorted(i for i, (l, _s, _u) in src[METHODS["workflow2 + robot + 2 drafts"]].items() if l)
    jobs = [(label, i, src[name][i][0]) for label, name in METHODS.items() for i in rooms
            if i in src[name] and src[name][i][0]]
    if len(sys.argv) > 2:
        jobs = jobs[:int(sys.argv[2])]
    results = []
    with Pool(int(sys.argv[1]) if len(sys.argv) > 1 else 8, initializer=init) as pool:
        for k, r in enumerate(pool.imap_unordered(job, jobs)):
            results.append(r)
            errs = [f"{key}: {r[key]['error']}" for key in ("sceneeval", "embodiedgen", "rect") if "error" in r[key]]
            print(f"{k + 1}/{len(jobs)} {r['name']} room {r['room']}" + (f" ERR {errs}" if errs else ""), file=sys.stderr, flush=True)
    json.dump(results, open(SCR / "indep_eval.json", "w"))
    print("saved", len(results))
