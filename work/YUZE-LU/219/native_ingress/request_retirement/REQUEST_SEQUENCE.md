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

用 PR #260 的提交 `dd423e5a8010e7371ee1ccbd589df00bc0ff6478` 核对按算子图编译的本请求。RTL 审计读取器核对了 128 个阶段的图摘要，以及 184,927 条母控页及目标记录，故意替换末阶段图摘要会被拒绝。TLM manifest 解析同一请求和已绑定 DDR 初始资产。远端 111676 用该提交的 TLM 入口和依赖执行开头四页，得到 88,379 次 DDR 读、160 次写及 88,539 次回调，退休数为零。运行结果没有数值和整机时序验收凭据。该前缀回执独立保留。

现有 RTL 严格审计要求输入 SRAM 提交发生在 `NATIVE_PAGE_LAUNCH` 之前。本版本 U0 必须先接 CALL 才会预留接收字。需要在正式执行和审计中把 CALL 打开接收窗口与读取索引的两个真实握手表达清楚。另一条可行设计是由有独立预留能力的路径先写并确认。两条路径都应保留精确页世代、数据值、写确认和首次索引读取的因果校验。本次组件结果未进入现有整机审计。没有合格的 P512/D128 tok/s。

## 复现

远端目录为 `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/framework-20261114-akeox2em/full-graph-zwl0Tr/merged-bmMd5X/native-request-6WI0tH/framework-r11-CatJ8r/p-native-audit-FMPaww/live-vocabulary-CgSH5M/joint-placement-CrmPRH/request-retirement`。用 `request-retirement.sbatch` 生成阶段表并跑协议回归，用 `request-gather.sbatch` 验证 MC 与 U0 的交接，用 `check_pr260_graph_input.py` 生成对当前 PR #260 的输入回执。将回执 manifest 交给 `pr260-graph-prefix.sbatch` 可以复跑四页。111676 的 `execution.json` SHA-256 为 `f31158d3f1b2c7f264ae66a05cf4646edfdaf0ea1a8b0c348654022a9ee39777`。`pr260-input-proof.json` SHA-256 为 `fda5fb332d16704ce775d633ce28d5c39a9fc9516bcb785b169c91317ab669cc`。管理结构检查使用当前检查脚本和远端管理结构快照，结果通过。

## 实际索引与 KV 回执

远端 111707 从已有 U0 路径记录 MC 启动、CALL、SRAM 字预留、写确认、首次读请求、首次读返回与成功页终端。正常和背压的写确认分别为 38,820 和 38,829 拍，首次读请求均为 38,907 拍。读回 128 位字匹配退休 token 81917 的约定编码。检查器拒绝漏 ACK、重复 ACK、提前读、读回错误数据和过期页世代。正常与背压证据 JSON 散列分别为 `8244ae001230cefa9fb83f9ae21cba16b6fdacbdd6820a90a92a8bc18da8afa2` 和 `1df284d2f87b2f81ecb43c47b28ea4e2598cd59416c0319a323fa187364b0f21`。

`extend_pr260_gather_audit.py` 针对 `dd423e5` 暂存 RTL 审计扩展。只有与同一部署、图摘要、页世代和目标匹配的绑定页允许 CALL 后确认。其他页仍使用现有启动前写入校验。现有页数、CALL 数、KV、token 及数值验收继续适用。使用 `test_pr260_gather_audit.py` 对 111707 的真实 Gather 事件与测试页头、阶段事件混合验证，保留独立的旧路径回归，完整运行暂未使用该扩展。

