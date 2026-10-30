# 493 最终网表的独立严格等价检查

Refs #121 / PR #122。494的严格同源LEC已通过：全部输入/输出匹配，diff0/1输入/输出均0，实际求解结果为UNSAT/IDENTICAL。16份原始文件、8份服务器大文件SHA索引、311份源Git blob和receipt输入/输出已核验。

本证据绑定513中三初态功能通过的同一份最终源，final-source receipt SHA为`70af2e70e7301805668c4bd9158cf2b66c5030b02d58bb389b9b01fd303a7513`。493的setup与494的原生DRC仍失败；本检查不抵消物理失败，不转移到当前505/507实现。

实际路径、采集时间、SHA和绑定结果见[index.json](index.json)。大文件保留授权服务器。
