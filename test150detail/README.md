# test150detail：带详细描述的 150 个房间测试集（2026-11-01）

从 `data_v4_detail/test.jsonl`（1,667 个房间，SAGE-10k、IL3D_3dfront、IL3D_synthetic，物体都带详细描述）中抽出的
150 个房间。用于在输入带 description 的条件下，对比 FastFill 各模型、GPT 和 related work。

## 抽样方式

- 生成命令（在 `fastfill-main` 下运行，可完全复现，`rows_sha256` 一致）：

  ```bash
  python3 fastfill/v2/ops/make_test300.py --test ../data_v4_detail/test.jsonl --output ../test150detail \
      --rows 150 --seed 0 --max-objects 512
  ```

- **没有排除任何房间**：上限设为 512 件（测试集最大 342 件），`over_capacity_excluded` 为 0。
- 按数据来源分层，份额与测试集比例一致（最大余数法）：IL3D_3dfront 78、SAGE-10k 44、IL3D_synthetic 28。
- 每个来源内用同一个随机数生成器（seed 0）不放回抽取；`rows.jsonl` 按原测试集顺序排列，行号 0–149 即房间编号。
- `rows_sha256`：`e86df753e279386e172265c31d50439bbea3a41171872f6052c4d5195cd4e593`

## 内容概况

| 项目 | 数值 |
|---|---|
| 房间 / 物体 | 150 / 4,044（旧 exp150 为 150 / 2,399） |
| 每个房间物体数 | 最少 1，中位数 7，最多 144；超过 100 件的 14 个 |
| 描述长度 | 中位数 21 个词；没有一个物体的描述只是类别名；不足 12 个词的 36 个 |
| 有约束的房间 | 146 个，共 341 条约束 |
| 有门窗的房间 | 103 个 |

## 文件

| 文件 | 内容 |
|---|---|
| `rows.jsonl` | 150 个房间，格式与 test.jsonl 相同（condition / target / validity / provenance） |
| `MANIFEST.json` | 抽样记录：种子、各来源数量、原测试集 sha256、每个房间在 test.jsonl 中的行号和 scene_id |

注意：这些房间都在 v4detail 模型的测试集里，没有参与这些模型的训练和验证。
