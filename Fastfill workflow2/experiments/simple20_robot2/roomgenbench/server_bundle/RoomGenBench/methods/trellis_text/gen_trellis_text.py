"""RoomGenBench method `trellis_text`: TRELLIS native text->3D (microsoft/TRELLIS-text-xlarge).

Resumable worker: processes up to --chunk unclaimed assets (or until --time-budget seconds
have elapsed), then exits. Run under bench/gpu_run.sh on hala (see run_loop.sh).
"""
import argparse
import os
import subprocess
import sys
import time
import traceback

os.environ.setdefault("SPCONV_ALGO", "native")
os.environ.setdefault("ATTN_BACKEND", "xformers")  # flash-attn is not installed in rgb_embodiedgen

HERE = os.path.dirname(os.path.abspath(__file__))
TRELLIS_DIR = os.path.join(HERE, "TRELLIS")
sys.path.insert(0, TRELLIS_DIR)
sys.path.insert(0, os.path.join(HERE, "..", "embodiedgen_v2"))
import rgbjob  # noqa: E402

METHOD = "trellis_text"
MODEL_ID = "microsoft/TRELLIS-text-xlarge"
SEED = 0
SIMPLIFY = 0.95
TEXTURE_SIZE = 1024
# TRELLIS to_glb output is glTF Y-up; rotation about +Y applied afterwards so that the
# object's front faces +Z (determined by inspecting smoke-test outputs, see README).
FRONT_ROT_Y_DEG = float(os.environ.get("TRELLIS_FRONT_ROT_Y_DEG", "0"))


def git_commit(path):
    try:
        return subprocess.check_output(["git", "-C", path, "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunk", type=int, default=8)
    ap.add_argument("--time-budget", type=float, default=1140.0,
                    help="stop starting new assets when elapsed + expected asset time exceeds this")
    ap.add_argument("--expected-asset-secs", type=float, default=120.0)
    ap.add_argument("--keys", nargs="*", default=None, help="restrict to these asset_keys (smoke test)")
    args = ap.parse_args()

    t_start = time.time()
    job = rgbjob.Job(METHOD)
    assets = rgbjob.load_assets()
    if args.keys:
        assets = [a for a in assets if a["asset_key"] in set(args.keys)]
    todo = job.claimable(assets)
    print(f"[{METHOD}] claimable {len(todo)}/{len(assets)}", flush=True)
    if not todo:
        return 0

    import torch
    from trellis.pipelines import TrellisTextTo3DPipeline
    from trellis.utils import postprocessing_utils

    t0 = time.time()
    pipe = TrellisTextTo3DPipeline.from_pretrained(MODEL_ID)
    pipe.cuda()
    load_s = time.time() - t0
    print(f"[{METHOD}] pipeline loaded in {load_s:.1f}s", flush=True)
    commit = git_commit(TRELLIS_DIR)

    n_done, max_asset = 0, args.expected_asset_secs
    for a in todo:
        if n_done >= args.chunk or time.time() - t_start + max_asset > args.time_budget:
            break
        key = a["asset_key"]
        if not job.try_claim(key):
            continue
        prev = job.read_sidecar(key) or {}
        attempts = int(prev.get("attempts", 0)) + 1 if prev.get("status") != "ok" else 1
        prompt = a["description"]
        # retry of a failed asset (e.g. spconv int32 overflow in the decoder) uses the next seed
        seed = SEED + attempts - 1
        inter = f"{job.inter_dir}/{key}"
        os.makedirs(inter, exist_ok=True)
        side = {"asset_key": key, "method": METHOD, "prompt": prompt, "seed": seed,
                "model": MODEL_ID, "trellis_commit": commit,
                "sampler": "pipeline.json defaults (25 steps, cfg 7.5, both stages)",
                "to_glb": {"simplify": SIMPLIFY, "texture_size": TEXTURE_SIZE},
                "front_rot_y_deg": FRONT_ROT_Y_DEG, "attempts": attempts,
                "host": job.host, "slurm_job": os.environ.get("SLURM_JOB_ID")}
        t1 = time.time()
        try:
            with torch.no_grad():
                out = pipe.run(prompt, seed=seed, formats=["mesh", "gaussian"])
            glb = postprocessing_utils.to_glb(out["gaussian"][0], out["mesh"][0],
                                              simplify=SIMPLIFY, texture_size=TEXTURE_SIZE,
                                              verbose=False)
            raw_path = f"{inter}/raw_trellis.glb"
            glb.export(raw_path)
            conv = rgbjob.convert_to_contract(job, key, raw_path, FRONT_ROT_Y_DEG, a["dimensions"])
            note = "" if attempts == 1 else f"retry {attempts}: seed {seed} (previous: {prev.get('notes', '')[:200]})"
            side.update(status="ok", seconds=round(time.time() - t1, 1), raw_glb=raw_path,
                        notes=note, **conv)
            del out, glb
        except Exception as e:
            traceback.print_exc()
            side.update(status="failed", seconds=round(time.time() - t1, 1),
                        notes=f"{type(e).__name__}: {e}"[:500])
        finally:
            torch.cuda.empty_cache()
        job.write_sidecar(key, side)
        job.release(key)
        n_done += 1
        max_asset = max(max_asset * 0.5, side["seconds"]) if n_done == 1 else max(max_asset, side["seconds"])
        print(f"[{METHOD}] {key}: {side['status']} {side['seconds']}s", flush=True)

    print(f"[{METHOD}] chunk finished: {n_done} assets in {time.time() - t_start:.0f}s "
          f"(load {load_s:.0f}s)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
