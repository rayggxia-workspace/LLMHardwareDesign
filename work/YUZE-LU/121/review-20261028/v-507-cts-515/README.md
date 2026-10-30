# 当前 V507 的 CTS 阶段证据

Refs #121 / PR #122。实际507/93623/node25已完成综合、floorplan、放置及CTS，进入GRT。15份原始文件、311份源Git blob与远端SHA已核对；源3e5a4c25838bb6d6e1bf2ead63ae69d0dcf2c2ab，归档bfc785a25e0a55c675d97bbee5205ac55b7c59fa1a95ebed893b46ee20ff021c，与505行为/证明/映射及506占用/有限S-V测量同源。

CTS setup WS为+0.00258504ns、TNS0、0违例；hold WS为−0.255989ns、TNS−4.46644ns、42违例；maxcap/maxslew0。实际CTS标准单元面积707193µm²。5218条时钟网的none策略逐行核验；内部LEC53478输入/53467输出全部匹配、diff0/1全0、UNSAT/IDENTICAL。

这只是CTS阶段证据，不能授予最终物理资格。后续完整布线、fresh RCX/STA、全部电气/PG/连通、原生及完整GDS DRC、最终功能/严格LEC、六文件/实际几何与全部端口仍须独立验收。旧493/494证据不转移到本源。

实际采集时间、路径、大小、SHA及全部原始指标见[index.json](index.json)。
