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

M11/M12全部接口引出是独立验证。run257保留严格GDS检查失败记录，经run259定位空区域惰性语义后由run260继续；尚未宣布P2通过。额外互联负载、组合时序、完整12层工艺、层次Lib/候选LEF覆盖资格均不能从本页自动取得。五宏整体仍未完成。
