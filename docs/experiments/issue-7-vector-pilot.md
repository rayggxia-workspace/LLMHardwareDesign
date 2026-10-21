# 首轮 VECTOR Block 硬化与顶层集成记录

- 日期：2026-10-21（中国标准时间，UTC+08:00）。
- 任务：[Issue #7](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7)。
- 交付：[PR #8](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/8)；初始脚本快照 `7e9bde5b763b19591dcbe4f49ade7b08ef093843`。
- 候选划分与后续对照：[实验计划](openTPU-llaccel-block-plan.md)。
- 复跑入口：`project/experiments/block_hierarchy/run_vec_pilot.py`；大体积输出保留在集群 `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7/`。

## 本次验证对象

使用 llaccel 原提交 `f7db8a22791a1ce9dc13e7c90b0b9b9386169aa5` 的完整 `vec_engine`，保持 16 路、原整数数值规则、操作集合、FIFO／拆分／归约／开方／除法、握手和响应状态，不裁成单个算术单元。原 core 对 `u_vec` 没有参数覆写；独立 elaboration 保留原配置。原声明接口为 26 个端口、2,246 个 bit，这不是最终物理 pin 数，也不是同时发生的数据流量。

独立 Block 采用 Nangate45 研究平台、3 ns 周期及 0.6 ns 输入／输出延迟作为工程预算假设。本轮已导出的综合／floorplan SDC 未显式设置外部驱动单元、输入转换时间或输出负载，因此还不是完整边界电气模型。没有声称这是完整 llaccel 系统重新签核的约束。SRAM bank、共享 crossbar、其他引擎、DMA 与 DRAM 不在该独立 Block 内。

本次尝试的步骤为：原 RTL 的完整 VECTOR 解析 → Block 独立综合／布局布线 → 从实际阶段导出 LEF 与时序模型 → 顶层以单个真实宏实例引用该实现、冻结位置再连接。Block 内部可以展开，顶层不得重新综合宏内部。直通 shell 是工程集成验证对象，不能替代真实的跨引擎通信图。

## 执行记录

| Attempt／作业 | 实际状态与含义 |
| --- | --- |
| `vec-screen-01`／89441 | 失败：计算节点没有从作业环境找到 Singularity；保留原日志，没有产生有效宏或物理结果 |
| `vec-screen-02`／89442 | 筛查通过：修正显式工具路径后，原完整 VECTOR 的 RTL 解析通过；确认镜像中的层次支持入口，不将网上最新变量直接当成镜像能力 |
| `vec-harden-01`／89443 | `TIMEOUT`，45:00；已完成综合和放置，停在 stage 4 修复前后 Kepler 门级 LEC 的 solver；未得 LEC 结论，未完成 CTS 或布线。Slurm `ExitCode=0:0` 不能覆盖 `State=TIMEOUT` 和时限终止日志 |
| `vec-top-01`／89444 | 运行前取消，原提交与状态保留；没有产生顶层结果 |
| `vec-top-02`／89445 | 依赖 89443，因依赖失效自动取消；未执行顶层实现 |
| `vec-harden-resume-01`／89447 | `FAILED`，约 10 秒，`2:0`；父作业及输入身份检查通过，但 `make -n finish` 因尚未执行阶段应生成的 SDC 副产物缺失而失败；没有继续物理流程。保留日志，恢复检查需改为核对首个待执行阶段 |
| `vec-harden-resume-02`／89448 | c64、16 CPU；实读 `TimeLimit=UNLIMITED`，保存调度快照；身份与首个待执行阶段的 dry-run 通过，实测直接接续 CTS、没有重跑综合；终态待回填 |
| `vec-top-03`／89449 | c64、16 CPU；实读 `TimeLimit=UNLIMITED`；`afterok:89448` 等待 Block 完成，尚无顶层物理结果 |

综合阶段记录了 259,349 个标准单元，标准单元面积为 460,078 µm²；这是 `1_synth.json` 的阶段指标，不是最终宏面积或制造占地。后续修复、时钟和布线还会改变资源。

本轮代码初次运行时尚未提交。运行器、配置和源输入的 SHA-256 用于绑定实际执行快照；事后保存的项目代码 commit 见页首与 PR 回执。各 attempt 之间确有版本差异，实际身份以各自的 `runner-inputs.sha256` 为准，不把基线仓库 commit 或某一后续快照冒称为所有作业的精确执行版本。[轻量结果索引](../../project/experiments/block_hierarchy/results/issue-7.json)收录各作业、工具与输入身份、阶段指标及远程日志路径。镜像已记录 SHA-256，OpenROAD 版本字符串为 `unknown`；实际二进制哈希可核对，未推断其版本号。

按用户后续明确指示，撤销早期试跑的人工运行时限。集群实读 c64、c96 的 `DefaultTime=NONE`、`MaxTime=UNLIMITED`；后续提交不设有限时长，并读回作业实际 `TimeLimit`。上述 45 分钟超时与已终止恢复作业仍属于真实历史，不删除或改写。

## 原实现的时序背景

本轮还定向读取了远程已有的 `llm_routing_analysis/runs/llaccel-v1-sta-final01/`。其 `audit_manifest.json` 记载使用原 `6_final.odb/sdc/spef`、Nangate45 typical 库、原约束和例外，且未修复或放松约束；OpenROAD 二进制哈希与本次镜像实际程序一致。既有 `run.log` 报告 `worst slack max=-4.44 ns`、`worst slack min=+0.01 ns`、`tns max=-8038.83 ns`。这是读取已有报告，未在本轮重跑该独立 STA，也未重新核对其全部输入。

其中最坏路径示例包括 `rst_n` 到 ATTENTION 寄存器的 recovery 检查；不能把上述最大延迟 slack 笼统解释为某条 VECTOR 算术路径的延迟。该背景表明原 3 ns 全 core 结果本身也不能当作时序闭合基线。新 VECTOR 若出现负 slack，仍须建立相同功能、包装、约束和实现阶段的 F0/H1 对照，不能把差异直接归因于 Block 划分。

## 验证及证据边界

筛查的 `hierarchy -check`、`check -assert` 等检查属于 elaboration／结构检查，不证明 RTL 与软件参考等价，也不证明新网表或路由后功能正确。原功能仿真、形式比较及独立全系统 STA 没有因本次选择了相同源码而自动完成。

后续按实际生成阶段记录 Block 产物、顶层的真实宏实例及位置、LEF／Liberty 是否来自最终路由、是否读入 SPEF、实际未布通与 DRC、setup/hold 报告、约束覆盖和失败项。工具退出为零、DRC 数字、某项 WNS 和整体签核是不同证据，不互相替代。

普通 H1 流程允许顶层常规 CTS／修复新增有源单元。本项目 H2 的固定底座验证还需冻结这些资源，声明定制金属／通孔／接点集合，并验证多个真正不同的计算图。当前单 VECTOR pilot 不提供后加工制造、预埋轨道收益、多计算图覆盖或能耗／成本优势结论。

## 后续实验

1. 用同一功能与相同接口包装建立 F0 扁平对照，先隔离硬宏边界带来的面积、端点、时序与布线代价。
2. 扩展到 llaccel 的完整引擎粒度 L0，保持原共享存储请求语义；独立 VECTOR shell 的结果不能外推为完整 core 的结果。
3. 对 openTPU 实施 ACT／MXU 分离与合并的同资源物理对照，复用已有 128 bit 链路的行为证据，补物理实现与活动／功耗，不重做同一轮等待注入扫描。
4. 从成功的 H1 实例建立冻结底座和受限定制 H2，最后检验至少两个实际不同的通信需求；各阶段分别报告失败和适用范围。
