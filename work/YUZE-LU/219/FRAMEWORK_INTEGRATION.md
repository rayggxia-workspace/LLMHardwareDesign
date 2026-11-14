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

## 同一计划中的原生索引和首个 RMS

`indexed_gather` 的 `index_window_offset` 可声明由原生入口写入的单个已对齐索引。
非零偏移引用完整的 SRAM 窗口作资源和覆写检查，并将索引的真实字节地址交给编码器。
索引只由声明的入口提供，不能作为普通 LOAD/STORE 的数据；覆盖后不能恢复成旧索引。
这让 Gather 读同一个窗口里的索引，后续 gamma LOAD 再复用整个窗口。

远端作业 109614 用封存图上的节点和真实权重地址联合编译位置 0、511、512、638 的
Gather 和首个 RMS。每个位置的 Gather、gamma LOAD、RMS 由同一份计划生成。
通过 #260 `1ea06be2` 的原 linker，12 份描述符以及四份局控镜像逐字节匹配分段归档。
调度器验证依赖，原 linker 的母控展开检查验证 CALL 目标及描述符地址。
每份计划的连线和指令来源一致。对照使用归档拓扑，范围是两个相邻算子。

- 远端目录 `framework-r10-WmbQfv` 内的 `audit-native-ingress-rms.py` SHA-256
  `efff33c68f2c7f30b694fb32c1d336049174fc4b305afe4f2068114018b81efc`。
- `audit-native-ingress-rms-109614.log` SHA-256
  `ad041829d2b5818528708743e0471c3f3bf17e876426faaa20094b515bb02d61`。
- 109613 远端回归通过 409 项，包括索引偏移、窗口复用及非法搬运检查。

## Block V2 直接描述符准入审计

远端 109637 对新 Algo1 重编的 #260 封存请求校验母控页、 CALL 展开、目标掩码、
描述符地址、CRC 和实际字节。共覆盖 184,927 个母控页、8,273,243 次 CALL。
对照 main `7a809d1e8dcda063c66f5ca18e9c186fb23ec668` 的 P scope 和 U39 本地 EXEC
入口，2,599,452 次 P 调用和 276,943 次 U 调用的原描述符头在对应直接入口会被拒绝。
其余 5,396,848 次 P 调用匹配该头部检查，是否支持完整字段、实际搬运、数值和命令完成仍需资格证据。
审计覆盖封存请求实际使用的四个目标。它检查直接复用原描述符的路径，局控镜像重编和服务重映射另验。

`native_service_routes.targets[].rejected_routes` 可把已证实的拒绝项接入搜索。每项包含
`schema`、`abi`、`opcode` 和 `reason`，沿用目标编号、组装实例及网表视图散列的核对。
同一目标的准入和拒绝表不能包含相同签名。用 `run.py --event-ir` 读取附表底座后，
真实 Gather 得到 `U0: rejected native signature (3, 7, 4): rejected_by_u_exec_header`。
搜到替代候选时仍需相应正向服务合同。阶段发布依赖也须有目标命令可观测的完成语义。

复跑脚本为 [audit_native_v2_dispatch.py](audit_native_v2_dispatch.py)。
`PYTHONPATH` 包含本分支的 `project/experiments/block_synthesis` 和 #260 固定版本的
`project/experiments/mother_control_native`。取远端同一编译目录下
`request-runtime-r2`、`v2-candidate-embedding` 和 `framework-r11-CatJ8r/main-source`
为前三个输入，第四个参数为新输出目录。源视图现场按散列核验，审计输出中的
`base-with-native-rejections.json` 可直接用作 `--event-route-base`。在同一输出目录，
`gather-event-ir.json` 和 `gather-hardware.json` 可直接用作 `run.py` 的前两个参数，
配合 `--event-ir --event-route-scope interface --event-control-fabric` 及候选底座的
`control-fabric` 复跑 Gather 诊断。

| 远端 `framework-r11-CatJ8r/native-dispatch-109637` 产物 | SHA-256 |
| --- | --- |
| `report.json` | `6a75691b78e522092a14b07b71be1ecab56b25aa29308f3efab438748c8d26cb` |
| `rejected-routes.json` | `f40b3dad848b07473a676831bc4b4a687932dba75d1b448fe94c03ff8d98ea00` |
| `base-with-native-rejections.json` | `d7dc3bf245da22db63b9d9f23900b32d50d6a036400552cedad08e3e9c4c5d00` |
| `compile/result.json` | `34917b05db437e408621e9605d1d7395e06f139def810b09b55e8370446b28a2` |

远端 109620 的 409 项回归通过。109409 是原拓扑上的独立严格运行，运行中的页和 DDR
回调仅用于观察进度。完整 Block V2 产品仍需实际 P/U 编码和服务映射、同底座的数据面绑定、
整份计划的联合布线、真实 KV 及 token 退休证据。

## Algo2 试布回执与 Algo1 重选

