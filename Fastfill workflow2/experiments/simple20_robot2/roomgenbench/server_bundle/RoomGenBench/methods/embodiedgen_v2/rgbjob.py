"""Shared helpers for RoomGenBench generation workers (embodiedgen_v2, trellis_text).

Resumable + concurrent-safe per bench/CONTRACT.md:
  * an asset is done when its sidecar says status "ok" (or "failed" after MAX_ATTEMPTS tries);
  * each asset is claimed with results/<M>/locks/<asset_key>.lock (O_CREAT|O_EXCL);
  * outputs are written to a tmp file and renamed.
"""

import json
import os
import socket
import time

import numpy as np

RGB_ROOT = os.environ.get("RGB_ROOT", "/group/streetsplat/WorldGrow/RoomGenBench")
ASSETS_JSONL = f"{RGB_ROOT}/bench/inputs/assets.jsonl"
MAX_ATTEMPTS = 2
STALE_LOCK_SECS = 3 * 3600  # lock from another host older than this is considered dead


def load_assets():
    with open(ASSETS_JSONL) as f:
        return [json.loads(l) for l in f if l.strip()]


def _pid_alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


class Job:
    def __init__(self, method):
        self.method = method
        self.root = f"{RGB_ROOT}/results/{method}"
        self.assets_dir = f"{self.root}/assets"
        self.locks_dir = f"{self.root}/locks"
        self.inter_dir = f"{self.root}/intermediate"
        for d in (self.assets_dir, self.locks_dir, self.inter_dir):
            os.makedirs(d, exist_ok=True)
        self.host = socket.gethostname()

    # ---------------- status ----------------
    def sidecar_path(self, key):
        return f"{self.assets_dir}/{key}.json"

    def glb_path(self, key):
        return f"{self.assets_dir}/{key}.glb"

    def read_sidecar(self, key):
        p = self.sidecar_path(key)
        if not os.path.exists(p):
            return None
        try:
            with open(p) as f:
                return json.load(f)
        except Exception:
            return None

    def is_done(self, key):
        sc = self.read_sidecar(key)
        if sc is None:
            return False
        if sc.get("status") == "ok" and os.path.exists(self.glb_path(key)):
            return True
        if sc.get("status") in ("failed", "fallback") and sc.get("attempts", 1) >= MAX_ATTEMPTS:
            return True
        return False

    def pending(self, assets=None):
        assets = assets if assets is not None else load_assets()
        return [a for a in assets if not self.is_done(a["asset_key"])]

    def claimable(self, assets=None):
        """Pending assets not currently locked by a live worker."""
        return [a for a in self.pending(assets) if not self.is_locked(a["asset_key"])]

    def is_locked(self, key):
        lp = self.lock_path(key)
        return os.path.exists(lp) and not self._lock_is_stale(lp)

    # ---------------- claiming ----------------
    def lock_path(self, key):
        return f"{self.locks_dir}/{key}.lock"

    def try_claim(self, key):
        lp = self.lock_path(key)
        for _ in range(2):
            try:
                fd = os.open(lp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o664)
            except FileExistsError:
                if self._lock_is_stale(lp):
                    try:
                        os.remove(lp)
                    except FileNotFoundError:
                        pass
                    continue
                return False
            with os.fdopen(fd, "w") as f:
                json.dump({"host": self.host, "pid": os.getpid(),
                           "slurm_job": os.environ.get("SLURM_JOB_ID"),
                           "time": time.time()}, f)
            # re-check after claiming (another worker may have finished it meanwhile)
            if self.is_done(key):
                self.release(key)
                return False
            return True
        return False

    def _lock_is_stale(self, lp):
        try:
            with open(lp) as f:
                info = json.load(f)
        except Exception:
            # unreadable / half-written: stale only if old
            try:
                return time.time() - os.path.getmtime(lp) > STALE_LOCK_SECS
            except FileNotFoundError:
                return True
        if info.get("host") == self.host and not _pid_alive(int(info.get("pid", -1))):
            return True
        return time.time() - float(info.get("time", 0)) > STALE_LOCK_SECS

    def release(self, key):
        try:
            os.remove(self.lock_path(key))
        except FileNotFoundError:
            pass

    # ---------------- writing ----------------
    def write_sidecar(self, key, data):
        p = self.sidecar_path(key)
        tmp = f"{p}.tmp.{os.getpid()}"
        with open(tmp, "w") as f:
            json.dump(data, f, indent=1)
        os.replace(tmp, p)

    def write_glb(self, key, scene_or_mesh):
        p = self.glb_path(key)
        tmp = f"{self.assets_dir}/.{key}.glb.tmp.{os.getpid()}"
        data = scene_or_mesh.export(file_type="glb")
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, p)
        return p


def rot_y(deg):
    """4x4 rotation about +Y (right-handed): +Z -> +X for deg=90."""
    r = np.deg2rad(deg)
    c, s = np.cos(r), np.sin(r)
    return np.array([[c, 0, s, 0], [0, 1, 0, 0], [-s, 0, c, 0], [0, 0, 0, 1]], dtype=np.float64)


