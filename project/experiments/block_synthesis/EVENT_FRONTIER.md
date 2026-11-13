# 按执行状态计算 Block 综合代价

Refs #219。以 #220 的 05602e4316dad898e19a31f49bbd19e2a6ab8b78 为基线。#251 的回归证据固定在 9abd46f5cbb4534bcfc614571ccd6d402ad11882。

## 实现与输入

现有覆盖前沿提供可选的事件执行模式。输入可以是带有硬件资格配方的算子图，也可以是内部任务、候选及硬件。事件模式的候选描述已资格化的阶段、输入片段及目标窗口、输出片段及写入窗口。硬件声明每个 S 的容量和窗口物理区间、每项服务的时间与资源、允许的 COPY/DDR 路径、并发容量、初始副本及静态线束约束。片段 ID 对应同一不可变值及表示。量化、转换和重排需要登记为计算服务。COPY 可以检查源和目标站点，要求值的身份保持一致。

每次从同一个前沿扩展候选时执行以下顺序。

1. 查询所需片段的当前副本、就绪时刻和窗口占用。有本地副本时可以直接消费。可达的片上 COPY 与有真实路由的 DDR 路径分别生成后继，按整项动作的完成时间、字节和静态网代价比较。候选可显式要求片上交接或 DDR 后备。
2. 预约本次事件实际使用的资源。DDR 路由可按请求、数据和 ACK 三段分别占用资源，并在整个期间保留信用或描述符槽。信用冲突后在第一个可尝试的边界重新计算三段预约。时间采用整数拍。端口、信用、容量、静态网预算和驱动互斥都是硬约束。
3. 复制源保持到目标 ACK。目标副本在写完成后可用。覆盖仍有消费者的唯一有效 S 副本之前，需要获得有效 DDR 后备。已经用完的临时值可以释放。全程检查真实窗口与存活期。
4. 用事件的完成时刻更新排程，用实际 DDR 读写事件更新字节，静态网用并集更新。DP 和严格贪心调用同一个转移。状态合并包含未来资源预约、片段副本、后备时刻与静态网。只有所有未来动作都无法回填的早期预约可以从搜索状态丢弃。

事件预约采用固定已有预约的插入策略。前沿可以选择不同的就绪任务顺序。一次转移内部的资格化阶段可声明 id 和 after 来表达并行分片及汇合；原顺序表仍按顺序解释。搬运可以占用阶段之间的空隙。DDR 当前按硬件声明的阶段和有限信用建模，历史预约在转移时保持原时间。需要改变已预约请求的优先级时，应在搜索中改变决策顺序。动态重排已预约请求、DDR 行缓冲和逐 beat 争用需要更细的服务合同。当前使用固定的物理 S 窗口，其他分配方案可由候选提供。

独立检查器从计划事件重建资源占用、数据写入和读取、COPY/STORE 的源保持、DDR 后备就绪、覆盖、字节与静态网集合。它不依赖搜索器的副本表和累计代价。单测另用逐拍参考核对 800 次随机容量预约。

## 调用

事件 IR 是编译器内部格式，包含 `tasks` 和可选 `covers`。硬件以 `event_model.kind=qualified-event-model-v1` 选择事件模式。现有 ONNX 和全图入口保留原有路径。

```text
python project/experiments/block_synthesis/run.py MODEL_IR.json HARDWARE.json NEW_OUTPUT --event-ir --event-width 8
python project/experiments/block_synthesis/run.py MODEL_IR.json HARDWARE.json NEW_OUTPUT --event-ir --event-width 1
```

宽度 1 的贪心每步只选一个后继，和多状态前沿共用同一个候选池、阶段预约和线路选择。比较时固定硬件配置、候选池、输入和连接预算。按完成时间、DDR 总字节、静态网代价依次比较。对比新旧成本模型时重放同一动作序列，并分开记录执行能力与搜索策略的收益。

## Qwen2.5-3B 三 P FFN 回放

