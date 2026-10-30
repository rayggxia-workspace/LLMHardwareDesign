# 七类基础宏：实际结果入口

任务[#143](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/143)，草稿[PR #144](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/144)。本页记录实际接收结果；功能/数值/接口合同见[BLOCK_V2](BLOCK_V2.md)。**当前M/N/G/S/T五宏合格；旧E合格结果保留为基线，新E增加S32→S16接口模式后重新验收；R仍在实施，七宏尚未齐。**

## 最终叶子物理结果

下表M/N/G/S/T及历史E均通过同一适用300MHz/0.1ns不确定度合同的最终物理检查、原生全片和完整未修改FreePDK45 GDS DRC、三组实际初态最终网表功能、严格全边界LEC及真实几何证明，并已本地核验六文件。历史E数据不能转记给新op13实现。时序值为真实时序端点的最小裕量；输入保护器件的被动端点分类及负例证据保留于各物理报告。

| 宏 | 边长µm | active单元面积µm² | setup最小裕量ns | hold最小裕量ns | 来源/最终门 |
|---|---:|---:|---:|---:|---|
| M | 930 | 304530.898 | 0.039857 | 0.018500 | 新源013→018，包024 |
| N | 510 | 68015.668 | 0.140712 | 0.017753 | 新Q1.14源027→028，包029 |
| E历史基线 | 600 | 63601.132 | 0.307090 | 0.021340 | 006→010，含源包023；不包含S32输入模式 |
| E当前 | 待验收 | 待验收 | 待验收 | 待验收 | 新源065/94007→066/94008→067/94009 |
| G | 400 | 22831.046 | 0.512034 | 0.017721 | 新源006→010，含源包023 |
| S | 1680 | 1181315.842 | 0.028545 | 0.007200 | #130精确同源300MHz成果，017重新核验 |
| T | 1040 | 431244.786 | 0.429092 | 0.007988 | #121精确同源300MHz成果，017重新核验 |
| R | 待验收 | 待验收 | 待验收 | 待验收 | 原源015/030/035/041/045；新源053→054、059→060、062→063，尚未接收 |

active单元面积不等于die面积。S/T均为标准单元存储，不能称为SRAM宏。M与旧#130的数值/命令合同不同，不能将面积差全归因于位宽，也不能当等吞吐比较。N/E/G的独立吞吐配比和长向量回放在规格中明示。

## 找到每个宏的最终文件

完整机器可读入口：[delivery-index.json](../work/YUZE-LU/143/delivery-index.json)，逐宏列出本地回执、服务器包、SHA-256和六文件真实路径。大体积数据不放入Git。

| 宏 | 本地实收目录 |
|---|---|
| M | `D:/Data/LLMHardwareDesign-issue143-runtime/deliverables/M` |
| N | `D:/Data/LLMHardwareDesign-issue143-runtime/deliverables/N-q14` |
| E | `D:/Data/LLMHardwareDesign-issue143-runtime/deliverables/E-v2` |
| G | `D:/Data/LLMHardwareDesign-issue143-runtime/deliverables/G-v2` |
| S | 索引/回执在`issue143-runtime/deliverables/S`；六文件复用`D:/Data/LLMHardwareDesign-issue130-runtime/deliverables/S/unpacked/native`，已重新SHA核验 |
| T | `D:/Data/LLMHardwareDesign-issue143-runtime/deliverables/T` |

新包的`unpacked/native`含`6_final.v/.sdc/.def/.odb/.spef/.gds`、真实`layout.png`和`pins.json`；`geometry`含候选LEF与实际接入证明；`evidence`含全部最终门，`meta`含绑定的最终源回执、合同及源码。S/T沿用原包结构，原始交付/源回执位于`evidence`。

新包可用`python project/experiments/block_v2/receive_bundle.py --remote-bundle <本任务实际bundle.json路径> --out <新的本地目录>`收件并验证完整成员、全部门与源码绑定。服务器根为`/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030`，只访问本任务成果。

## 尚未完成和保留的失败

- R保持既有S32宽状态、影子提交和GDN/SSM/卷积合同；实际709124映射单元。五个物理尝试使用同一RTL与映射，最终只选一个合格实现。038只读探针在030的实际放置ODB测得bank_role驱动92059个负载、可分578个空间组；035只增加原生物理缓冲。035已实际插入674个原生缓冲、电气修复299秒完成，但放置后的setup修复仍有负裕量；041据此在分组后增加显式时序驱动全局放置。045再将额外20ps的hold修复裕量留到CTS阶段：仅放置进程目标为0，CTS新进程重新加载0.02ns，最终SDC和门槛不变。全部方案仍需取得最终资格。探针证据见[目录](../work/YUZE-LU/143/r-fanout-probe/index.json)。不能用中间阶段或诊断代替最终通过。
- `deliverables/N`为旧UQ0.16候选，已被S16 Q1.14取代；不能作为最终N。021/022新编码的首次物理尝试有两项M2原生DRC，失败保留；027/028在0.42布局密度下重新取得全部资格。
- 053是R的局部临时算术候选：原S32状态、S65乘积、S64点积、全部顺序控制不变，仅将RNE输入收至S65、结果/合并临时值收至S52。直接抽取新旧RTL数值case的全输入SAT证明、翻转结果/溢出负例以及三组实际初态回归均通过，每初态仍为379979检查/178456拍。它必须重新综合、执行全部六阶段及最终门；不能把前五条同原源物理链的结果转给它，也不预先宣称面积或时序改善。原始小证据见[r-temp-proof](../work/YUZE-LU/143/r-temp-proof/receipt.json)。
- 本轮为M1–M10固定、宏内M10接口的原生叶子结果；候选LEF不等于层级Liberty、M11/M12系统或制造签核。八模型完整整数质量与系统调度/吞吐未验证。
- 登记pending、看板unverified/同步pending、独立审查人待指定，PR未合并；不提前关闭Issue。

## R中间证据：2026-10-31 03:45 CST

015的原生CTS完整等价检查已于03:16:56返回UNSAT/IDENTICAL，严格核验292950输入、292936输出全部对应、差异计数为0，随后进入全局布线。CTS中间setup/hold仍有负裕量，不能据此填写最终结果表。原始完整证明与明确标注为子集的058诊断分别归档于[诊断索引](../work/YUZE-LU/143/r-solver-diagnostics/index.json)。051/052/057的30分钟超时均不形成等价结论；生产门和接收标准未改变。

053仍在新RTL重新综合；同源2400µm/.45物理候选仅已准备，尚未提交，不将计划写成结果。

## R新映射与物理策略：2026-10-31 04:41 CST

053新源综合实际通过，6088.264秒、710389单元、映射面积1459590.678µm²；原映射为709124单元/1458349.256µm²。因此暂时没有面积压缩收益证据，仍需看关键路径和最终物理结果。S32状态/S65乘积/S64点积未变，局部临时算术全输入证明与三初态回归保持。

三条新源物理链使用完全相同的RTL和映射：053为3000µm/.25；059为2400µm/.45；062只在059策略上显式允许原生CTS使用BUF_X4/X8/X16/X32。已读回实际make变量，300MHz、0.1ns不确定度、HOLD_SLACK_MARGIN=.020及全部最终门未变。059/93977→060/93980→061/93981；062/93978→063/93982→064/93983。gate/pack复用同次封存的059/062源码快照，不创建新的实现变体。

当前8个真实物理作业，其余成功依赖后继不占allocation；单个R最终门最多三项同时就绪，所以采用3×16核动态补位。所有R仍未取得最终资格，最终只选择一个实现。[新映射及中间回读索引](../work/YUZE-LU/143/r-physical-trials.json)明确标注prefix而非完成回执，不替代最终物理证据。
