# V281独立物理门拒收

Refs #121 / PR #122。V270原生流程通过不能覆盖本拒收。281的physical-v返回失败，真实STA有9397项setup、4项hold、12项电容、3项slew违规；最差setup −2.166809797ns、hold −0.006283ns。PG、全部输入连接、层数、真实M10接点及寄生覆盖检查通过，但不能覆盖时序/电气失败。

最坏路径源DFF $auto$ff.cc:337:slice$498452的Q=offset[1]，目的DFF $auto$ff.cc:337:slice$457216的Q=output_mem[6][16]。同一最终网表只读定位，实际timing.rpt和报告SHA保留。逐元素total逻辑复用了依phase选择的mul_b，将无关回放offset选择接入逐元素结果路径。修订先分离point_b，仅逐元素total使用；共享乘法阵列及其他phase仍使用mul_b。P_WRITE下原mul_b与point_b相同，不添加数值/容量/周期例外；新源数值、映射及随后物理证据仍需实际执行，修复尚未授予通过。

281其余DRC/功能/严格LEC按真实依赖继续收尾，不因物理失败取消已开始工作；delivery-v/geometry-v已按真实失败阻塞。S/R分支不挪旧V资格。原生270和281源/失败报告全部保留。

index保存17原始文件及实际捕获时间；verification核验14个稳定输出绑定。失败时Python traceback在worker finally已写receipt后追加到node-queue-child.log，receipt里其SHA是空文件；完整实际日志由index新SHA绑定，并显式记录差异，不把两者描述为相同。所有业务输出仍须严格匹配，原始日志/报告空白不归一化。
