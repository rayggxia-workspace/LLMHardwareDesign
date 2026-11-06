# 紧凑 16 KiB 局部 SRAM S

任务为 [Issue #200](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/200)。两种 S 都是有自己版图和边界引脚的独立宏。每颗实例独占四个 256×128 bit 单端口 bank。复用的是 #186 使用的 bank 设计和经哈希绑定的视图。

| 宏 | 信号引脚 | 接口 |
| --- | ---: | --- |
| `local_s_base` | 273 | 2 根时钟和复位、10 位地址、1 位读写、128 位写数据、128 位读数据、4 根请求与响应握手 |
| `local_s_p` | 965 | 上述 273 根，再加 33 根供数请求、3 根供数完成、137 根 A、519 根 B |

VDD/VSS 单独计。普通端口最多两笔未完成请求，按接收次序返回。写确认由实际 bank 写入阶段之后产生，写响应的数据位固定为零。接入普通端口的选择由局控承担。P 的普通访问和 feeder 分阶段运行，旧响应或 feeder 完成未收走时保留当前阶段。局控应等普通请求全部退休再发 feeder 命令，并在收到 feeder 完成后恢复普通访问。两种新请求在空闲时若同时呈现，硬件只接收 feeder 请求。

## 实测候选

以下面积从最终 ODB 中实例矩形计算，分母是整颗宏的矩形面积。每颗的四个 bank 共占 369,848.2001 µm²。有效占地包含 SRAM bank 外框和有功能的标准单元，扣除填充、tap、endcap、天线保护单元。160 格面积统计用于发现大空区，也可用导出的实例矩形检查实际通道。

| 宏 | 外框 µm | 功能标准单元 µm² | 有效占地 | 16×10 网格占用低于 10% | OpenROAD 布线末次违例 |
| --- | ---: | ---: | ---: | ---: | ---: |
| S_base，隔离行版 | 880 × 520 | 7,441.616 | 82.45% | 0 | 0 |
| S_P，隔离行和输入延时版 | 900 × 540 | 29,210.258 | 82.11% | 0 | 0 |

S_base 隔离行版的独立 M1–M10 TT 300 MHz 审计给出 setup/hold +158.919/+33.924 ps，完整原生 GDS DRC 为 0。S_P 初版的独立时序审计给出正的 setup/hold，并发现 0.011 fF 的最大电容超限。完整 GDS 分别在初版 S_base/S_P 发现 2/8 条 WELL.4。隔离行通过重新切割标准单元行修复，外框和所有信号引脚不变。S_P 再对四个 feeder 命令输入各加一个 BUF_X1，独立审计给出 setup/hold +324.828/+8.592 ps，完整原生 GDS DRC 为 0。两颗均通过实际寄生、供电、连通、全部端点时序和四 bank 周期与脉宽检查。更紧的 880 × 528 µm S_P 已完成详细布线，最终面积利用率 85.84%，但 hold 为 −12.924 ps，且有两条最大电容违例。完整原版 GDS 规则集和独立审计结果单列。

S_P 在上下侧用三条宏观引脚带，中心距边缘约为 12、72、124 µm，左右侧相应为 12、40、68 µm。每带内部保留旧 4 µm 交错，宏观带与微观交错分别计。并行引出要求同一侧、同一层中的信号拥有独立轨道。S_P 在每一侧使用两层分担出口，包含短距离非优选方向走线。S_base 用优选方向即可。

按原 M11/M12 研究规则，分别对全 273 和 965 个信号同时建模，逐网检查连通，另外由 KLayout 写出、读回 GDS 并独立检查间距和通孔包围。两套全引脚测试均通过，最终 ODB 的全部 M10 端口矩形与测试起点严格相同。测试线止于宏外各自的端点，使用理想对齐的 2 µm 研究规则。真实邻宏接入、宏间走廊竞争和上层金属寄生时序属于顶层验收。

## 复跑和证据

在 `docs/REMOTE_RULES.md` 指定的服务器目录复制本分支源，按候选独立提交。以下在源目录执行，其中 `$task` 是包含 `source` 和 `jobs` 的新目录。

```sh
sbatch -p c64 --ntasks=1 --cpus-per-task=10 --array=0-5%6 \
  --job-name=yzl-s200 --output="$task/jobs/%A-%a.log" \
  project/experiments/compact_local_s/worker.sh "$task"
```

以上是初始扫描。选定版图使用 c96，每项 12 核。S_base 提交索引 0，传入 `--row-breaks`。S_P 提交索引 4，传入 `--row-breaks --cap-margin 35 --hold-margin .008 --hold-buffer-stages 1`。从 Git 导出源码到 Linux，保留 shell 脚本的 LF 换行。

数组 worker 会核对实分配的 CPU affinity。早期在 c64 每个候选用 10 核。c96 扫描用 12 核，并实际在 node18 同时运行 8 个候选。原生 GDS DRC 直接在 ORFS 原生流出的 GDS 上执行，不使用合并或转换版代替。独立审计由 `audit.sh` 读取原始 300 MHz SDC、最终 ODB/SPEF，生成抽象 LEF、时序模型和检查回执。抽象视图需在父层验证使用边界。

服务器证据根目录为 `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-200-compact-local-s`。S_base 选用 `run08-base0/results/0`，独立审计在 `audit08/base0`。S_P 选用 `run10-delay1/results/4`，审计在 `final-gates/p-audit`，完整的候选扫描仍保留。每个结果目录有最终实例占地、M10 端口、上层测试 GDS、KLayout 检查和原生流程回执。

- Slurm 98213、98231 保存原生候选扫描。首轮过高的 30 ps hold 修复目标触到缓冲上限，S_P 调为 5 ps 修复目标后重跑，验收仍使用原 SDC 和 Liberty。
- 98234 使用真实 OpenRAM 模型通过 RTL 回归。98238 从两个最终 ODB 重导出网表，实际标准单元模型和 OpenRAM 模型通过三种初态，覆盖 bank 交错地址、写确认、读回、背压、A/B 供数和阶段互斥。
- 98239、98240 完成四 bank 所有时钟、地址、控制和数据边界的映射至布线后严格等价。对每颗的一个地址位反相均被拒绝。
- 最终所选两颗的三初态回归和四 bank 等价分别由 98409、98410、98411 执行并通过。独立审计 98350、98412 均通过。早期回归的产物单独保留，不能代替选定版图的证据。
- 复用的 bank GDS 规范化、M3 落点和输出隔离脚本来自 #186 验收归档。保留四颗 bank 的 SHA-256 绑定和原 Nangate45 M1–M10 约束。

## 协作回执

项目 `llm-hardware-design`，负责人 YUZE-LU，分支 `task/200-compact-local-s`。登记 [management-hub PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5) 尚待合并。仓库缺少 `config/board.json`，管理员待核验条目和同步。交付见 [PR #203](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/203)，待独立审查。
