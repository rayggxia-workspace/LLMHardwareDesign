# 按字检查产出有效性，分开报告场景通过与覆盖

Issue179 / PR180；Melodydt；2026-11-07 Asia/Shanghai。

综合前第8步沿用九个固定控制目标、64 bit ISA、单时钟及3.333333333 ns目标。扩展原生主机回放、原有恢复测试和通用控制合同测试；仅新增观察/故障注入bench，不修改控制RTL。

研究发现缓冲区级valid不足：一个单字producer不能保证声明为四字的缓冲区都已经产生。编译器改用(buffer,word)有效集；单字操作仅标word0，JOIN/RECEIVE按实际范围标记，SEND/P四字输入逐字检查。保留完整初始化的主机载体用例，增加四项负例，不通过伪造额外产出来获得长度覆盖。

覆盖以实际采样记录及原始Verilator数据为证据，区分target/case、生命周期、原生sequencer、选定转换、事件、监督状态、全局opcode及代码行。PM丢失立即复位可能在posedge观察器采到state8前结束，因此另跑独立四拍保持用例；不凭错误回执推断状态覆盖。J可验证数值clamp，但现有done接口无SAT标志，不声称其RESULT饱和诊断已覆盖。通用BIND/REPORT由真实通用夹具提供，不冒充原生配方会生成这些操作。

详细矩阵、源码/归档/输出SHA、未命中行及有限覆盖定义见project/control_matrix_v1/README.md与work/Melodydt/179/control-matrix-validation.json。测试成功不授予新增组合STA、CDC/RDC或物理资格；第9步仍需冻结综合交付。
