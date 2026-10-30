# V 原生几何交付

2026-10-28 CST，Refs #121。只读导出已验收最终ODB，源SHA为`4280498654d2ada1f1910008240c0b09b27d37ffe318e30a5f8aa8591f967c94`，原数据库及M1–M10未修改。

[完整文件索引](five-macro-geometry.json)列出wire/via、PG、实例pin及OBS占用，文件保存在授权服务器，1586330086B，SHA-256为`588e843c08d615ea543d11f920dc44bf688b6e5995b687cf20e45ca9406833f9`。本地仅保存小型文件及索引。TSV保留net alias，OBS表示禁布区域，不作为金属导体。

实际包含4509260条wire、13202952条wire-via、6262036条instance-pin、355个block-port矩形、956条供电形状、312480条供电via及2283551条instance-obstruction。[RECT独立补全](native-rect-completion.json)绑定最终DEF `fe0115368b4b79f600fdf0a2a4b43b01ea60bef6ef9c4cdf2fb4658cde428fd1`，普通网络RECT共0处，逐矩形多重集一致；不只依赖安装版路径迭代器。

[M10底部几何合同](m10-access.json)包含277个真实signal pin、net身份、DBU坐标，核对0.6µm via10 cut及0.1µm底部enclosure可放入既有接点，三个负例通过。只证明底部几何容纳，不证明上层布线或via10/11电气参数。

`candidate.lef`为安装版OpenROAD只读导出；abstract coverage、通用层次Lib及M11/M12系统资格仍为false。[接收回执](receipt.json)SHA-256为`641354363f136d82442da03317dc130fb7b173e32b13971c44fb39925ae1eb65`。最终单块四项验收与图像见[交付入口](../README.md)。
