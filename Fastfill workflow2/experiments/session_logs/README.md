# 运行记录索引（给审阅的人看）

这个文件夹保存的是做分析、对比实验时用到的脚本、输出和图。它们原来放在会话的临时目录里，2026-10-28 复制到这里。正式运行的输入和输出不在这里，在上一级的 `experiments/` 下面，见第一节。

所有文件都检查过，没有 API key：只出现过占位符 `<your_openai_api_key_here>` 和测试用的 `"x"`。`.env` 没有复制。

## 1. 正式运行（在 `experiments/` 下）

| 文件夹 | 是什么 | 设置 |
|---|---|---|
| `simple20/` | workflow2，不带机器人检查（17 个房间） | `config.json` |
| `simple20_robot/` 和 `simple20_robot_b/` | 加机器人：0.5 m，初稿请求带机器人要求，搜索用站位区，分层评审。前一个跑了 4 个房间，后一个跑了 16 个 | `config.json` |
| `simple20_robot2/` | 再加两份初稿择优 + 尺寸回退。**这一轮用的是旧的选初稿规则**（合法性违规少优先），房间 22、66、108 选错了初稿；规则后来已改 | `config.json` |
| `*.log` | 每次运行的终端输出 | |

每个运行文件夹里的文件：

- `config.json`：运行参数，包括模型、机器人宽度、初稿份数等。
- `rows.jsonl`：**输入**。每行一个房间：房间多边形、门窗、固定物体、家具清单、约束；`target` 是数据集里的真实布局，只用于评测。
- `room_XXX.json`：**每个房间的完整结果**。
  - `layout`：最终布局，每件家具的尺寸、位置、朝向和支撑；
  - `diagnostics.stages`：初稿、程序修复后、最终三个阶段的布局，可以逐步对比；
  - `diagnostics.assessments`：每个阶段的检查结果；
  - `diagnostics.draft`：初稿调用记录，两份初稿时还有每份的评分；
  - `diagnostics.check`：修复过程，包括每次尝试的目标、是否接受和原因；
  - `diagnostics.semantic`：LLM 审查；
  - `diagnostics.robot`：机器人检查报告；
  - `timing_s`：各步耗时；`cost_usd`：费用。
- `predictions.jsonl`：所有房间的最终布局，和 `rows.jsonl` 一一对应。
- `ledger.json`：花费记账。`summary.json` 和 `eval/`：汇总和评测。
- `roomgenbench/`（只在 simple20_robot2 下）：导出给 RoomGenBench 的 bbox 场景、资产清单，以及本地 3D 查看页面。
- `compare_topdown/`（只在 simple20_robot2 下）：俯视对比图，包括真实标注、GPT、Holodeck、LayoutVLM 和我们的结果，并叠加了机器人可达区域。

**这些运行没有保存 GPT 的原始提示词和回复**，只记了 token 数、费用和耗时。从 2026-10-28 起，`run_draft.py` 会把每次调用写进 `<输出目录>/llm_calls/room_XXX.jsonl`，见第五节。

评测表：

- `experiments/robot_check/table.md`：我们自己的检查器在 0.4、0.5、0.6 m 下评所有方法。**修复时优化的就是这个检查器**，结果偏向我们。
- `experiments/independent_eval/table.md`：**没有优化过的独立指标**，包括 SceneEval 原版代码的可通行、碰撞、出界，EmbodiedGen 原版的 RoamTrajectoryGenerator，以及一个新写的矩形底盘加 3D 手臂的机器人模型。

## 2. `scripts/`：分析脚本

都在 `Fastfill workflow2/` 目录下用 `../.venv/bin/python scripts/<名字>` 运行。

| 脚本 | 做什么 |
|---|---|
| `indep_eval.py` | 独立评测，生成 `independent_eval/table.md` 的原始数据。依赖 `third_party/sceneeval_subset` |
| `robot_crosscheck.py` | 用另一套网格实现交叉核对机器人检查，一致率 98–99%；并测 1 cm 扰动后结论翻转的比例 |
| `eval_robot_plan.py` | 离线对比"安全余量"和"站位区硬条件"四种配置，只重跑修复，不调用 API |
| `repair_v2.py`、`repair_zones.py`、`robot_repair_try.py` | 早先的离线修复实验：站位区、分层评审、尺寸回退 |
| `why_robot.py` | 分析机器人指标为什么差 |
| `prof66.py` | 房间 66 修复耗时的性能分析 |
| `render_compare.py`、`plot_room.py` | 画俯视图 |
| 其余（`a_plus_repair.py`、`replay*.py`、`refine_*.py`、`compare_staged.py`、`metrics20.py`、`directlayout_*` 等） | 更早几天的实验：workflow 第一版的分组和分阶段摆放、DirectLayout 基线 |

## 3. `outputs/`：分析的输出

| 文件 | 内容 |
|---|---|
| `indep_eval.json`、`indep_table.json`、`indep_eval.err` | 独立评测：每个布局的结果、汇总表、运行日志 |
| `eval_robot_plan.out`、`.err`、`_layouts.json` | 余量和硬条件对比：结果表、每个房间耗时、修复后的布局 |
| `crosscheck_disagree_0.5.json`、`_0.6.json` | 两套实现结论不一致的物体清单 |
| `roomgenbench_assembly_test/` | 第一次验证导出格式时，用 RoomGenBench 装配器装出的场景 |
| `wedge_mock_run/` | 用 WEDGE-main 自带的模拟回复跑的一轮演示输出 |
| `orders50.log`、`mine.log` | 更早的运行日志 |

## 4. `figures/`、`third_party/`、`earlier_runs/`

- `figures/`：对比截图。
  - `crowd_*.png`：家具是否扎堆的对比；
  - `room079*.png`、`box079.png`：3D 查看器的截图；
  - `renders/`：几个房间的俯视渲染；
  - `r15.png`、`front22.png`、`robot_gt.png`：单个房间的分析图。
- `third_party/sceneeval_subset/`：SceneEval（MIT 协议）的可通行、碰撞、出界三个指标原文件。`metrics/__init__.py`、`metrics/registry.py`、`scenes_stub/` 是我们写的最小替身，只为让这三个文件能单独导入，指标代码本身没有改。
- `earlier_runs/`：更早几天在临时目录里跑的实验结果。
  - `orders3*/`、`orders_test/`：workflow 第一版不同摆放顺序的对比；
  - `quality50/`、`cmp50/`：test50 上的质量和对比实验；
  - `dl_test/`：DirectLayout 测试；
  - `lgpt/`：LayoutGPT；
  - `rw/`：related work 资料整理。

## 5. 以后的运行会自动保存 GPT 输入输出

`workflow/llm.py`：只要设置了环境变量 `WORKFLOW_LLM_LOG_DIR`，每次调用（成功或失败）都会追加一行 JSON 到 `<目录>/<WORKFLOW_LLM_TAG>.jsonl`，内容是：

- 时间、房间标签、模型；
- `instructions`（系统指令）、`prompt`（输入）、`response`（原始回复）；
- token 用量、费用、耗时、重试次数；
- 失败时的错误信息。

**API key 和请求头不会写入。** `experiments/run_draft.py` 默认打开这个功能，输出到 `<--out>/llm_calls/room_XXX.jsonl`；加 `--no-llm-log` 可以关闭。测试见 `tests/test_llm_log.py`。
