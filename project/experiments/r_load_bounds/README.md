# R 原始 LOAD 地址边界回归

关联 [Issue #242](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/242)。修复源 commit：`f034be2b7c87137b92f7bfce274a5485647e512d`；原始反例源：main `c4d7b960599b9d292f27eb4429d5f226a7156c95`。结果和 SHA 见[实验记录](../../../docs/experiments/issue-242-r-load-bounds.md)。

## 装载合同

`load_index` 是 128 位装载拍地址。先检查完整 10 位索引，再交给内部状态行地址截位。

| load_target | 对象 | R256 合法索引 | R1024 合法索引 |
| --- | --- | --- | --- |
| 0、1 | 两个 S32 状态 bank | 0–63 | 0–255 |
| 2、3 | key、query，8×S16/拍 | 0–3 | 0–15 |
| 4 | x、update、skip，各两拍 | 0–5 | 0–5 |
| 5 | decay、beta，同一拍 | 0 | 0 |
| 6 | history，4×S32/拍 | 0–5 | 0–5 |
| 7 | taps，8×S16/拍 | 0–3 | 0–3 |

原始端口对非法索引保持 `load_ready=0`，不接受请求、不写入任何状态或操作数，也不额外产生 command 响应。直接调用者必须预先检查并返回错误，或撤回非法请求；一直保持非法 `load_valid` 不会自行完成。现有 `ucf_r256_service` 在协议入口接受并终结非法请求、返回地址错误，未修改其源码。合法索引仍遵循原有空闲、命令优先及写回排空约束。

## 覆盖与判据

- `tb_load_bounds.sv` 对两容量分别初始化全部合法状态与操作数；遍历八个目标的全部 10 位非法索引，每个保持三周期；逐目标核验完整状态、全部操作数及最后一个合法地址的恢复写入。状态通过真实 host 读口校验，操作数因无读口而观察内部寄存器，按 S16/S32 数据布局独立解码。
- 非法装载后执行单位 UQ31 decay 和 query-dot，对照独立计算的状态与 S32×S16 累加结果；覆盖读/命令响应背压、复位时抑制握手及复位后合法写入。
- `tb_service_bounds.sv` 使用实际 C 适配器和 R256；每目标检查首个非法索引与 1023、错误响应四周期背压、原状态不变及合法请求恢复。
- 每例运行三种配置：初始全 1/seed 143、随机/seed 143、随机/seed 144。负控制必须以旧主干源码在 `t=0 i=64` 报错退出，脚本只有识别到该预期缺陷才判定负控制通过。

## 服务器复跑

先遵守 [REMOTE_RULES](../../../docs/REMOTE_RULES.md)。以下在获授权的个人服务器目录中的完整 Git checkout 执行；每轮使用全新输出目录。脚本路径固定到本项目既有工具安装，不安装新工具。Slurm 数组最多同时运行两例，每例 c64/4 核、无限时，计算由 `srun` 在分配节点内运行。

```bash
run=/public/home/yuzelu/Melodydt/issue242-r-load-bounds/run02
mkdir "$run"
mkdir "$run/source" "$run/old-main"
git archive --format=tar f034be2b7c87137b92f7bfce274a5485647e512d \
  project/experiments/r_load_bounds \
  project/rtl/r_local_state/r_stream_local.sv \
  project/rtl/r_local_state/r_state_store.sv \
  project/rtl/block_cfj_v1/ucf_r256_service.sv > "$run/source.tar"
tar -xf "$run/source.tar" -C "$run/source"
git show c4d7b960599b9d292f27eb4429d5f226a7156c95:project/rtl/r_local_state/r_stream_local.sv \
  > "$run/old-main/r_stream_local.sv"
cp "$run/source/project/experiments/r_load_bounds/job.sh" "$run/job.sh"
cd "$run"
sha256sum source.tar > source.tar.sha256
sbatch --parsable job.sh
```

容器为 `/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif`，SHA-256 `49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a`；Verilator 5.042，容器 Python 3.10.12。`run.py` 保存编译命令、输入/运行器 SHA、工具版本、CPU affinity、退出码及输出日志 SHA。

需要单例诊断时，在已分配的 Slurm 资源和同一容器中执行：

```bash
python3 -B project/experiments/r_load_bounds/run.py --case raw256 --out /全新输出目录
# --case 可选 raw1024 / service256 / negative；negative 还需 --old-rtl /旧源/r_stream_local.sv
```

判据是全部九次正向执行退出 0 且有 PASS，三次旧源负控制均检出指定缺陷，Slurm 包装作业退出 0。负控制中的仿真退出 1 是预期结果。保留编译 WIDTH 等既有警告，`-Wno-fatal` 与现有运行方式一致；本回归不构成严格 lint、原 192 项最终网表回归或物理重新验收。
