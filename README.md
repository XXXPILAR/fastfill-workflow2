# FastFill workflow 2：机器人可用的家具摆放（代码 + 实验结果）

在给定房间（任意多边形、门窗、固定障碍物）、家具清单和约束的前提下，为每件家具输出尺寸、位置和朝向，要求：
- 合法：不碰撞、不出界、不挡门，约束必须满足；
- 机器人可用：门与门之间连通，需要操作的家具能走到，柜门能打开，台面物品在手臂范围内；
- 摆放合理。

这是 WorldEdge 流程的第 ② 步（家具摆放）。

## 2026-11-02 更新：任务模式（必须家具 + 扩充家具）

上游的任务分析 agent 给出：
- 房间壳子和 room type；
- 完整的家具清单（每件都有详细描述和支撑关系）；
- **必须家具**（任务要用的）、**要打开的家具**（articulation）；
- 硬约束。

其余家具是**扩充家具**。任务模式把它们全部摆出来，优先级是**合法 → 机器人可达 → 任务**：

- **必须家具**：不删、不缩小、优先修复，最后必须合法（不碰撞、不出界、不挡门、约束满足）而且可达（机器人能走到；台面上的物品在手臂范围内；要打开的家具前面有开门空间）。
- **扩充家具**：同样检查和修复。只有在全屋重新找位置也失败时，**为了给必须家具让路**才删除；它自己修不好的问题保留并报告，不删。
- **兜底**：如果必须家具仍有问题，或者流程中途出错，就交出**只放必须家具**的房间。这一步由程序完成，不调用 GPT；先保证合法、可达，再尽量满足约束，满足不了的约束列出来交回上游。所以无论如何都会交出一个房间。

用法、输出字段和已知限制见 `Fastfill workflow2/README.md` 的 "Task mode" 一节。运行时加 `run_draft.py --task-roles`，必须家具和 articulation 从每行的 `task` 字段读取。

**目前的结果**（gpt-6.1-sol，中转站，FastFill 1.7B 全量微调给尺寸）：

| | 原流程 | 任务模式（第一版，30 个房间） | **任务模式（当前代码，10 个房间，含之前失败的 3 个）** |
|---|---|---|---|
| 必须家具合法且可达 | 90.7% | 97.1% | **100%** |
| 所有必须家具都没问题的房间 | 70% | 90% | **100%** |
| 任务可完成 | 86.0% | 95.3% | **100%** |
| 扩充家具保留 | 100% | 99.2% | 98.3% |

详见 `experiments/exp30tasks/eval/table.md` 和 `eval_rooms10/table.md`，三维对比页是 `compare_view.html` 和 `compare_view_rooms10.html`（必须家具标红）。

**正在跑的**：`exp150tasks`，在 test150tasks 的 150 个房间上跑我们的方法、GPT 单独、LayoutGPT、Holodeck、LayoutVLM。这次提交只包含它的脚本和 FastFill 尺寸，结果等跑完再补。

**和上下游对接还没定的地方**：
- 必须家具、articulation 用什么正式字段传；
- 约束类型：现在只支持 8 种；
- FastFill 要在 GPU 服务器上跑，而服务器连不上中转站，所以现在是"服务器算尺寸，本机跑流程"两段式。如果上游的 Asset Resolver 已经给出资产尺寸，可以直接传入，不需要 FastFill。

## 目录

| 路径 | 内容 |
|---|---|
| `Fastfill workflow2/` | **我们的方法**：`workflow/` 是代码，`experiments/` 是运行和评测脚本，以及所有已跑的实验结果；`tests/` 是 115 个单元测试。详见其中的 `README.md` |
| `Fastfill workflow2/experiments/exp150detail/`、`exp30tasks/`、`exp150tasks/`、`exp150tiers/` | 2026-11-01/02 的实验：FastFill 尺寸 vs GPT 自己定尺寸；任务模式 vs 原流程；layout stage 正式实验（进行中）；按难度分档（早先的方向，已不用） |
| `test150detail/`、`test30tasks/`、`test150tasks/`、`test150tiers/` | 对应的数据集，每个目录里有中文 `README.md`，写了怎么选房间、怎么生成任务，以及复现命令 |
| `Fastfill workflow2/experiments/exp150/` | **本次正式实验**：150 个房间的名单（`rooms.json`）、一键启动脚本 `run_all.sh`、进度查看脚本 `status.sh` |
| `Fastfill workflow2/experiments/session_logs/README.md` | 分析脚本、对比实验、图的索引（中文） |
| `fastfill-main/` | workflow2 依赖的 `fastfill` 包：数据格式、评测、FastFill 模型代码 |
| `test300/` | 测试集的 300 个房间（`rows.jsonl`，抽样记录见 `MANIFEST.json`），以及之前的 GPT-5.6 一次生成结果 |
| `server_runs/test300-v4/` | FastFill base/D/E 在 test300 上的输出（spread 解码），workflow 从这里读家具尺寸，也作为"FastFill 纯跑"基线 |
| `related work code/baselines/` | related work 基线（LayoutGPT、Holodeck、LayoutVLM、I-Design、DirectLayout）的适配脚本 `adapters/`、仓库版本 `SOURCES.txt`（新增了 LaviGen 和 RoboLayout，只用 `fetch_baselines.sh` 拉取，不放进仓库）、之前的完整运行结果 `runs/full_agentsize/` 和 `runs/exp150_g61/`（LayoutVLM 的资产和渲染图没有放进来） |

## 在服务器上准备

```bash
git clone <this repo> fastfill-v4 && cd fastfill-v4
python3.11 -m venv .venv && .venv/bin/pip install -r requirements-experiments.txt   # 脚本默认用 fastfill-v4/.venv
```

