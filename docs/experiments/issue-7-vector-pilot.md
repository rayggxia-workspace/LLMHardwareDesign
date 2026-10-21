# 首轮 VECTOR Block 硬化与顶层集成记录

- 日期：2026-10-21（中国标准时间，UTC+08:00）。
- 任务：[Issue #7](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7)。
- 候选划分与后续对照：[实验计划](openTPU-llaccel-block-plan.md)。
- 复跑入口：`project/experiments/block_hierarchy/run_vec_pilot.py`；大体积输出保留在集群 `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7/`。

## 本次验证对象

使用 llaccel 原提交 `f7db8a22791a1ce9dc13e7c90b0b9b9386169aa5` 的完整 `vec_engine`，保持 16 路、原整数数值规则、操作集合、FIFO／拆分／归约／开方／除法、握手和响应状态，不裁成单个算术单元。原 core 对 `u_vec` 没有参数覆写；独立 elaboration 保留原配置。原声明接口为 26 个端口、2,246 个 bit，这不是最终物理 pin 数，也不是同时发生的数据流量。

独立 Block 采用 Nangate45 研究平台、3 ns 周期及 0.6 ns 输入／输出延迟作为工程预算假设。没有声称这是完整 llaccel 系统重新签核的约束。SRAM bank、共享 crossbar、其他引擎、DMA 与 DRAM 不在该独立 Block 内。

本次尝试的步骤为：原 RTL 的完整 VECTOR 解析 → Block 独立综合／布局布线 → 从实际阶段导出 LEF 与时序模型 → 顶层以单个真实宏实例引用该实现、冻结位置再连接。Block 内部可以展开，顶层不得重新综合宏内部。直通 shell 是工程集成验证对象，不能替代真实的跨引擎通信图。

## 执行记录

| Attempt／作业 | 实际状态与含义 |
| --- | --- |
| `vec-screen-01`／89441 | 失败：计算节点没有从作业环境找到 Singularity；保留原日志，没有产生有效宏或物理结果 |
| `vec-screen-02`／89442 | 筛查通过：修正显式工具路径后，原完整 VECTOR 的 RTL 解析通过；确认镜像中的层次支持入口，不将网上最新变量直接当成镜像能力 |
| `vec-harden-01`／89443 | 已提交 c64、16 CPU、45 分钟上限；结果待本记录后续更新，不能把作业启动当作硬化成功 |

本轮代码初次运行时尚未提交。运行器、配置和源输入的 SHA-256 用于绑定实际执行快照；合入前在提交回执补充承载这些脚本的项目 commit，不把基线仓库 commit 冒称为本轮代码版本。

## 验证及证据边界

筛查的 `hierarchy -check`、`check -assert` 等检查属于 elaboration／结构检查，不证明 RTL 与软件参考等价，也不证明新网表或路由后功能正确。原功能仿真、形式比较及独立全系统 STA 没有因本次选择了相同源码而自动完成。

后续按实际生成阶段记录 Block 产物、顶层的真实宏实例及位置、LEF／Liberty 是否来自最终路由、是否读入 SPEF、实际未布通与 DRC、setup/hold 报告、约束覆盖和失败项。工具退出为零、DRC 数字、某项 WNS 和整体签核是不同证据，不互相替代。

普通 H1 流程允许顶层常规 CTS／修复新增有源单元。本项目 H2 的固定底座验证还需冻结这些资源，声明定制金属／通孔／接点集合，并验证多个真正不同的计算图。当前单 VECTOR pilot 不提供后加工制造、预埋轨道收益、多计算图覆盖或能耗／成本优势结论。

## 后续实验

1. 用同一功能与相同接口包装建立 F0 扁平对照，先隔离硬宏边界带来的面积、端点、时序与布线代价。
2. 扩展到 llaccel 的完整引擎粒度 L0，保持原共享存储请求语义；独立 VECTOR shell 的结果不能外推为完整 core 的结果。
3. 对 openTPU 实施 ACT／MXU 分离与合并的同资源物理对照，复用已有 128 bit 链路的行为证据，补物理实现与活动／功耗，不重做同一轮等待注入扫描。
4. 从成功的 H1 实例建立冻结底座和受限定制 H2，最后检验至少两个实际不同的通信需求；各阶段分别报告失败和适用范围。
