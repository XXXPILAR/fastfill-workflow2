"""Assemble per-object assets into one room mesh per (method, scene).

    python bench/assemble.py --method trellis_text            # all 5 scenes
    python bench/assemble.py --method shap_e --scenes gym
    python bench/assemble.py --method sage_gt                 # reference: SAGE GT meshes
    python bench/assemble.py --method layout_boxes            # the input: bboxes only

Method assets (results/<M>/assets/<asset_key>.glb) follow bench/CONTRACT.md:
glTF Y-up, front +Z, arbitrary scale/offset. SAGE's object frame is Z-up, front +Y,
width along X, origin at the bottom-centre of the bbox. Each asset is
  1. rotated glTF -> SAGE frame,
  2. yaw-snapped: if its footprint is a rotated rectangle (e.g. a 3/4-view generation),
     it is turned by the smallest angle that axis-aligns the footprint; if the footprint
     aspect then contradicts the bbox aspect it is turned a further 90 deg,
     if the upright fit still contradicts the box badly, a 90 deg tip about X or Y is used
     when it halves the summed |log extent ratio| (flat items generated standing, etc.),
  3. scaled anisotropically so its AABB equals the bbox, bottom-centre at the origin,
  4. rotated (Euler XYZ, degrees, R = Rz Ry Rx) and translated by the layout.
Steps 1-4 are identical for every method; the per-instance decisions are logged in
results/<M>/scenes/<scene>.json.
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image
from scipy.spatial import ConvexHull

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ROOT / "bench" / "inputs"
SAGE = Path("/group/streetsplat/WorldGrow/data/sage10k_raw")
SCENES = ["gym", "restaurant", "livingroom", "bedroom", "bathroom"]

# glTF (Y-up, front +Z) -> SAGE (Z-up, front +Y): x' = -x, y' = z, z' = y
GLTF_TO_SAGE = np.array([[-1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], float)
# Output room GLBs are standard glTF (Y-up): SAGE world (x, y, z) -> glTF (x, z, -y).
# Metadata JSON (walls, bboxes) stays in SAGE world coordinates.
SAGE_WORLD_TO_GLTF = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1]], float)

FLOOR_RGBA = [168, 150, 126, 255]
WALL_RGBA = [236, 233, 226, 255]
DOOR_RGBA = [139, 101, 70, 255]
PLACEHOLDER_RGBA = [96, 104, 112, 140]
PLACE_RGBA = {"floor": [77, 128, 204, 230], "wall": [214, 120, 60, 230], "on_object": [90, 170, 100, 230]}


def euler_xyz_deg(rot):
    rx, ry, rz = (math.radians(rot[k]) for k in ("x", "y", "z"))
    Rx = trimesh.transformations.rotation_matrix(rx, [1, 0, 0])
    Ry = trimesh.transformations.rotation_matrix(ry, [0, 1, 0])
    Rz = trimesh.transformations.rotation_matrix(rz, [0, 0, 1])
    return Rz @ Ry @ Rx


def place_matrix(obj):
    T = trimesh.transformations.translation_matrix([obj["position"][k] for k in ("x", "y", "z")])
    return T @ euler_xyz_deg(obj["rotation"])


def colored_box(extents, transform, rgba):
    box = trimesh.creation.box(extents=extents, transform=transform)
    box.visual = trimesh.visual.ColorVisuals(box, face_colors=np.tile(rgba, (len(box.faces), 1)))
    return box


def effective_status(method, sidecar_path):
    """Status used everywhere (rooms, asset thumbnails, site). One benchmark-level rule:
    the Infinigen V2 row shows only V2's own generators; assets the V2 agent made with the
    legacy Infinigen-1 factories bundled in 2.0.0a2 (`api == "infinigen1_legacy"`) count as
    "failed" there, since the separate infinigen_v1 row covers those factories."""
    if not Path(sidecar_path).exists():
        return "missing"
    j = json.load(open(sidecar_path))
    if method == "infinigen_v2" and j.get("api") == "infinigen1_legacy":
        return "failed"
    return j.get("status", "ok")


# ----------------------------------------------------------------------------- shell
def build_shell(room):
    """Floor + walls (with door cutouts) + closed door panels. Walls are extruded outwards
    from the room boundary so the interior faces lie on the layout lines."""
    parts, walls_meta = [], []
    W, L = room["dimensions"]["width"], room["dimensions"]["length"]
    ox, oy = room["position"]["x"], room["position"]["y"]
    parts.append(("shell_floor", colored_box(
        [W + 0.2, L + 0.2, 0.05],
        trimesh.transformations.translation_matrix([ox + W / 2, oy + L / 2, -0.025]), FLOOR_RGBA)))
    center = np.array([ox + W / 2, oy + L / 2])
    doors_by_wall = {}
    for d in room["doors"]:
        doors_by_wall.setdefault(d["wall_id"], []).append(d)
    for wi, w in enumerate(room["walls"]):
        a = np.array([w["start_point"]["x"], w["start_point"]["y"]])
        b = np.array([w["end_point"]["x"], w["end_point"]["y"]])
        length = np.linalg.norm(b - a)
        u = (b - a) / length
        n = np.array([-u[1], u[0]])
        if np.dot(n, (a + b) / 2 - center) < 0:
            n = -n
        H, t = w["height"], w["thickness"]
        yaw = math.atan2(u[1], u[0])
        # 1D intervals along the wall that are solid for the full height, plus lintels.
        cuts = sorted((d["position_on_wall"] * length - d["width"] / 2,
                       d["position_on_wall"] * length + d["width"] / 2, d) for d in doors_by_wall.get(w["id"], []))
        segs, s0 = [], -t  # extend past both ends by t to close the corners
        for c0, c1, d in cuts:
            segs.append((s0, c0, 0.0, H))
            segs.append((c0, c1, d["height"], H))
            s0 = c1
        segs.append((s0, length + t, 0.0, H))
        name = f"shell_wall_{wi}"
        for si, (s, e, z0, z1) in enumerate(segs):
            if e - s < 1e-3 or z1 - z0 < 1e-3:
                continue
            mid = a + u * (s + e) / 2 + n * t / 2
            T = trimesh.transformations.translation_matrix([mid[0], mid[1], (z0 + z1) / 2])
            T = T @ trimesh.transformations.rotation_matrix(yaw, [0, 0, 1])
            parts.append((f"{name}_s{si}", colored_box([e - s, t, z1 - z0], T, WALL_RGBA)))
        for c0, c1, d in cuts:
            mid = a + u * (c0 + c1) / 2 + n * (t * 0.5)
            T = trimesh.transformations.translation_matrix([mid[0], mid[1], d["height"] / 2])
            T = T @ trimesh.transformations.rotation_matrix(yaw, [0, 0, 1])
            parts.append((f"{name}_door", colored_box([c1 - c0, 0.04, d["height"]], T, DOOR_RGBA)))
        walls_meta.append({"name": name, "normal": [float(n[0]), float(n[1]), 0.0]})
    return parts, walls_meta


# ----------------------------------------------------------------------------- assets
def load_glb_parts(path):
    """Flatten a GLB into a list of meshes with node transforms applied."""
    scene = trimesh.load(path, force="scene", process=False)
    parts = []
    for node in scene.graph.nodes_geometry:
        T, gname = scene.graph[node]
        g = scene.geometry[gname]
        if not isinstance(g, trimesh.Trimesh) or len(g.faces) == 0:
            continue
        m = g.copy()
        m.apply_transform(T)
        # Full metalness with no metallic-roughness map is an exporter default (TRELLIS to_glb and
        # EmbodiedGen write it on every asset over a baked albedo texture); show such materials as
        # non-metallic. Materials with a metallic-roughness map (Infinigen, Hunyuan3D) are untouched.
        mat = getattr(m.visual, "material", None)
        if isinstance(mat, trimesh.visual.material.PBRMaterial) and mat.metallicRoughnessTexture is None \
                and (mat.metallicFactor is None or mat.metallicFactor >= 0.99):
            mat.metallicFactor = 0.0
        parts.append(m)
    return parts


def min_area_yaw(xy):
    """Angle in (-45, 45] deg that best axis-aligns the 2D point set, and the area ratio
    (min-area rectangle / current AABB)."""
    try:
        hull = xy[ConvexHull(xy).vertices]
    except Exception:
        return 0.0, 1.0
    edges = np.diff(np.vstack([hull, hull[:1]]), axis=0)
    angles = np.unique(np.mod(np.arctan2(edges[:, 1], edges[:, 0]), np.pi / 2))
    best, best_area = 0.0, None
    for th in angles:
        c, s = math.cos(-th), math.sin(-th)
        p = hull @ np.array([[c, s], [-s, c]])
        area = np.prod(p.max(0) - p.min(0))
        if best_area is None or area < best_area:
            best, best_area = th, area
    aabb = np.prod(hull.max(0) - hull.min(0))
    if best > math.pi / 4:
        best -= math.pi / 2
    return best, (best_area / aabb if aabb > 0 else 1.0)


def fit_asset(parts, dims, log):
    """parts: meshes in glTF convention. Returns meshes in SAGE object frame fitted to dims."""
    parts = [p.copy() for p in parts]
    for p in parts:
        p.apply_transform(GLTF_TO_SAGE)
    V = np.vstack([p.vertices for p in parts])
    th, ratio = min_area_yaw(V[:, :2])
    yaw = 0.0
    if ratio < 0.93 and abs(th) > math.radians(3):
        yaw = -th
    R = trimesh.transformations.rotation_matrix(yaw, [0, 0, 1])
    Vr = trimesh.transform_points(V, R)
    ext = Vr.max(0) - Vr.min(0)
    w, l = dims["width"], dims["length"]
    a_asset, a_box = ext[0] / max(ext[1], 1e-6), w / max(l, 1e-6)
    if (a_asset > 1.3 and a_box < 1 / 1.3) or (a_asset < 1 / 1.3 and a_box > 1.3):
        yaw += math.pi / 2
        R = trimesh.transformations.rotation_matrix(yaw, [0, 0, 1])
        Vr = trimesh.transform_points(V, R)
    target = np.array([w, l, dims["height"]])
    # Tip rule: keep the method's up axis unless the upright fit contradicts the box badly
    # (summed |log extent ratio| > 1.2) and a 90-degree tip about X or Y halves that error,
    # e.g. a book generated standing whose box lies flat.
    def fit_err(P):  # scale-invariant: compare proportions (log extents minus their mean)
        le = np.log(np.maximum(P.max(0) - P.min(0), 1e-4))
        lt = np.log(np.maximum(target, 1e-4))
        return float(np.abs((le - le.mean()) - (lt - lt.mean())).sum())
    err_up, tip = fit_err(Vr), None
    if err_up > 1.2:
        best = None
        for axis in ([1, 0, 0], [0, 1, 0]):
            for yaw90 in (0.0, math.pi / 2):
                Rt = (trimesh.transformations.rotation_matrix(yaw90, [0, 0, 1])
                      @ trimesh.transformations.rotation_matrix(math.pi / 2, axis) @ R)
                err = fit_err(trimesh.transform_points(V, Rt))
                if best is None or err < best[0]:
                    best = (err, Rt, "x" if axis[0] else "y")
        if best[0] < 0.5 * err_up:
            R, tip = best[1], best[2]
            Vr = trimesh.transform_points(V, R)
    lo, hi = Vr.min(0), Vr.max(0)
    ext = np.maximum(hi - lo, 1e-4)
    S = np.diag(list(target / ext) + [1.0])
    c = (lo + hi) / 2
    Tc = trimesh.transformations.translation_matrix([-c[0], -c[1], -lo[2]])
    M = S @ Tc @ R
    for p in parts:
        p.apply_transform(M)
    log.update({"yaw_snap_deg": round(math.degrees(yaw), 1), "tip": tip,
                "scale": [round(float(x), 3) for x in target / ext]})
    return parts


def load_sage_gt(scene_dir, source_id):
    """SAGE GT PLY (x y z + per-corner texcoords) -> textured trimesh in SAGE object frame."""
    path = SAGE / scene_dir / "objects" / f"{source_id}.ply"
    with open(path, "rb") as f:
        counts = {}
        while True:
            line = f.readline().decode().strip()
            if line.startswith("element"):
                _, name, n = line.split()
                counts[name] = int(n)
            if line == "end_header":
                break
        V = np.frombuffer(f.read(counts["vertex"] * 12), "<f4").reshape(-1, 3)
        T = np.frombuffer(f.read(counts["texcoord"] * 8), "<f4").reshape(-1, 2)
        raw = f.read()
    nf = counts["face"]
    rec = np.frombuffer(raw, dtype=np.dtype([("n0", "u1"), ("v", "<i4", 3), ("n1", "u1"), ("t", "<i4", 3)]), count=nf)
    pairs = np.stack([rec["v"].reshape(-1), rec["t"].reshape(-1)], 1)
    uniq, inv = np.unique(pairs, axis=0, return_inverse=True)
    img = Image.open(SAGE / scene_dir / "objects" / f"{source_id}_texture.png")
    mesh = trimesh.Trimesh(V[uniq[:, 0]], inv.reshape(-1, 3), process=False)
    mat = trimesh.visual.material.PBRMaterial(baseColorTexture=img, metallicFactor=0.0, roughnessFactor=0.85)
    mesh.visual = trimesh.visual.TextureVisuals(uv=T[uniq[:, 1]], material=mat)
    return [mesh]


# ----------------------------------------------------------------------------- main
def assemble(method, scene_key, out_dir):
    """Objects that share an asset and bbox share one glTF mesh; each instance is a node
    whose matrix is SAGE_WORLD_TO_GLTF @ placement, so the GLB stays compact."""
    scene_in = json.load(open(INPUTS / "scenes" / f"{scene_key}.json"))
    shell, walls_meta = build_shell(scene_in["room"])
    out = trimesh.Scene()
    for name, m in shell:
        out.add_geometry(m, node_name=name, geom_name=name, transform=SAGE_WORLD_TO_GLTF)
    if method == "sage_gt":
        sage_layout = json.load(open(next((SAGE / scene_in["sage_scene"]).glob("layout_*.json"))))
        src = {o["id"]: o["source_id"] for o in sage_layout["rooms"][0]["objects"]}
    cache, shared, report = {}, {}, []
    asset_dir = ROOT / "results" / method / "assets"
    for i, obj in enumerate(scene_in["objects"]):
        key, dims = obj["asset_key"], obj["dimensions"]
        log = {"id": obj["id"], "type": obj["type"], "asset_key": key, "description": obj["description"],
               "place": obj["place_id"] if obj["place_id"] in ("floor", "wall") else "on_object"}
        dkey = tuple(round(dims[k], 4) for k in ("width", "length", "height"))
        share_key, make_parts = None, None
        if method == "sage_gt":
            sid = src[obj["id"]]
            log["status"] = "ok"
            share_key = ("gt", sid)
            make_parts = lambda sid=sid: load_sage_gt(scene_in["sage_scene"], sid)
        elif method != "layout_boxes":
            sidecar = asset_dir / f"{key}.json"
            glb = asset_dir / f"{key}.glb"
            status = effective_status(method, sidecar)
            log["status"] = status
            if status in ("ok", "fallback") and glb.exists():
                if key not in cache:
                    try:
                        cache[key] = load_glb_parts(glb)
                    except Exception as e:  # unreadable asset -> placeholder
                        cache[key] = []
                        log["error"] = repr(e)[:200]
                if cache[key]:
                    share_key = (key, dkey)
                    make_parts = lambda key=key, dims=dims, log=log: fit_asset(cache[key], dims, log)
                else:
                    log["status"] = "failed"
            elif status in ("ok", "fallback"):
                log["status"] = "missing"
        else:
            log["status"] = "box"
        node = f"obj_{i:03d}"
        log["node"] = node
        T_node = SAGE_WORLD_TO_GLTF @ place_matrix(obj)
        if share_key is None:
            rgba = PLACE_RGBA[log["place"]] if method == "layout_boxes" else PLACEHOLDER_RGBA
            box = colored_box([dims["width"], dims["length"], dims["height"]],
                              trimesh.transformations.translation_matrix([0, 0, dims["height"] / 2]), rgba)
            out.add_geometry(box, node_name=node, geom_name=node, transform=T_node)
        elif share_key not in shared:
            names = []
            for k, part in enumerate(make_parts()):
                gname = f"{node}_p{k}"
                out.add_geometry(part, node_name=gname, geom_name=gname, transform=T_node)
                names.append(gname)
            shared[share_key] = (names, {k: v for k, v in log.items() if k in ("yaw_snap_deg", "tip", "scale")})
        else:
            names, fit_log = shared[share_key]
            log.update(fit_log)
            for k, gname in enumerate(names):
                out.graph.update(frame_from=out.graph.base_frame, frame_to=f"{node}_p{k}", matrix=T_node, geometry=gname)
        report.append(log)
    out_dir.mkdir(parents=True, exist_ok=True)
    out.export(out_dir / f"{scene_key}.glb")
    counts = {}
    for r in report:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    meta = {"method": method, "scene": scene_key, "room_type": scene_in["room_type"],
            "room": scene_in["room"]["dimensions"], "walls": walls_meta, "counts": counts, "objects": report}
    json.dump(meta, open(out_dir / f"{scene_key}.json", "w"), indent=1)
    return counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", required=True)
    ap.add_argument("--scenes", default=",".join(SCENES))
    args = ap.parse_args()
    out_dir = ROOT / "results" / args.method / "scenes"
    for s in args.scenes.split(","):
        print(args.method, s, assemble(args.method, s, out_dir), flush=True)


if __name__ == "__main__":
    main()
