# Independent evaluation (metrics not optimised by the workflow)

Rooms: the 20 rooms of `simple20_robot2` (fewer where a method has no layout). `*` = our own checker, which the workflow optimises.
SceneEval: its own metric code (navigability, collision with a 5 mm double check, out of bound with 99 % of sampled points over the floor) on box meshes.
EmbodiedGen: its RoamTrajectoryGenerator (clearance 0.25 m). rect base: a 0.5 x 0.7 m base with 16 headings planned from the doors; parked = front within 0.30 m facing the furniture within 30 deg; 3D arm = 0.85 m from a 0.9 m shoulder 0.2 m ahead, facing within 60 deg.

| method | rooms | legal* | rooms ok @0.5* | SceneEval NAV (0.2 m) | SceneEval NAV (0.5 m) | SceneEval COL % objects ↓ | SceneEval OOB % objects ↓ | EmbodiedGen roam ok | EmbodiedGen one region | EmbodiedGen largest share | rect base: furniture parked | rect base: items in 3D arm reach | rect base: rooms all reached | 1 cm jitter pass→fail ↓ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ground truth | 20 | 45.0 | 15.0 | 91.1 | 88.2 | 26.8 | 14.0 | 100.0 | 50.0 | 92.5 | 79.3 | 72.1 | 15.0 | 0.0 |
| GPT-5.6 one-shot | 20 | 80.0 | 45.0 | 97.6 | 95.8 | 2.6 | 6.6 | 100.0 | 60.0 | 96.4 | 78.6 | 80.5 | 45.0 | 2.0 |
| Holodeck | 20 | 45.0 | 5.0 | 98.9 | 94.1 | 32.9 | 0.5 | 100.0 | 65.0 | 98.5 | 89.5 | 81.7 | 35.0 | 0.0 |
| LayoutVLM | 20 | 60.0 | 20.0 | 98.4 | 90.6 | 16.8 | 40.0 | 100.0 | 50.0 | 97.5 | 75.0 | 70.1 | 35.0 | 0.0 |
| LayoutGPT | 20 | 20.0 | 0.0 | 97.2 | 89.5 | 27.7 | 24.6 | 100.0 | 45.0 | 94.9 | 54.8 | 80.0 | 20.0 | 30.0 |
| FastFill base | 20 | 15.0 | 5.0 | 98.6 | 89.9 | 19.4 | 17.5 | 100.0 | 40.0 | 96.8 | 56.8 | 67.4 | 15.0 | 0.0 |
| ours C_final | 19 | 100.0 | 52.6 | 96.5 | 92.3 | 0.0 | 2.2 | 100.0 | 52.6 | 94.4 | 71.7 | 75.9 | 36.8 | 0.0 |
| workflow2 (no robot) | 17 | 100.0 | 47.1 | 92.2 | 91.5 | 0.0 | 4.4 | 100.0 | 52.9 | 91.3 | 73.8 | 70.7 | 41.2 | 0.0 |
| workflow2 + robot | 20 | 95.0 | 70.0 | 97.3 | 91.9 | 1.7 | 4.3 | 100.0 | 70.0 | 98.0 | 91.4 | 90.7 | 55.0 | 5.3 |
| workflow2 + robot + 2 drafts | 20 | 90.0 | 70.0 | 96.7 | 91.3 | 1.7 | 3.1 | 100.0 | 60.0 | 93.0 | 70.8 | 66.7 | 40.0 | 4.0 |