`retry_event_route.py RESULT BASE HANDOFF ROUTES NEW_RESULT [--net PHYSICAL_NET_ID]`
读取当前 Algo2 `--handoff` 入口发出的 `route-contract/1` 搜索回执。
它独立验证先前的计划、程序和线束，以底座、需求、布线输入及反馈内容的散列核对本次试布。
选中的失败物理网经逐位成员回到逻辑需求，再以相同 Event IR、候选库、底座和布线预算重跑。
重复试验延续上一次主动选择的排除项。省略 `--net` 会使用本次回执中的全部失败网。
排除项只进入试验结果，不改动底座及原硬件清单。固定需求保留，单凭搜索耗尽不能形成硬性物理约束。

远端 109665 在此前同一 C0→U0 数据交接上使用 Algo2 `4ebd2a2fc`，
显式将试布扩展预算设为 1，生成真实网级回执。选择数据线
`net-018b5e04b11627fecef6014e`，Algo1 将其映射到 `stored:C0->U0`。
这份单消费者候选池缺少替代输入路径，重搜如实返回 `no_plan_in_bounded_search`。
`framework-r11-CatJ8r/feedback-109665/routes.json` 的 SHA-256 为
`650ef4dfa4d0abf2ee372a27070f175bbb1426ec76d23219eca2230b7b686e29`，
`retry.json` 为 `df6200977ebe7ecfda16a8f29d62cbfafbd68495b18208c8099ee1de949340eb`。

新增回归用同一个 Algo2 入口生成等价失败回执，并在具备替代路径的候选池中验证重选。
结果走 DDR STORE/LOAD，各 16 B，计划散列变更，指令和布线重新从这个后继计划发布。
测试也核对了更换底座和更换试布输入后的拒绝行为。

## 同一计划交给 Algo2 与 #260 指令页读取器

`link_event_deployment.link_verified_event` 从已选的 Event IR、方案和底座独立重建控制与线束，
再按目标和 provider 契约检查编码器实际产出的每次调用。比较内容包括调用数、有序的
(schema, ABI, opcode) 以及每条调用的完成条件。通过后交给归档的原生 linker 做 CRC、
拓扑、目标和原生等待检查。原生链路与 Algo2 交接使用同一个计划和底座。
`export_native_tlm_pages.write_tlm_page_tables` 用 #260 的 PM 格式读回并封存母控页、
目标掩码、描述符地址范围和字节，拒绝 DDR 地址重叠及描述符来源偏差。

远端作业 109741 从真实模型首层三 P FFN 的归档 scope 重新编译。选择 P0/P1/P2，
使用基于 main Block V2 摆位、额外放置包交换器的候选底座。交换器将全局目标 0/1/2
分别重绑定到各 P 的本地目标 0。该用例按 P 的 stream-A16 命令入口建立研究用清单。
该清单只用于 interface 范围。三个局控镜像、母控镜像及 24,576 B 描述符与归档字节完全一致。
Algo2 的实际 handoff 读取器接受 975 个位成员和 730 根待布控制网。
由 #260 `1ea06be2` 字节一致的 `export_tlm_mother_program.py`、`replay_tlm_mother.py`、
`native_tlm_local.py`、`native_program_runtime.py` 独立读回 1 页、192 次 CALL、64 组 WAIT，
核对每次目标、地址和描述符校验，属于无计时编码检查。七个故障注入均按预期拒绝。

| 远端产物，位于 `framework-r11-CatJ8r/native-same-plan-109741/` | SHA-256 |
| --- | --- |
| `summary.json` | `3c6158a91c09f3909f6131d22d5c6de1d191dfe10a7c3ec133685ecf36e4f8b9` |
| `handoff.json` | `28e1c4737d444932d901db120e19ee6b9ed0ff5818332bc7365ef63ab2b6f402` |
| `algorithm2-input.json` | `312813c949ffef72e9c51f383e3ddffe5c9b0e80e6e19a2a6c06dafe316b6958` |
| `native-route-requirements.json` | `0927cd27682ed3c66aad6216d46875fb6137aadb485fd1f0fc228ed6279dd366` |
| `tlm-pages/proof.sha256` | `756044049a470207268a3e6bfcf7207a21649c3086099c77d43c6ea3c7b9480d` |

回归作业 109728 通过 410 项测试和项目管理结构检查。默认网格的实际试布 109733
接收相同 handoff，730 根网均报未找到网格接入。试验回执 `native-route-109733.json` 的
SHA-256 为 `da71d1ab752e973bb1c94265f63309020f68c8e0ab7bcd6c0416c19094870fa4`。
物理后续使用同一份输入测试细接入网格。样本的 WAIT 以整个 scope 的结束为单位。
scope 内的 K128 输入窗口交付、权重 DMA、Gate/Up 到 Mid 的阶段协作、主控装载和确认网络
还须在 main 共同底座上落地；整图服务、KV 追加及真实 token 退休仍需完整 #260 请求执行。


## Algo1 原生命令的数据面准入

`native_service_routes.targets[].routes[].requires` 按目标和命令签名声明必要的物理需求 ID。
Algo1 在选候选之前核对需求及其依赖的端点。选中服务时，把相关需求计入同一方案的
线束并集。缺少端点时，服务给出具体的需求 ID。端点齐全进入试布和后续物理验收。

