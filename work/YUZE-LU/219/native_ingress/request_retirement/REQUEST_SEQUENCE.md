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

## PR #260 短程吞吐诊断

完整 P512/D128 任务 109409 已取消。使用 `dd423e5a8010e7371ee1ccbd589df00bc0ff6478` 的指令驱动 TLM 和原版后处理脚本，在相同编译部署上远程并行评估。

| 模式 | 作业 | 输入与计时边界 | 检查入口 |
| --- | ---: | --- | --- |
| Prefill | 111805 | 空 KV，两个输入位置，计时到第二个位置第 36 层残差完成 | `audit_prefill.py` |
| Decode | 111806 | 512 个代表性 KV 历史位置，从第一次新 token 退休计时到第二次退休 | `audit_native_decode_timing.py` |

两项采用 PR #260 流水用例的 TLM 参数，使用 512-bit SRAM 端口、每 DDR 通道 32 个信用及 KV 读窗口 8。部署封印是 `9fc35ec5fb682adce14f20458c9d5b22aef84c4722bd74823b39f241e760968e`，decode 历史绑定是 `78347abd13135d71a678ff87b4760175ea81fb701a4edb022e080165321f2b4e`。吞吐取自完整短程的模拟时间。该执行器在本组用例沿用 Qwen2.5-3B 的 36 层短程合同和模型化局控。

`pr260-fast.sbatch` 接收远端输出根、固定版本代码目录、部署、内存目录表、decode KV 绑定、模式和 SRAM 位宽。复跑所需资产为远端目录 `pr260-dd423e5`、框架目录的同级 `request-runtime-r2` 及同处的 `request-memory-r2/ddr-initial.tsv`，decode 历史绑定来自远端 `issue260-request-kv-binding-dbIUacE6/bound-104206/binding.json`。每个作业输出 `execution.json`、`page-timing.jsonl` 和 `timing-audit.json`。两项均在远端运行。

111805 跑完 578 页，原版审计通过。空 KV 的两个输入位置合计模拟 363,205,986,672 ps，得到 **5.5065 token/s**。原版核对 288 条 KV 写入，92,323,014 笔 DDR 读取与 48,384 笔写入全部回调。运行结果的 `timing_calibrated` 和 `numerically_accepted` 均为 false。111806 已进入第二步，等第二次 token 退休后回收诊断吞吐。短 decode 使用 PR #260 的全零历史 KV 和首步输入 840。两项旧运行的资源来自该执行器内建配置。

| 111805 产物 | SHA-256 |
| --- | --- |
| `execution.json` | `bdd127cb6138da3c0855e538958a9515b3a177facb2c976ff0b07992c884965c` |
| `page-timing.jsonl` | `989f3ef5a87b51ebb9294312241e433e5d2e82690e69c85208ebef1691a1b921` |
| `timing-audit.clean.json` | `cbb6636c94022569fa0636be68ba1f8fc71f91e99d9ee411bd95d5dc02534a17` |

容器 shell 启动提示混入原始 `timing-audit.json` 首行。使用相同固定版本审计脚本独立复跑，去掉启动提示后的 JSON 与纯 JSON 逐项一致。


## 对同计划底座的 TLM 准入

Algo1 选择映射和时序依赖，并输出封存的母控／局控程序、地址表和同计划布线。TLM 消费这份计划与独立提供的目标底座。候选连线经端点重绑后可作为评估假设。经确认的连线预测还需要相应的 Algo2 布线和时序凭据。

`tlm_plan_preflight.py` 先校验底座物理视图、交接摘要、封存程序的所有成员、控制投影和路由需求。然后用底座目标、schema、ABI、opcode、完成语义及实际端点重新判断派发。用封存的原描述符和替换局控镜像重建 Gather，检查 639 个替换页及母控字节。TLM 模型按替换后的五字段签名匹配已经安装的可调用实现。评估入口还未安装此底座的服务模型，所以没有运行时序和吞吐。

| 远端 112167 的全计划回执 | 服务签名 | CALL |
| --- | ---: | ---: |
| 底座缺派发 | 12 | 2,875,756 |
| 底座缺确切完成信号 | 2 | 980,080 |
| 候选派发和线束相符，当前入口缺 TLM 实现 | 7 | 4,417,407 |

