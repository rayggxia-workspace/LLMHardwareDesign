# S：16KiB工作存储宏，新版300MHz最终结果

唯一基础实现：1024×128bit、16KiB有限工作空间、单1RW端口、访问控制和输出背压。使用标准单元构成存储，不称为SRAM宏。连续读取无背压4096字/4096拍已由最终网表验证。

| 项目 | 真实结果 |
| --- | --- |
| 最终源 | 280 fresh修复后finish → 280独立四门/最终文件/完整原生几何 |
| 外框／外框面积 | 1610×1610µm／2.5921mm² |
| 有源／物理专用单元面积 | 1068582.648／1392832.392µm² |
| 最小setup／hold | +0.687419／+0.012282ns |
| 接点 | 273个真实2×2µm M10信号接点 |
| DRC | 原生全片0、完整未修改FreePDK45 GDS deck0，含天线和全部原生间距 |
| 最终网表功能 | 三初态各98424检查；1024地址、20000随机周期、连续读取和背压覆盖 |
| 严格LEC | 262545输入／262532输出全匹配，diff0，UNSAT/IDENTICAL |
| 最终文件 | [Verilog/SDC/DEF/ODB/GDS/SPEF位置、大小与SHA](final-native.json) |
| 完整原生几何 | [原ODB保持、wire/via/PG/pin/OBS和全部DEF RECT](native-geometry.json) |

[实际GDS全图](block_v1_s16k.png)已查看，图SHA及来源见[图像绑定](image-source.json)；[真实接点](pins.json)与[via10落点及负例](m10-access.json)均由最终ODB读回。原生1610µm外框图不替代全部端口上层布通图。

原258独立原生M2 spacing失败保留。280仅在声明同网处追加0.1×0.03µm RECT，非目标DEF字节完全相同，随后新fill/finish/RCX及全部新门通过；没有规则排除、时序例外或网表功能变化。完整几何独立解析并补齐这唯一normal-net RECT，原ODB保持。

[37份实际原始文件及同源核验](../../review-20261028/s-final-0610/README.md)记录最终源48da2735…、DRC e33ecc55…、交付55a93ad7…和几何78e58311…绑定。大数据库留在授权服务器，索引提供精确位置。

292/93044已完成本宏全部273端口P2/baseπRC；highπRC142输入cap失败，297逐端口base/high输出C通过，完整结果见本页末尾。新增M11/M12、12层工艺、层次Lib或全阵列资格不由原生通过自动获得。

实际M10接点图：[pins.svg](pins.svg)。全部273端口同时引出的实际P2几何及16位细图见[interface-plots](interface-plots/plot-manifest.json)，通过原生全掩膜XOR0和新增M10负例；图不代表负载或RC已合格。1690²µm测试外框包括40µm halo，原生1610²µm不变。

边界πRC实际结果：base全部端口通过，setup/hold+0.586439/+0.012282ns，电容裕量仅+0.017889fF；high有142电容违规，最差−44.113152fF，故不合格。见[完整回执](../../review-20261028/s-boundary-rc-0627/README.md)。逐端口输出C修订297已完成：base/high均通过，setup分别+0.662945/+0.636128ns、hold均+0.012282ns，见[实际载荷](../../review-20261028/s-output-load-0629/README.md)。
