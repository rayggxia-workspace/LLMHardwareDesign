# #219 的请求阶段交接

## 图、页和 KV 使用同一计划

`request_phase_bindings.py` 读取已封存的图部署、同计划 Algo2 交接、KV 指令回执、词表退休计划和 Gather 局控记录。它读回 Algo2 交接，按图摘要核对各阶段，展开有序页号和页世代，并核对每条 token 依赖的前一页、下一页局控镜像和目标 SRAM 字。阶段表只包含静态约束和地址。运行时 token 与 KV 回执仍从各自服务取得。

Qwen2.5-3B 样本产生 128 条阶段记录和 127 条 decode 索引交接，覆盖 184,927 页。prefill 的 512 个位置需要 73,728 次 KV 提交，后续每步各 144 次。阶段表 JSON SHA-256 为 `0e13dfe33b6fe1f28c907251f6a82e5e833cbce6160c5c1488b4d8c58befcd01`，TSV 为 `ab7b13a4028861f48668c1ccae067a07adfada133d3a48ff76935903e9488b67`。运行配置来自图与编译产物。验证覆盖当前样本，其他模型的 lowering 和执行需要各自的回归。

## 从退休到 U0 索引提交

现有 `native_request_sequence` 在最后一页、KV 和词表 token 均成功后允许退休。后继页使用这一结果作为 `page_input_token`。`native_request_index_gate.sv` 捕获页世代、索引字地址和 token。MC 通过 CALL 启动已安装的 Gather 页。U0 的 LINK_RECEIVE 预留出现后，写入器在约定的 16 B 字中写入 token。对应 ACK 返回后，局控继续读索引。过早完成、错误预留或写确认错误会把该页标为失败。失败后需要复位联动控制器。

远端 111683 通过页/退休控制器和索引门控的协议回归。正常、延迟确认、错误世代、过早完成和错误预留得到预期结果。111657 将请求控制器和门控接到实际 MC、交换器、U0、SRAM 及 DMA RTL。测试从 111303 封存的 151,936 个 logits 现场归约得到 token 81917。前一阶段页完成与 KV 回执由测试发送，DDR 数据端由测试从封存权重行应答。它验证事务顺序和数据搬运，主底座的实时 KV 提交、P0 物理返回和 C0 索引发送端仍需绑定。该夹具把 U0 单笔在途 ACK 与本次写标签关联，错误 ACK 标签另在协议回归覆盖。

| 111657 事件 | 正常 ACK | 延迟 ACK |
| --- | ---: | ---: |
| 词表 token 到达 | 38,731 | 38,731 |
| KV 回执到达 | 38,745 | 38,745 |
| 请求控制器退休 | 38,747 | 38,747 |
| Gather CALL | 38,756 | 38,756 |
| 索引 SRAM 确认 | 38,820 | 38,829 |
| Gather 结果最后一字确认 | 41,311 | 41,311 |

## PR #260 当前入口

用 PR #260 的提交 `dd423e5a8010e7371ee1ccbd589df00bc0ff6478` 核对按算子图编译的本请求。RTL 审计读取器核对了 128 个阶段的图摘要，以及 184,927 条母控页及目标记录，故意替换末阶段图摘要会被拒绝。TLM manifest 解析同一请求和已绑定 DDR 初始资产。远端 111676 用该提交的 TLM 入口和依赖执行开头四页，得到 88,379 次 DDR 读、160 次写及 88,539 次回调，退休数为零。运行结果没有数值和整机时序验收凭据。完整 TLM 作业 109409 继续执行原评估输入。

现有 RTL 严格审计要求输入 SRAM 提交发生在 `NATIVE_PAGE_LAUNCH` 之前。本版本 U0 必须先接 CALL 才会预留接收字。需要在正式执行和审计中把 CALL 打开接收窗口与读取索引的两个真实握手表达清楚。另一条可行设计是由有独立预留能力的路径先写并确认。两条路径都应保留精确页世代、数据值、写确认和首次索引读取的因果校验。本次组件结果未进入现有整机审计。没有合格的 P512/D128 tok/s。

## 复现

远端目录为 `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/framework-20261114-akeox2em/full-graph-zwl0Tr/merged-bmMd5X/native-request-6WI0tH/framework-r11-CatJ8r/p-native-audit-FMPaww/live-vocabulary-CgSH5M/joint-placement-CrmPRH/request-retirement`。用 `request-retirement.sbatch` 生成阶段表并跑协议回归，用 `request-gather.sbatch` 验证 MC 与 U0 的交接，用 `check_pr260_graph_input.py` 生成对当前 PR #260 的输入回执。将回执 manifest 交给 `pr260-graph-prefix.sbatch` 可以复跑四页。111676 的 `execution.json` SHA-256 为 `f31158d3f1b2c7f264ae66a05cf4646edfdaf0ea1a8b0c348654022a9ee39777`。`pr260-input-proof.json` SHA-256 为 `fda5fb332d16704ce775d633ce28d5c39a9fc9516bcb785b169c91317ab669cc`。管理结构检查使用当前检查脚本和远端管理结构快照，结果通过。
