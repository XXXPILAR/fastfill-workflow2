"""One exported room as a textured 3D room on a laptop: no GPU, no asset generation.

The meshes come from RoomGenBench's own web rooms (``site/data/<method>/<scene>.room.json``): every instance node
``obj_<i>_p<k>`` there holds the asset already fitted to its box in SAGE's object frame (front +Y, bottom centre at
the origin). Each of our objects takes the closest library asset by type (exact type, then a few synonyms, then shared
words; ties go to the closest box proportions), scaled to our box and placed by ``bench/assemble.py``'s own
``place_matrix``; the shell is its ``build_shell``. An object with no match stays a grey box. The assets were made
for SAGE's descriptions, not ours: this shows the layout in 3D, it is not a RoomGenBench method run.

    ../.venv/bin/python experiments/rgb_local_room.py \
        --scene experiments/simple20_robot2/roomgenbench/inputs/scenes/room_079.json

Writes ``<scene>.glb``, ``<scene>.html`` (a three.js viewer with the GLB inlined: open it in a browser) and
``<scene>.matches.json`` next to the scene (``--out`` elsewhere).
"""
import argparse, base64, importlib.util, io, json, math, re
from pathlib import Path

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parents[1]
RGB = HERE.parent / "RoomGenBench-30f2e059d046ccd4aa928d0109a09a52f11693b5 2"
SCENES = ["gym", "restaurant", "livingroom", "bedroom", "bathroom"]
SYNONYMS = {"carpet": "mat", "rug": "mat", "couch": "sofa", "tv": "mediaconsole", "television": "mediaconsole",
            "flowerpot": "plant", "pottedplant": "plant", "bottle": "shampoobottle", "desk": "table",
            "bookcase": "bookshelf", "trash": "trashcan", "lamp": "tablelamp", "picture": "painting"}


def norm(text: str) -> str:
    return re.sub(r"[^a-z]", "", text.lower())


def words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", text.lower()) if len(w) > 2}


def library(rgb: Path, method: str, assemble) -> list[dict]:
    """Every asset of ``method``'s five web rooms, once per asset key, in its own box's frame."""
    out, seen = [], set()
    for scene in SCENES:
        scene_in = json.loads((rgb / "bench" / "inputs" / "scenes" / f"{scene}.json").read_text())
        room = json.loads((rgb / "site" / "data" / method / f"{scene}.room.json").read_text())
        glb = trimesh.load(io.BytesIO(base64.b64decode(room["glb"])), file_type="glb", force="scene")
        parts = {}
        for node in glb.graph.nodes_geometry:
            m = re.fullmatch(r"obj_(\d+)_p\d+", node)
            if m:
                parts.setdefault(int(m.group(1)), []).append(glb.graph[node][1])
        for i, obj in enumerate(scene_in["objects"]):
            if i not in parts or obj["asset_key"] in seen:
                continue
            seen.add(obj["asset_key"])
            out.append({"key": obj["asset_key"], "type": obj["type"], "description": obj["description"],
                        "scene": scene, "dims": obj["dimensions"],
                        "meshes": [glb.geometry[g] for g in parts[i]]})
    return out


def match(obj: dict, lib: list[dict], room_type: str):
    t = norm(obj["type"])
    t = SYNONYMS.get(t, t)
    def score(a):
        at = norm(a["type"])
        s = 3 if at == t or at.rstrip("0123456789") == t else 2 if t and (t in at or at in t) and len(at) > 3 else 0
        if not s:
            s = len(words(obj["type"]) & (words(a["type"]) | words(a["description"]))) * .5
        if not s:
            return None
        d, e = obj["dimensions"], a["dims"]
        aspect = sum(abs(math.log(max(d[k], 1e-3) / max(e[k], 1e-3))) for k in ("width", "length", "height"))
        return s + .3 * (norm(room_type)[:4] in a["scene"]) - .1 * aspect
    ranked = sorted(((score(a), n) for n, a in enumerate(lib)), key=lambda x: -1e9 if x[0] is None else x[0],
                    reverse=True)
    return lib[ranked[0][1]] if ranked and ranked[0][0] is not None else None


def fitted(meshes: list, dims: dict) -> list:
    """The asset's parts scaled anisotropically to ``dims`` (width X, length Y, height Z), bottom centre at 0."""
    lo = np.min([m.bounds[0] for m in meshes], 0)
    hi = np.max([m.bounds[1] for m in meshes], 0)
    size = np.maximum(hi - lo, 1e-6)
    target = np.array([dims["width"], dims["length"], dims["height"]])
    T = np.diag([*(target / size), 1.])
    T[:3, 3] = -np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]]) * target / size
    out = []
    for m in meshes:
        m = m.copy()
        m.apply_transform(T)
        out.append(m)
    return out


