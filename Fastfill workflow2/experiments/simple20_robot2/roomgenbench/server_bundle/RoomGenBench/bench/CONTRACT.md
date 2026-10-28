# RoomGenBench — method contract

Goal: **layout → room mesh**. For each of 5 SAGE-10k rooms, every method turns the
layout (object 3D bboxes + per-object text description) into object meshes; a shared
assembler (`bench/assemble.py`, owned by the orchestrator) places them into the room
shell and exports one room mesh per (method, room).

## Hard rules

- **Inputs are text + bboxes only.** Read only `bench/inputs/`. Never read anything under
  `/group/streetsplat/WorldGrow/data/sage10k_raw` (no SAGE meshes, textures, previews,
  materials). A method may generate its *own* intermediate image from the text
  (text→image→3D); record that in the sidecar and README.
- Prompt = the object `description` (you may prepend/append a fixed method-wide template,
  e.g. "white background, single object"). Do not use the scene style or other objects.
- Never substitute GT. If an asset cannot be produced, mark it `failed` (the assembler
  draws a grey placeholder box) or `fallback` (a clearly-noted proxy), never silently.

## Inputs

`bench/inputs/assets.jsonl` — 184 unique assets (deduplicated by type+description),
one JSON per line:

| field | meaning |
|---|---|
| `asset_key` | file stem to use for outputs, e.g. `armchair_2eaaa0e3` |
| `type` | free-form category, e.g. `armchair`, `wallart`, `book_1` |
| `description` | the text prompt |
| `dimensions` | metric bbox `{width, length, height}` = extent along object-local X, Y(depth, front–back), Z(up) |
| `place` | `floor` / `wall` / `on_object` |
| `scenes`, `n_instances` | which rooms use it, how many copies |

`bench/inputs/scenes/<scene>.json` — per-room layout (shell + instances); you normally
don't need it.

## Outputs (per method `<M>`, a short snake_case id)

```
results/<M>/assets/<asset_key>.glb    the generated object
results/<M>/assets/<asset_key>.json   sidecar (see below)
results/<M>/intermediate/<asset_key>/ optional: T2I image, raw outputs, logs
results/<M>/README.md                 version (git tag/commit), env, exact commands,
                                      settings, deviations, runtime, failure list
methods/<M>/                          your scripts (generation, sbatch files)
```

**GLB convention** (the assembler relies on it):
- glTF standard **Y-up**, object's **front faces +Z** (sofa/chair/bed: the side you sit
  or lie on faces +Z, backrest/headboard at −Z; cabinet/shelf/TV: doors/screen face +Z;
  wall art / mirror / clock: visible face +Z, back towards −Z). Width runs along X.
- Any scale and offset — the assembler normalises the asset's AABB to the bbox
  (anisotropic fit) and moves its bottom-centre to the placement point.
- Keep the method's native appearance: baked texture (PBR or base colour) or vertex
  colours. ≤ 200k faces, textures ≤ 2048 px (the assembler compresses for the web).
- One mesh or a small node hierarchy; no cameras/lights.

**Sidecar JSON**:
```json
{"asset_key": "...", "method": "<M>", "status": "ok|fallback|failed",
 "prompt": "<exact text fed to the model>", "seconds": 12.3, "notes": "...",
 "...method-specific...": "seed, factory name, objaverse uid, t2i image path, ..."}
```

## Compute

- **GPU**: the cluster GPU quota for this user is full and every GPU is allocated.
  The usable GPU is the local **hala RTX A6000** (~40 GB free), which is shared with the
  user's own 3DGS training — never touch or kill other processes.
  - Every RoomGenBench GPU process on hala must run under the lock:
    `bench/gpu_run.sh <command...>` (an `flock`). One RoomGenBench GPU process at a time.
  - Hold the lock **≤ ~20 min** per invocation: batch scripts process a chunk of assets,
    exit, and are re-invoked, so other methods can interleave.
  - Optionally also `sbatch --gres=gpu:1` a backup worker (it will queue; fine). Inside a
    SLURM GPU job do not use the lock.
- Generation scripts must be **resumable** (skip assets whose sidecar has `status: ok`)
  and **claim** each asset with an exclusive lock file
  `results/<M>/locks/<asset_key>.lock` (`os.open(..., O_CREAT|O_EXCL)`), so local and
  SLURM workers can run concurrently. Write outputs atomically (tmp file + rename).
- **CPU-heavy work** (Blender/Infinigen, big embedding jobs): SLURM CPU-only jobs, which
  start immediately: `sbatch -p batch --cpus-per-task=N --mem=XG -t HH:MM` (no `--gres`).
  hala's CPUs are all allocated, so don't run heavy CPU loads there directly.
- `source bench/env.sh` first in every shell/job: it points HF/torch/pip caches at shared
  cephfs (`/scratch` is node-local). The HF token is already in that cache.
- Conda envs: create new ones named `rgb_<M>` (they land in
  `/group/streetsplat/.conda/envs/`, visible cluster-wide). Do not modify existing envs;
  `conda create --clone` if you want to start from one.
- Logs: `logs/<M>_*.log`.

## Don'ts

Don't modify `bench/` (except reading/running it), other methods' `results/`/`methods/`,
or anything outside `RoomGenBench/` other than your own conda env. Don't cancel SLURM jobs
you didn't submit. Don't git push or commit to the cloned repos.
