# Issue #7 独立并发实验记录

- 更新时间：2026-10-21（中国标准时间，UTC+08:00）。
- 用户授权：并发运行、监视并同步记录，避免与主线冲突；允许同节点多实验；不设置人工时限。
- Issue：[候选 Block 与分层实现 #7](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7)，负责人 YUZE-LU，状态沿用 `in_progress`；审查人、优先级待指定。
- 独立分支：`task/7-parallel-blocks`；本地工作树 `D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-7-parallel-blocks`。
- 代码：[parallel_blocks](../../project/experiments/parallel_blocks/README.md)。主线 `task/7-block-routing`／[PR #8](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/8) 继续负责 VECTOR 和 PG 修复。本会话不修改其文件、输入、时限或作业。
- 并发交付：[草稿 PR #10](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/10)，只包含本批新目录／专有记录，与主线 PR #8 分开审查；个人补充见 [进度](../../progress/YUZE-LU/parallel-blocks-7.md)，恢复见[交接](../handoffs/2026-10-21-issue-7-parallel-blocks.md)。

## 实验与资源

| Case | 对象与目的 |
| --- | --- |
| `llaccel-gemm` | 原完整 GEMM，含双缓冲、累加、尾处理及写回 FIFO，固定 v1 `EPILOGUE_FUSION=0`；补充第二种计算 Block 的独立物理结果 |
| `opentpu-act` | small ACT 独立实现，保留宽读和写入状态／全部容量；为 O0-W 准备 |
| `opentpu-mxu` | small MXU 独立实现，保留任务、取数、FIFO、计算与 FP32 后处理；为 O0-W 准备 |
| `opentpu-act-mxu` | 同配置 ACT＋MXU 的原连接内化，作为 O1-W 合并实现；不加缓存、不串行化、不加周期 |

一个 c64 节点分配 64 CPU，四个 step 各 16 核，以 `srun --exclusive --cpu-bind=cores` 隔离。任务名 `lyz-par4`。调度器使用 `select/cons_tres`／`CR_CORE,CR_PACK_NODES`、`task/cgroup`；实际 node／CPU 与 `UNLIMITED` 以提交回执、allocation 和 step 记录为准。主线正在使用 node3，本批选择当时空闲的 node7。

## 验证与边界

- 主线原回归／形式结果不自动授予新包装或网表；每路执行自身 elaboration、`hierarchy -check`、`check -assert`，记录真实端口及 RAM 实例清单。
- 源 RTL 不改，包装不加寄存器；openTPU 合并连接对照原 `otpu_slice` 的 `u_act`／`u_mxu`。物理流程显式关闭阶段 LEC，因此不声称门级等价；主线默认 LEC 不取消。
- openTPU 使用原 revision 的 synthetic fakeram LEF／Liberty 研究模型，不是实际 SRAM、GDS 或签核；分开与合并使用同一模型规则和资源参数。工具 DRC／STA 均按实际报告分别记录。
- 本批 openTPU 的 IO delay 作用于实际 clk，端口 hold 仍检查；历史完整 small 的 virtual clock、端口 hold 例外和 CTS latency hook 未沿用。两者边界预算不同，不做历史 PPA 的直接收益比较。
- 四路产物不能直接相加后宣称已完成 O0-W 顶层；还需分开宏的实际顶层布线、同边界时序覆盖、面积／时钟／PDN／通道成本。H2 固定资源、多计算图及受限定制尚未执行。

## 执行回执

17:01（UTC+08:00）提交 **89458 `lyz-par4`**，实际在 node7 同时运行四个 step，每个 16 CPU，allocation 为 64 CPU，开始时再次确认 `UNLIMITED`。runner commit `2568623f91f871e139c4b7544d00d0181ce4cb01`，精确执行文件由计算节点 `runner-inputs.sha256` 标识。代码后续加入的监视器不冒称为该次提交前已运行代码。

18:04:57（UTC+08:00）快照确认：**四路均 `COMPLETED 0:0`，批次总耗时 41:33，89460 审计也 `COMPLETED 0:0`／21 秒**。四路最终 ODB／SPEF／报告均存在，路由 DRC、天线 net／pin 违例均为 0，setup／hold TNS 均为 0，max-slew／fanout 违例均为 0。以下 WS 是当前单角、当前边界预算下的工具结果。

| Case／step | 耗时 | Setup WS（ns） | Hold WS（ns） | Max-cap 违例 | 非 filler 实例面积（µm²） | 声明端口／signal bit |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `llaccel-gemm`／89458.2 | 41:30 | +0.781452 | +0.0250618 | **49** | 471,803 | 27／3,753 |
| `opentpu-act`／89458.1 | 5:59 | +1.22599 | +0.0322719 | **2** | 35,870.1 | 19／860 |
| `opentpu-mxu`／89458.0 | 30:09 | +0.267694 | +0.0524039 | **12** | 428,669 | 37／2,172 |
| `opentpu-act-mxu`／89458.3 | 33:59 | +0.478511 | +0.0342305 | **41** | 460,394 | 40／1,662 |

**四路执行完成，但四路均未通过完整电气验收。** 终态审计列出的工具预算门槛中，四路唯一 false 项均为 `max_cap_zero`；产物校验成功不能覆盖电容违例或未执行的功能／系统验收。GEMM 的实例面积全部来自标准单元；openTPU 数字含 synthetic SRAM 宏，不能跨项目直接比较绝对 PPA。

ACT 最终工具报告非 filler 实例面积 35,870.1 µm²，其中标准单元 6,722.88 µm²、synthetic SRAM 宏 29,147.2 µm²；die 106,410 µm²，不混为一个面积口径。最终日志分别报告 VDD/VSS 的所有 shape 连通；未额外重跑独立 PG／STA 签核。默认活动与 synthetic 宏模型的功耗／IR-drop 不当作真实应用结果。

实际 elaboration 确认分开两块的 SRAM 实例之和与合并块一致：ACT 为 4×32×128＋2×32×64 bit 的 1R1W 模型；MXU 为 3×64×72、1×64×40、1×64×96、1×64×64 bit 的 1R1W 模型；合并后同类型／同数量。声明端口数与 bit 数是接口记录，不是最终物理 pin、带宽或制造接点统计。

机器记录保存于 `project/experiments/parallel_blocks/results/`，远程大文件保留在独立 `parallel-blocks-01/`，监视器只读远程轻量报告并写本分支快照。Issue #7 使用[同一条并发回执](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7#issuecomment-6312241685)持续更新，避免覆盖主线正文。后台 heartbeat 工具明确不支持临时侧聊，因此未成功创建定时唤醒；本轮主动跟踪，不声称结束对话后仍有后台监视。

为保证批次结束后自动落盘终态，另提交 **89460 `lyz-par-audit`**：c64、1 CPU、`afterany:89458`、实际 `TimeLimit=UNLIMITED`。它是一次性依赖审计，不做周期轮询或物理重跑。独立 `observer-v1/` 绑定脚本哈希；四路均结束后在计算节点核对各 `output-files.sha256`，保存 `completion.json`、其 SHA、逐 case 校验日志和门槛结果。电容／时序等不通过会保留为 false，不因采集成功而标为通过。

实际核对 438 个产物条目全部通过（GEMM 108、ACT 111、MXU 109、合并 110）。已取回[冻结终态](../../project/experiments/parallel_blocks/results/parallel-blocks-01-completion.json)，下载字节 SHA-256 与计算节点记录一致：`4e6d7c24518f8ef55d45b57eb5325d0e7329dfc773273f8c339c4496fd885903`。后续监视器不会改写冻结终态；新增采集字段只写 `latest.json`。

## 本轮诊断与改进顺序

电容违例数量的演变如下，来源为各阶段原生 metrics；阶段寄生模型不同，不能将数量差直接当作修复器效果的严格对照。

| Case | 放置优化 | 详细放置 | CTS | GRT | 最终提取报告 |
| --- | ---: | ---: | ---: | ---: | ---: |
| GEMM | 0 | 1 | 0 | 5 | 49 |
| ACT | 0 | 0 | 0 | 0 | 2 |
| MXU | 0 | 3 | 3 | 9 | 12 |
| ACT＋MXU | 0 | 0 | 0 | 1 | 41 |

`3_4_place_resized.log` 和 `5_1_grt.log` 实际调用均为 `repair_design -verbose`，没有显式电容修复裕量。18:01 提交一次性 **89478 `lyz-cap-read`**（node7、1 CPU、UNLIMITED，已 COMPLETED 0:0），只在计算节点读取当前同一镜像的流程源码；确认 ORFS `util.tcl` 将 `CAP_MARGIN` 传入 `repair_design -cap_margin`，`variables.yaml` 将其定义为允许提前多修复的裕量。原始源码包留在 `parallel-blocks-cap-diagnostic-01/flow-sources.json`，SHA 为 `57647db58c2b952ff320ea8c0502aee057dc764be482cf7da5f86e13916d906e`；[本地摘录与回执](../../project/experiments/parallel_blocks/results/parallel-blocks-cap-diagnostic-01.json)下载核对了该 SHA。

这支持“路由后负载变化且前期修复裕量不足”的**候选解释**，尚未证明唯一根因。最差报告行分别是 GEMM `_331213_/ZN`（limit 60.73／cap 72.71），ACT `_5280_/Z`（60.50／63.15），MXU `_215362_/ZN`（26.02／33.13），合并 `u_mxu.f_tl[6]$_SDFFE_PP0P_/Q`（60.73／71.81）。表格未声明单位，因此本地逐行保留原报告文本，不擅自标单位；这些是具体驱动 pin，不能笼统归因于 ACT–MXU 接口。

本轮已经改进监视器：明确打印产物校验与失败的工具预算门槛；在最新索引保存逐阶段 max-cap 数量、最终电气违例原文和资源账单。实际再次采集确认四路保存的违例行数 49／2／12／41 与最终 metrics 一致。未修改旧 runner、SDC、原始数据或主线作业，**本轮未发起第二轮 PNR**。

下一轮建议按以下顺序推进，不扩散无依据的参数扫描：

1. **先用最小 ACT 试验电容裕量。** 固定现有 RTL、时钟／IO 预算和 16 线程，对比 `CAP_MARGIN=10`、`20` 与原始 0 基线；新目录保留全部输入。以最终提取后的电容、setup／hold、DRC、面积变化共同判断，再决定是否用于另外三块。参数尚未执行，不能称已修复。
2. **补齐功能与边界模型后再复用硬块。** 独立包装连接／数值回归和源到网表等价尚未完成；还需确定来自相邻块的驱动、负载及输出预算，不通过放宽时钟、false-path 或删除电容检查取得通过。
3. **把 ACT 与 MXU 分开的硬块实际重连到顶层。** 沿用主线供电／层次接口经验，记录顶层连线、时钟／PG、通道和边界时序，再与同配置合并块比较。当前 684 bit 的 ACT–MXU 数据／控制连接在拆分实现中尚无真实跨块布线；独立面积、线长或违例数量相加不能替代顶层结果。

## 并发资源是否需要调整

Slurm 账单记录批次 `TotalCPU=09:46:40`，分配的 `CPUTimeRAW=159552` 秒，即约 **22.1% 的已分配 CPU 时间被记为实际 CPU 使用**。这是本次账单口径，不是四路没有同时运行。各 step 的实际 CPU 时间／墙钟时间平均为：ACT 约 2.17 核，GEMM 5.37 核，MXU 5.58 核，合并 5.38 核；物理流程含低并行阶段，不能据平均数认定任意阶段只需这些核。

ACT 在约 6 分钟结束，另外三路需 30–42 分钟；四个固定 16 CPU 槽位中有一槽长期空闲。下一轮有足够独立变体时，值得比较小块 4／8 核与大块 8／16 核，并以受分配核数约束的任务队列及时补位；还没有线程数对照，不能宣称 8 核不增加耗时。电容裕量对照和线程数对照应分开，避免同时改两个因素。任何后续作业仍使用非 debug 节点、实际 UNLIMITED、独立目录，不取消主线。

## 接入与交付

复用 Issue #7，不接管其整体状态。登记沿用管理中心 PR #5，本轮再次读回仍 OPEN／未合并，状态 pending；本项目无 `config/board.json`，已知 Projects 查询缺 `read:project`，实际看板 unverified／同步 pending，不扩权限或另建看板。并发成果在 PR #10 独立审查，供主线决定合入顺序；不覆盖 PR #8 回执或擅自合并。

实际检查：管理结构、Python 编译、远程 Bash 语法和 `git diff --check` 通过；前一交付 `790820880bcdc07fabecddbb8bd8ff7c94e00dae` 的 [Project structure CI](https://github.com/rayggxia-workspace/LLMHardwareDesign/actions/runs/39576683446) success。本轮实际执行增强后的监视器、SHA 核对和四路最终报告行数比对，均通过；当前提交 CI 以 PR 最新回执为准。管理 CI 只验证项目结构，不代表物理、功能或签核验收。
