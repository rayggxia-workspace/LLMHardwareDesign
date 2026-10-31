# V306 placement 真实路径诊断

Issue #121 / PR #122。314/93070自然COMPLETED/0:0；源a5471da98433ae6b026fe0894da2dce79c228d25，archive d0834a674d888ae305a9be3215b02c850d98f2e68f32a182f34795c0d1a7af3a。只读306已完成的3_5_place_dp.odb，不重跑或改写原布局。

`index.json`封存11个原始小文件的字节数/SHA及实际终态；7个稳定输出与receipt绑定。实际最差setup−1.713852644ns，输入cmd_index[0]到product[6][64]。`path-source-mapping.json`将真实网表端点映射到product寄存器，不将输入端口误当FF。

执行成功只是获得诊断；placement估计RC/理想时钟不能替代最终寄生时序。原始ODB/SDC/网表/配置/库/setRC前后SHA相同，306继续CTS。原报告不截改、不豁免路径；下一步分开操作数选择和乘法，并对逐元素结果分级，见对应决策文档。
