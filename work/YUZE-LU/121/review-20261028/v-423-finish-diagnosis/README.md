# V423 最终流程完成，时序仍不接收

Refs #121 / PR #122。93602/node16已自然COMPLETED/0:0，源77952fc6/归档4cfad28e。23份原始报告/回执与309个归档源Git blobs已核验；完整原始路径及实际input.v端点映射见path-source-mapping.json。

最终setup WS −0.0875939ns、TNS −1.35826ns、37违例；hold WS +0.0700393ns、TNS0、0违例；max_cap2、max_slew0。stdcell面积716102µm²，die1250²µm。完整RCX560513 nets；内部最终LEC53254/53243、diff0、UNSAT/IDENTICAL。六阶段通过不替代上述失败。

首个max路径由function_sent[0]经回放选择/减法夹紧到function_unit.x1[13]（即函数输入寄存器，不能误称LUT内部流水失败）。424/93603已自动启动独立物理/DRC/最终三初态功能等；原任务正常收尾。新候选在回放选择与完整S33减法之间增加寄存，须新数值、命令周期、预算及最终布局布线验收；不继承423资格。
