# 按执行状态计算 Block 综合代价

Refs #219。以 #220 的 05602e4316dad898e19a31f49bbd19e2a6ab8b78 为基线。#251 的回归证据固定在 9abd46f5cbb4534bcfc614571ccd6d402ad11882。

## 实现与输入

现有覆盖前沿增加可选的事件执行模式。输入仍由 lowering 提供任务、候选及硬件。事件模式的候选描述已资格化的阶段、输入片段及目标窗口、输出片段及写入窗口。硬件声明每个 S 的容量和窗口物理区间、每项服务的时间与资源、允许的 COPY/DDR 路径、并发容量、初始副本及静态线束约束。片段 ID 对应同一不可变值及表示。量化、转换和重排需要登记为计算服务。COPY 可以检查源和目标站点，要求值的身份保持一致。

每次从同一个前沿扩展候选时执行以下顺序。

1. 查询所需片段的当前副本、就绪时刻和窗口占用。有本地副本时可以直接消费。可达的片上 COPY 与有真实路由的 DDR 路径按当前等待、字节和静态网代价比较。候选可显式要求片上交接或 DDR 后备。
2. 预约本次事件实际使用的资源。DDR 路由可按请求、数据和 ACK 三段分别占用资源，并在整个期间保留信用或描述符槽。时间采用整数拍。端口、信用、容量、静态网预算和驱动互斥都是硬约束。
3. 复制源保持到目标 ACK。目标副本在写完成后可用。覆盖仍有消费者的唯一有效 S 副本之前，需要获得有效 DDR 后备。已经用完的临时值可以释放。全程检查真实窗口与存活期。
4. 用事件的完成时刻更新排程，用实际 DDR 读写事件更新字节，静态网用并集更新。DP 和严格贪心调用同一个转移。状态合并包含未来资源预约、片段副本、后备时刻与静态网。只有所有未来动作都无法回填的早期预约可以从搜索状态丢弃。

事件预约采用固定已有预约的插入策略。前沿可以选择不同的就绪任务顺序。一次转移内部的阶段顺序来自资格化服务，搬运可以占用阶段之间的空隙。DDR 当前按硬件声明的阶段和有限信用建模，历史预约在转移时保持原时间。需要改变已预约请求的优先级时，应在搜索中改变决策顺序。动态重排已预约请求、DDR 行缓冲和逐 beat 争用需要更细的服务合同。当前使用固定的物理 S 窗口，其他分配方案可由候选提供。

独立检查器从计划事件重建资源占用、数据写入和读取、COPY/STORE 的源保持、DDR 后备就绪、覆盖、字节与静态网集合。它不依赖搜索器的副本表和累计代价。单测另用逐拍参考核对 800 次随机容量预约。

## 调用

事件 IR 是编译器内部格式，包含 `tasks` 和可选 `covers`。硬件以 `event_model.kind=qualified-event-model-v1` 选择事件模式。现有 ONNX 和全图入口保留原有路径。

```text
python project/experiments/block_synthesis/run.py MODEL_IR.json HARDWARE.json NEW_OUTPUT --event-ir --event-width 8
python project/experiments/block_synthesis/run.py MODEL_IR.json HARDWARE.json NEW_OUTPUT --event-ir --event-width 1
```

宽度 1 的严格贪心对照使用单任务动作。若要评估复合动作，应另建立每步只选择一个后继的对照。比较时固定硬件配置、候选池、输入和连接预算。按完成时间、DDR 总字节、静态网代价依次比较。对比新旧成本模型时重放同一动作序列，并分开记录执行能力与搜索策略的收益。

## 交给上层布线

与 #227 的接口目录、底座清单及 #259 的 `upper_router` 同树运行。输入使用本轮事件排程的 `result.json`，并提供生成它的原事件 IR、硬件清单、接口目录、候选／冻结底座和布线规则。发布器重跑独立事件验证器，从每个选中的执行方式、原生阶段、实际搬运以及固定连接重建静态需求。依赖的预约、确认和控制信号由接口目录展开。每个物理位由 #227 的真实端点合同核对。

```text
python project/experiments/block_synthesis/publish_event_handoff.py EVENT_IR.json HARDWARE.json result.json CATALOG.json BASE.json RULES.json handoff
python project/experiments/upper_router/run.py handoff/algorithm2-input.json routes.json --handoff handoff
```

如果两份 PR 分开检出，给发布器传入 `--upper-router`，指向 Algo2 检出中的 `project/experiments/upper_router`。

接口试验交付事件程序、逐位连接、绑定网表和路由输入，由同一份排程指纹关联。产品调用加 `--scope product --control-images IMAGE_MANIFEST.json`，必须具有冻结底座的 ODB/DEF/GDS/netlist/SPEF、硬件的 `program_target.controllers` 和同一 topology ID 下完整的目标 ISA 镜像。镜像清单 schema 为 `algo1-control-images/1`，其 `source` 包含 IR、硬件和排程 SHA-256，每项包含 `controller/level/abi/path/bytes/sha256`，路径相对镜像清单。发布结果包含已校验的镜像字节。编码、程序回放和联合物理验收各有独立证据。尚缺目标 ISA 编码的事件排程可走接口试验。

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