远端 111718 以同一全图原样编出的阶段 126、127 的 288 条 KVR1 描述符执行 P0 SRAM→DDR 写回。输入为按流和位置重排的封存 KV，并写入各描述符真实指定的 SRAM 字区间。两次运行各 576 笔描述符读、2,304 笔 DDR 写均完成回调和退休，读回数据逐字节匹配。正常的阶段回执在 42,391 与 84,851 拍，背压时在 51,219 与 102,150 拍。真实回执在后一拍驱动该阶段的完成。页完成和词表 token 由测试端提供，仍需和同一执行中的 live QKV 与词表对接。复现入口为 `request-kv-store.sbatch`，基于封存的 105338 组件输入和 111352 同计划 KV 指令回执。111718 的 `audit.json` SHA-256 为 `d1e2f0e6650857d8aeb375d7a015daf65943066d6887b54577d94f3fad7ba989`。

## 同页实时 QKV 与 KV

远端 111756 在已有实时 QKV 组件上执行全图阶段 127、层 0、第 2 页的原始 84 条描述符。测试以 token 81917 及真实权重重算输入和投影，四条 KVR1 把位置 638 的四条流写入 DDR，正常和背压模式各完成 32 笔写请求。20 个投影 tile 的 640 个输出字在两种模式下逐字节一致。该测试在组件拓扑重链母控并按全图的输入所有权初始化 SRAM。阶段控制器收到四条真实回执，在其余 140 条流缺席时保持等待。

复现入口为 `same-plan-live-qkv.sbatch`。111756 的描述符 SHA-256 为 `62f16a8fa51906061768b5ed058d6a8d7f07cb744042a2e1fc16c592484fd6ec`，`qkv-phase-audit.json` 为 `02463210601d964eeb114ef361c37748fd144528621545b6703bdd14fc59fc51`。远端 `proof.sha256` 逐项核对通过。

## Algo2 回执复核

111828 对照 111294 的同图交接与 111290 的有界联合试布。两份交接的布线规范和底座摘要一致，重绑编译程序后入场回执有变化。5,935 根网中有 2 根通过几何检查，5,913 根耗尽搜索预算，20 根没有找到网格接入。后者集中在 P2 描述符 17 根、P1 fence 1 根和 P0 分组控制 2 根。Algo2 把这 5,933 条诊断都标为非硬约束。复核脚本为 `route-input-survey.sbatch`，产物 SHA-256 为 `e1c4aaf1893f51d7b874f60d70c6f550ba40758cd36d4d13fdccc66bf63b6bbf`。

## PR #260 短程吞吐

完整 P512/D128 任务 109409 已取消。使用 `dd423e5a8010e7371ee1ccbd589df00bc0ff6478` 的指令驱动 TLM 和原版后处理脚本，在相同编译部署上远程并行评估。

| 模式 | 作业 | 输入与计时边界 | 检查入口 |
| --- | ---: | --- | --- |
| Prefill | 111805 | 空 KV，两个输入位置，计时到第二个位置第 36 层残差完成 | `audit_prefill.py` |
| Decode | 111806 | 512 个代表性 KV 历史位置，从第一次新 token 退休计时到第二次退休 | `audit_native_decode_timing.py` |

两项采用 PR #260 流水用例的 TLM 参数，使用 512-bit SRAM 端口、每 DDR 通道 32 个信用及 KV 读窗口 8。部署封印是 `9fc35ec5fb682adce14f20458c9d5b22aef84c4722bd74823b39f241e760968e`，decode 历史绑定是 `78347abd13135d71a678ff87b4760175ea81fb701a4edb022e080165321f2b4e`。吞吐取自完整短程的模拟时间。该执行器在本组用例沿用 Qwen2.5-3B 的 36 层短程合同和模型化局控。

`pr260-fast.sbatch` 接收远端输出根、固定版本代码目录、部署、内存目录表、decode KV 绑定、模式和 SRAM 位宽。复跑所需资产为远端目录 `pr260-dd423e5`、框架目录的同级 `request-runtime-r2` 及同处的 `request-memory-r2/ddr-initial.tsv`，decode 历史绑定来自远端 `issue260-request-kv-binding-dbIUacE6/bound-104206/binding.json`。每个作业输出 `execution.json`、`page-timing.jsonl` 和 `timing-audit.json`。两项已提交，吞吐待作业结束与原版审计。
