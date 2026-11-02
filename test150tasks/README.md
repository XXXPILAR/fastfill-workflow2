# test150tasks：150 个带任务的房间（2026-11-02）

Layout stage 实验用的数据集。每个房间都有：
- 2–3 个家用机器人任务；
- 必须家具（任务要用的物体）和扩充家具（其余物体）；
- 需要打开的家具（articulation）。

和 test30tasks 的格式完全相同：每行是原数据集的行，**`condition` 和 `target` 不变**，另加一个 `task` 字段。所有方法拿到的是同一个房间、同一份物体清单，只比摆放。

## 房间怎么选（`room_quality.json`、`selection.json`）

从 `data_v4_detail/test.jsonl`（1667 个房间，物体都带详细描述）里，先选出同时满足下面条件的房间，共 423 个：
- 真实布局合法：没有碰撞、没有出界、没有挡门；
- 每个物体的类别和描述一致；
- 每个物体都标明放在哪里；
- 至少 6 件物体。

**不要求有门**：没有门时，机器人检查把最大的空地当作入口。

然后选 150 个：
| 来源 | 房间 | 选法 |
|---|---|---|
| IL3D_3dfront | 32 | 合格的全部选上（小房间） |
| IL3D_synthetic | 41 | 合格的全部选上（小房间，都没有门） |
| SAGE-10k | 77 | test30tasks 的 28 个全部选上，另外从合格房间里随机抽 49 个（种子 0） |

| | 数值 |
|---|---|
| 物体总数 | 6,599 |
| 每个房间物体数 | 最少 6，中位数 18，最多 189 |
| 没有门的房间 | 51 |

## 任务怎么来（`tasks_source.json`、`task_agent/`）

由 `experiments/task_agent.py` 模拟上游的任务分析 agent 生成：每个房间调用一次 gpt-6.1-sol（reasoning medium，经中转）。

**模型能看到的**：房间类型和大小；每个物体的 id、类别、放在哪里、描述（前 40 个词）。真实位置和尺寸都看不到。

**规则**（完整提示词写在 `tasks_source.json` 的 `instructions` 里）：
- 每个房间 2–3 个任务；
- 只拿取、搬运小物件，家具只作为取放的位置或要打开的对象；
- 不能把东西从地上挪到地上；
- 不使用墙上的装饰；
- 房间里没有可拿的小物件时，任务可以是"把机器人带来的东西放到某件家具上"（带来的东西不列入物体清单）。

**自动校验**：
- 每个 id 必须是这个房间里的物体；
- 要打开的家具必须是任务用到的；
- 不能有两个任务用的物体完全相同；
- 每个房间至少 2 个任务。

不合格就把问题反馈给模型重写，最多 2 次。

**结果**：
- 150 个房间全部生成成功，共 348 个任务（102 个房间 2 个，48 个房间 3 个）；
- 花费 $2.17，用时约 7 分钟；
- 每个房间的请求和回答都保存在 `task_agent/room_XXX.json` 里。

**必须家具** = 任务用到的物体，加上它们所在的家具（递归），由 `make_task_rooms.py` 计算。这次所有任务都已经列出了所在的家具，所以没有额外补充。

| | 数值 |
|---|---|
| 任务 | 348 |
| 必须家具 | 652（每个房间 2–10 件，中位数 4） |
| 扩充家具 | 5,947（每个房间中位数 14） |
| 要打开的家具 | 100 |
| 必须家具之间的约束 / 涉及扩充家具的约束 | 53 / 333 |

**检查**：
- 没有任务用到墙上的装饰；
- 抽查的房间里没有搬动家具的任务；
- 7 件被标为"要打开"的家具，类别看起来不像能开合（边桌、梳妆台、吧台、床头柜、尿布台、带抽屉的工具车，以及一件类别写成 appliance 的冰箱），但看描述都是有抽屉或门的，合理；
- 所有任务和它引用的物体见 `review.txt`。

test30tasks 的 30 个房间也在这 150 个里，但这里的任务是任务 agent 生成的，**不是** test30tasks 里手写的那些。

`rows_sha256`：`e4069b804b872a92cec7d0311e6c6b5f1cc2f30a9770c3503108a3a4864e59bd`

## 文件

| 文件 | 内容 |
|---|---|
| `rows.jsonl` | 150 行，带 `task` 字段（格式见 test30tasks/README.md） |
| `rooms.json` | `[0, …, 149]` |
| `base_rows.jsonl` | 选中的原始行，不带 `task` |
| `selection.json` | 怎么选的，以及每个房间在 test.jsonl 里的行号 |
| `room_quality.json` | 1667 个房间的质量检查结果 |
| `tasks_source.json` | 任务 agent 的输出（以及完整提示词） |
| `task_agent/room_XXX.json` | 每个房间的请求、回答和花费 |
| `review.txt` | 每个任务和它引用的物体（类别、放在哪里、描述） |
| `MANIFEST.json` | sha256 和每个房间的统计 |

## 复现

在 `Fastfill workflow2` 下运行：

```bash
../.venv/bin/python experiments/room_quality.py --rows ../data_v4_detail/test.jsonl --output ../test150tasks/room_quality.json --min-doors 0
../.venv/bin/python experiments/select_task_rooms.py --rows ../data_v4_detail/test.jsonl --quality ../test150tasks/room_quality.json \
    --keep ../test30tasks/rows.jsonl --keep-manifest ../test150detail/MANIFEST.json --rooms 150 --output ../test150tasks
WORKFLOW_LLM_ATTEMPTS=0 ../.venv/bin/python experiments/task_agent.py --rows ../test150tasks/base_rows.jsonl \
    --output ../test150tasks/tasks_source.json --api relay --model gpt-6.1-sol --rpm 30 --workers 6
../.venv/bin/python experiments/make_task_rooms.py --rows ../test150tasks/base_rows.jsonl --tasks ../test150tasks/tasks_source.json \
    --output ../test150tasks --review > ../test150tasks/review.txt
```

前两步可以完全复现。第三步调用 GPT，每次生成的任务会不一样，所以以 `tasks_source.json` 为准。测试见 `tests/test_task_agent.py`、`tests/test_task_rooms.py`。