VIEWER = """<!doctype html><html><head><meta charset="utf-8"><title>{title}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>html,body{{margin:0;height:100%;background:#f3f1ec;font:14px system-ui}}#info{{position:absolute;left:12px;top:10px;
background:#fffd;padding:6px 10px;border-radius:6px}}button{{margin-left:8px}}</style></head><body><div id="info">{title} · drag to orbit, scroll to zoom
<button id="walls">walls: low</button></div>
<script type="importmap">{{"imports":{{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
"three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}}}</script>
<script type="module">
import * as THREE from 'three';
import {{ OrbitControls }} from 'three/addons/controls/OrbitControls.js';
import {{ GLTFLoader }} from 'three/addons/loaders/GLTFLoader.js';
const renderer = new THREE.WebGLRenderer({{antialias: true}});
renderer.setPixelRatio(devicePixelRatio); renderer.setSize(innerWidth, innerHeight);
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene(); scene.background = new THREE.Color(0xf3f1ec);
scene.add(new THREE.HemisphereLight(0xffffff, 0x8a7f70, 2.0)); scene.add(new THREE.AmbientLight(0xffffff, .8));
const sun = new THREE.DirectionalLight(0xffffff, 1.6); sun.position.set(4, 8, 3); scene.add(sun);
const camera = new THREE.PerspectiveCamera(50, innerWidth / innerHeight, .05, 200);
const controls = new OrbitControls(camera, renderer.domElement);
const bytes = Uint8Array.from(atob("{glb}"), c => c.charCodeAt(0));
new GLTFLoader().parse(bytes.buffer, '', g => {{
  scene.add(g.scene);
  const walls = [];
  g.scene.traverse(o => {{ if (o.isMesh) {{ o.material.side = THREE.DoubleSide;
    if (o.name.startsWith('shell_wall')) walls.push(o); }} }});
  const modes = ['low', 'hidden', 'full']; let mode = 0;
  const apply = () => walls.forEach(w => {{ w.visible = modes[mode] != 'hidden';
    w.scale.set(1, 1, 1); if (modes[mode] == 'low') {{ w.material.transparent = true; w.material.opacity = .35; }}
    else {{ w.material.transparent = false; w.material.opacity = 1; }} }});
  apply();
  document.getElementById('walls').onclick = e => {{ mode = (mode + 1) % 3; e.target.textContent = 'walls: ' + modes[mode]; apply(); }};
  const box = new THREE.Box3().setFromObject(g.scene), c = box.getCenter(new THREE.Vector3()), s = box.getSize(new THREE.Vector3());
  controls.target.copy(c); camera.position.set(c.x + s.x * .6, c.y + Math.max(s.x, s.z) * 1.1, c.z + s.z * 1.1); controls.update();
}});
addEventListener('resize', () => {{ camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight); }});
renderer.setAnimationLoop(() => {{ controls.update(); renderer.render(scene, camera); }});
</script></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", type=Path, required=True, help="an exported scene (export_roomgenbench.py)")
    ap.add_argument("--method", default="embodiedgen_v2", help="whose assets: a folder of RoomGenBench's site/data")
    ap.add_argument("--roomgenbench", type=Path, default=RGB)
    ap.add_argument("--out", type=Path, help="default: next to the scene")
    a = ap.parse_args()
    spec = importlib.util.spec_from_file_location("rgb_assemble", a.roomgenbench / "bench" / "assemble.py")
    assemble = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(assemble)
    scene_in = json.loads(a.scene.read_text())
    lib = library(a.roomgenbench, a.method, assemble)
    out = trimesh.Scene()
    shell, _walls = assemble.build_shell(scene_in["room"])
    for name, m in shell:
        out.add_geometry(m, node_name=name, geom_name=name, transform=assemble.SAGE_WORLD_TO_GLTF)
    matches = []
    for i, obj in enumerate(scene_in["objects"]):
        T = assemble.SAGE_WORLD_TO_GLTF @ assemble.place_matrix(obj)
        found = match(obj, lib, scene_in.get("room_type", ""))
        if found:
            parts = fitted(found["meshes"], obj["dimensions"])
        else:
            d = obj["dimensions"]
            parts = [assemble.colored_box([d["width"], d["length"], d["height"]],
                                          trimesh.transformations.translation_matrix([0, 0, d["height"] / 2]),
                                          assemble.PLACEHOLDER_RGBA)]
        for k, part in enumerate(parts):
            out.add_geometry(part, node_name=f"obj_{i:03d}_p{k}", geom_name=f"obj_{i:03d}_p{k}", transform=T)
        matches.append({"id": obj["id"], "type": obj["type"],
                        "asset": None if found is None else {k: found[k] for k in ("key", "type", "scene", "description")}})
    out_dir = a.out or a.scene.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = a.scene.stem
    glb = out.export(file_type="glb")
    (out_dir / f"{stem}.glb").write_bytes(glb)
    (out_dir / f"{stem}.matches.json").write_text(json.dumps(matches, ensure_ascii=False, indent=1))
    title = f"{stem} ({scene_in.get('room_type', 'room')}) · {a.method} assets"
    (out_dir / f"{stem}.html").write_text(VIEWER.format(title=title, glb=base64.b64encode(glb).decode()))
    hit = sum(m["asset"] is not None for m in matches)
    print(f"{hit}/{len(matches)} objects matched to {a.method} assets; {len(glb) / 1e6:.1f} MB")
    for m in matches:
        print(f"  {m['type']:<16} -> {m['asset']['type'] + ' (' + m['asset']['scene'] + ')' if m['asset'] else 'grey box'}")
    print(out_dir / f"{stem}.html")


if __name__ == "__main__":
    main()
