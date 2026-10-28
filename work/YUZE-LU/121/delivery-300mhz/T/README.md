# T：6 KiB 结果交接宏，新版300MHz原生最终结果

首版唯一实现，标准单元存储；一份结果租约，不能同时计算两份6KiB容量。接收结果后，保持到下游完整消费并释放，具备生产/消费位置、完成控制和背压。内部M1–M10已完成并通过同源最终验收。

| 项目 | 真实结果 |
| --- | --- |
| 原生最终源 | run246 native → run249 exact10/3ns final source |
| 外框/面积 | 1040×1040µm / 1.0816mm² |
| 时序目标 | 300MHz，I/O0.8ns、output50fF，其余见批准预算 |
| 最小setup / hold | +0.429092 / +0.007988ns |
| 实际接点 | 全部386个信号位，native M10，2×2µm，内部落点 |
| DRC | native全片0；完整未修改FreePDK45 GDS deck0 |
| 最终网表功能 | 三初态各242事务/224032周期/2839953断言，连续384拍384结果传输 |
| 严格LEC | UNSAT/IDENTICAL，98886输入/98892输出全部匹配，差异0 |
| 最终文件 | Verilog、SDC、DEF、ODB、SPEF、GDS及逐文件大小/SHA见[原始交付索引](final-native.json) |
| 完整原生几何 | run256真实wire/via/PG/instance-pin/OBS与DEF RECT导出，原ODB不变 |

[真实原生版图预览](../../review-20261028/t-preview-0055/transaction6k.png)。[交付/完整几何回执](../../review-20261028/t-delivery-0049/index.json)，[独立四门证据](../../review-20261028/checkpoint-20261029-0045/index.json)，[严格LEC](../../review-20261028/t-lec-0015/index.json)。服务器大文件均位于批准项目目录，原始索引给出完整路径；没有上传大数据库到Git。

全部接口run261的P2几何也已通过：386位同时连接，DEF/ODB三次真实读回、joined GDS所有原生层XOR0、真实新增M10金属负例拒绝、新层宽度/间距/切孔/包围检查通过。[P2原始三报告](../../review-20261028/t-p2-0112/index.json)。257/260的检查失败及259只读定位均保留，没有省略空层或放松整数DBU规则。

[全386位实际几何图](interface/all-ports.png) · [16位写接口](interface/write-data16.png) · [16位读接口](interface/read-data16.png) · [输入/生成器/图文件SHA](interface/plot-manifest.json)。灰色仅表示原生宏边界；图取自真实DEF/ODB几何，已经独立GDS精确比对，未重画宏内布线。

全测试外框1120×1120µm，每根引出376µm，总长145136µm；via10=386/via11=196。简化模型每线base58.4270fF/high87.6405fF，全部386根线的base电容超过原48fF线预算，须单列同源接口负载/时序测试。制造、完整12层工艺、组合时序及层次Lib/候选LEF覆盖资格不从本页取得；五宏整体仍未完成。

新增[实际输出负载敏感性](../../review-20261028/load-0200/README.md)：50/60.427015/89.640522fF均通过，最小setup分别+0.429092/+0.422594/+0.404473ns、hold均+0.007988ns。原最终ODB/SDC/SPEF及全部文件保持；每个点包含完整端点、电气、RC覆盖、实际小电路精确序列化及错负载负例。仅集中输出C，不包括输入/clock线、串联R、耦合或远端驱动；组合接口300MHz仍未取得资格。
