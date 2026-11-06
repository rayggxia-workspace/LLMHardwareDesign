# 九实例 M11/M12 试布

关联 Issue #191 和 #184。候选输入来自 PR #190 的 P16/J16 和 PR #189 的 U16/C16/F16。只读使用验收 LEF。基线实验使用被动布线，电气迭代加入原生缓冲。父层传输控制、PG、时钟和接收端 READY 使用试验边界。两根 ready 网接到预留侧的代理端点。其余数据、valid 和 stored/accept 网用于测量真实 Block pin 的几何通路。实际控制接入后须重新验证握手和负载。

## 运行

1. 将本目录的脚本复制到自己的远程试验目录。链接五份验收 LEF 为 P.lef、U.lef、C.lef、F.lef、J.lef。
2. 从固定容器取 NangateOpenCellLibrary.tech.lef 为 native.tech.lef，再运行 `python3 overlay.py native.tech.lef technology-2um-v1.json overlay`。两份输入脚本来自同仓库 project/experiments/block_v1。
3. c64 用 `sbatch --partition=c64 --ntasks=1 --cpus-per-task=10 --array=0-7%8 --job-name=yzl-nine-route --output=slurm-%A_%a.log run.sh`。Slurm 可将六组打包到同一节点。c96 按资源状况改为 12 核，单个 OpenROAD 进程读取分配到的核数。索引 8–13 为裁切诊断。
4. `python3 audit.py case-<job-id>-*` 输出逐候选 JSON。DEF 的网覆盖和 M10 via 形状初筛需与独立几何、连通性和 RC/STA 证据分开使用。

## 候选

- 0–3 在九实例中试 C0↔U0。每方向 128 位数据和 valid、stored、ready，共 262 根网。0/1 横向相邻，2/3 纵向相邻。偶数用 128 µm 间隔，奇数用 256 µm。
- 4–7 与 0–3 相同布局，同时加入 P0 的 M→G 34 根真实 pin 网，共 296 根网。
- 8/9 裁切到 P0，只保留 M→G 34 根网。10–13 裁切到 C0/U0。

手写引导仅用于把全局布线容量报错和详细布线几何诊断分离。Nangate45 原生层固定，2 µm 上层规则沿用研究配置，未做工艺校准。

## 独立构造对照

`python3 escape.py case-<job>-<index> 2` 先分配落点附近的短逃逸，再在两层连接主干。它输出逐段网线 JSON。`python3 validate_escape.py case-<job>-<index>/escape-2.json` 独立检查网表覆盖、连通、下包围及简化上层几何。通过后用 `python3 export_escape.py case-<job>-<index>/escape-2.json` 生成研究 DEF。

`python3 reservations.py case-<job>-<index>/inputs.json` 生成九实例预留区并检查不重叠。`python3 screen_load.py <解包目录> case-<job>-<index>/escape-2.json` 从 C16、U16 的原网表和原 Liberty 执行均匀线电容初筛。需按本次研究规则解释数值。

## 紧凑摆位与驱动迭代

- 用 run_compact.sh 跑 24 个摆位和种子组合。每个 Python 搜索占一核。
- 用 screen_load.py 和 eco_load.py 由选中的几何生成逐端口负载。P 用 eco_drive.sh 迭代，C/U 用 eco_neighbor.sh。每个 EDA 作业在 c64 使用 10 核，可并行提交。
- 用 p_valid_relay.sh 添加 P 原生中继，再用 split_valid_route.py 和 validate_escape.py 生成并复核两段上层线路。
- 用 eco_drc.sh、eco_function.sh、connect_eco.sh 和 eco_overlay.sh 核对原生与上层产物。源 P4/M/G、SRAM、验收脚本和网表来自对应远程交付目录。需要选择明确的候选 ID。工程回执中的历史 ID 对应原始日志。
- run_top_sta.sh 分别跑 low、high，然后用 coupon_timing_receipt.py 核对 297 根线上层寄生、真实接收寄存器组的 setup/hold，以及负载和转换时间检查。代理边界的时序另存。
