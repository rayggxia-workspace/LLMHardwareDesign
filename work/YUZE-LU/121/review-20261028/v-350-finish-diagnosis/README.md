# V350 最终提取后负时序对照

Refs #121 / PR #122。旧选定源845bf03cd935066bf209acf8bd21c789bac89b4d、归档5cec93b8838ee95ec8dd3767fda307144e761354e72183f4d81a49c74b9b8aad；9份原始快照、308源Git blobs与所有V RTL、input.v与早期GRT的SHA一致性核验，见index.json/verification.json。

实际6_finish.rpt来自fresh RCX：setup −0.11ns、TNS −11.47ns；hold报告仅舍入为0.00ns，不据此声称独立最终hold通过。最差max从offset[0]到stat_block_min[6]，源寄存器与完整路径见path-source-mapping.json；min从group_unit.numerator[91]到group_unit.digits[91]。阶段变化后关键路径不同于此前GRT的N_WRITE合并路径，不能假定修复一条即覆盖所有路径。

首个快照07:58:57 UTC（15:58:57 CST）时原生汇总尚在生成；随后终态读回见terminal/index.json。六原生阶段完成不代表300MHz通过，更不代表独立STA/DRC/功能/LEC及接口资格。当前V357需完整自己的新源链；原350自然收尾，351/352只因未分配而退休，无作业被取消。
