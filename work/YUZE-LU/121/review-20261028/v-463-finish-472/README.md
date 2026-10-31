# V463实际最终物理报告

Refs #121 / PR122。实际新六阶段自然结束，309归档Git blob与远端源SHA逐项核验，源36a02f4ade26171cd447e9ed91a5f9be4a5f05bd，归档2efd4206723d201b9678d0a2beff17fc59c4643058af91a271f98b384c3e0ea4。23原始文件及回执输入/已采稳定输出SHA绑定。

最终setup WS−0.0540381ns、TNS−1.32069ns、60违例；hold WS+0.025434ns/TNS0，maxcap1/maxslew0。标准单元面积715659µm²，外框1250²µm。内部最终LEC53460输入/53449输出、diff0/1全0，UNSAT/IDENTICAL；RCX559794网。详细route报告空不能替代独立native全芯片DRC。

首个setup路径从point_op[2]到point_rounded[4][127]；首个min为reset到point_count[0]。映射单元与原input.v实际端口/寄存器逐项绑定见path-source-mapping.json。物理300MHz仍拒收，独立464最终门已通过原dispatcher提交93610；不能用全流程返回0替代时序/电气接收。