1. **API key（不要放进仓库）**：新建 `~/.fastfill_api.env`，权限设为 600，写入两行：
   ```
   OPENAI_API_KEY=<中转站 key>
   OPENAI_MODEL=gpt-6.1-sol
   ```
   如果要放在别的位置，用环境变量 `FASTFILL_API_ENV=<路径>` 指定，基线也会读这个变量。地址不需要写进这个文件，启动脚本默认用 `https://api.kbsfdxc.net/codex/v1`，可以用 `BASE_URL=...` 换成另外两个接入点。
2. **基线仓库**：运行 `bash "related work code/baselines/fetch_baselines.sh"`，它会按 `SOURCES.txt` 里固定的 commit 拉取 LayoutVLM、Holodeck、LayoutGPT、IDesign 和 ReSpace。这几个仓库没有放进我们的仓库，因为其中有的没有许可证文件。
3. **基线的 Python 环境**：放在 `related work code/baselines/envs/holodeck/` 和 `envs/layoutvlm/`（LayoutVLM 的依赖见 `envs/layoutvlm-req.txt`，Holodeck 的依赖见它自己仓库的 requirements）。LayoutGPT 直接用 `.venv`。Holodeck 和 LayoutVLM 的适配器用"有尺寸的盒子"代替 3D 资产，**不需要准备 Objaverse 资产库**。
4. **LayoutGPT 的示例库**：需要 `data_v4_v2_fixed/train.jsonl`（1.6 GB，太大放不进 git），从 HuggingFace 数据集 `XXXpilar/fastfill-v4-v2-fixed` 下载，放到项目根目录 `data_v4_v2_fixed/` 下。
5. **自检**：`cd "Fastfill workflow2" && ../.venv/bin/python -m pytest -q tests`，应该是 115 passed。

## 运行之前的正式实验（exp150，2026-10-28）

注意：exp150 用的是旧的 test300 房间，物体描述基本只有类别名。现在流程要求每个物体都有详细描述，所以重跑 exp150 需要设置 `WORKFLOW_ALLOW_BARE_DESCRIPTIONS=1`（`run_all.sh` 里已经设好了）。

```bash
cd "Fastfill workflow2"
bash experiments/exp150/run_all.sh          # 所有组在后台启动；可以重复运行，已经完成的房间会跳过
bash experiments/exp150/status.sh           # 查看进度、费用估算和最近一分钟的请求数
RUN_GROUPS="g1_main gpt_pure" bash experiments/exp150/run_all.sh    # 只跑其中几组
```

所有组都用 **gpt-6.1-sol、推理强度 medium**，通过中转站的 `/chat/completions` 接口调用。**所有组的请求合计不超过每分钟 30 次**，靠一个共用的计数文件 `experiments/exp150/.rpm_state.json` 加文件锁实现。

| 组 | 内容 | 输出 |
|---|---|---|
| `g1_main` | 主方法：规划 → 两份初稿择优 → 程序修复（全屋挪动、3 轮、180 秒上限、余量 0.1 m、站位区硬条件，0.5 m 机器人）→ 审查一次 | `experiments/exp150/g1_main/` |
| `g2_gpt_robot_prompt` | 规划 + 一份初稿，提示词里告诉 GPT 有机器人，但没有程序修复和审查 | `experiments/exp150/g2_gpt_robot_prompt/` |
| `g3_no_robot` | 消融：主方法去掉所有机器人相关部分 | `experiments/exp150/g3_no_robot/` |
| `gpt_pure` | 纯 GPT：一次调用，GPT 自己给出尺寸和位姿，不修补（`fastfill.v2.ops.llm_probe` 的协议） | `experiments/exp150/gpt_pure/` |
| `layoutgpt`、`holodeck`、`layoutvlm` | related work，各自的适配器 | `related work code/baselines/runs/exp150_g61/<方法>/` |

不需要调用 API 的部分，在实验跑完后离线计算：
- **FastFill 纯跑**：直接用 `server_runs/test300-v4/` 里的输出；
- **其余消融**（去掉审查、单份初稿、不全屋挪动、不加余量和硬条件）：从 `g1_main` 保存的初稿和中间阶段离线重算。

每个房间的 GPT 输入和输出都会记录在 `<组>/llm_calls/room_XXX.jsonl` 里，不含 key。每次运行的参数记在 `<组>/config.json`。

**预计**：总共约 3000 次调用，在每分钟 30 次的限制下至少需要 2 小时，实际估计 5–8 小时。费用按 gpt-5.6-sol 的官方价格估算（gpt-6.1-sol 的价格还没有核实）约 $150–200；每组都设了预算上限，超出会自动停止。

## 注意事项（2026-10-28 实测）

- **中转站的 `/responses` 接口**会把请求里的 `instructions` 字段换成它自己约 3300 token 的 Codex 系统提示，模型因此看不到我们的指令。`/chat/completions` 接口不会这样。所以 `workflow/llm.py` 和 `adapters/relay.py` 走中转站时都用 `/chat/completions`，指令作为 system 消息发送。当时出问题的那次试跑保存在 `Fastfill workflow2/experiments/relay_smoke/main_INSTRUCTIONS_DROPPED_by_relay/`。
- **新旧结果不能混比**：之前在 `simple20*`、`test300/gpt56`、`runs/full_agentsize` 里的结果用的是 gpt-5.6-sol 或官方 API，和这次的 exp150 不可直接比较。
- **机器人检查器的偏向**：自家检查器是修复时优化的目标，用它打分会偏向我们。独立评测（SceneEval 原版代码、EmbodiedGen 的 RoamTrajectoryGenerator、矩形底盘加 3D 手臂）见 `Fastfill workflow2/experiments/independent_eval/` 和 `session_logs/scripts/indep_eval.py`。
