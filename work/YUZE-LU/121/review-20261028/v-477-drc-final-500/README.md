# 旧476最终版图完整DRC终态

Refs #121 / PR122。实际477/93614自然FAILED/1:0；12份原始文件、1份大GDS远端大小/SHA索引，311份源文件与归档Git blobs逐字节核验，receipt输入/稳定输出及498的同一final-source精确绑定。

- 原生全芯片DRC：472项，Metal Spacing 470、NS Metal 2。
- 完整未删改FreePDK45 GDS deck：129类别、2项，均为METAL9.2；具体坐标与边对见[index.json](index.json)和原始full-deck.lyrdb。
- 原deck SHA为4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147，未排除规则、未豁免。两种检查分别失败，不能互相抵消。
- 队列child日志在receipt封存后自然追加AssertionError，原始空日志SHA与追加后SHA分开记录；其余输出匹配receipt。没有重新运行EDA。

旧476/477最终setup负裕量和maxcap2的物理拒收保持；498功能与499严格LEC通过不能改变该结论。这里只封存旧源b3471a05ed1761944a4523d5cae17ee858720f87的失败证据，不转移到当前493，不继续修复已被替代的旧版图。当前493必须取得自己的全部最终物理、功能、严格LEC、交付、几何与接口结果。