远端 109781 用 109741 的真实首层三 P 方案复查同一候选摆位。以 main P2545 的 DEF
和 ODB 散列、原生 DMA 端点清单及逐位逻辑接口对照九个需求包。每个 P 有 678 位描述符、
684 位权重和 86 位 FENCE。P 侧描述符已有 647 个组级 M10 端点，另外 31 个通过
同一原生导体的别名接入。每个 P 仍有 770 位权重和 FENCE 需要从原生叶端点引到组边界。
候选中缺 DMA 实例和 4,344 个对应的 DMA 侧接点，另有 18 项常量连接待落实。
加入这些真实需求后，Algo1 拒绝该候选并列出九个缺项。需求仍处于端点绑定阶段。

复现入口 [audit_native_dma_prerequisites.py](audit_native_dma_prerequisites.py)。
依次输入远端 `native-same-plan-109741`、`../joint-ddr-4C8sHe`、原联合摆位的
`packet-pdma-contract.json` 及新输出目录。前两个目录相对于远端编译目录
`framework-r11-CatJ8r`。第三份输入位于
`/public/home/yuzelu/project-circuit/issue185-joint-packet-dma-bound-20261113-01/`。
输出 `base.json`、`hardware.json` 和 `compile.json` 保留搜索诊断和逐位需求。

细网格试布 109758 对 109741 的 730 根控制网布通 27 根，按研究几何规则核对。
其余 174 根未找到网格接入，521 根耗尽扩展预算，8 根在本次搜索中未找到路径。
这份回执仍待产品级布线和验证。旧拓扑上的严格 #260 运行 109409 独立推进。

| 远端产物，位于 `framework-r11-CatJ8r/` | SHA-256 |
| --- | --- |
| `native-dma-prerequisites-109781/report.json` | `1326876127ddbe6c9937c60955946538cbbd1ba1219e45bc7a7eda8a7c93e9e8` |
| `native-dma-prerequisites-109781/compile.json` | `fd2065623339a9641d3277c1ce2370b8e9b26cb6d976e19e6bbac3af2742e757` |
| `native-route-109758.json` | `9eaed1c3c78504d2030afeb18d5a5770b88df3965629743fc5052499178acd9f` |

远端 109782 通过全部 410 项回归。日志 SHA-256 为
`bf907ee4136057850f5c66a3ba30804a5e373fa33b0faf294f71ae9c25632200`。
通用准入回归覆盖缺需求、真实端点闭合后重新准入，以及所选命令在同计划输出中
登记需求。现有候选摆位无独立 DMA 宏的轴对齐矩形空间。同一 main P 版本的下一步是
核对 DMA 有效物理接点和组边界逃线，再验证一版带足够空间的共同摆位。

### DMA 低层接点与上层接入

远端 109786 读取 109781 所用的 DMA-v45 与 main P2545 原始 ODB，
核对每个逻辑端口的既有 BPin 坐标、层和方向。DMA 一侧的 4,344 个接点
全部已摆在原生层，其中 2,210 个在 M5、2,134 个在 M6。描述符的 2,034 个为
M5 1,246 个、M6 788 个。权重的 2,052 个为 M5 961 个、M6 1,091 个。
FENCE 的 258 个为 M5 3 个、M6 255 个。P2545 的 647 个 M10 及 801 个无
独立 BPin 的端口和前次清单一致，其中 31 个描述符端口已有同导体别名。

远端 `framework-r11-CatJ8r/native-dma-pin-access-109786` 留有逐位坐标
`dma.tsv`、`p.tsv` 和 `report.json`。报告 SHA-256 为
`be01e43faf23a1a44573639b9748f128a94d08b3c161ddd65425c553637eeeff`。
`audit-dma-existing-pins.sbatch` 与 `audit-dma-existing-pins.tcl` 位于同一
远端编译目录。下一次物理试验可从这些已摆低层接点向 M10 引出，
核对实际连通和间距，然后把通过的几何与共同摆位一同交给 Algo2。


## 含数据面的三 P 同计划接口试验

109804 核对 main P2545 的 770 路权重与 FENCE 端口。每一位属于一个组边界 BTerm
和一个单独的 M10 叶端点，组级 ODB 无既有连接线，也无其他叶或标准单元接点。
按原始三个 P 的摆位变换，逐位登记 2,310 个真实叶端点。此输入用于
直接从叶宏 M10 向上接入的试验。端口附近的间距、可接入性和连通仍要检查。

采用原 DMA-v45 摆位，按其 4,344 个已知逻辑端口生成待验证的 M10 端口计划。
九组与 MC 坐标沿用 main。为独立 DMA 位于原 P2 以东留出空间，DMA 原点
取 `[9576000, 0]` DBU，给 P2 和 DMA 的外框留 `100000` DBU 间隙。
候选右边界扩到 `13596000` DBU，原边界为 `11726000` DBU。
`route-contract/1` 的 `staged_source_views` 模式将源 ODB 和端口计划分别绑定到
真实散列。仅允许 candidate 范围，端点归属仍按组校验。正式冻结和产品范围的
物理视图要求继续生效。109818 的四项反例覆盖假冻结、产品入口、缺失计划和缺失实例。

