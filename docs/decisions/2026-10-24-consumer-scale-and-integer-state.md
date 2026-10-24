# 完整消费者和连续状态后的划分取舍

2026-10-24，Liangruizhi；[Issue66](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/66)/[PR67](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/67)，[实测报告](../experiments/issue-66-scale-state.md)。状态：有证据的数值/资源合同决定，制造边界仍候选。

1. 保留逐通道base+tileδ ACT8和ACT16两种出口；不强制早转K128。完整hidden的静态8/同范围16共37次sat，tileδ本批0sat，早转K128省128B/row却增加norm/未最终RQ的next16误差。完整norm会重新建立A8，不把ACT16消费代价套给其后的A8矩阵。
2. 将ALIGN/残差/完整H归约/norm/新A8作为逻辑闭包。整数input RMS候选已独立逐码验算，不能宣称所有norm或GDN全整数。16KiB内装不下20,480B aligned行；两遍源读或spill、宽乘、sqrt/div和端口均计候选成本，未决定物理同宏。
3. 采用S32作R优先工作参考，保留S16与D15/D31 profile。理由是本批32步误差显著降低；反例是同范围长窗仍sat184/193，不能固定通用静态范围。D31消除近1衰减量化为1的风险，却未证明普遍质量收益，不能直接要求额外宽硬件。
4. 固定完整K预测与更新/提交次序、单owner/epoch/position及范围失败义务；不固定R专用物理宏。V32 old/new占满32KiB，aux不能免费；V16、S侧shadow及可证明原位提交是独立资源路线。完整V128 head norm屏障不能因state按Vtile可分而删去。
5. 对长窗饱和保留原格式/scale，不按评价重拟合。下一实验先定义范围/重定标epoch或合法fallback，再同资源调度；R内部SiLU/QK L2norm/GatedRMS/gates另行资格。当前没有应用误差预算或整图证据，不写普遍可用/端到端收益。

取舍原因：避免重复模型排行榜，把资源用于仍会改变M/V/R/S边界的数值域、有限端口、range管理及物理资格。Phi保持独立封存。成员Issue55/63工程不由此接管，需接收其实际端点/时序/布线证据后再收敛制造方案。