复用 #251 两套已归档 RTL 日志，按已登记的 SHA-256 验证归档并读取同一试验的描述符与原始 `K_PROFILE`。每例按实际三 P 并行的 scope 边界回放 928 次 Gate/Up 和 516 次 Down 的 K128 准备、COPY ACK、源窗口释放。X 的 16 个 A16 分片沿用原 U.S 地址，86 个 Mid 分片按 29／29／28 留在原三个 P.S，Down 的 512 字结果按描述符留在各 P.S。两个阶段报告里的计时边界余量单列入各自的末尾；阶段内使用真实 COPY ACK 时间差。

| RTL 来源 | 压力模式 | Gate/Up cycles | Down cycles | 严格贪心 | 宽度 8 DP |
| --- | ---: | ---: | ---: | ---: | ---: |
| 102603，early | 0 | 586103 | 263811 | 849914 | 849914 |
| 102603，early | 1 | 658258 | 283649 | 941907 | 941907 |
| 102604，baseline | 0 | 590628 | 269574 | 860202 | 860202 |
| 102604，baseline | 1 | 664099 | 284527 | 948626 | 948626 |

每行使用 seed 25001，独立核对初态 0／1／2，共 12 例。每例重建 44,544 字 Gate/Up COPY 和 24,768 字 Down COPY，模型中的激活 DDR 为 0 B。另从 192 个描述符及 DMA 返回总数独立核对 71,884,800 B DDR 读取与 96,256 B 片上写确认。归档给出 K 切片和总计数；权重各 beat 的发出及返回时刻未被投影成可重调度的事件。回放沿用该 fixture 的 admission 顺序和真实阶段间等待，两种搜索均展开 64 个候选。测得搜索时间约为贪心 0.17–0.33 秒，含贪心保底重放的 DP 0.34–0.71 秒。提供器之间的周期差来自 RTL 配置。

```text
git fetch --no-tags origin task/250-w8a16-base-contract
python project/experiments/block_synthesis/benchmark_event_ffn.py ARCHIVE_102603 --job 102603 --mode 0 --initial 0
python project/experiments/block_synthesis/benchmark_event_ffn.py ARCHIVE_102604 --job 102604 --mode 1 --initial 2
python -m unittest discover -s project/experiments/block_synthesis -p test_*.py -q
```

归档索引位于 #251 的 `work/YUZE-LU/250/native-services/ffnnative/index.json`。运行器从固定提交读取独立汇总与 SHA-256。#220 的 R24 真实权重边界回归也已按原流程复跑，21 条有限 S 数值轨迹通过，独立重核四初态共 36 份已冻结 RTL 日志和错行／错 K 负对照。新产生的 FFN 事件表是排程回放，未重新生成 RTL 控制镜像。

## 算法效果和后续验收

同候选池的定向测试中，贪心选了先完成但远离消费者的生产绑定，总计 12 拍。DP 保留另一条前沿，在消费者目标 S 直接生成结果，总计 9 拍。禁用片上路由的用例会生成真实 STORE/LOAD，并分别计 16 B 写和 16 B 读。共享通道压力用例中，DDR data 阶段等待通道，issue 已发出，信用一直持有到 ACK。相同工作与字节产生不同完成时间。

固定 Qwen FFN 回放的 DP 收益为 0%。要量出整段算法收益，下一步需要从 #251 的原生指令和服务合同生成能改变 admission、并发分片或权重请求顺序的候选，独立核对各候选的整数数值、ACK、资源和真实 DMA 时序，再在同一套硬件和候选上比较。完整模型、程序部署、SystemC、能耗和 token/s 需要各自的验收。


## 算子图、程序与布线需求

```text
python project/experiments/block_synthesis/run.py MODEL.json HARDWARE.json NEW_OUTPUT --event-graph
python project/experiments/block_synthesis/run.py MODEL.onnx HARDWARE.json NEW_OUTPUT --event-graph
```

算子图用与 ONNX 导入器相同的 tasks、values、inputs 和 outputs 表示。ONNX 入口共用 #220 的图规范化。硬件的 event_model.recipes 按域、算子、属性、输入输出形状和数值格式登记绑定。阶段可引用 in:0、out:0、tmp:名称，并将它们绑定到物理 S 窗口。片上初始数据、外存后备、宏和传输资源、实际控制站点与线束模板由硬件合同提供。生产程序应使用实际资格化的服务。test_event_compiler.py 包含完整配置样例。

