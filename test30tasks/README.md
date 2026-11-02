# test30tasks：带任务的 30 个高质量房间（2026-11-02）

模拟上游任务分析 agent 的输出。每个房间有 2–3 个家用机器人任务，房间里的物体分成两组：
- **必须家具**：任务要用到的物体；
- **扩充家具**：其余所有物体。

这样每个房间都具备上游会给我们的全部内容：
- room type；
- 房间壳子；
- 必须家具及其关系；
- 哪些要做 articulation；
- 扩充家具，每件都带详细描述。

## 房间怎么选（`room_quality.json`）

从 test150detail 的 150 个房间中，选出同时满足下面五条的房间，共 33 个：

| 质量条件 | 原因 |
|---|---|
| 真实布局合法：没有碰撞、没有出界、没有挡门（用 `experiments/robot_check.py` 检查，和 exp150 打分用的是同一套） | 原始数据本身要可信 |
| 每个物体的类别和描述一致 | IL3D 里有类别写 "drawer chest"、描述却是一张床这样的错误 |
| 每个物体都标明了放在哪里（`support_parent`） | 必须知道什么东西放在什么上面 |
| 至少 1 扇门 | 机器人要从门口进来 |
| 至少 6 件物体 | 才能分出必须家具和扩充家具 |

在这 33 个里，再去掉真实布局中机器人几乎够不到任何家具的 3 个（109、134、143），剩下 30 个。真实布局普遍不是为 0.5 m 宽的机器人设计的，150 个房间里只有 3 个能完全通过机器人检查；让布局通过这项检查，正是我们这一层要做的事，所以这一条只用来去掉最差的几个房间。

各来源通过五条条件的情况：
- **IL3D_3dfront**：78 个里只有 18 个真实布局合法，最后 2 个入选。
- **IL3D_synthetic**：28 个房间都没有门，0 个入选。
- **SAGE-10k**：28 个入选。

| | 房间 | 物体总数 | 每房间物体数（最少 / 中位 / 最多） | 必须家具（最少 / 中位 / 最多） | 扩充家具（最少 / 中位 / 最多） |
|---|---|---|---|---|---|
| 合计 | 30（SAGE-10k 28，IL3D_3dfront 2） | 2,248 | 8 / 76 / 142 | 3 / 7 / 10，共 204 | 3 / 70 / 135，共 2,044 |

另有：86 个任务，28 件需要 articulation 的家具，22 条必须关系（约束里涉及的物体全是必须家具），61 条约束涉及扩充家具。

## 任务怎么写（`tasks_source.json`）

任务由 Claude（claude-opus-5-5）在 2026-11-02 读每个房间的物体清单（类别、描述、放在哪里）后**逐个手写**，不是用脚本或其他模型生成的。

- 每个任务列出它用到的物体 id：
  - 要拿取或操作的物体；
  - 它现在放在哪里；
  - 要放到哪里；
  - 机器人要在哪件家具前工作。
- 任务要打开的物体（柜门、抽屉、冰箱、洗衣机、箱子）列在 `articulation` 里。
- **必须家具** = 任务用到的物体，加上它们所在的家具（递归）。比如杯子在桌上，桌子也是必须家具。这次所有任务都已经写明了所在的家具，所以脚本没有额外补充（`supports_added` 为空）。
- 生成后逐条核对过：每个任务的文字和它引用的物体类别、描述一致。

## 文件

| 文件 | 内容 |
|---|---|
| `rows.jsonl` | 30 行。每行就是 test150detail 里对应的那一行，**`condition`（输入）和 `target`（真实布局）都没有改**，只多了一个 `task` 字段 |
| `rooms.json` | `[0, …, 29]`，给各个运行脚本的 `--rooms` / `--indices` 参数用 |
| `tasks_source.json` | 手写的任务（数据来源） |
| `room_quality.json` | 150 个房间的质量检查结果、通过的 33 个、选中的 30 个 |
| `MANIFEST.json` | 输入和输出的 sha256、每个房间的统计 |

`task` 字段的例子（第 0 行，test150detail 第 16 号房间）：

```json
{"base_index": 16, "room_type": "living dining room",
 "tasks": [{"text": "Take the wine glasses out of the dark sideboard and put them on the dining table.",
            "uses": ["obj_0003", "obj_0007"], "articulation": ["obj_0003"]}, …],
 "required_ids": ["obj_0002", "obj_0003", "obj_0007"],
 "expansion_ids": ["obj_0000", "obj_0001", "obj_0004", "obj_0005", "obj_0006"],
 "articulation_ids": ["obj_0003"], "supports_added": [],
 "required_constraints": [2], "expansion_constraints": [0, 1]}
```

`required_constraints` 和 `expansion_constraints` 是 `condition.constraints` 里的下标。

**注意**：现在的输入格式（`fastfill.v2`）还没有"必须 / 扩充"和 articulation 字段，所以这些信息暂时放在 `task` 字段里，`condition` 保持原样。现有的流程和打分脚本都可以直接读这些行，但它们**还不会使用**这个区分。要让流程做到"必须家具一定不能错、扩充家具可以删改"，需要另外修改流程。

`rows_sha256`：`9ec104e72cb281df6ca86efcb6750885b38bee31bb54af5114e54fb16d34296e`

## 复现

在 `Fastfill workflow2` 下运行：

```bash
../.venv/bin/python experiments/room_quality.py --rows ../test150detail/rows.jsonl --output ../test30tasks/room_quality.json --pick 30
../.venv/bin/python experiments/make_task_rooms.py --rows ../test150detail/rows.jsonl --tasks ../test30tasks/tasks_source.json \
    --output ../test30tasks --review      # --review 会逐条打印任务和它引用的物体，方便核对
```

测试见 `Fastfill workflow2/tests/test_task_rooms.py`。
