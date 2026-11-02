# test150tiers：同一个房间的 easy / medium / hard 三个版本（2026-11-02）

仿照 EmbodiedGen 的场景复杂度等级。EmbodiedGen 的求解器按三层摆放：先放大件家具，再放家具上的中等物品，最后放桌面小杂物。
等级决定启用几层（`room_gen/gen_room.py` 里的 Simple / Medium / Detail）。这里对 **test150detail 的同一个房间**
做三个版本，只改变物体密度，房间、门窗、固定物和每个物体的描述都不变。

## 分层规则

每个要摆放的物体，按输入里的支撑关系和真实尺寸分成三层。真实尺寸只用来给测试集分层，任何方法都看不到：

| 层 | 规则 | 例子 |
|---|---|---|
| 1 家具 | 落地或挂墙（`support_parent` 是 floor、wall 或没有） | 桌子、柜子、床、壁灯 |
| 2 中等物品 | 放在别的物体上，真实尺寸最长边 ≥ 0.3 m | 台灯、花瓶、绿植、靠枕 |
| 3 小杂物 | 放在别的物体上，最长边 < 0.3 m | 书、杯子、笔、蜡烛 |

| 版本 | 保留的层 |
|---|---|
| easy | 1 |
| medium | 1–2 |
| hard | 1–3，也就是原房间 |

- 一个物体放在被删掉的物体上时，它也一起删掉。
- 涉及被删物体的约束一起删掉。
- 目标布局、`validity` 和 `provenance` 里按物体排列的列表（`target_source_ids`、`field_evidence`）同步删减。
- 其他字段原样保留。

## 用了哪些房间

只用三层都有的房间：test150detail 里的 40 个 SAGE-10k 房间。
- IL3D 的 106 个房间只有家具层，所以不用。
- 另有 4 个 SAGE 房间不用：1 个只有家具；3 个（115、132、136）没有中等物品，它们的 medium 版本会和 easy 完全一样。

| 版本 | 房间 | 物体总数 | 每个房间物体数（最少 / 中位数 / 最多） | 约束 |
|---|---|---|---|---|
| easy | 40 | 1,597 | 12 / 36 / 112 | 63 |
| medium | 40 | 1,870 | 16 / 44 / 119 | 72 |
| hard | 40 | 3,227 | 24 / 78 / 144 | 102 |

## 文件

| 文件 | 内容 |
|---|---|
| `rows.jsonl` | 80 行：每个房间的 easy 和 medium 版本，房间按 test150detail 的顺序排列，每个房间先 easy 后 medium。格式和 test150detail 相同，`provenance.tier` 记录等级、原房间编号和保留的物体数 |
| `MANIFEST.json` | 每个房间三个版本的记录：原房间编号（`base_index`，test150detail 的行号）、物体数、约束数、各层物体数，以及该版本在 `rows.jsonl` 里的行号。hard 版本的行号是 `null`：hard 就是 test150detail 里的原行，**不重复写入**，它的结果直接用主实验在 test150detail 上的结果 |

`rows_sha256`：`93b51bda60afa93519bf50ce0d9754ef94d19d373fa20f038155d28246b1c4a1`

## 复现

在 `Fastfill workflow2` 下运行：

```bash
../.venv/bin/python experiments/make_tier_rooms.py --rows ../test150detail/rows.jsonl --output ../test150tiers
```

脚本写文件之前会检查每个版本：
- 都是合法的请求（每个物体都带描述）；
- 目标布局合法；
- 房间和保留下来的物体与原房间逐字相同。

测试见 `Fastfill workflow2/tests/test_tier_rooms.py`。
