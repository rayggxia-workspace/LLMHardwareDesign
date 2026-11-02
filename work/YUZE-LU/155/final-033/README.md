# Issue155 整块 SRAM S 最终工程证据

[正式报告](../../../../docs/S_SRAM_FINAL.md) / [Issue155](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/155) / [PR158](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/158)。

95227完整四银行16KiB S综合、布局布线、RCX及全量原版GDS DRC=0；95229独立审计/最终实际模型三初态功能、95230严格四银行全pin符号边界等价及错误地址负例、95233严格所有输入/日志/六文件SHA汇合全通过。setup +0.097132ns、hold +0.007969ns；cap/slew/fanout违规0。原标准单元S不变。

[source-binding-index.json](source-binding-index.json) 为机器入口，含实际源bfe44f86/汇合源50bcee00、所有实际源归档Git原始字节核验及文件SHA/远端位置。[验收原件](evidence/acceptance.json)、[原始全DRC](evidence/whole-gds-drc.lyrdb)、[审计](evidence/audit.json)、[功能](evidence/function.json)、[形式](evidence/formal.json)、[版图](layout.png)、[ZIP交付回执](delivery.json)。原始报告/日志按远端字节实收，不改换行或trim；较大六文件、银行视图、完整信号网表、实际源归档和历史源bundle在授权远端ZIP及本地镜像。

controls保存实际井表示正/负控制。它们不独立授予资格，当前033所有掩模一致性及完整原版deep DRC仍须通过，已由本次最终汇合实际重验。267×4父级实际接点及同网绑定、复合路由LEF和原生267pin读回在implementation和acceptance中。先前反例/失败保留continuation019–021，不转用旧单项结果。

限制：TT/1.1V/25C、银行原理图表征、内部wire PEX未实现、上游HL复制LH；最终模型默认延迟慢时钟功能验证，300MHz来自独立提取RC的STA；非系统/多角点/foundry signoff。工程验收true，独立审查/合并false。Issue in_review，不自行合并。登记PR5 pending，board未配置、看板unverified/同步pending，处理人待指定。