109815 从同一真实首层三 P 算子计划生成控制、描述符、权重与 FENCE 需求，
导出 4,981 根物理网和 10,300 个接点。Algo2 的实际读入器接受 interface 交接，
按 400 DBU 局部网格枚举，每个接点都有至少一个候选位置。路由结果另由 109817 检查。
新 DMA 的 M10 shapes 是计划位置，需通过独立原生层布线，接点的网格枚举仅检查几何入口。

109816 独立读回同方案的母控与局控编码。对照已有 scope 的真实描述符，母控、
三份局控与 24,576 B 描述符逐字节一致。固定 #260 `1ea06be2` 读取一页、192 条
CALL、64 组 WAIT。结果范围为接口编码，原生层数据连接和整图运行仍未验收。

| 远端产物，位于 `framework-r11-CatJ8r/` | SHA-256 |
| --- | --- |
| `p-v2-direct-m10-109804/base.json` | `c223edb790a7864af751bd2e8cba782a46a2ade84e171c29ea3b53b9e15f5745` |
| `dma-m10-global-109793/landings.tsv` | `ec4ecb7d4f0bf7c6a7b31d59af06d02141aa8089d5015ce93c1b2b9050d718cc` |
| `draft-native-dma-handoff-109815/summary.json` | `11ddad9cc2a0546f0b54f214e38effd59c2f0144f6d7d3451439c5fe06251519` |
| `draft-native-dma-handoff-109815/requirements.json` | `8e736fbe37ec14b54b4e64fc56ec707715bf7a203c66b949be110665bae14a38` |
| `draft-native-dma-handoff-109815/algorithm2-input.json` | `b808e867cc75f24a628fae0692b2f6ac9c17ad42de54c9b31be12a89e12f602c` |
| `staged-dma-native-109816/summary.json` | `4b406f6ec480fa4a83f553c695ea83cea5f95316fcc29f10697957988b34ef31` |
| `regression-109814.log`，410 项通过 | `b5eb30d5860a03a37efbfe067e07820a10c224f6e523711af90805f7d3cdc916` |
| `dma-staged-gate-109818.log` | `a756519c70bcffc427880c4394a4b362a28aa888c9645b9fa9fd446d337afd23` |

复现脚本位于 [dma-m10/](dma-m10/)。作业输入还使用上节锁定的源 ODB、逐位表和
三 P 存档 scope。当前原生层试布保留全部 DMA 实例与原始逻辑，只在新的物理试验副本中
分配 M10 端口。整图仍需动态 token Gather 的真实 DDR 至 U 服务、后续完整服务映射、
真实 KV 和 token 退休。109409 是旧拓扑的独立严格进度。

## 七点模型复核与整图缺项

远端 109837 在同一资源和阶段时长下复现整算子屏障 16 拍、tile 发布后交接 12 拍。两个
输出 tile 的峰值活跃量是 32 B 和 16 B，物理窗口分配保持固定。10 拍的独立完成命令对照
采用另一份假设接口。只接受命令完成的后端会拒绝两个提前发布的等待边。
109838 在同一候选池内加入同通道背景搬运，单宏／双宏从 24／16 拍变为 24／29 拍。
这两组数据使用声明的资源模型。109839 的八项回归覆盖区间填空、信用跨阶段持有、旧请求
重计价以及 KV 写确认后才允许覆盖和读取。DDR 快照中按通道预留的近似与共享控制器
逐请求重放分别用于不同计价入口。

普通类型化图 lowering 现在一次返回所有缺少绑定的节点及其类型签名，保留首条
`reason` 和输入图、硬件散列。无效数据依赖仍直接失败。缺少绑定的图不产生计划和执行输出。
109846 用归档的 1,084 节点 prefill 和 1,156 节点 decode 浮点图检查覆盖报告。使用 Gather 专用
候选表，decode 仅为诊断声明了形式输入的 DDR 后备。该试验用于检查报告，整数移植状态由
独立的命令审计提供。

同一次审计将 #260 封存整数请求的 21 项完成合同匹配到 16 个目标／头部签名，逐项与 main
解码审计及 8,273,243 个 CALL 的统计核对。2,876,395 个 CALL 的原描述符被当前 P/U 入口
拒绝，5,396,848 个只有头部匹配。Gather 对应 U0 的 `(3,7,4)`，639 个 CALL 需要
`destination_commit_ack`。替代服务还须连通真实数据路径，并验证该完成语义。

Algo2 109817 实际试布同一三 P 方案的 4,981 根网。在一轮、每网 3,000 次扩展预算下布通
8 根，48 根报告接点搜索失败，4,925 根耗尽预算。结果保留为接口范围，待解决真实 M10
接入及上层寻路。109793 在原生层全局布线时超时，依赖它的详细布线未启动。

| 远端文件 | SHA-256 |
| --- | --- |
| `seven-point-review-qYmOkT/handoff-109837.log` | `a4ea63bd4b848de339e1261f6775934a1e97939cd173e9e8d10e036533f86db3` |
| `seven-point-review-qYmOkT/placement-109838.log` | `fc4f6b36fd6c4c9c063f75641907eef9d5aaa034ed2fcc5e0238b77f39ca5a98` |
| `seven-point-review-qYmOkT/coverage-reg-109844.log`，410 项通过 | `f297896809f908baec67dbb893d0100680453622e0ed14b34a2839c00282c95e` |
| `seven-point-review-qYmOkT/whole-graph-coverage.json` | `f39aefaf19f2e082cf3fc9d93d6bd0660bc02d5878936d8754958adee8f90bdf` |
| `staged-dma-upper-109817.json` | `66d3f896d38d5ddfd3a806950902839bd827d0b7555cd15a4450a326baca0e25` |

