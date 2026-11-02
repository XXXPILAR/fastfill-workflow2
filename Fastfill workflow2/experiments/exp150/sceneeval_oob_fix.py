"""SceneEval's OutOfBoundMetric on exp150 with the floor mesh 1 cm below the floor.

evaluate.py builds each object as a box whose bottom face lies exactly on the floor plane; SceneEval samples points
on every object's surface and casts each straight down onto the floor mesh, so the bottom face's points start ON the
floor plane and whether their rays count as hitting it is numerical chance: objects well inside the room were flagged
(in 60 g1 rooms, 56 of 84 flagged objects stood on the floor inside it). Lowering the floor mesh by 1 cm makes every
point above the floor hit it while a point beyond the floor polygon still misses; nothing else changes.

    ../.venv/bin/python experiments/exp150/sceneeval_oob_fix.py [workers]   # writes eval/sceneeval_oob_fixed.json
"""
import contextlib, io, json, sys
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import evaluate as ev  # noqa: E402  (paths, rooms, method loading)
import numpy as np  # noqa: E402
import trimesh  # noqa: E402
from metrics.out_of_bound import OutOfBoundMetric, OutOfBoundMetricConfig  # noqa: E402

FLOOR_DROP_M = .01


def job(args):
    name, k, layout = args
    if not layout:
        return name, k, None
    row = ev.ie.ROWS[k]
    scene = ev.ie.BoxScene(row, layout)
    floor = scene.t_architecture["floor_0"].copy()
    floor.vertices = np.asarray(floor.vertices) - np.array([0, 0, FLOOR_DROP_M])
    scene.t_architecture = {"floor_0": floor}
    with contextlib.redirect_stdout(io.StringIO()):
        b = OutOfBoundMetric(scene, OutOfBoundMetricConfig(threshold=.99, volume_sample_multiplier=5000.,
                                                           min_sample_points=1000)).run()
    return name, k, (sum(v["out_of_bound"] for v in b.data.values()), len(b.data))


def main():
    ev.init()
    src = ev.load()
    jobs = [(m, k, src[m][k][0]) for m in ev.METHODS for k in ev.ROOMS]
    out = {m: {} for m in ev.METHODS}
    with Pool(int(sys.argv[1]) if len(sys.argv) > 1 else 8, initializer=ev.init) as pool:
        for n, (m, k, v) in enumerate(pool.imap_unordered(job, jobs)):
            out[m][str(k)] = v
            if (n + 1) % 150 == 0:
                print(f"{n + 1}/{len(jobs)}", file=sys.stderr, flush=True)
    (HERE / "eval/sceneeval_oob_fixed.json").write_text(json.dumps({"floor_drop_m": FLOOR_DROP_M, "rooms": out}))
    for m in ev.METHODS:
        vals = [1 - a / b if b else 1. for a, b in (v for v in out[m].values() if v)]
        print(f"{m[:40]:40} scenes {len(vals)}  OOB (in-bound share, mean over scenes) {100 * sum(vals) / len(vals):.1f}")


if __name__ == "__main__":
    main()
