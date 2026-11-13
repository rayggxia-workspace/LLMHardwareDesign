# 九组底座上的 Algo1 框架收敛

2026-11-14 CST，Issue #219。比较基于快照提交 `5efa7c26e`。保留远端 PR #257
的图编译、控制 IR 和布线交接基线 `a326d04e`。两条分支的前沿、执行和验证实现
发生冲突，合流后须同时通过两边的回归。

## Tile 交接和候选排序

从同一组服务和 SRAM 窗口试排两个 16 B tile。
`benchmark_tile_handoff.py handoff` 通过编译器和独立计划检查，导出实际等待边。

| 配方 | 模型周期 | 两个输出 tile 的峰值活跃字节 | 依赖 |
| --- | ---: | ---: | --- |
| 整算子屏障 | 16 | 32 B | 消费者第 12、14 拍开始，分别等对应数据发布和整算子退休 |
| 阶段交接 | 12 | 16 B | 消费者第 4、10 拍开始，只等对应 tile 发布 |
| 独立提交命令的假设配置 | 10 | 16 B | 两条生产命令各自以 tile 提交结束，只需命令完成级等待 |

前两行使用同一硬件模型。第三行使用另一份服务合同，单独说明原生接口须怎样支持独立交接。
活跃字节从写阶段开始到最后一位消费者读取结束统计，只覆盖这两个输出窗口。
测试的两个窗口仍是固定物理地址，峰值下降未被计作 SRAM 面积或分配器收益。

`benchmark_tile_handoff.py placement` 固定两个计算候选，分别强制试排并从同池搜索。
空闲时单宏 24 拍、双宏 16 拍，加入占用 P1 同通道的后台请求后，分别是 24、29 拍，
搜索切回单宏。这是声明资源下的模型排序反转。外存字节分别为 64 B 和 128 B，
差额来自后台请求，同一压力下两个候选的搬运量相同。

## 两个后端

- 算法 2 当前实现 `4ebd2a2fc` 的 `--handoff` 已读取 #257 U 组真实 M10
  端点样本。130 根待布线通过研究几何规则，物理资格仍为 false。接口读取
  `upper-router/1`、`handoff.json`、`program.json`、`wiring.json`
  和 `requirements.json`。产品范围还核对冻结底座、逐位端点和控制镜像。
  main `7a809d1e` 的 Block V2 九组位置是候选图，项目有六类组级 DEF 的散列，
  仍需将九个实例及主控的变换、顶层端点、预连、障碍和时钟/复位/数据网络绑定到同一个底座。
- #260 `1ea06be2` 的消费者读取封存的程序页、原生 CALL/WAIT、128 B 描述符、
  局控资产、初始 DDR 镜像及 KV 合同。现有 `link_native_program.py`
  的输入是同一计划生成的 `block-event-control/1` 和 `block-event-demands/1`，
  现有 WAIT 等目标返回整条命令完成。对阶段边先验证目标 ABI，能独立提交的服务按 tile
  生成真实指令；无法观测的阶段边须明确报出。现有封存请求经消费端审核
  184,927 页和 8,273,243 次 CALL；同包一页 TLM 跑通，141 笔 DDR 请求均回调，
  无 token 退休。两项用于验证消费接口，尚无新 Algo1 计划贯通到该请求包的证据。

