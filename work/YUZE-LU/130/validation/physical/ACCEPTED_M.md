# Issue130：M 的已接收原生候选

2026-10-29，Asia/Shanghai。[Issue130](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/130)／[PR132](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/132)。仅本侧任务的新 M；S 继续验收，不能据此宣布整个任务完成。

| 项目 | 实际结果 |
| --- | --- |
| 结构 | 64 个 S8 乘法器，完整归约／累加／S16 分解和合并，A128／B512 独立输入；同一套 RTL |
| 原生尺寸／金属 | 980×980µm；固定 M1–M10 |
| 实际 active 单元面积 | 405283.452µm²；另有 476192.668µm² filler／tapcell 等 physical-only 单元，不能将 mapped 面积当作最终面积 |
| 信号接点 | 867 位；全部为宏内部 M10 的 2×2µm 接点；实际 ODB 逐位核验 |
| 约束 | Nangate45 typical；300MHz，0.1ns 时钟不确定度；输入 BUF_X2/Z，输出 50fF；I/O max0.8ns/min0.2ns |
| 最终提取 setup／hold | +0.047354788ns／+0.009898194ns；所有实际数据端点均检查 |
| 电气／RC／连通 | cap、slew 违规均0；RC覆盖、驱动、PG、放置、接点全部通过 |
| DRC | 原生 whole-chip 报告为空；完整未修改 FreePDK45 GDS 规则 total_items=0 |
| 最终网表功能 | 三个硬件初态均通过，每次191485检查／160639拍 |
| 严格等价 | 映射到最终物理网表的全边界严格 LEC 通过；显式 UNSAT／IDENTICAL，无未匹配边界 |

实际源为 `repair21/results/repair-m-08`，修复代码 commit `88ec748bddc2632aa3344a6ca3e55c38acbd9d44`。其最终文件封存于 `qualify24/results/source-m`。物理／功能／严格等价分别为93326、93327、93329；完整DRC为qualify25/93332；93346验证四门同一source receipt后封存交付。完整DRC运行约48.6分钟，没有跳过FEOL或天线检查。

服务端共同前缀：`/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/`。上述目录完整名称依次为 `issue130-m-feed-repair21-20261029`、`issue130-m-feed-qualify24-20261029`、`issue130-m-feed-qualify25-20261029`。

最终六文件和布局图：`issue130-m-feed-qualify25-20261029/results/delivery-m/native/`。
压缩包：`issue130-m-feed-artifacts26-20261029/results/bundle-m/block-feed-m-native.tar.gz`，263331897字节，SHA256：`2a754fb462120efe19573aa33438ab7c157f6ac1b9fe00252de121a3e79691a2`。

本地已下载并逐个校验32个成员，未改动原文件：`D:/Data/LLMHardwareDesign-issue130-runtime/deliverables/M/unpacked/native/`。包含 `6_final.gds/.def/.odb/.v/.sdc/.spef`、`pins.json`、`layout.png`，检查回执位于相邻 `evidence/`。本地 `received.json` 保存全部六文件SHA。

仓库保留 [29个原始小文件字节档案](accepted-m-receipts.zip) 和 [可核验索引](accepted-m-index.json)。执行：

```powershell
python -X utf8 project/experiments/block_feed_v1/verify_evidence.py
# 新目录首次解包；已有 unpacked 时只核验，不覆盖原始文件：
python -X utf8 project/experiments/block_feed_v1/verify_bundle.py D:/Data/LLMHardwareDesign-issue130-runtime/deliverables/M
```

这里“合法”指上述明确合同下的原生叶子候选。尚未取得层级 Liberty／abstract coverage 资格，也未取得 M11/M12 整系统互连或实际新增金属工艺制造签核。50fF输出合同不能代替任意长度上层线的负载验证。旧失败候选和父任务旧宏均未转移验收资格。

实际完整原生几何导出93347亦已通过，ODB保持原字节，完整DEF矩形覆盖与三项错误接点控制均通过。原始导出754768611字节留在服务器同目录`results/delivery-m/geometry/`；本地`D:/Data/LLMHardwareDesign-issue130-runtime/deliverables/M/geometry/candidate.lef`已按原报告SHA核验，142047字节。此LEF仍为候选abstract，未宣称abstract coverage／层级时序通过。

完整几何的8个小型原始文件另存于 [accepted-m-geometry.zip](accepted-m-geometry.zip)，包括候选LEF、实际pins、接入负控制和原生矩形覆盖回执；索引同时绑定最终ODB和原交付receipt，不将几何导出等同于上层互连验收。