回执覆盖 184,927 页，重绑 5,935 根候选网和 12,330 个端点。选取两份编译归档对 580 页、26,607 条描述符逐项核对封印、重定位描述符和完成语义，覆盖全部 21 个签名的样本。阶段、页号、描述符下标均从 0 起。例如阶段 0 第 1 页的描述符 0 和 1 分别是 U0 的 gamma 读入和 RMSNorm。阶段 0 第 147969 页描述符 0 的词表投影要求 `tile_consumed`，当前 P0 接口缺该完成信号。词表结果、C0 索引生产端及其物理连接缺口在回执中另列。

### 复现

新工具位于本页同目录。远端 `tlm-input-LmzyNWWZ/preflight-with-call-evidence.json` 的 SHA-256 为 `69b1208ffa2e8274b5f866efc45656864ce967b2ec5aeec626c3741b4c80c618`。保持算法二读回时的独立候选底座路径，输入名对应远端 111873、109637 和 112167 的归档。运行 Python 3.11，并在 `PYTHONPATH` 加入 `block_synthesis`、`upper_router`、`native_ingress`、Gather 局控合同及母控编解码器目录。

```bash
python3.11 -B tlm_plan_preflight.py "$deployment" "$handoff" "$base" \
  "$control_fabric" "$rewrite_profile" "$control_projection" "$receipt" \
  --gather "$gather_locals" "$direct_call_audit" \
  --call-archive 0 0 "$archive_row0" \
  --call-archive 0 147679 "$archive_row511"
```

本次部署用 `request-runtime-r2`，交接用 `handoff-111873`，底座用 `geometry-110384/base.json`，控制投影用 `v2-native-control-request-r2/requirements.json`，Gather 局控用 `request-110369`。全量准入统计来自已封存的服务清单，逐字节指令定位来自显式给出的归档页范围。通过 6 项模型查找及替换回归，并在真实交接上拒绝混用底座与指令包。

下一步需要底座绑定的 SRAM、DDR、互联和时钟参数，以及按同一签名实现的服务模型。先用已重链的 U0 Gather 执行位置 0 的单页，按母控 CALL、目标写确认和 WAIT 核对完成语义。覆盖实际计划所需服务后，再固定场景与同一底座的参数，比较两个 Algo1 计划。

### SRAM 容量和端口位宽由外部配置

给 `tlm_plan_preflight.py` 或 `tlm-preflight.sbatch` 加 `--sram-config sram.json`。参数文件用 `base_sha256` 绑定目标底座，每个实例独立填写 `assembly`、`capacity_bytes`、`read_bits` 和 `write_bits`。例如下列配置比较 U0 连续宽读的潜在的影响。

```json
{
  "base_sha256": "5e29e7ad71e1be84b5b8fd8b5a327d4672bef511af8b567a7c08d6f36ee0620b",
  "sram": {
    "U0.data": {"assembly": "U0", "capacity_bytes": 16384, "read_bits": 512, "write_bits": 128},
    "P0.data": {"assembly": "P0", "capacity_bytes": 16384, "read_bits": 128, "write_bits": 128}
  }
}
```

字地址仍以 16 B 为单位。服务支持连续合并时，令端口一次能传的字数为位宽除以 128。每笔事务在端口边界及服务允许的边界截断，沿用 PR #260 的对齐拆分原则。程序存储可以另设具名实例，数据端口参数不会传给程序装载。Gather 本身逐个 16 B 写入并等待确认，事务换算按其 128-bit 服务能力计。外部参数的文件散列及值写入回执，服务派发仍由既有候选底座凭据决定。

远端 112358、112359 用同一计划与底座分别提交 128-bit 和 512-bit 的 U0 读参数，P0 及 U0 写参数相同。支持合并的对齐 8 KiB 读从 512 笔变为 128 笔，两种配置的 Gather 存储仍为 512 笔。两份准入回执除参数外完全一致。10 项测试通过。以上结果覆盖参数绑定和事务拆分，评估入口尚未执行计划或计算 token 时间。

| 远端 `tlm-input-LmzyNWWZ/sram-profile-6RafkmGL` 产物 | SHA-256 |
| --- | --- |
| `preflight-128.json` | `71ed9ec8580df6371c89fcea18cb9928df856a7a17c02a8860104bdad248aa22` |
| `preflight-512.json` | `704ea81e1314419f2b8796799e6af246728bf0da18546ee04b9a36e0ce0d12d4` |
