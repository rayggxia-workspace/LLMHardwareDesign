# Issue162：复用FastRoute完整物理链，队列内存迁移及单位纠正

更新时间：2026-11-05T01:56:39+08:00。[Checkpoint87](../../../work/YUZE-LU/162/continuation-checkpoint-87.md) / [227项远程原件与源绑定](../../../work/YUZE-LU/162/continuation-proof-87/index.json)。原CUGR15530与已有FastRoute15620各三小例实际通过；误把8000DBU当8um导致的pitch8实验15531被原严格格点拒绝，原件保留、两处代码已显式撤回，原4um=8000DBU/2000DBU每um本来一致。当前FastRoute15640复用原source1526，严格7阶段与实际11149接线/5380摆放/node25六组16CPU/320GiB预测400GiB准入通过。

旧source93控制器只接受最多128GiB，六份224GiB后继STA在准入前拒绝；原规格/结果保留，唯一新名称迁至已有node6/source269（上限256），实际读回未再拒绝且等待真实几何。各阶段原物理/300MHz门不变；其余六份增长策略STA在支持224GiB的node24队列中。只fresh守卫替换本人5400和已有等价对照覆盖的12841子步骤；R、其他任务和旧CUGR3751不动。现有快照helper15770重放当前CUGR15220作一轮DRC定位，不能替代持续运行的完整验收。

**仍无完整全图零冲突、几何/native XOR/PG/三档分布RC300MHz联合通过。继续布局布线、不合并。** 六宏/R256/S1350/23类138文件/345状态宿主及453/S5380保留。8父节点36×16动态、c96六槽，实际内存门保持；登记PR5 pending、看板unverified/同步pending、审查待指定。

原始材料以[远程索引](continuation-proof-87/index.json)、[接收核验](continuation-proof-87/reception.json)、[本地辅助/发布/撤回核验](continuation-proof-87/local-index.json)为准。当前HEAD生产两文件逐Git blob等于source1526，两个发布提交保留错误实验与显式撤回；本轮所有几何/RC/300MHz门未改。此前证据承接[86](continuation-checkpoint-86.md)及[九份STA内存修正](sta-resource-correction1544/index.json)，新迁移覆盖其中15220三项与15640三项。

原1575在提交任何任务或取消前因错误假定5494为64GiB而拒绝，孤立config15750和原脚本保留；1577按12841实际64GiB重新核验，225GiB汇总预测需286GiB实际可用，才替换精确95391.130。15770仍需读取真实最终诊断输出；DRC详细报告可能不完整，不能以样本冒称全部违规分布。节点内满槽是实际快照，不宣称每时刻连续满载。