编译输出 program.json 和 wiring.json 均带选中计划及硬件的哈希。主控描述各操作的参与局控及完成依赖，局控描述读写地址、服务、传输和存储确认。同一条线束的每次动态使用都追溯到对应控制序号，静态逐位端点只展开一次。连接组可在 nets 的 signals 中登记 driver、sinks 和位宽。缺少端点模板的组会在结果中标记。

- 用 --event-route-base 和 --event-route-module 可调用项目现有路由合同生成 requirements.json，绑定使用的物理视图由路由合同校验。
- 用 --event-prior-result 和 --event-route-feedback 可按上一次选中计划重编。反馈文件带上次 wiring.json 的 source 和 trial_exclude。排除只应用于该次试布映射，固定连接不能移除。
- 给出锁定的 --event-native-assembler 后，两 U_64 的合格子集可输出 mother.bin、local0.bin、local1.bin。已验证的命令为 E Add/Mul、S128 定长存储链路及相应 ACK。程序超出局控描述符容量、使用 DDR 或需要该 ABI 无法表达的跨目标同步时，返回明确的阻塞原因。
- 硬件合同可通过 event_model.indexed_gather 声明索引读端点及其 S 窗口、资源占用、地址宽度和估计带宽。编译器对显式定点打包的 Embedding 生成 INDEXED_LOAD，按实际选择的行计外存字节，并在目的 S 写确认后释放依赖。当前已验证控制解释器，两 U_64 汇编后端尚无该指令的原生编码。

## 对抗回归与验收边界

| 验收项 | 实际结果 |
| --- | --- |
| 36 层、108 个任务，末段强制复用同一束线 | 单束预算恢复到 720 拍；并发额度一份时为 1008 拍。12、24、36、48 层的同类试验均恢复合法方案。 |
| DDR 信用及代价 | 27 组信用空档均重新找到可用窗口。典型 ACK 从第 29 拍回到第 15 拍。输入提前到达但无法缩短动作时，可选零 DDR 的后继。 |
| 36 层算子图控制回放 | 同一静态线束覆盖 36 次不同的数据传输，131 个逐位端点请求。注入延迟 ACK 后整数结果一致，错误控制目标和错误 ACK 语义均拒绝。 |
| 路由后端往返 | 现有路由合同接收全部 131 个逐位请求。无物理 pin 的候选清单明确返回 unbound。反馈排除原线束后重新生成 36 次传输及另一组逐位端点。 |
| 真实母控与两 U_64 局控 | 从 16 层整数 Add/Mul 算子图新生成 160 B 母控及 4528 B、4672 B 两份局控镜像。Verilator 5.042 在正常、背压和中途复位各三初态均通过；每次 15 笔实际跨组存储 ACK、496 B 确认写入，逐笔数据与源释放匹配，最终 SRAM 结果逐位一致。正常 1780 拍，背压 2401 拍，复位重跑 2421 拍。 |
| 真实 Qwen2.5-3B Embedding | 从原始导出图提取 Gather，使用已有的 151936×2048 定点权重。`[1, 2]` 和 `[0, -1]` 各从外存读取两行，共 8192 B，输出与原独立参考的 SHA-256 一致。越界用例在任何表读取前被拒绝，另验证了延迟目的写确认。证据范围为控制解释器功能回放。 |
| 真实 Qwen2.5-3B 全图 | ONNX SHA-256 0950df534497881f416a3f8b8fac1a265764ea2f4879943695a2d800a5c9158f，B1/S2 prefill、无 KV，规范化后 1803 个节点。从真实权重重新生成 8850 条整数指令，经五组清单登记 1083 个有限循环和 4333 个候选。#257 独立重搜宽度 1 和 8，两份母控与局控控制 IR 序列化后均在三组真实 token 上得到与历史独立整数参考逐位一致的 logits。 |

真实 RTL 回归用冻结的 algorithm-fix-105-current-mother-u/fixture 源目录、已锁定的 SRAM bank 模型及官方汇编器；测试入口是：

