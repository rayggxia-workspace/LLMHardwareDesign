# V337实际CTS路径诊断

原337/93180继续正常route。4_cts_final.rpt最差setup−0.41ns、TNS−868.39ns；路径由输入网表原单元映射到group_unit.sqrt_mode与组级余数（twice_remainder[29]是优化别名）。原始8文件、输入网表大小/SHA和映射见index/path-source-mapping.json。

只读取已完成CTS的报告与原input.v；未启动EDA、未改任何布局/网表/寄生，不把中间CTS当作最终提取STA。后续尝试完整130bit分组减法，须全输入SAT和全部新源验证；诊断本身不赋予300MHz资格。