def _rot(axis, deg):
    r = np.deg2rad(deg)
    c, s = np.cos(r), np.sin(r)
    M = np.eye(4)
    if axis == 0:
        M[:3, :3] = [[1, 0, 0], [0, c, -s], [0, s, c]]
    elif axis == 1:
        M[:3, :3] = [[c, 0, s], [0, 1, 0], [-s, 0, c]]
    else:
        M[:3, :3] = [[c, -s, 0], [s, c, 0], [0, 0, 1]]
    return M


# (generated thin axis, target thin axis) -> (rotation axis, degrees) mapping the first onto the second
# axes in glTF frame: 0=X (width), 1=Y (up/height), 2=Z (front-back depth)
_THIN_FIX = {
    (1, 2): (0, 90),   # lying flat, should stand upright: +Y face -> +Z (front)
    (2, 1): (0, -90),  # standing, should lie flat: +Z face -> +Y (up)
    (0, 2): (1, -90),  # thin along X, should be thin along Z: +X face -> +Z
    (2, 0): (1, 90),   # thin along Z, should be thin along X: +Z face -> +X
    (0, 1): (2, 90),   # X -> Y
    (1, 0): (2, -90),  # Y -> X
}
THIN_RATIO = 0.35


def align_thin_axis(scene, dims):
    """Canonicalisation for clearly thin objects (wall art, clocks, mirrors, rugs, ...).

    If the target bbox is clearly thin along one axis and the generated mesh is clearly thin
    along a *different* axis (e.g. a wall clock generated lying face-up), rotate the mesh by 90deg
    so the thin axes coincide (face-up -> faces +Z). Uses only the asset's own input bbox dims.
    Returns a description string, or None if nothing was changed.
    """
    t = np.array([dims["width"], dims["height"], dims["length"]], dtype=float)  # glTF X, Y, Z
    b = scene.bounds
    e = np.asarray(b[1] - b[0], dtype=float)
    ts, es = np.sort(t), np.sort(e)
    t_thin, g_thin = int(np.argmin(t)), int(np.argmin(e))
    if t_thin == g_thin:
        return None
    if ts[0] / max(ts[1], 1e-9) >= THIN_RATIO or es[0] / max(es[1], 1e-9) >= THIN_RATIO:
        return None
    axis, deg = _THIN_FIX[(g_thin, t_thin)]
    scene.apply_transform(_rot(axis, deg))
    names = "XYZ"
    return (f"thin-axis fix: generated mesh thin along {names[g_thin]} (extents {np.round(e, 3).tolist()}), "
            f"target bbox thin along {names[t_thin]}; rotated {deg:+d} deg about {names[axis]}")


def convert_to_contract(job, key, raw_path, front_rot_y_deg, dims, max_faces=200_000):
    """raw mesh/GLB -> results/<M>/assets/<key>.glb in the contract convention.

    1) rotation about +Y by front_rot_y_deg (method-wide native->front +Z), 2) align_thin_axis,
    3) quadric decimation if > max_faces. Returns dict of sidecar fields.
    """
    import trimesh
    scene = trimesh.load(raw_path, force="scene")
    raw_ext = [float(x) for x in (scene.bounds[1] - scene.bounds[0])]
    if front_rot_y_deg:
        scene.apply_transform(rot_y(front_rot_y_deg))
    fix = align_thin_axis(scene, dims)
    out = {"raw_extent_xyz": raw_ext, "front_rot_y_deg": front_rot_y_deg, "orient_fix": fix}
    st = mesh_stats(scene)
    if st["faces"] > max_faces:
        for name, g in list(scene.geometry.items()):
            target = int(len(g.faces) * max_faces / st["faces"])
            scene.geometry[name] = g.simplify_quadric_decimation(face_count=target)
        out["decimated_from_faces"] = st["faces"]
        st = mesh_stats(scene)
    job.write_glb(key, scene)
    out["stats"] = st
    return out


def mesh_stats(scene):
    import trimesh
    if isinstance(scene, trimesh.Trimesh):
        geoms = [scene]
    else:
        geoms = [g for g in scene.geometry.values() if isinstance(g, trimesh.Trimesh)]
    nf = int(sum(len(g.faces) for g in geoms))
    nv = int(sum(len(g.vertices) for g in geoms))
    tex = []
    for g in geoms:
        mat = getattr(getattr(g, "visual", None), "material", None)
        for attr in ("baseColorTexture", "image"):
            im = getattr(mat, attr, None) if mat is not None else None
            if im is not None:
                tex.append(list(im.size))
    b = scene.bounds
    return {"faces": nf, "vertices": nv, "textures": tex,
            "bbox_extent_xyz": [float(x) for x in (b[1] - b[0])]}


if __name__ == "__main__":
    # python rgbjob.py <method>  -> prints "<pending> <claimable> <ok> <failed>"
    import sys
    j = Job(sys.argv[1])
    A = load_assets()
    st = [(j.read_sidecar(a["asset_key"]) or {}).get("status") for a in A]
    print(len(j.pending(A)), len(j.claimable(A)), st.count("ok"), st.count("failed"))
