# R 原生几何交付

2026-10-28 12:00 CST，Refs #121。只读导出已验收的同一最终ODB，源SHA为`736d8e10d63c134b3ea81fb7eb34d69cd947c3d5be456f09240800d5459305e1`；有源电路及M1–M10未修改。

[完整文件索引](five-macro-geometry.json)列出原生wire/via、供电、实例pin及OBS的完整占用文件，保存在授权服务器，2983490452B，SHA-256为`5f46edf4ffd5fbb218945b158409b8bb77d3c2e9f25127d5dfc99d140ae38c2e`。TSV保留net alias；OBS为禁布信息，不是导体。本地保存索引、小型几何及回执。

实际导出6832019条wire、21130425条wire-via、12663068条instance-pin、400个block-port矩形、1495条供电形状、767745条供电via和6748269条instance-obstruction，包含原生metal1–10及via1–9。[RECT补全](native-rect-completion.json)独立读取封存DEF的全部普通网络RECT，共0处；逐矩形多重集一致，原ODB哈希未变。不能只凭安装版路径迭代器声称几何完整。

[M10底部几何合同](m10-access.json)含278个真实signal pin、net身份、DBU坐标及0.6µm via10 cut/0.1µm底部enclosure。只证明底部enclosure能放入既有0.8µm接点，三个负例检查通过；不证明上层布线或via10/11电气参数。

`candidate.lef`由安装版OpenROAD只读导出；abstract coverage、层次Lib和M11/M12系统资格仍为false。[接收回执](receipt.json)SHA-256为`119c0d1241f9bad5ff9530f339394e051d0585540a4a5c7ae7b5517a41620eca`。原最终DRC、物理、功能和严格LEC见[单块交付](../README.md)。

[232终态快照](../../../results/run232-five-macro-115939/index.json)记录92620自然COMPLETED/0:0、11分27秒，复用225原队列/源归档/共享claim，仅接续R几何，没有重跑已完成S。旧V222依赖不作最终V入口，V的有效几何是228。