```text
python project/experiments/block_synthesis/event_native_acceptance.py FROZEN_FIXTURE NEW_OUTPUT
```

该入口生成全新的图、指令镜像和测试输入，运行同一批 RTL，再核对每笔传输和最终 SRAM bank 写入。运行时通过 VERILATOR 和 SRAM_BANK 指定工具和 bank 源文件。输出 report.json 及各场景日志。

## 整图有限循环回归

长循环作为有资源租约的服务进入事件前沿，保留定点运算、地址视图、私有 S 工作窗和外存区域。每次派发包含参与局控、逻辑依赖和资源槽上一个占用者的完成依赖。布线需求由选中绑定生成，每个逻辑线束的每次使用带派发序号。

```text
python event_full_acceptance.py MODEL HARDWARE ARCHIVED_INTEGER_PROGRAM NATIVE_QUALIFICATION WEIGHTS ACTIVATION LOGITS GOLD NEW_OUTPUT ORACLE ...
```

作业 102835 从模型、权重和校准重新编译整数循环，并与归档逐项比对。两个搜索宽度同池、同五组资源、同为最多 10 束。两者均为 3737426296286 模型 tick、1716609014656 B 模型外存读取、303549442752 B 模型外存写入、10 束逻辑需求。三组 token 在两种搜索下均逐位一致。报告 SHA-256 为 `77bc6c033fffdf6583e6a9f609f392db3f48f6c20dcdf733d0b859654e9a1fa6`。冻结目录为 `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/event257-full-yfd7s3HJ`，含源哈希、计划、控制 IR 和布线清单。

固定上述 10 束逻辑连接并排除其他 22 束后，两个搜索宽度仍能重新生成通过检查的整图控制 IR。放宽至 12 束后，排除 `U0.E.read` 会使同一整图重新选择 `C0.E`，生成 12 束需求和新的控制 IR。删掉一个必要 ACK 依赖后，解释器拒绝该程序。整图回归使用保守逐字写回服务与虚拟外存。R24 驻留、分片候选和 #251 原生 FFN 尚未接入整图事件搜索。整图控制 IR 由解释器执行，原生母控及局控二进制编码待接入。

## 算法 1 到算法 2 的交接

```text
python run.py MODEL HARDWARE NEW_OUTPUT --event-graph --event-width 8 --event-control-fabric CONTROL.json --event-route-base BASE.json --event-route-module ROUTE_CONTRACT.py --event-route-catalog CATALOG.json --event-route-adapter UPPER_ROUTER/adapter.py --event-route-technology RULES.json
```

物理接口模板可直接登记在硬件清单。已有独立物理目录时用 `--event-route-catalog` 按需求 ID 接入，调度成本仍来自硬件清单。物理底座引用的 ODB、网表和 GDS 在搜索前验证哈希。贪心与 DP 都检查选中连接及其必需连接的闭包。每条额外连接在预算中计一次，声明为固定的逐位连接还要在底座上核对原生连通关系。缺 M10 接点、方向不符或造成多驱动的候选会被搜索排除。

控制接口从 `--event-control-fabric` 读取，也可直接作为硬件清单的 `control_fabric` 字段。格式为 `block-event-control-fabric/1`。其中 `mother` 指定母控电路实例，`targets` 把控制分组关联到局控实例、硬件目标号和所需线束，`bundles` 声明控制电路实际具备的信号。P、U 等分组只用于指派控制权。端点 ID 指向具体电路实例，例如 `P0.LC/task_valid_i`。母控的命令、局控的完成回传以及握手都按硬件声明展开，可以直接连接，也可以经过底座提供的分发器或回传仲裁器。

下例是接口格式演示。这里的两根信号和端口名用于说明字段，实际清单应登记整个接口的位宽、有效信号、背压、信用和其他控制侧带。

