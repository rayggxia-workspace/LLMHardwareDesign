# V：向量计算宏，300MHz 原生最终结果与有限接口

每种宏只保留一个基础实现。V 包含八路逐元素/统计、两条独立函数 lane、组级函数单元和有限回放/选择状态；功能、精确数值域及操作延迟以[修订合同](../../../../../docs/BLOCK_V1_REVIEW_CONTRACT.md)为准。

| 项目 | 当前实际结果 |
| --- | --- |
| 唯一实现 | 576 RTL → 801 case1 单 RECT 修复 → 804 fresh RCX/final report → 805 最终源 |
| 外框 | 1260×1260µm，1.5876mm² |
| 最小 setup / hold | +0.012849 / +0.029884ns，27066 实际 timed endpoints |
| 接点 | 277 个真实内部 M10 信号位，各 2×2µm |
| DRC | 原生全片 0；完整未修改 FreePDK45 GDS deck 129 类、0 项 |
| 功能 | 最终网表 all-ones/random121/random122，各 574942 检查、425971 拍，通过 |
| 严格等价 | 同源最终网表 UNSAT/IDENTICAL，差异输入/输出全部 0 |
| 原生几何 | wire/via/PG/instance-pin/OBS 全部导出，400 原生 DEF RECT 精确补全；原 ODB 保持 |
| 全部端口引出 | 806/94105 全部 277 位同时接通，三次 DEF/ODB 读回一致，合并 GDS 原生各层 XOR 0 |
| 有限接口时序 | 三项输出负载及 base πRC 通过；high πRC 三处输入电容失败保留 |

[最终六文件位置、大小与 SHA](final-native.json)包括 Verilog、SDC、DEF、ODB、GDS、SPEF，已对授权服务器实际文件核验；大数据库保留原路径。[818 独立采集索引](../../review-20261028/v-805-delivery-geometry-818/index.json)封存 42 原始文件、7 个实际服务器大文件 SHA、364 归档 Git 源及 41 个回执输出绑定，全部来自同一最终源 `9ef42c0f…`。[820 核验记录](../../review-20261028/verification-820.json)保留本地采集器路径分隔符错误及修复事实，该错误未改动远程 EDA。

[完整实际 GDS 图像](block_v1_v.png)已通过 `view_image` 查看，[图像来源与查看记录](image-source.json)绑定最终交付回执；图像不能替代逐项 DRC 或详细 pin 图。[277 个 pin 坐标/形状](pins.json)、[M10 接入形状与负例](m10-access.json)、[完整原生几何索引](native-geometry.json)可查。原生 pin 方向与普通/特殊连接位于原始 `native-pins.tsv`，完整 wire/via/PG/OBS 数据位于服务器 `source-occupancy.tsv`，路径和 SHA 均在几何索引中。

[全部 277 位接口总览](interface/all-ports.png) · [16 位输入局部图](interface/input-data16.png) · [16 位输出局部图](interface/output-data16.png) · [图像来源与 SHA](interface/plot-manifest.json)。三张 PNG 均已查看，来自真实 DEF/ODB/GDS 对照的几何；灰色宏内部未在接口图中重画。[821 原始接口证据](../../review-20261028/v-806-interface-821/index.json)封存 29 原始文件和 1 个实际服务器大文件 SHA，精确绑定当前 805 交付及全信号几何。

本例测试外框 1340×1340µm，每侧 40µm halo 已计价；总线长 125216µm、via10=277、via11=133。每线 base 电容 69.615–70.858fF，277 位均超过原 48fF 线预算；不能以几何接通授予时序资格。[822 核验及五任务并行证据](../../review-20261028/verification-822.json)保留原始数据。

806/94105 已自然完成，`COMPLETED/0:0`，用时 12 分 17 秒。[823 实际负载/πRC 证据](../../review-20261028/v-806-load-rc-823/index.json)封存 119 原始文件、12 个实际服务器大文件 SHA、364 归档 Git 源及全部回执输入/输出绑定。实验完成和实际 STA 通过分开记录：

| 有限场景 | 实际 STA | 电容 / slew 违规 |
| --- | --- | --- |
| 全部 133 输出，原批准 50fF 负载 | 通过 | 0 / 0 |
| 全部输出，base 线电容加 2fF 接收负载 | 通过 | 0 / 0 |
| 全部输出，high 线电容加 2fF 接收负载 | 通过 | 0 / 0 |
| 全部 277 输入/输出/clock，base 串联 R、两端半 C 的 π 模型 | 通过 | 0 / 0 |
| 全部 277 输入/输出/clock，high=1.5×R/C 的 π 模型 | **失败** | **3 / 0** |

五个场景的 27066 实际 timed endpoints 最小 setup/hold 均为 +0.012849/+0.029884ns。high πRC 失败端口为 `cmd_index[4]`、`cmd_valid`、`cmd_index[7]`，电容分别为 134.650940、123.723190、122.657120fF，超过 121.154999fF 限值。失败未豁免；没有放宽约束、修改原生电路或另造裕量实现。仅检查输出集中负载无法发现这类输入限制，因此不能拿三项输出通过替代全部端口 πRC 结果。

[824 逐项核验](acceptance.json)接收本版原生 300MHz V 宏和声明的有限 base 接口场景。high 敏感性保持失败，候选 LEF 抽象覆盖、层次时序库和完整 M11/M12 系统资格仍未授予。旧 767 的完整 GDS 失败及旧资格保持历史记录，不移用于当前源；R 尚未完成，五宏整体仍进行中。Refs #121 / PR #122。
