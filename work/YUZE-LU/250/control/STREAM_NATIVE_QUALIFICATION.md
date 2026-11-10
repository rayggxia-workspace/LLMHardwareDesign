# 固定 staging 窗口与真实 COPY 的原生闭环

Refs #250。`p_native_stream_record_executor.sv` 是独立候选，保留已验收的 contig executor、原 A frontend 和 serial guard。typed provider 仍拒绝 service2；本回执没有把 K128/256 的 record 发生器写成 whole projection/FFN 外层已实现。

| Slurm | 真实覆盖 | 结果 / c64 6×10分配的实耗 |
|---|---|---|
| 102343 | 固定256B S窗口；完整key/gen16/K/session/ticket隔离旧prefix；LOAD背压、覆写S、真实M数值 | 18 PASS；9s elapsed，20.612 CPU-s |
| 102346 | 加入 early-cancel 后同正例回归 | 18 PASS；9s，20.675 CPU-s |
| 102347 | COPY只提供4个S128字时取消；真M CANCEL/DRAIN/DROP，然后同上下文重做K256 | 18 PASS；8s，20.546 CPU-s |
| 102353 | 真实U/P四银行S、fallback量化、128bit Header/RX、版本化COPY、A→M→S | 18 PASS；9s，22.470 CPU-s |
| 102359 | 真COPY在prefix4处halt，源/link/S/A/M排空，RX取消释放，再同owner/context数值复用 | 18 PASS；8s，22.000 CPU-s |

102353 每 trial 有八个限定范围、18个 M record、315次W64请求和返回、24个真实结果S128 ACK。十二个K128输入由U的S32源经真实量化器计算 max/shift/RNE，16个真实写ACK后才能形成Header。Header和COPY共用原128根数据线；总24个Header flit、192次COPY源读、192个目的写ACK。P目录的shift来自实际RX，A读取受对应COPY的真实ACK prefix约束。

数值输入构造明确：整数oracle原来使用 `Aold × scale × 2^8`；本回归给U真实S写入 `S32=Aold×256`，量化器实际选择shift0，输出A16=`Aold×256`。两者表达同一数值，M按真实shift0运行，与独立Fraction/RNE整数oracle逐位一致。shift不是host直接宣告就绪；完整模型的真实上游producer仍要另验。

LOAD证明由真实16次S响应形成，携带完整key、COPY gen16/session/ticket/K以及独立A slot/gen/shift。它是现有前端的一份有限保持回执，没有新增FIFO。成功回执和COPY/link/S排空后，RX释放S窗口，此时A内部槽仍live。随后真实覆写192个staging S字，原A仍能正确完成所有M消费；`source_reads_drained`与A FREE始终区分。

102359 中，COPY halt后仍保持已offer的VALID直到接受，真实返回与目的ACK排空；未形成完整A的前端返回匹配的error LOAD terminal。P正常取消让当前唯一W record完成FILL（最多1088/1152B），再用真实bank/gen/record发CANCEL与DRAIN，清理真实RF上下文。没有虚构EXEC/INPUT/ABORT或SACK。然后相同Akey/RFowner/context重做K256正确。每trial合计51个W64请求和返回、36次A读（取消4+重做32）、2个最终S ACK、4个range票退役。当前正常取消会继续取完这一个W record，成本明确保留；未注册partial W截断和其字节计数。

接口及位宽见 `project/experiments/shared_x_control/p_native_stream_contract.json`。额外current-window元数据86bit，early-cancel会话/标志67bit；无新增私有SRAM、A payload或结果FIFO。量化器、Header TX/RX、COPY113bit身份、原有每P16B保持和S仲裁都要另计实际有源面积。宽身份只是局控内部总线，不能直接扩成宏或母控大量pin。

完整源/向量/日志/CSV/银行模型存于run61–68原SHA的≤1MiB exact parts，所有失败保留（102341脚本误名、102350/352严格测试端告警，未绕过）。`followup-*.json`记录实际CPU及原始路径，`sacct-61-68.txt`记录完整accounting。功能时钟10ns，不是300MHz物理验收。

仍未覆盖：typed service2与完整outer、fullK11008流式执行、三P吞吐、流式输入与真实MC/全局DMA同次联合、五类provider、COPY16bit通用rearm、紧急raw ABORT恢复、布局布线、能耗/token/s。COPY wire generation仍是16bit，不能靠改名32bit掩盖ABA；耗尽须先真实namespace协调排空与rearm。

后续固定 stream COPY 为不预取下一源字的配置（源737784597，root a424fd244 等价）：P也是COPY源时，原预取会让下一源读响应堵住旧目的写ACK，形成同S有序响应环。现在只有16B hold空闲才offer下一源读，无新增payload。旧单元参数默认1保持历史资格，stream epoch wrapper显式0。102370实际量化/Header/COPY/M/S 18 PASS（9s，22.586 CPU-s），102371实际中途halt/取消/复用18 PASS（9s，22.026 CPU-s）。seed1正例4997→5285周期，取消1055→1103，费用如实保留。run69–70完整源/日志/CSV/向量以原SHA≤1MiB分片保留；没有将原配置的吞吐或物理资格移交给新配置。
