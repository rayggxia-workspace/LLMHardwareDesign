# S 原生几何交付

2026-10-28 06:29 CST，Refs #121。只读导出已验收的同一最终ODB，源SHA为`de0775b46044c99879cc7907766cb7f156604677638e645f9b539348f2f417b4`；有源电路及M1–M10未修改。

[完整文件索引](five-macro-geometry.json)列出原生wire/via、供电、实例pin及OBS的完整占用文件，保存在授权服务器，1652760870B，SHA-256为`8da46f7bca053545c9da637b57337d90d59214ee3b3233d922ccd1f361f5b42a`。TSV保留net alias；OBS为禁布信息，不是导体。本地只保存索引、小型几何及回执。

实际导出3290989条wire、10392957条wire-via、7073210条instance-pin、378个block-port矩形、1282条供电形状、559020条供电via和5676458条instance-obstruction，包含原生metal1–10及via1–9。[RECT补全](native-rect-completion.json)独立读取封存DEF的全部普通网络RECT，共0处；逐矩形多重集一致，原ODB哈希未变。不能只凭安装版路径迭代器声称几何完整。

[M10底部几何合同](m10-access.json)含273个真实signal pin、net身份、DBU坐标及0.6µm via10 cut/0.1µm底部enclosure。只证明底部enclosure能放入既有0.8µm接点，三个负例检查通过；不证明上层布线或via10/11电气参数。

`candidate.lef`由安装版OpenROAD只读导出；abstract coverage、层次Lib和M11/M12系统资格仍为false。[接收回执](receipt.json)SHA-256为`9e8dd3990074a3137e571b63a78d808b795758b70e614d1e883ae2eba51d481d`。原最终DRC、物理、功能和严格LEC见[单块交付](../README.md)。
