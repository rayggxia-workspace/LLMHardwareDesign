# V：向量计算宏，300MHz 原生最终结果与待完成接口

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
| 当前待完成 | 806 全部端口引出、读回对照、有限上层 RC，以及接口总览/数据局部图 |

[最终六文件位置、大小与 SHA](final-native.json)包括 Verilog、SDC、DEF、ODB、GDS、SPEF，已对授权服务器实际文件核验；大数据库保留原路径。[818 独立采集索引](../../review-20261028/v-805-delivery-geometry-818/index.json)封存 42 原始文件、7 个实际服务器大文件 SHA、364 归档 Git 源及 41 个回执输出绑定，全部来自同一最终源 `9ef42c0f…`。[820 核验记录](../../review-20261028/verification-820.json)保留本地采集器路径分隔符错误及修复事实，该错误未改动远程 EDA。

[完整实际 GDS 图像](block_v1_v.png)已通过 `view_image` 查看，[图像来源与查看记录](image-source.json)绑定最终交付回执；图像不能替代逐项 DRC 或详细 pin 图。[277 个 pin 坐标/形状](pins.json)、[M10 接入形状与负例](m10-access.json)、[完整原生几何索引](native-geometry.json)可查。原生 pin 方向与普通/特殊连接位于原始 `native-pins.tsv`，完整 wire/via/PG/OBS 数据位于服务器 `source-occupancy.tsv`，路径和 SHA 均在几何索引中。

当前只证明原生计算宏及上述交付结果。806 尚未完成，V 总验收仍为 false；候选 LEF 抽象覆盖、层次时序库和完整 M11/M12 系统资格仍未授予。旧 767 的完整 GDS 失败及旧资格保持历史记录，不移用于当前源。Refs #121 / PR #122。
