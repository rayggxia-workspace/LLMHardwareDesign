# V493实际最终报告：setup拒收

Refs #121 / PR122。实际493/93618全六阶段自然结束；24份原始报告/配置、311份归档源Git blob与远端SHA逐一核验、receipt输入及已采输出SHA核验，详见index.json。

最终setup WS −0.0538716ns/TNS −0.470731ns，hold WS +0.0494002ns，maxcap/maxslew均0。1250×1250µm外框、最终标准单元面积715077µm²。RCX提取558801 nets/3187793 rsegs/8307387耦合电容。内部严格LEC为UNSAT/IDENTICAL，所有diff0/1 inputs/outputs为0；不能抵消setup拒收。

实际最差路径为operand_reduce_mask[0]到stat_block_sq[67]，对应最终报告及综合网表原始cell映射见path-source-mapping.json。该源未通过300MHz；494独立最终检查继续，495接口等待真实资格。没有从旧476/477转移物理资格。