## 原生 WAIT 准入与 DMA 接点实布

执行输出启用完成级等待限制。前沿扩展建立重放意图后，若命令间的依赖无法由
目标 ABI 在发令前等待对方完成，则舍弃该扩展并保留其他候选。纯计时模式仍可研究内部
阶段交接。导出器保持独立复查。109870 的同池测试中，11 拍的模型方案需要提前发布事件，
16 拍的方案让发布事件成为命令完成，输出了对应 WAIT 及同源线网。仅有 11 拍候选时不产出
执行包。新测试与原有 410 项远端回归均通过，109897 项目结构检查通过。

DMA 原生侧使用 109793 已验证的同一摆位数据库与 M10 接点清单。109857 只对 4,344 个
数据端口网络生成全局导引，全部有导引。109860 对这些网络做详细布线，4,344 个 M10
BTerm 的位置及方向不变，逐端口有布线对象，内部路由 DRC 报告为零。该作业范围是独立
DMA的数据接口。时钟、电源、其余网、提取时序及整个底座仍需各自的物理证据。
109893 用实布数据库和端口记录更新候选清单，重新从同一三 P 计划生成 4,981 根 Algo2
输入和固定 #260 的母控页。两端读回同一份计划散列，192 次 CALL、64 组 WAIT 及归档
指令字节保持一致。产品资格仍未建立。

针对先前 109817 的 48 个接点失败，109851 用原端点集合复算。48 根在加入已布上层铜线前
均有独立合法接点，加入后候选被挡。109894 将这些点反查到逻辑需求，25 根属于
P2 描述符束，另有 P1 描述符等。每个受影响端点及其逻辑束见远端报告。预算耗尽的其余网
需要进一步搜索，现有结果未证明几何不可布。

109882 用 main `7a809d1e` 的 C/U 源与候选成品视图核对真实 Gather。
C0 的发送数据来自本地 S；U0 在部署状态下检查单个已预留的 16 B 地址；目标写 ACK 后，
RECEIVE 回报 16 B 并释放预留。C0→U0 的 153 个逻辑信号有相应端点，候选中仍欠
运行时索引到物理 DDR 行的服务及 C0 的数据填入路径。历史拓扑的 105791 已验证真实
prompt 行取数，一个 8 KiB 行有 128 个 DDR beat 与 512 个 SRAM 写 ACK。封存合同的
639 次 Gather 中，512 次取 prompt DDR 索引，127 次取上一退休 token；两类都须在
新底座保留。U39 仍拒绝直接复用老描述符。独立旧拓扑 109409 仍在 prefill，尚未见 token 退休。

远端根目录为前述框架工作目录下的 `ingress-route-iN0LbH`。

| 文件 | SHA-256 |
| --- | --- |
| `wait-admit-109870.log` | `2fd12ca309fb8089ab885eb3e9b61b4439605608db26ee22095a86f948b94987` |
| `drt-ports-109860/routes.tsv` | `fc2e401fb06f64d6876a0a2876504ac11444bad75f6f7859744d957a5bdf4cb2` |
| `drt-ports-109860/dma-detail.odb` | `1d14a88f851aab79c3747f93c54cc067603d4b8c153ac6a8e2a2b0a24f0893f6` |
| `routed-handoff-109893/summary.json` | `7132f4a7ff3689ef08d30740a4e4d7c2800407d3d94acd2ef6a9a7dc9f218651` |
| `routed-native-109893/summary.json` | `4aa08522da6a600f0d8057000d31f5aa1037ee25639ae15caf85f2803cc17d3c` |
| `routing-impact.json` | `057840d00731ce0e918ece03b8f282e38ce3e2a58f2de4b2ef5b083b20cd2d08` |
| `gather-ingress-audit.json` | `4231790e8b1d621d63b93249d0edaf0d5bdfc398f9b2c6afa21fba32cc240fe1` |

## C0 到 U0 的逐字提交与试布回执

Algo1 按 `u-stored-link` 只接受单个 16 B 对齐字，两端地址范围均为 0 至 16368。
独立验证器重复检查该约束，物理接口禁止把这类端点映成 DDR。发现单条候选过宽时，
搜索仍可选择其他合法路由。109968 通过 413 项远端回归。

109992 从同一 Block V2 C0→U0 端点候选出发。单字原计划指令及端点保持一致，
直接把一个 8 KiB 词嵌入行放进单次预留会被拒绝，去掉约束的控制组会错误接受。
已放入 C0 SRAM 的一行拆成 512 条分片 COPY，每条等目标提交 ACK，消费指令等待该分片。
Algo2 独立读回与控制 IR 同源的计划，静态成员 858 个，待布信号网 734 根，与单字的端点规模一致。
这项实验验证算法排程与 Algo2 接口准入。它从源 SRAM 已有完整行开始，下一步需让真实
运行时索引经 DDR 取得对应行，再打通 #260 指令编码和动态执行。

