# 在服务器上把 workflow 的 layout 渲染成 3D 房间（RoomGenBench + TRELLIS-text）

这个包里有：

- `RoomGenBench/bench/inputs/`：我们 20 个房间的 layout（`scenes/room_*.json`）和资产清单（`assets.jsonl`），格式与 RoomGenBench 相同。
- `RoomGenBench/bench/assemble.py`：RoomGenBench 原版装配器，没有改动。
- `RoomGenBench/methods/trellis_text/gen_trellis_text.py`：RoomGenBench 原版 TRELLIS-text 生成脚本，没有改动。
- `RoomGenBench/methods/embodiedgen_v2/rgbjob.py`：只改了一处，根目录改为读取环境变量 `RGB_ROOT`。原版写死成了 `/group/streetsplat/...`。

## 步骤

```bash
# 0. 上传并解压
scp server_bundle.tar.gz <server>:~/
ssh <server>; tar xzf server_bundle.tar.gz; cd server_bundle

# 1. 一次性安装（登录节点，需要联网；约 20–40 分钟）
bash setup_env.sh
#    conda 环境 rgb_trellis：TRELLIS 用 RoomGenBench 当时的 commit 442aa1e，torch 2.4 + CUDA 11.8
#    模型下载到 ./cache/huggingface，计算节点不需要联网

# 2. 生成并装配一个房间（需要 1 张 GPU，显存 ≥ 16 GB）
bash run_room.sh                     # 默认房间 79：7 个资产，约 10–20 分钟
#    Slurm 集群：先改 run_room.sbatch 里的分区和账号，再执行
sbatch run_room.sbatch room_079

# 其他房间
bash run_room.sh room_015,room_197   # 多个房间用逗号分开
bash run_room.sh all                 # 全部 20 个房间：159 个资产，大约 3–5 小时
```

脚本可以断点续跑：已经生成好的资产会自动跳过。

## 结果

- `out/room_079.html`：内嵌了 GLB 的 3D 查看器。下载到电脑上，用浏览器打开即可（需要联网加载 three.js）。
- `out/room_079.glb`：完整的房间模型，可以用 Blender 或任何 glTF 查看器打开。
- `out/room_079.json`：每个物体的装配记录，包括状态、自动转正的角度和缩放比例。
- `RoomGenBench/results/trellis_text/assets/`：每个资产的 GLB 和说明文件（sidecar）。

下载结果：

```bash
scp -r <server>:~/server_bundle/out .
```

## 注意

- **架构**：TRELLIS 依赖的 CUDA 扩展（spconv、kaolin、diffoctreerast、nvdiffrast）只有 x86 的现成安装包。在 ARM 服务器（比如 Isambard-AI 的 GH200）上要从源码编译，`setup_env.sh` 很可能在这一步失败。优先用 x86 的 GPU 机器。
- **描述很短**：有些房间的物体描述就是类别名（例如 "bed"），生成出来的资产会比较普通。
- **朝向**：装配严格按照 layout 里的朝向。这批 layout 的朝向参考过 FastFill 输出的朝向，而 FastFill 的朝向只表示轴向，不区分前后，所以个别家具可能背对房间。