```json
{
  "schema_version": "block-event-control-fabric/1",
  "mother": "MC",
  "targets": {"P0": {"controller": "P0.LC", "target_id": 0, "bundles": ["ctrl.P0"]}},
  "bundles": {
    "ctrl.P0": {
      "cost": 1,
      "signals": [
        {"name": "command", "role": "command", "width": 1, "driver": "MC/cmd", "sinks": ["P0.LC/cmd"]},
        {"name": "done", "role": "done", "width": 1, "driver": "P0.LC/done", "sinks": ["MC/done"]}
      ]
    }
  }
}
```

多位信号用 `{bit}` 展开端点。共享分发和回传线束可以通过 `requires` 引用，在静态预算中只计一次。每次 EXEC、COPY 或有限循环派发都会继承其参与局控的线束。只提供逻辑硬件清单时，仍可生成 `control-connectivity.json`，包括选中局控、目标号、逐位驱动与接收端和派发来源。使用路由底座时，同一端点 ID 须出现在底座清单中。端点如何引出、几何是否合法及实际布线由算法 2 和物理后端处理。

同时提供布线适配器和工艺规则时，默认验收范围为 `product`。已有清单仍可用 `control_groups[*].control_net` 和 `mother_control_group` 描述直接命令／完成接口。跨站 COPY 在路由配置登记 `transport_abi` 和 `transport_width_bits`。若数据端点属于独立叶宏或适配器，可用 `transport_owners` 分别指定源和目的物理归属。服务的外存接口可用 `memory_local_owner` 指定本地端。 `ready-valid-commit` 要求 data、valid、ready 和目的写入 ACK。项目的 `u-stored-link` 还核对地址及预留握手。DDR 路径需登记实际外存接口归属。

- `program.json` 给出母控派发、等待条件和局控描述符。
- `requirements.json` 给出逐位源与目的端点、原生服务、外部接口、预连和依赖关系。逐位网可追溯到同一次映射及其派发记录。
- `algorithm2-input.json` 是现有布线入口读取的 `upper-router/1` 输入。`handoff.json` 记录程序、需求、底座和输入哈希，以及待布物理网数。

交接时重新检查事件计划并重建程序及连接需求。控制流、端点清单和底座与映射输入一致后，交接包才进入算法 2。仅核对已有接口时，显式指定 `--event-route-scope interface`，回执使用 `interface_ready_for_algorithm_2`。只提供路由合同与底座时可以生成逐位绑定诊断。

作业 102856 重编译 Qwen2.5-3B 全 36 层、B1/S2 prefill、无 KV。宽度 1 和 8 各生成 1083 次派发。两套控制内容与作业 102835 已逐位回放的版本逐项相同，新增底座接口绑定。#231 的 attempt71 目录将 10 项需求绑定为 6 项底座原生服务和 4 项实际外部接口，交接入口通过，新增顶层信号网为 0。四项外部接口止于底座边界，整机 DMA 和母控物理分发还需要对应底座资源。

同一作业另用真实 U0/U1 的 N→E M10 接点验证有新增连线的交接。宽度 1 和 8 都将 36 次派发合并为 130 根静态网。屏蔽 U0 的一个目的接点后，两种搜索都自动改绑 U1，程序与逐位布线输入同步更新。错误的派发关联被拒绝。冻结结果位于 `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/event257-handoff-yzd7XOKN`。验收入口为 `event_handoff_acceptance.py`。

Qwen 宽度 8 的交接输出还由布线 CLI 独立读取并通过结果检查。新增连线用例验收至布线输入校验。综合目录共 340 项单测，含单独启用锁定汇编器执行的一项原生编码测试。

### 对抗复验

第一轮改为从独立检查通过的事件计划重建程序和连线。清空连线、替换母控目标、改写 ACK、引用同一绑定中的错误事件、伪造计划汇总均被拒绝。

第二轮将局控命令／完成、跨站写入 ACK 和数据位宽纳入候选资格。第三轮核对逐位端点实际归属和原生连通，补测错误控制归属、ACK 复用、伪造预连、直接使用其他局控的存储窗口、替换底座等情形。两种搜索在合成底座上都产生同一次映射的 131 根跨组传输网和 4 根控制网，现有算法 2 搜索并验证全部 135 根。合成底座验证接口和路由行为，真实 U 组回归验证实际 M10 接点的准入与改绑。

