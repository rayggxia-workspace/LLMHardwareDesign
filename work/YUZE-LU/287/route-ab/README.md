# A/B真实走线：几何、负载探针与端点资格

2026-11-17，YUZE-LU，Refs #287 / PR #288。固定main 00b288f00e6d64e29ce9ba2ff2a5edb01bc58291。远程原件 `/public/home/yuzelu/project-circuit/issue287-route-ab-20261117`。

## 结论

本轮已完成几何复核、六条真实走线静态电场探针及C/U实际端点单元检查。尚未完成联合STA：两方案的C/U来自未完成详细布线的CTS实现，不能继承此前合格C V3/U39的时序回执。抽样C→U输出均为BUF_X1，线路负载已明显超过该单元Liberty最大电容，200MHz与300MHz都不能据此判为电气通过。

|方案/样本|实际长度mm|线网自电容Cg+Cc fF|对地fF|互容有符号和fF|
|---|---:|---:|---:|---:|
|A C→U，data97|3.060|508.87|37.92|470.95|
|A C→U，data47最长|5.010|418.67|216.34|202.33|
|B C→U，data97|3.060|523.65|36.69|486.96|
|B C→U，data47最长|5.010|525.61|178.90|346.71|
|B G→S，data22|5.092|796.74|93.54|703.21|
|B S→G，ready最长|5.296|663.66|167.28|496.39|

data97是排序中位附近实际样本，不能与统计中位数混淆。A/B的C/U总体中位长为3.053/3.056mm，最大5.010mm；B G/S中位5.092mm、最大5.296mm。

C实际端点：outgoing_data[47]由output3684/BUF_X1/Z驱动，data97由output3739/BUF_X1/Z驱动；U对应接收为wire9302、wire16603的BUF_X4/A。典型角Liberty以fF为单位，BUF_X1/Z max_capacitance=60.6537fF；BUF_X4/A电容3.401892fF。仅线路静态自电容就是输出限制的6.90–8.67倍，尚未加接收引脚和块内连线。真实分布RC的slew和延迟需另算，不能把此比较当作完整STA，亦不能从线网C直接换算最高时钟频率。降频不改变该库电容限制。

## 资格及模型边界

- A映射后的306根C/U网（P金属作为障碍保留）及B全536网通过声明的矩形间距、连通、边界/M10包围规则。不是foundry DRC，下层金属完整检查未包含。B中P相关网不评时序，但在场景中保留电极。
- 输入归档 `routing-results-archive`，本地原始路径为 `C:/Users/wine10/.codex/visualizations/2026/11/17/01a1e836-f66f-7262-8cfe-48c393b92969/`。A使用original-route映射到placement-mapped后的真实几何；B使用route-fixed.json（归档route.json）。远程A-mapped.json保留。场景SHA见field-probe-index.json。
- C/U交接软链接实际指向 `yzl-cu-overlay-physical-20261116/{C,U}/flow/results/nangate45/{c,u}-overlay-current/base/4_cts.odb`；SHA分别64d2fe9a…、7e2a2151…。stopped-current-checkpoints.json明确写明mapped placed CTS、native detailed routing not accepted；原后端作业118433/118434按用户要求取消。因此本轮未擅自恢复被取消的实现，也未以旧合格版本冒充当前版。
- B G→S有既存父层驱动（audit.json逐位列出），例如F0.S.req_valid已有hold15100/Z。现有B是压力映射，替换输入驱动属于测试网表操作；实际接入前必须明确切断点和功能协议，不能保留多驱动然后宣称正常联合仿真。
- 场求解器使用#199原二进制SHA d6fb74c2…，均匀介电常数3.9，M10/M11/M12与via高度沿用#215研究模型，宽2um。包括实际上层线/落点和P导体，不含完整下层真实金属、接收引脚或块内寄生。不含电感、动态串扰和完整分布R。本轮产物是静态总负载探针，不是合格SPEF或完整RC/STA验收。
- 探针节点采用导体盒中心，仅使用Maxwell行总量；不使用来源/捕获bins分摊制作SPEF，避免继承#222来源分摊资格问题。场求解总电容1σ统计误差0.147%–0.222%，行守恒残差小于4e-12fF。这不是模型系统误差界，也不是全矩阵互易性验证。短弱互容有随机符号噪声，未静默截断并重新分配。

## 作业和继续入口

119521因A过滤混入G/S失败；119522几何复核通过。119523因将三维节点误写成盒子格式失败；修复后119524在debug/node27分配12核、6任务各2线程，21秒完成，单行4194304 walks。119525分配2核并行导出两端实际ODB端点，日志含PORT_EXPORT_COMPLETE。原失败状态failed-119523-status.json留服务器。场行原始JSON、日志和场景留服务器，紧凑摘要及SHA在本目录。

复现时复制脚本到新目录，修改绝对输入/输出根，依次sbatch audit.sbatch、field.sbatch、ports.sbatch；ports.tcl在上一级。summarize_probe.py读取场行，lib_probe.py在同容器读取典型角库。不要覆盖此轮证据。

下一步先确定物理基底：若保留这版overlay功能，须先完成C/U后端验收；若使用已验收版本，应重新映射引脚并布线，保留A/B作为长度/拥塞目标，不能只换时序模型。之后提取与块内寄生去重的分布RC、接入真实驱动和接收路径，跑200/250/300MHz setup/hold/cap/slew并做零顶层RC对照。当前驱动过载提示需要输出缓冲/重复器或布局缩线；选型和位置须随真实基底重验。

规则rayggxia-project-collab 1.0.0。完整联合验收受上述输入资格阻塞，待审查；管理中心登记PR5 pending，缺board配置，Projects unverified/同步pending。未关闭Issue或合并PR。
