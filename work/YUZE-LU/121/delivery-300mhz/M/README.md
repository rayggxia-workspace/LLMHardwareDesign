# M：矩阵乘加宏，新版300MHz原生最终结果

唯一基础实现：64个共享S8乘法器、局部归约、8路S64累加、有限操作数银行、S16分解与S128合并/RNE饱和；完整计算引擎边界。归约与累加在M内部。数值格式、操作延迟和局部缓冲以[修订合同](../../../../../docs/BLOCK_V1_REVIEW_CONTRACT.md)为准。共享S32缩放参数不自动等于逐通道独立缩放。

| 项目 | 真实结果 |
| --- | --- |
| 原生最终源 | run255 native → run258 exact10/3ns final source |
| 外框/面积 | 740×740µm / 0.5476mm² |
| 最小setup / hold | +0.008340 / +0.013190ns |
| 接点 | 275个真实M10信号位，全部2×2µm内部接点 |
| DRC | 原生全片0，完整未修改FreePDK45 GDS deck0 |
| 功能/等价 | 最终网表三初态与独立严格LEC全部通过；分组进位全128输入位SAT等价、溢出正负例另有证据 |
| 最终文件 | Verilog、SDC、DEF、ODB、SPEF、GDS逐文件位置/大小/SHA见[原始最终索引](final-native.json) |
| 完整原生几何 | run258原ODB保持、全部wire/via/PG/pin/OBS及DEF RECT导出通过 |

[原生版图](block_v1_m.png) · [最终文件/DRC/完整几何回执](../../review-20261028/finish-0125/index.json) · [物理/最终功能](../../review-20261028/checkpoint-20261029-0100/index.json) · [严格LEC](../../review-20261028/m-lec-0103/index.json)。大数据库保留批准服务器，原索引给出完整路径。

完整接口run262也已通过P2几何：275位同时连接；真实DEF/ODB三次读回和joined GDS全部原生层XOR0，新增M10金属负例被拒；新层几何规则通过。[P2原始三报告](../../review-20261028/m-p2-0130/index.json)。全测试外框820×820µm，每根280µm，总线长77000µm；via10=275/via11=133。简化模型每线电容base43.5095fF/high65.2642fF，base未超过原48fF线预算；高变体及完整接口输入/输出时序仍待单独验证。不能从几何接通推断组合300MHz或12层工艺资格。
