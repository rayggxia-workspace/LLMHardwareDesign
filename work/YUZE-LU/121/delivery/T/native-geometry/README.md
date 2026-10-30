# T 原生几何交付

2026-10-28 03:07 CST，Refs #121。只读读取已验收的同一最终ODB；有源电路和M1–M10均未修改。

[完整文件索引](five-macro-geometry.json)列出原生布线/过孔、供电、实例pin、master及block OBS的完整占用文件（保存在授权服务器，664909090B）及SHA。TSV按net alias保留电气身份；`instance-obstruction`和`block-obstruction`是禁布信息，不应当作金属导体。

[RECT独立补全](native-rect-completion.json)从封存最终DEF提取全部普通网络RECT，共0处。安装版路径迭代器会漏RECT，因此不能只使用历史`../geometry/`报告；本结果补全后重新逐矩形多重集核对，原始ODB哈希不变。

[M10底部几何合同](m10-access.json)含386个真实signal pin、net身份、DBU坐标和0.6µm via10 cut/0.1µm底部enclosure。这里只证明bottom enclosure容纳于既有M10接点，不证明上层布线、via10/11电气参数或完整M11/M12系统。

`candidate.lef`由实际安装版OpenROAD只读导出；abstract coverage、层次Lib和M11/M12系统资格仍false。原最终DRC/STA/功能/LEC资格见[单块交付](../README.md)。
