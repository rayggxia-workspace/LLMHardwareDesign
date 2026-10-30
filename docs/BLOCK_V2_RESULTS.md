# 七类基础宏：实际结果入口

任务[#143](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/143)，草稿[PR #144](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/144)。本页记录实际接收结果；功能/数值/接口合同见[BLOCK_V2](BLOCK_V2.md)。**目前六宏完成，R仍在实施，七宏任务尚未完成。**

## 最终叶子物理结果

以下六宏均通过同一适用300MHz/0.1ns不确定度合同的最终物理检查、原生全片和完整未修改FreePDK45 GDS DRC、三组实际初态最终网表功能、严格全边界LEC及真实几何证明，并已本地核验六文件。时序值为真实时序端点的最小裕量；输入保护器件的被动端点分类及负例证据保留于各物理报告。

| 宏 | 边长µm | active单元面积µm² | setup最小裕量ns | hold最小裕量ns | 来源/最终门 |
|---|---:|---:|---:|---:|---|
| M | 930 | 304530.898 | 0.039857 | 0.018500 | 新源013→018，包024 |
| N | 510 | 68015.668 | 0.140712 | 0.017753 | 新Q1.14源027→028，包029 |
| E | 600 | 63601.132 | 0.307090 | 0.021340 | 新源006→010，含源包023 |
| G | 400 | 22831.046 | 0.512034 | 0.017721 | 新源006→010，含源包023 |
| S | 1680 | 1181315.842 | 0.028545 | 0.007200 | #130精确同源300MHz成果，017重新核验 |
| T | 1040 | 431244.786 | 0.429092 | 0.007988 | #121精确同源300MHz成果，017重新核验 |
| R | 待验收 | 待验收 | 待验收 | 待验收 | 原015→039；几何030→033；分组035→036；分组后时序放置041→042；仅放置hold目标0的045→046，尚未接收 |

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
- 本轮为M1–M10固定、宏内M10接口的原生叶子结果；候选LEF不等于层级Liberty、M11/M12系统或制造签核。八模型完整整数质量与系统调度/吞吐未验证。
- 登记pending、看板unverified/同步pending、独立审查人待指定，PR未合并；不提前关闭Issue。
