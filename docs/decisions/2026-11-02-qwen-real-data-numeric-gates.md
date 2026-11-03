# 决策：真实参数F的有限尺度验证与质量接受分开

Issue151/PR152，待外部审查。95247真实layer0小前缀FP32→F数值诊断、95248两静态profile四完整F行RTL通过；源d0c40f57/f7fc7614，见[报告](../QWEN_LAYER0_NUMERIC_RTL_REPORT.md)。

只新增N epsilon/M最终READ shift静态控制常量，不改原生算术或旧44源。叶宏支持命令不等于旧top能选择，也不等于M11/M12永久绑定电路已经实现。继续固定模型程序边界，动态tensor/weight与程序可变性分开。

cal按relative L2选到W9，但eval最大误差上升、82权重clip；W8无clip折中没有本轮RTL资格。没有阈值/代表性语料/框架对照，不据平均改善定稿模型尺度，不放宽旧准入。真实A只签收单S/T容量与程序静态候选，controller/spool/layout/供参和物理仍需实现。