源码和归档描述符对账表明，固定 #260 在字节 4–5 读取 128 字节描述符长度，main C/U 的
本地服务在同一位置读取 257、258、259 三个 stored-link 操作码。目标要先预留地址，源发送
等目的 SRAM 写入 ACK，随后目标 RECEIVE 报完成并释放预留。此处需要把外层 CALL 合同
映射到目标局控的本地命令。当前直接复用两份描述符布局无法表达它。

同一 4,981 网 DMA 试布以同样的每网搜索预算比较两种接点选择。109947 基线几何通过 8 根，
109946 贪心预留仅通过 5 根。109978 单独分配落点时，10,300 个端点中有 8,982 个获分配，
1,318 根网至少缺一个落点。回执用于识别局部接入问题。搜索未找到路线时，Algo1 的重试要求显式
指定要试排除的网，记录原失败码及非硬约束属性，并在重排后生成新的同源指令及网表。

远端目录仍为 `ingress-route-iN0LbH`。

| 文件 | SHA-256 |
| --- | --- |
| `route-abi-109968.log` | `724bd71623838e50302aea08d69dab33ccb7d8ae9b0c25c4aa6439c8b9a9831b` |
| `real-stored-transport-109992.json` | `893bc64bff697aeac7a82cd841485f7c929e68734f9c8a15d2ee0437e4b25ae2` |
| `real-stored-transport-109992-fragments.json` | `c2edc75f1bb0eea065ddfb1b5ca4ef4a3608e8ed1dd01ac63b96fbad64640d99` |
| `escape-route-109946.json` | `9a0e415d475154bddc0e842893a277af6ff6c585bd3e6f8348084cd6d55522fc` |
| `escape-route-109947.json` | `165905570386978513fc71fc373ed1b3cdd15cbe1085dc4c787b3a9e15799f23` |
| `escape-route-109978.json` | `03242bcd7d960c3822f589227ccf35d97438bdfae363eb729f8d8812b765e7a2` |
| `stored-word-native-boundary-109992.json` | `ce4064231cc0dd0a4ab1e7a23b7d391e74617a05d09ee4e35e8512bb59860856` |

## C/U 存储链路的局控编码与动态查表入口

109992 的 512 次 16 B COPY 来自同一份已核对计划。远端 110079 重新生成控制和连接需求后，
以已归档 C/U 存储链路使用的汇编器为每次 COPY 生成两个局控 PM 片段。C 执行 SEND，U 执行
RESERVE 和 RECEIVE。两端局控可同组发起，U 的地址预留生效后才可接收数据，源端以目的 SRAM
写入确认结束发送，后续复用等待两端结束。生成 1,024 份镜像，单份最多 496 B。读回核对原始
执行记录、地址单位和完成事件，另拒绝了角色重复、弱化完成条件及地址不对齐三种错误输入。
512 个消费占位操作仍待原生绑定。

