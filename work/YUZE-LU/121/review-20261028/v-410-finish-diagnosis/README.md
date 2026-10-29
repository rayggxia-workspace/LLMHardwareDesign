# V410真实finish诊断：未通过300MHz

Refs #121 / PR #122。run410 / job93585 / node16，2026-10-30 04:46 CST自然COMPLETED/0:0。源33bb0916943a72f5b07860d89a24d088cf6e893c，归档ec978042c42931a8b15527588ea9dfa2f1c95683108d26111345158b6c27da26。23份原始文件大小/SHA、309源Git blobs与远端SHA、归档/manifest核验见verification.json和index.json。

实际全六阶段、RCX557041 nets、提取后VDD/VSS连接完成，5_route_drc.rpt为空；流程内最终LEC51206输入/51195输出、diff全0、UNSAT/IDENTICAL。HOLD_SLACK_MARGIN0.080ns、4984时钟网none实际读回。以上不能替代独立验收。

最终setup WS −0.125095ns/TNS −11.2002ns、381违例；hold WS +0.0302328ns/TNS0、0违例；max_cap1、max_slew0。标准单元面积711369um²（不混同含filler总面积），die1250×1250um。实际max cap wire186337/Z：Limit242.31、Cap400.53、Slack−158.22，单位保持原始报告口径。

第一max路径low_product[2][33]到output_mem[83][21]；第一min路径cmd_data[43]到b[1][11]。完整路径和实际input.v映射见path-source-mapping.json，未以顶层FF名字猜测功能。410不接收；411/93599已实际运行独立检查，结果另收。后续N_MERGE流水修复需新源全部测量和最终验收，不转移此处资格。