快照分支接入了 #257 的控制、线束发射器和基于硬件配方的图 lowering。
`run.py MODEL HARDWARE OUT --event-graph` 从类型化图生成计划、控制和线束需求。
此前以两节点图走完新编译路径与算法 2 入口。内部阶段的串行配方可以使用，任意阶段 DAG
仍待合流。完成级等待可导出，无法由命令 ABI 表达的阶段边会被拒绝。原生 tile 的
独立确认仍待验证。产品计时以真实
权重、自产 KV、合法程序、联合事务和 token 实际退休为验收。参考
[PR #257](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/257)、
[PR #260](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/260)。

后续用同一编译路径重编了 #257 的 36 个原始任务 U 组图。交接读取带源视图的候选
摆位，算法 2 以 `--handoff` 检查新计划来源并通过 130 根实际端点线的几何校验。
放置的组级源视图仅在候选范围接受，产品范围仍要求整体冻结视图。该候选来自旧 #230
资源摆位，和 main 的 Block V2 九组加 MC06 目标属于不同物理版本。

## 完整图入口和原生 linker 回归

新增 `--event-native-program` 和 `--event-native-profiles`，复用 #257 的整型有限循环
lowering。循环属于已资格化的服务，完整工作量、参与局控和资源租约进入同一个搜索。
程序的模型 SHA、整数工作和外存区域均经检查。可通过 `--event-route-base`、`--event-route-catalog`
和 `--event-control-fabric` 在试排时绑定接口。布线成本包含依赖线束闭包，缺接点的候选在
搜索时排除。端点合同同时区分新增逐位连线、已有组内服务、以及仅到组边界的接口。

编译成功后可直接从编译结果发布，无需重复提供派生的 IR 和已解析硬件。

```text
python publish_event_handoff.py RESULT CATALOG BASE RULES OUT --upper-router UPPER_ROUTER
python UPPER_ROUTER/run.py OUT/algorithm2-input.json ROUTES --handoff OUT
```

Qwen2.5-3B 的 B1/S2 无 KV 回归覆盖 36 层，宽度 1、8 各执行 1083 次有限循环派发
和 8850 条整数指令。用真实权重重新编译后，两种宽度各三组 logits 与独立整数参考逐位一致。
在旧 #230 组级摆位上，完整图交接经 Algo2 `4ebd2a2fc` 读取，确认六项原生服务、四项外部
边界和零根新增线。同版代码另用两 U 实例的 36 任务回归校验 130 根新增线。前者的外部接口
仅到组边界，main 的 Block V2 九组加 MC06 仍需要同版本的控制、DMA 和完整顶层端点合同。
109147 用 main 六份源 DEF 核对远端 packet 合同的 2613 条有向连接需求。九组和 MC06
涉及的组级 BTerm 均匹配方向及 M10。合同还引用 `sw` 的 1509 个不同端点，而 main 这版
候选摆位没有 `sw` 实例。该交叉检查只核对源端点，等待 Algo2 给出实际组装及控制实现。

使用 #260 的真实 prefill 图、封存权重布局和归档 native linker，重编第一层选定的
三 P SwiGLU scope。新 Algo1 的控制计划通过 192 次 CALL 链接，母控、三个局控镜像及描述符
逐字节匹配独立保存的可执行参考。这次检验原生接口兼容性，选中的服务是单个强制绑定。
用 #260 归档 linker 重编位置 0、511、512、638，每个位置覆盖 36 层。
新增路径保留 indexed Gather 的原生 provider，将要求外部可见的输出编成显式 STORE，
并核对原生 RMS、残差等整窗口原地更新的旧版本及读写依赖。STORE 的完成条件是目标提交确认。
四个位置共 5214 份二进制与归档逐字节一致，覆盖首段 prefill、首次词表派发和 decode。
这是 #260 既有拓扑上按阶段调用新 Algo1 的链接验证。全请求正在重新编译，仍需将全图选择
传给两个后端，在 Block V2 底座绑定真实 DDR 地址和 KV 版本，并用 #260 执行到 token 退休。

## Block V2 候选摆位上的同计划交接

事件计划的 `nets` 包含直接使用的线束及其传递依赖。指令和连线输出保留直接使用者，
同时展开所需依赖，旧版直接线束清单仍可读取。原生 linker 对照计划核对全部依赖，
Algo2 用同一计划散列和物理源散列读取交接。

远端 `native-request-6WI0tH/v2-candidate-embedding` 使用 main 的九组和 MC06
候选坐标，另在 (1950, 5240) µm 放置已有独立交换器的源视图。该坐标是本次候选假设。
按组 DEF 平移 M10 实际 BTerm 后得到 4244 个包控制端点。用真实 prefill 位置 0
的 Gather IR、DDR 地址和原生 provider 重新编译，得到 432 条控制连接成员，其中
431 根待布。原生描述符、母控和局控二进制与该位置的参考一致。Algo2 `4ebd2a2fc`
通过交接读回；其冻结产品入口需要整体顶层视图。
远端复跑入口为同级目录的 `verify-v2-embedding.py`，SHA-256
`ca188a779aecd09fb2521ebb5b5b4c537b5f679d746714f4bceae27930a8dce7`。

旧研究配置的 16000 DBU 接入间距无法落到这批 M10 端点。用 400 DBU 接入间距、
相同 via 切孔和包围尺寸，对 863 个实际端点和 431 根待布线均找到候选接入点。
这里覆盖控制链的一项真实服务，候选接入点仍需联合布线和物理验收。全图服务、
DMA 数据路径、顶层时钟和复位仍需绑定到同一底座。

## 全请求封包和 Block V2 服务缺口

109206 完成 80 个并行编译任务，封存 639 个位置。109215 复验并生成 128 个请求阶段、
184,927 页和 8,273,243 次 CALL。与归档比较，130 份二进制全部逐字节相同。初始
DDR 镜像绑定 439 个只读资产及 72 个后续状态，状态写表覆盖 92,016 个 K/V 行。
初版包缺少 #260 性能消费者需要的 `ffn-activation.tsv`，109246 在发出第一条事务前
退出。109408 改用项目提交 `fed2d9be3` 的页封包器，从同一批新编译阶段的封存凭据
生成 activation 读表，并核对每行对应先前确切的 8192 B STORE。109409 依赖新版封包，
使用原 `1ea06be2` 性能入口执行全请求。

109408 已封存新版程序和内存初始化表。重新生成的 23,004 行 activation 地址与参考相同，
地址表以各页先前实际发出的 STORE 描述符为依据。109422 独立解析全部 184,927 页的
原生描述符和目标位掩码，核对 23,004 页 FFN 输入和紧随其后的 Down 写回绑定。
109409 已进入 prefill 并报告实际 DDR 读写回调，首个 token 要等 prefill 全部结束。

从 109215 的母控页目标掩码和服务签名得到 P0、P1、P2、U0 四个执行目标。109384
通过独立交换器的封存目标表和四组 M10 端点导出 1248 个控制连接成员、881 根网、
2129 个端点。Algo2 适配器读回通过。这个交接基于既有 #260 拓扑的已生成指令，
覆盖包控制，不包含整个 Block V2 图的共同搜索、DDR 数据面、时钟、复位或最终物理布线。
对照包的 881 根网各有候选 M10 接入点。109334 全组搜索超时，109400 在较短的
单网扩展预算下报告 431 根控制网预算耗尽，保留为试布结果。

确定的服务缺口在 U39。Gather 的 #260 TLM 记录头为 `(schema, ABI, opcode) = (3, 7, 4)`，
U39 走 `u_n32_controlled_64` 的本地控制器，`exec_ok` 要求执行描述符首 32 位为 1。
U39 的 N32 路径接受阶段提交、Softmax、结果排出三种行操作。包转发和目标编号的匹配
只能绑定控制线。产品映射要有实际实现支持的服务、编码器和搬运合同，才能让 Algo1
在搜索时纳入这条候选。参考 [U39 本地执行入口](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/7a809d1e8dcda063c66f5ca18e9c186fb23ec668/project/rtl/block_v2/u/pu_native_lc.sv#L172)
与 [U39 N32 描述符](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/7a809d1e8dcda063c66f5ca18e9c186fb23ec668/project/rtl/block_v2/u/u_n32_s128_group.sv#L32)。

Algo1 的搜索现在可以读取底座中的 `native_service_routes`。候选声明目标组及编码器 ID。
硬件目录中的 `native_provider_contracts` 给出该编码器需要的调用签名和各调用的完成语义。
底座记录目标组、数字 ID、网表视图及散列，并列出该目标实际提供的签名及完成语义。
产品模式用这些声明过滤搜索。候选底座提供该表时，接口模式也执行相同过滤。
编码后的实际字节仍由原生 linker 校验。既有的端点交接可单独用于研究和诊断。
远端 109436 使用真实 Gather 描述符及 U39 视图复现缺口，搜索给出
`U0: no physical service route for signatures [(3, 7, 4)]`。
该检查只核实 Gather 的拒绝条件。九组的完整服务库存及数据搬运合同仍需同版本底座证据。

| 作业 | 结果 | 证据 SHA-256 |
| --- | --- | --- |
| 109359 | 四个边界位置的各阶段均找到链接器消费的 Algo1 源计划 | `48eae1ff246b4422401f105e3e91159cab2b3db77c096d732db60cb766bf472f` |
| 109356 | 全包 130 份二进制与独立归档一致 | `6189db73a2b35a19cf3d6446e5d17db4d8bc11636e17ca01836622c7d8c49c3b` |
| 109384 | 新编译请求控制连线，`v2-native-control-request/algorithm2-input.json` | `a7fa920581a20cf8c25770ed6580ca349d6dfbdcd5c96d7b3cb29491310b4d41` |
| 109392 | 881 根参考控制网的 M10 接入检查 | `fd58de785add96a3eb34ed0fff386da2d37cadb746ccf4789b67b933a2dd3d93` |
| 109400 | 431 根控制网的有限预算试布 | `acbc407f6f98f478133e41f19ea4a9ce30821a77c4922fa539460cd82484199d` |
| 109408 | 带 activation 的新版封包，`request-runtime-r2/proof.sha256` | `9fc35ec5fb682adce14f20458c9d5b22aef84c4722bd74823b39f241e760968e` |
| 109410 | 新版封包 130 份二进制一致，唯一变化的元数据为来源凭据 | `e4d5ed2cfec0fdb3c02ae94bf051d61862b58b8aee79e6f984a8b79703679cc3` |
| 109411 | 新版封包重新生成 Algo2 控制输入，`v2-native-control-request-r2/algorithm2-input.json` | `dba355bb7af57113ce1d5083a4b875e826b522c4099f575164f164fa9169fa99` |
| 109422 | 新版封包全页服务角色和 FFN 输入、输出绑定核验 | `87017ec7ff2221524824d2d5855e9aa9d4dd0ebdd42a312b013105be4a70cbec` |
| 109434 | 406 项算法回归通过，含真实服务路由缺失时选择可执行备选 | `7f0ab553d505d37d7eea90a5020544d0d2d81a46c9ded9a7c544428c15186fb3` |
| 109436 | U39 Gather 候选在同一底座被搜索排除 | `495f41b267c22755af90b7e2b486690d4b15b4276c049c975cc390624c3302ed` |

本轮远端目录为上述目录下的 `full-graph-zwl0Tr`。合并源及回执在 `merged-bmMd5X`。

| 作业 | 结果 | 证据 SHA-256 |
| --- | --- | --- |
| 109108 | 整图重新编译及 6 次 logits 核验，`accepted/report.json` | `9c5d503bdacd41e894828860d3c52d828cf549364b04169f933fd67f99d8f5c9` |
| 109123 | 两 U 的 130 根网通过当前 Algo2 | `55d57588587daf5a679516b353eb915cce6a274e3c5dec3399bc7e123205e2fe` |
| 109124、109126 | 完整图发布与当前 Algo2 回读，`qwen-route.json` | `8381cff5de97fb51a2dd151354f735a0c94e22f96543b31117c52ed240c63507` |
| 109135 | 192 次原生 CALL，`native-scope/scope-link.json` | `4d5f3dbbca761b73382251b18f7d1c039230e9e98f0643de1d15043c83726017` |
| 109143 | 402 项回归通过，含当前 Algo2；`release-source.sha256` | `96cd55ab3b3d9487564f9a41f99caed249048afadb9033d40e73171d822b86e5` |
| 109144 | 最终代码再编完整图及 6 次 logits 核验，`accepted-final/report.json` | `a4253b0c3ed56c3b785cf20d8f0a8d952e6db30d4f05595df0286229e4b6af43` |
| 109147 | main 候选组 DEF 与 packet 控制端点核对，`v2-packet-endpoints.json` | `cea07799579bee486102a9352ddf417e63771ded90163e8f8f6a1b09f045d961` |
| 109198、109203 | 四个边界位置重编；109198 的 prefill 哈希参数错误由 109203 修正 | `native-request-6WI0tH/r3`、`r4` |
| 109221 | 404 项回归通过，`regression-109221.log` | `d8afe41f08dba901ca1d7b765d93c4c3dfa88485c402fb710756834d565f7c30` |
| 109225 | 5214 份二进制一致，`binary-diff-109225.log` | `cc2cb67c1f963e33339d2e22b9ee9e3b814941f0fd288567f134cdf540b7c1b7` |
| 109206、109215 | 639 个位置重编及初版封包，`request-runtime/proof.sha256` | `57ddccc1ac67891fe312ce449fcd451be18ad07851d7eee79df32d8ed617db9e` |
| 109246 | 初版包缺 FFN activation 地址表，TLM 启动前退出 | `2e721ef83e7c1caaad0237526f828e245dba1ce98e51a57e6cef5ffd4e105fc2` |
| 109409 | 完整 #260 TLM，无 checkpoint、短程或预装 KV 参数，`strict-tlm-109409/progress.jsonl` | 已进入 prefill |
| 109283 | 405 项回归通过，含控制线束传递依赖 | `bb29bf84deca42d6938ceedc1cd11107137a3b950cce38e2606bd67c207470fe` |
| 109326 | Block V2 候选上的 Gather 同计划链接及 Algo2 读回 | `ab46cea37e098ed7192a55e5015ae8e6762740f726cf2f3114ff94cfaa7c42db` |
| 109330 | 431 根候选控制线的 M10 接入间距检查 | `064b37f47d8da5856996c7a60eea62c025d0fb7605207f68abcd66464661a83b` |

109119/109120 最初用了旧端点检查器，109122 则发现原生资源声明尚未接入。更新检查器和
接入声明后，109123/109124/109126 通过相应范围。109136 的缺接点负例保留了另一条
合法 DDR 路径，109143 补上 DDR 线束需求后复测。

## 同一计划的原生端点凭据

绑定物理底座的编译结果现在同时导出 `requirements.json` 和
`native-route-requirements.json`。Algo2 继续读取现有交接文件，其中包含固定底座需求。
原生 linker 的 `route_binding` 接受后者、同一目录输入中的 catalog 和 base，以及
`route_contract.verify_requirements`。原生凭据只包含被选命令及其传递线束需求，
来源字段与 control IR 一致。两个文件的计划、硬件、底座和 catalog 散列一致，
交接清单的 `native_route_request_sha256` 记录原生凭据的校验值。
该凭据仅证明端点绑定，仍须使用目标实际服务路由核验可执行性。

远端在 `native-request-6WI0tH/v2-candidate-dual-receipt` 复用真实 prefill Gather。
原生 linker 拒绝直接传入 Algo2 需求文件，读取原生端点凭据后生成的母控、局控和
描述符仍与参考逐字节一致。Algo2 通过交接校验，含 431 根待布控制线。
109446 首次读取时，试验脚本生成的文件名缺少 `.json` 后缀；109448 纠正命名后
用同一产物验证两个后端。候选交换器位置仍为此前的研究假设，U39 的 Gather
服务拒绝证据仍适用。

| 作业 | 结果 | 证据 SHA-256 |
| --- | --- | --- |
| 109447 | 406 项回归通过，`framework-reg-109447.log` | `f4ebfacceea0e18a157e11813e594c155054cebb876aec6d2dafd63f3fe63fae` |
| 109448 | Algo2 交接和原生凭据读回，`v2-dual-read-109448.log` | `92dc0b5c47c361b308555c76d754f17e48a2b6151d32bb82aa7fdf12570bd709` |
| 109446 | 原生负对照与三份镜像一致性通过，`native/deployment.json` | `39c9ac67025f1fbb136c7bbf4049526c34dfa6ee5371722e6042f8b975eb426e` |

## 数据端点交接与整包描述符入口核对

使用 main `7a809d1e` 的九组和 MC06 坐标、已有候选交换器坐标，以及对应组的散列锁定源视图。
`audit-v2-data-link.py` 按组 DEF 逐位提取 stored-link 的驱动、接收、M10 几何和实例平移。
`C0 → U0`、`C0 → U1` 各有完整的 153 个信号端点角色，包括 128 位数据、地址、
valid/ready、写确认和接收窗口预留。反向两条路径各缺少 U39 的 128 位
`outgoing_data` M10 几何。存在逻辑 BTerm 时仍要求实际金属接入。

用一个已驻留 C0 的 16 B 片段和 U0 的模型服务试排，选择 `stored:C0->U0`。
同一计划的 Algo2 包包含 734 根待布网，其中 153 根是该数据链。Algo2 接口校验、
哈希源视图的逐位重绑、重建整个路由输入，以及原生端点凭据与计划散列核对均通过。
在 400 DBU 接入网格下，1592 个端点、734 根网均有几何候选接入点。
这个用例只验证物理接点与计划交接，服务时长和驻留输入是试验假设。
联合布线、原生命令及真实 DDR 搬运仍需各自的证据。
第一次作业 109466 生成了数据包，随后 Algo2 的可选冻结底座入口要求整体 GDS。
本次用接口入口读回，并逐一校验组级源视图与重绑结果。产品入口继续要求整体冻结视图。

`audit-v2-native-headers.py` 读取 109408 封存的实际调用签名，按真实目标编号，
对照主分支源清单中 P 的 `p_scope128_decode` 和 U 的 `pu_native_lc`。
21 类、8,273,243 次调用中，5,396,848 次的 schema/ABI 对上 P scope 头，
2,599,452 次在 P scope 入口被头部条件排除，276,943 次在 U39 native EXEC 入口被
描述符首字条件排除。核对的是原样复用 #260 描述符的前置条件。头部匹配的调用
还需验证控制封包、操作数、目的地址、完成事件和数据面。P0 的 LOAD、STORE、
RoPE、KV 等同样需要寻找实际实现或重新编码，因此补一个 Gather 编码器还不足以闭环。

远端工作目录为 `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/framework-20261114-akeox2em/full-graph-zwl0Tr/merged-bmMd5X/native-request-6WI0tH`。复跑需要将同版本的 Algo1 模块加入
`PYTHONPATH`，数据链核对同时需要 Algo2 `4ebd2a2fc` 的模块。两个脚本的输入均为
已有封存包和源视图。候选目录是 `v2-candidate-dual-receipt`，主分支源清单是
`project/rtl/block_v2/source-manifest.json`。

| 工件 | SHA-256 |
| --- | --- |
| `v2-data-link-readback/algorithm2-input.json` | `612eb35340d14bdc70821d46dfc690f2b2bfcab92fc3e10c7440db70aa82ac0e` |
| [数据链读回](v2-data-link-readback.json) | `f61bff2968c32d0a18bf4414f6c928804b3d415ca6b38a57de5f625511f93150` |
| [全包描述符头核对](v2-native-header-audit.json) | `d7b5eb2a476c4b13d2798a4091459e84bdd83dab4cb2499fd655fd3e2b39d976` |

## 联合摆位的 P–DMA 交接与 main 端点对照

从 109408 同一份封存程序的目标掩码和真实服务签名派生 1248 个包控制连接。
三 P 的 `(0x02505001,0x02504d02,2)` scope 调用另需描述符、512 位权重和 M60 完成栅栏。
在 #185 的联合 A 摆位中绑定 4344 个 P–DMA 连接成员，另核对 18 项常量接收位。
用联合前 DEF 的实际端口恢复 93 个描述符驱动别名。按电气驱动合并后导出 5132 根网、
10724 个物理端点。交接绑定 #260 封存包散列。硬件服务兼容性不由端点覆盖推断。

远端 109556 用 OpenDB 检查全部 10724 个选中端点的归属、方向及 M10 几何。其中
2310 个是叶宏 ITerm，8414 个是已放置的父层逃线 BTerm。后者在原始 cut ODB 中没有
下层连线。另从已有 DRT 试布 ODB 读回本次选中的 2129 个控制 BTerm，各自均有
下层连线。该试布 ODB 为独立的控制逃线供体。剩余 6285 个选中父层数据端点尚未下层布通。

Algo2 `4ebd2a2fc` 直接读取 `algorithm2-input.json` 与同目录的 `--handoff`。
全量输入通过接口验证，所有端点各自有几何候选接入点。109559 的每网 12 次扩展
试布完成 1 根，5129 根达到预算，2 根报告 `grid_access_not_found`。
这些诊断来自有限预算，不作为不可布的证明。候选底座 `placed_parent_cuts` 要求实际 ODB
及端点来源，产品入口仍要求整体冻结视图。

联合 A 的 P 网表为 `66cc8f9c`，摆位也与 main 九组不同。另用 main P2545 的 ODB
对照同一逻辑合同。每组 P 的 678 个描述符逻辑位中，647 个有组级 M10 接点，
31 个与已有接点共用同一个原生网。684 个权重位和 86 个栅栏位在 M60 叶宏上直接有
M10 几何。独立放置的 DMA v45 ODB 有对应的 4344 个逻辑 BTerm，均需父层引出。
这两项审计把 main 侧的数据通路问题缩小到同一摆位上的 DMA 引出、配套控制和服务合同。
同一 main 摆位外框为 5863 × 6033 µm。用组级 DEF 外框检查独立 DMA v45 的
1960 × 1960 µm 区域，现有外框中没有无交叠矩形位置。保留所有现有组和交换器坐标时，
东侧示例需要增加 835 µm 宽度。这个检查只约束当前 DMA 外框及组位置，尚未计入
物理间距、PG 和布线，也未搜索重新摆放或不同 DMA 布局。
远端 `main-dma-placement-fit.json` SHA-256 为
`52d78f024a0bb276658823de3c6f638f3e06de7a72a8e6c3802db83a7b2a5f8f`。
外部 DDR、其余 DMA 客户端、KV 读写、全图原生 provider、时钟复位和联合验收仍待绑定。

远端目录为 `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/framework-20261114-akeox2em/full-graph-zwl0Tr/merged-bmMd5X/native-request-6WI0tH/joint-ddr-4C8sHe`。大文件留在服务器。
复跑将本分支 `project/experiments/block_synthesis` 和 Algo2 `4ebd2a2fc` 的
`project/experiments/upper_router` 加入 `PYTHONPATH`，然后执行：

```text
python -B project_joint_ddr.py JOINT PREJOIN_DEF NATIVE_PACKAGE CONTROL_PROJECTION OUT
python -B UPPER_ROUTER/run.py OUT/algorithm2-input.json OUT/routes.json --handoff OUT --rounds 1 --max-expansions 12
```

`JOINT` 是远端 `issue185-joint-packet-dma-bound-20261113-01`。
`PREJOIN_DEF` 是同级 `issue185-joint-flat-layout-20261113-01/seed-A.def`。
`NATIVE_PACKAGE` 和 `CONTROL_PROJECTION` 分别是 `joint-ddr-4C8sHe` 上一级的
`request-runtime-r2` 和 `v2-native-control-request-r2`。 `OUT` 为新建空目录。

| 工件或作业 | SHA-256 |
| --- | --- |
| `algorithm2-input.json` | `3db5dee214335d53fd2b1e3ee1bf720183540541c4142363ae290ca6cf5b5c7b` |
| `handoff.json` | `ff832bf88d6c78fd77bfc3528c592b62dc3b666952ee01b009a25aba6b0bd59f` |
| `report.json` | `fab55c8584e1c7bab02e54025e8cc58badcbab9d99a344bb343663acc2732215` |
| 109556 OpenDB 读回 | `3cd7925cf49204934bc1424c98b8da08f79996bba56d4d0973cfc1633d094dfd` |
| 109559 有限预算试布 | `34c4b3941946982b75dff20b751aa00c1a4673909a11302a33e8477a7d45d385` |
| 109565 的 407 项算法回归 | `19dfa801ea54d76c90ab4470e99071068f7bc7a59c13c05c02917dc4bcb75cbd` |
| 109557 和 109560 的 main P 与 DMA 对照 | `1e974aa553632588a52f63571c475e11008b6dd0e0b7b9560a622935e63f5db7` |

## 远程回执

目录 `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/framework-20261114-akeox2em`。

| 作业 | 结果 | 输出 SHA-256 |
| --- | --- | --- |
| 108990 | 整算子屏障与 tile 阶段交接 | `0d0ab7d9f6118343bf9096b025b267928fe448f1b06c88bc7cbf730e85605943` |
| 108991 | 同候选池 DDR 压力排序反转 | `fc4f6b36fd6c4c9c063f75641907eef9d5aaa034ed2fcc5e0238b77f39ca5a98` |
| 108992 | 项目结构及 396 项算法测试通过，源 `9242b5ab2` | `7681b5b0928ac79511c88f54c9404a3f2f846d5c0cae6c5032960e5fdf9c3217` |
| 109000 | 加入独立提交命令模型和 ABI 缺口报告 | `5e1699f97a9376d2e80f6aa9c343574fa51dc3a376f4c66cf63922ec9c4336b7` |
| 109010 | 当前算法 2 接口回放，`route-current-u.json` | `22a17a3e05d779a3c1471d589266d9aa30e8ac90b7371436518411ec7a7c444b` |
| 108968 | #260 母控页和 CALL 读取检查 | `3898d96c3dd1e988a9cb8d95dba0d7070ffce6dadbb2ff2865fafd100a97c219` |
| 109009 | #260 一页回放，`execution.json` | `cdec2acc56348b638c1e8cfb269d5e1a5b647590008e567f2135360aacd419ca` |
| 109035 | 类型化图经快照编译和当前算法 2 消费、控制 IR 正负对照 | `111708d475d995f7cc09643b35064f66399ac3145bd9b76706cef1b1a5d1f22a` |
| 109043 | `b8ae3a696` 项目结构及 400 项回归通过 | `c4fb7e86995c3ac9c5c13b2349eccd75cc913683b25567c037cb1410ba06b81a` |
| 109054 | 新编译 U 组交接与 130 根网几何校验，`u-route.json` | `1f0cefb51f7c53e40dacf780313e052904aae9ff27dc07843100e18e1654f2cc` |

以上作业均 `COMPLETED 0:0`。一页 TLM 的早期启动失败（108995、108998、109006）
已保留，分别修正了 Slurm 下的路径和归档依赖。
作业 109048 拒绝了仅含各实例源视图的输入。109054 使用增加候选摆位校验的适配，
继续对每份源视图做哈希核对。

项目 `llm-hardware-design`，协作规则 `rayggxia-project-collab 1.0.0`，Issue #219
继续进行，负责人 YUZE-LU，独立审查人待指定。登记沿用 management-hub PR #5。
当前无 `config/board.json`，看板 unverified，同步 pending。

## 有限循环的分组外存接口

全图 lowering 从独立核对的原语读写计数和候选宏绑定推导 `memory_by_site`。
`IO` 原语使用候选指定的 IO 站点，其余原语使用实际执行宏的站点。
每个局控的 `RUN_LOOP` 描述符带该站点的 `external_memory`，功能回放检查它与选中服务一致。

硬件可以提供 `finite_loop_memory_interfaces`，按局控组名和 `read`、`write` 配置。
每个方向声明 `nets`、`abi`、`external_owner` 和 `width_bits`。
已有的传输 ABI 逐位检查控制组和外部端点、方向、宽度与确认信号。搜索在候选上计入这些
实际线束和传递依赖。缺接口时保留有流量方向的逻辑需求，产品准入报告该组缺失的接口。
原生服务和最终完成信号仍由独立的 native dispatch 准入检查。

远端 109588 重新编译既有 36 层 B1/S2 无 KV 图。4,333 个候选中 4,328 个有多站点
外存需求。选中 1,083 次派发，2,165 份局控命令带非空外存需求，所有字节数与原总计相符。
布线和局控输出引用同一计划散列。该输入仍有 10 组未绑定的接口需求。
日志 `audit-loop-memory-109588.log` SHA-256 为
`a5e21268dd2514d9c1dd6bfcf6e523504823fa51e4fe87e19b4f561ae2427395`。