固定的 [#260 页执行入口](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/260)
读回边界复核拒绝这些 PM 内的 1,536 条旧局控执行记录作为外层 DDR CALL 描述符。每个目标
各需 512 份不同的 PM 片段，本次请求装包器要求同一阶段内每目标的常驻 PM 字节一致。这个回执
提供局部编码和读回证据，完整图还需绑定可长期驻留的本地服务和运行时输入接口。

远端 110045 在上述候选的 C0/U0 网表与联合 DMA 连接合同中核对接收端点。已绑定的 DMA 数据路径
仅至 P0/P1/P2。C0/U0 有片上数据接收与写确认端口，合同中没有把按 token 索引读出的 DDR 行送到
这些端口的适配路径。封存索引表含 512 个 DDR prompt 输入和 127 个来自前次退休的输入。下一步
需要以这些运行时来源驱动已校验的 DDR 行地址和传输，再发布目的 SRAM 的存储完成事件。

复现脚本为 `audit-ddr-ingress.py` 和 `verify-stored-link-control.py`，使用
`ingress-route-iN0LbH/native-stored-tpmuEH` 中的 Slurm 回执。项目结构检查 110080 通过。

| 文件 | SHA-256 |
| --- | --- |
| `ddr-ingress.json` | `4aca2d8a8c713613fbcab7802549055958984aad4bd17794ad2a48782ad87d1a` |
| `control-110079/report.json` | `abb68bd9d5d6e8be0d4165b6f857a5c7299d71b6cdbefd713212dd90ce68b46f` |
| `control-110079/stored-link-pm-manifest.json` | `f1b06533f90579f149d33367760de7a00852ac51ab84d0ac52b1bf6d5fffce43` |

## 从已链接的查表指令生成运行时索引表

`event_request_ingress.py` 依据选中的 Gather、已链接 CALL 的内容和母控页位置生成 #260
的 `input-index.tsv`。校验计划身份、目标、字节地址、表范围、CRC 和目的端写确认语义。
Prompt 指向真实 DDR burst 和索引所在 lane。Decode 记录上一 token 的退休来源。
`export_native_tlm_pages.py` 可直接封存单页或多页 prompt 片段的索引记录。
整包回归由每个封存 stage 的 proof 找到其母控页，每项均与整包内的 CALL 和描述符核对。

远端 110128 从 639 份已链接的 Gather 重建索引表，与参考整包逐字节相同。
其中 512 条来自 DDR prompt，127 条来自前一次退休。偏移、计划身份、CRC、输入来源及重复页
负例均拒绝。110127 让旧拓扑的 #260 后端执行了新导出的首个 prompt 页，
收到 141 次实际 DDR 回调，落地 4 笔输入索引写和 512 笔结果写，结果与实际权重镜像的 8 KiB
行一致。其余索引记录验证覆盖的是封包对应关系，尚无该次整包的新退休记录。
远端 110129 的项目结构和 413 项回归通过。

110130 对同一候选底座的 v45 DMA 与已声明的 M10 接点做静态核对。现有合同使用客户 0、1、2、
9、10、11。逻辑客户 3 至 8 支持按 128 B 对齐的两拍请求，当前端点目录缺这些客户的 684 个
请求、返回及关闭信号成员。真实 8 KiB 权重行可以按 64 个双拍记录发出，在两个通道各 32 条。
就支持两拍的端点读取单个 prompt burst 时还会读相邻 64 B。没有将这些逻辑客户选入产品计划，
地址产生、端点引出和 U.S 写确认需要同一个实物服务合同。

远程目录为 `ingress-route-iN0LbH/request-ingress-6BvrlA`。

| 文件 | SHA-256 |
| --- | --- |
| `receipt-110128/report.json` | `f25879ea94c8615511665f6fc0eec03c66f2bf8c503a8f0c5b7197d6f11ce41c` |
| `timed-110127/report.json` | `37d744fff2f3ebf1ac51561f2cc9e07a07371dd3c275d7198419a9951a13f266` |
| `regression-110129.log` | `0b38944e4bcf598f86be19e01da45ade2a5b995b5aa3ac3cb7b82b5b01dd58a0` |
| `lanes-110130.json` | `7b9f2b5745e3de7ed46b916e90b4b07bae880efb42858137ade87be15da95147` |

## Gather 的 v45 DMA 接点与双拍请求

110151 在源摆位中找到 client 3 的 684 个不同端口，均有内部端子和唯一边界端子。源接点位于 M5 的有 414 个，位于 M6 的有 270 个。110152 保留前次 4,344 个 M10 接点的坐标并生成合计 5,028 个布线引导。110153 在独立 DMA 实例内完成这些端口的详细布线，全部端口有线对象，最终 DRC 报告为空。

110165 校验详细布线文件后，将新增 684 个接点导入既有候选底座目录。110170 重新生成原三 P 对照的同一计划，Algo2 独立读取 4,981 根网，待布引脚、线网和障碍几何一致。110176 从同一计划和同一物理底座散列生成固定 #260 页，由读取器核对 192 个 CALL、64 组 WAIT，归档描述符和母控指令保持字节一致。首跑 110175 已写出读回摘要，作业因脚本核验文件名写错而退出。修正后完整通过。新增端点是 DMA 侧物理事实。本次没有新增 Gather 服务到 `native_service_routes`，也没有生成带占位对端的 Algo2 线网。

110160 用 v45 client 3 的真实约束编出每条 DDR record 的两次 64 B 请求。两次请求依次使用同一 tag base、连续 64 B 地址和相同通道。源 RTL 在接纳第二拍时自动关闭该 record。512 条 prompt 索引都选择到正确的 burst，另外核对 127 条上一步退休来源的表记录。按第一条 prompt 实际回调取得索引，再用它读真实权重行，对照收到 130 次 DRAMsim3 回调，其中行数据为两个通道各 32 条双拍 record。SRAM 模型在确认全部 512 个 16 B 输出字后才报告完成，8 KiB 与真实权重文件逐字节一致。6 项地址、跨度和标签错误被拒绝。首跑 110159 的验证器误要求 prefill 各位置的 page 都为 0，改为按 `(step, page)` 检查顺序后通过。

候选底座的 U0 已有逐字存储链路，在部署期间一份运行时 reservation 只接受一个地址。保留现有协议时，整行需要逐字获取所有权。新的可常驻 Gather 服务需要为整行持有地址窗口，读入实时索引，发出合法 record，并按目的端逐字 ACK 结算后再发完成事件。该服务、两端实连及 #260 的同计划整图退休仍待验收。110160 的格式回放使用 #260 归档后端的 DDR 与 SRAM 模型，范围为一个 prompt 位置，未接入 Block V2 局控。

远端目录

`/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/framework-20261114-akeox2em/full-graph-zwl0Tr/merged-bmMd5X/native-request-6WI0tH/framework-r11-CatJ8r/ingress-route-iN0LbH/gather-block-v2-skqxd3`

| 远端文件 | SHA-256 |
| --- | --- |
| `detail-110153/dma-detail.odb` | `9d4cc09be229a6683679bee0f4261c678c74f3f0d13207a9c6c167c29f03bde4` |
| `detail-110153/routes.tsv` | `15a8d78bf1fd9cc2d9952848cd7b48c2c6dafb4cc4a4b42e9a628f08c969fcbd` |
| `format-110160/report.json` | `24b90f1d7dd18d37c34a2585544dfc92f74bc6cb3f72c1cb495c38a00de525f4` |
| `base-110165.json` | `86bb713f56abdccf770b321a4a74f480e4846d82d33e30dc99679289c3ac6f43` |
| `algo2-110170/summary.json` | `54c865f8598ef464c1ded22917c0c15dfc39d2a0e4cf5ec4587b04380f31ad3a` |
| `pinned-native-110176/summary.json` | `aaa68ec3dd630939cbb4e98f5be781e8926d5465d0269d7724bd1aeb1c4e1649` |

## U0 Gather 的局控程序和两端布线交接

以 main 已审计的 U 控制源码和 v45 DMA client 3 构建独立候选。Algo1 将选定的
`INDEXED_LOAD` 编成 version 2 局控程序。程序区为 352 B，依次执行 `L_EXEC`、
`L_WAIT` 和 `L_END`。服务从私有 SRAM 读取运行时索引并持有互不重叠的输入与结果
窗口，按双拍请求从外存读取 8 KiB 行。标签允许一条 record 的两拍乱序返回。最后
一个 16 B 目标写 ACK 后才报告完成。单条命令中的访问节奏由服务控制，Algo1 输出
受目标提交约束的等待。

110195 用旧链接描述符独立核对字段和完成条件，拒绝四个错误候选。在原接点目录上，
650 根网只有 DMA 端可绑定。110208 对 639 条已封存计划逐条核对新编码，涵盖 512 条
prompt 位置和 127 条上一 token 来源记录，共生成 16 份不同的局控 PM。

110275 通过真实局控、v45 DMA 和目标 S SRAM 检查首个 prompt 的 Gather。110286 又通过
U0 外层四拍 CALL 接口执行同一镜像，使用单银行程序 SRAM，验证回传四拍中的任务标识和
完成状态。用例从封存 prompt 提取索引 840，测试端通过 DMA 后端供给真实权重行并打乱
双拍返回顺序。128 个回传和 512 次目标写确认全部到齐，SRAM 内容逐字节核对。没有生成
波形。这里使用测试端预装索引和供数，产品运行仍需母控指令启动的索引交付及实际 DDR
后端。

110281 在相同的 U 逻辑边界和已归档 PM 银行实现上完成综合。110293 使用 U39 外形和原
叶块位置完成候选摆放。保留 1575 个现有逻辑接点的位置，分配 650 个 DMA M10 候选接点。
45 个常量输出逐位实例化 tie cell，保持独立可绑定的驱动端。旧版叶宏导出接点仍用于几何
避让。110302 从 OpenDB 核对 650 个不同信号和 M10 矩形，并生成这 650 根网的全局导引。
下层详细布线在 N32 的 `s_req_address[1]` 处报无法接入，尚无经详细布线验收的 U0 接点。
详细布线用副本移除无几何的边界对象及内部共享常量。完整候选网表和摆位凭据保留。

110305 用新端点和 DMA 实布端点重新选定 Gather。同一份计划输出 650 根数据连接和
352 B 局控程序，Algo2 `--handoff` 独立读回 650 根网与 1300 个端点。
发布的 PM 与 110286 执行的镜像逐字节相同。交接限于 Gather 数据接口，此处
未发布产品布线或 #260 可执行整包。110306 使用 Algo2 原入口试布一轮，每个候选最多
2000 次扩展。1 根通过研究几何检查，648 根耗尽预算，1 根报告接入搜索失败。完整结果
`algo2-110306.json` 的 SHA-256 为
`39773e190559e7ec0b43284c38d6729fa87658695c4c48a6a3d55dbd106ec337`。
在明确的 N32 接入错误后取消 110296 的详细布线作业。

远端目录为同一框架目录下的 `ingress-route-iN0LbH/resident-gather-HefhYQ`。
[候选源码与复跑入口](gather-v2/resident/README.md)。

| 远端文件 | SHA-256 |
| --- | --- |
| `request-110208/local-sidecars.json` | `4186ab8c4081b543d53891aab5daa322b39f6ad59cdbb277891b354134865e16` |
| `frame-program-110286/result.log` | `8e48f217953cdb502bb47e7a03e27db1420a150daec50254f3ba435fdc240312` |
| `frame-map-110281/mapped.v` | `301558e7e68511ae4197b0b961df31e451099d262fd93abaf80d245ff251904c` |
| `frame-place-110293/staged-u.odb` | `0ac468bec1cf2b067b909ea719e3e6149fc7334ae29690c3eb6b8fb3b4a9d303` |
| `frame-route-110302/staged-ports.tsv` | `ff84e707cbbbf1de854cf1be53082a58706ea77cd7abf7b3b54a1239c970c120` |
| `handoff-110305/algorithm2-input.json` | `ca19846eb67f2184b213bbd8e37dca496c8c63ddc78f1be99cf4d351764f1378` |
| `handoff-110305/summary.json` | `498dcfc3276e136729ed47176dbc68a461913d3535a9b6c5994d87cf61e87407` |
| `handoff-110305/local.pm` | `1b7ffac566df3c40a25bed6f91ba12003db9982b38726a6c3f2e6bb90479c304` |
