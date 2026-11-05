# Issue162：新S仲裁器全部单块验收通过，新组合重新实测

更新时间：2026-11-05T05:45:25+08:00。[Checkpoint93](../../../work/YUZE-LU/162/continuation-checkpoint-93.md) / [695项实际原件](../../../work/YUZE-LU/162/continuation-proof-93/index.json) / [23类六文件与源绑定](../../../work/YUZE-LU/162/source-binding-current1773.json) / [345项状态归属](../../../work/YUZE-LU/162/state-ownership-current1773.json)。main六宏、S1350内部驱动及R均保留，外部R工作不动。

新增控制块S仲裁器3200um的原生P&R、300MHz时序/电气、完整native/GDS DRC、三初态功能、严格LEC、六文件/图全部通过；固定PG完整GDS DRC、VDD/VSS连通、freshRC时序和完整功能视图同一性亦通过。setup/hold最差+1.194584/+0.022119ns。相对原1470um面积增加8.0791mm²，必须计入新组合，不能继承旧摆放/RC。

1757库选择通过，但按新pin自动分组触发既有316Link8/25bank断言失败；失败拓扑/原规格/结果保留，三个从未启动的后继按原字节归档。source1772仅拓扑生成器新增“逻辑分组参考”，1029项/归档/反向补丁审计1774通过，其余1028源文件及全部验收门不变。实际1773拓扑通过，345宿主/316Link8/全部逻辑连接与453精确相同；1778源绑定审计通过，其他22物理类型完整行相同，只有S仲裁器选用新的合格六文件。所有实际物理检查仍使用新3200um引脚与尺寸。

新组合功能编译、原生STA及初始摆放已独立启动；初始摆放已完成仅线容下界阶段，后继等实际原生STA。node4实测452.816GiB低于全部三个旧搜索加224GiB STA所需476.8GiB；只退役本任务16180/95391.169，原5+次非零DRC/全部部分结果保留、UID/spec/source/PID/无最终输出核验通过。余两项搜索加STA预测352GiB需438.4GiB，实际准入记录通过；不降低门槛。8父节点快照实际34/36活跃：node4内存限制三项，node5初始完成后等依赖三项；原索引scope旧文字35项已另附勘误，原件不修改。c96六×16动态补位，父任务、旧3751、其他工作不动。

**仍未获得完整组合全网零冲突、native几何/XOR/PG、三档分布RC 300MHz及联合最终交付资格。继续布局布线定位迭代，不在检查点停止，不借单块通过宣布系统通过，不合并。** 规则1.0.0；登记PR5 pending；看板缺配置unverified/同步pending；审查待指定；Issue in_progress / PR Draft。

承接[92](continuation-checkpoint-92.md)。[实收](continuation-proof-93/reception.json)、[原索引计数勘误](continuation-proof-93/capture-scope-erratum.json)。
