# 新 M 组点积 / scale-RNE 单元回执

2026-11-11，Asia/Shanghai；Refs #250 / PR251。源与复跑说明见 [w8a16_m](../../../../project/experiments/w8a16_m/README.md)。本目录是算术候选单元证据，不是完整M/局控/整模型或物理验收。

| 作业 | 执行源 | 结果 | 覆盖 |
|---|---|---|---|
| 102060 | c9bbbf63bd6daeb9faeb7c4f43038c47888a672f | FAILED 1:0，3秒 | 首次严格编译拒绝宽度和bench命名/初始化警告；未执行数值回归，六份失败日志保留 |
| 102063 | 8562afadefc9499862e7842070522f7becbf2849 | COMPLETED 0:0，10秒 | 6 seeds，24576个scale向量、13800个M输入beat、3048个M响应 |
| 102065 | a25f01c52453290dc99d75dce8a6226e498d9f9f | COMPLETED 0:0，10秒 | 6 seeds，28788个scale向量、17839个M输入beat、6526个M响应；补RNE正负tie、无效inactive scale、短beat、重试、活跃状态和背压响应复位 |

三个作业均c64同一节点分配60核、6×10并行；编译每份最多10核，单位仿真单线程，未把分配核数说成实际仿真线程数。工具Verilator5.042在ORFS容器运行；容器hash、分配、每份构建/运行日志与源hash都在不可变回收包。Verilator bind目录的执行字节hash尚未在这些作业内记录，不能补写成当时已经冻结；后续最终物理/RTL回归需一并冻结。

首次失败通过显式44bit上下界、匹配bench top及独立初始化修复，保留严格width检查；未将Wno-fatal作为修复。随后扩展有意义覆盖并重跑，而非把第一次单位通过当终点。

[index.json](index.json)记录原始远程root、源commit和3组日志/执行源共6包SHA-256。base64文件保存原tar字节（不重新打包）；完整执行源另外封包，逐项对照原manifest，不依赖新clone能否找到本地执行commit对象。生成输入向量和可执行文件保留远程，输入按seed与精确源可重建。归档提交不冒充执行提交。

离线审计逐项校验包hash、无危险路径/链接、原执行源字节与原manifest、六seed完整性、四类构建/运行日志hash及PASS。当前PASS；它不读取生成向量原始字节，不能冒充已离线数值重跑。`sacct`终态在提交归档前已读回核验。

未完成：实际checkpoint分组向量、数值head部署、16投影上下文/ACK/LC、S与权重接口、宏整合、最终网表和300 MHz物理。新单元仍是candidate。用户要求持续修复/迭代直到完整任务验收；本记录不是停工或完成声明。