作业 102860 在宽度 1 和 8 下各拒绝 17 项合成负对照。真实 U0 的端点分别注入缺失、方向错误和多驱动，两个搜索宽度均改绑 U1。两组都缺端点时搜索拒绝输出。Qwen 全图重跑在 `interface` 范围保留 1083 次派发，默认 `product` 范围报告缺少母控到参与局控的实际接口，并拒绝生成算法 2 输入。冻结目录为 `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/event257-handoff-TRjq2OBX`。验收报告 SHA-256 为 `2b4c83811e0c7de5185f0d3cc445a29eabc75d366de863e84fe55be1df2c60dd`。

控制接口清单回归覆盖 128 和 512 位接口、共享分发与回传、目标筛选、共享线束预算、缺失返回路径和多驱动。控制与数据占用同一端点时，搜索只排除冲突的连接组合，并保留可行映射。逐位需求展开覆盖直接与间接线束，缺任何一项模板时标为 `unbound`。重映射沿用同一底座和目录，省略预算时使用上次预算。提交另一个底座上的反馈、篡改目标号或删除局控接点都会触发拒绝。

合成底座用新的清单替换逐组 `control_net`，为数据指定独立叶宏归属，并加入一条共享控制依赖。贪心和 DP 交给现有算法 2 的 136 根网均通过其搜索和检查。综合目录 345 项单测通过。另用独立穷举检查 160 个小图，125 个有解时无截断 DP 的时间和线束成本均与穷举一致，35 个无解时均拒绝输出。

用 Qwen2.5-3B 全 36 层归档有限循环候选和合成控制接口清单重跑事件搜索。两种搜索各生成 1083 次派发和 512 根控制信号，计划通过独立检查，控制程序通过解码检查。估算时间、DDR 读写量和数据线束与归档基准一致。宽度 8 的三个任务时刻改变，仍满足同样的依赖和资源约束。此项覆盖整图事件映射及逻辑交接。

## 交给上层布线

与 #227 的接口目录、底座清单及 #259 的 `upper_router` 同树运行。输入使用本轮事件排程的 `result.json`，并提供生成它的原事件 IR、硬件清单、接口目录、候选／冻结底座和布线规则。发布器重跑独立事件验证器，从每个选中的执行方式、原生阶段、实际搬运以及固定连接重建静态需求。依赖的预约、确认和控制信号由接口目录展开。每个物理位由 #227 的真实端点合同核对。

```text
python project/experiments/block_synthesis/publish_event_handoff.py EVENT_IR.json HARDWARE.json result.json CATALOG.json BASE.json RULES.json handoff
python project/experiments/upper_router/run.py handoff/algorithm2-input.json routes.json --handoff handoff
```

如果两份 PR 分开检出，给发布器传入 `--upper-router`，指向 Algo2 检出中的 `project/experiments/upper_router`。

接口试验从同一份验证过的排程重建母控 DISPATCH/END、各局控命令及完成依赖，同时生成逐位连接、绑定网表和路由输入。发布器也接受 `--event-graph` 产生的 `result.json`。把该结果里的 `event_ir` 保存为第一个位置参数所指的文件，发布器核对其与编译结果一致，并采用结果里已解析的硬件清单。产品调用加 `--scope product --control-images IMAGE_MANIFEST.json`，必须具有冻结底座的 ODB/DEF/GDS/netlist/SPEF、硬件的 `program_target.controllers` 和同一 topology ID 下完整的目标 ISA 镜像。镜像清单 schema 为 `algo1-control-images/1`，其 `source` 包含 IR、硬件和排程 SHA-256，每项包含 `controller/level/abi/path/bytes/sha256`，路径相对镜像清单。发布结果包含已校验的镜像字节。编码、程序回放和联合物理验收各有独立证据。尚缺目标 ISA 编码的事件排程可走接口试验。

本轮跨 PR 回放使用 36 次传输的合成图。72 个算子生成 178 个派发，36 次 COPY 重用同一套 131 根静态位线。Algo2 通过完整接口检查并布通全部 131 根。底座几何为测试输入，实物接入证据另见 #185 与 #259。
