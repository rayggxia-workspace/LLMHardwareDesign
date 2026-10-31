# 既有bridge辅助宏与块内供数器的实现归属

本研究属于 [Issue #151](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/151)，配套[六类方案](SIX_CONNECTION_SCHEMES_STUDY.md)。只读核对既有源码、生成器和证据索引；没有修改 PR #132/#133/#144 的分支、RTL、配置或服务器作业，没有重跑仿真或物理验收。

- 核验身份：Melodydt（GitHub ID 172562968）。
- 核验日期：2026-10-31，Asia/Shanghai。
- PR #133 发布头：`b1864046b1adfa5101cff3235742b4068aa78ee3`，未合并。
- PR #132 发布头：`4dd994bf256c1a3a16163756a3a486139984ecff`，未合并。
- PR #144 七宏参考头：`5e787714362d957b79c2997141cf05eeebb85afc`。其 M/S 与 #133 旧版物理副本不同，旧资格不能转移。
- 文中“通过”指原交付的证据记载；本轮工作是源码/索引审计，不是重新授予硬件资格。

## 1. 结论与名词边界

PR #133 的 `bridge` 是有有限 payload 存储和局部控制的独立辅助硬宏；`bank` 是独立的并行缓冲硬宏，并非存储 bank；`booster` 是单路缓冲硬宏；`return` 是 booster master 的另一个实例，不是第四种设计。它们在预制 M1–M10 内有有源单元，后定制 M11/M12 只连接其真实 M10 接点。

PR #132 的 S 有真正的四个存储 bank，内部同时包含有限 M 供数器。其 `block_feed_pair` 是用于验证的组合顶层，其中的 M→T 路由 mux 不能当作已经物理实现的通用互联宏。

必须分别记录 RTL module、物理 hard macro 和 test glue。一个 Verilog module 名字本身不代表独立硬宏；生成器明确选择的硬化 top、视图、外框和最终接收证据才界定物理边界。

## 2. PR #133 的四个名称分别是什么

| 名称 | 实际 RTL/生成方式 | 功能和状态 | 物理边界与已有记录 |
| --- | --- | --- | --- |
| `bridge` | `linkclose_bridge.sv` 包含 `linkclose_elastic` 和 `linkclose_bridge`；生成器再创建 `linkclose_bridge_fixed` | 2×131bit payload 队列；每包128bit数据、capture、error、saturated；另有队列读写指针/占用、命令capture寄存器、10bit T写索引及sticky观测标志 | 生成的 top 把 bridge 与输出驱动一起展开硬化；740×160µm；140个显式固定BUF_X16，其他观测输出使用BUF_X2；原独立接收 run921 |
| `bank` | 生成 `linkclose_buffer140`，140个并列 `BUF_X16` | `o[i]=BUF_X16(i[i])`。附带一位 `canary` 翻转FF；payload不经过FF，没有payload队列、地址生成、协议状态机或调度功能 | 1040×160µm 独立辅助硬宏，原独立接收 run921。完整TS连接使用其中139路：128data＋10index＋1valid |
| `booster` | 同一生成器创建 `linkclose_buffer1` | 单个BUF_X16直通，另有canary FF。数据/ready路径没有寄存器，不增加协议阶段 | 64×64µm 独立辅助硬宏；原接收 run916 |
| `return` | `native['return']=dict(native['booster'])`，复用相同视图 | 与booster相同；只是摆在返回路径上的第二个实例 | 同一64×64µm master，多一个物理实例和占地。不能重复宣称为一套新设计 |

源码依据：

- [B1：弹性队列、包格式与bridge局部控制，L1–62](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/b1864046b1adfa5101cff3235742b4068aa78ee3/project/rtl/block_v1/linkclose_bridge.sv#L1-L62)。
- [B2：`generate()`创建bridge封装及buffer140/buffer1，L20–55](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/b1864046b1adfa5101cff3235742b4068aa78ee3/project/experiments/block_v1/linkclose_physical.py#L20-L55)。
- [B3：独立硬化、M1–M10、驱动保护和六阶段，L99–150](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/b1864046b1adfa5101cff3235742b4068aa78ee3/project/experiments/block_v1/linkclose_physical.py#L99-L150)。
- [B4：return复用booster master，L28–42](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/b1864046b1adfa5101cff3235742b4068aa78ee3/project/experiments/block_v1/linkclose_route.py#L28-L42)。

这里的canary FF用于候选本身的时钟/复位可观察结构，不是数据流水寄存器。不能把bank或booster描述为“可存一拍数据”“靠事件触发下一宏”或“打断ready组合逻辑”的协议单元。真正让上游ready不直接依赖下游ready的是bridge的有限队列。

## 3. bridge做什么，谁负责整个流程

`linkclose_elastic` 的 `s_ready=!reset && used<2`，只看本地占用，不组合依赖下游 `m_ready`；`m_valid` 看是否非空。push写入一项，pop推进读指针，支持通常的同时入/出。队列已满而当拍pop时，因s_ready仍为0，会留下一个准入气泡。背压时payload保持。[B1 L9–25]

bridge在M命令握手时保存 `command_capture`，为后续响应附加标记。所有M响应先进入队列；capture=0的普通装载/配置应答被排空，capture=1的响应才向T的write通道输出。T begin握手使写索引清零；每次实际写握手后索引加一。[B1 L30–58]

下列决定仍由外部测试/未来系统控制器提供：

- 下发哪些M命令，以及哪条命令的响应应该capture。
- 何时向T发begin、长度是多少，何时允许写入。
- 何时commit、消费、release，怎样排空S的写响应。
- 发现错误/饱和后整个任务如何处理。

bridge没有任务ID、token/head/tile标识、上下文版本、依赖表或完整模型调度器。`observed_error`/`observed_saturation`是sticky观测位；`write_valid`只由valid、capture和write_enable决定，并未自动根据error过滤、撤销或回滚T。不能把这套局部协议直接描述成通用的事务失败处理。

[B5：组合测试顶层的外部控制端口与T/S接线，L2–43](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/b1864046b1adfa5101cff3235742b4068aa78ee3/project/experiments/block_v1/linkclose_mts_bench.sv#L2-L43)。

## 4. 两条实际物理链路的准确接线

### M→bridge→T

前向/局部返回共275根：

1. M→bridge 132根：rsp_data128、rsp_valid、rsp_error、rsp_saturated、cmd_ready。
2. bridge→M 1根：response_ready接rsp_ready。
3. bridge→T 139根：write_data128、write_index10、write_valid。
4. T.write_ready→booster→return→bridge.write_ready，共3段。

源：[B6：完整MT网络定义，L43–55](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/b1864046b1adfa5101cff3235742b4068aa78ee3/project/experiments/block_v1/linkclose_route.py#L43-L55)。

M的命令valid/capture、T的begin/write_enable等外部控制不在这275根片段中自动生成。物理链路接通不等于整条系统控制链已经实现。

### T→bank→S

前向/返回共281根：

1. T.read_data128→bank.i[127:0]→S.din128。
2. T.read_index10→bank.i[137:128]→S.addr10。
3. T.read_valid→bank.i[138]→S.req。
4. S.ready→booster→return→T.read_take，共3段。

因此地址由T本身的顺序read_index提供，bank只逐位缓冲；没有额外的地址生成器、基址加法或重排。实际流固定写入与read_index相同的S地址。推广到任意tensor区域，需要另设计基址/边界/仲裁和响应管理，不能赋予当前bank这些能力。

源：[B7：完整TS网络定义，L57–67](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/b1864046b1adfa5101cff3235742b4068aa78ee3/project/experiments/block_v1/linkclose_route.py#L57-L67)。

测试bench另有 `verify_req/verify_addr` mux，用于将S切换到读回检查；`read_enable`、`s_take`等由外部驱动。[B5 L37–43] 这些是功能验证胶合，不在bank里，也不能推导为已经有共同底座调度器。

## 5. M/T/S内部改动：真实驱动修复副本

PR #133不是只增加宏外辅助块。实验还在独立副本中把选定端口实际驱动由BUF_X4换成BUF_X16：

| 宏 | 修改的端口集合 | 实际数量 | 原交付副本外框 |
| --- | --- | ---: | --- |
| M | rsp_data[127:0]、rsp_valid、rsp_error、rsp_saturated、cmd_ready | 132 | 740×740µm |
| T | read_data[127:0]、read_index[9:0]、read_valid、write_ready | 140 | 1040×1040µm |
| S | ready | 1 | 1610×1610µm |

`linkfix.py: selected_port()`精确选择以上端口；`implement()`从封存GRT副本实查驱动并swapMaster，重新PG、合法化、增量GRT、DRT、fill/finish和RCX。原综合/placement/CTS被继承，没有全部从头重跑。功能RTL接口未变，但物理master/RC/时序变了，必须当作新物理版本验证。

- [B8：端口选择，L20–21](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/b1864046b1adfa5101cff3235742b4068aa78ee3/project/experiments/block_v1/linkfix.py#L20-L21)。
- [B9：实际swapMaster与修复流程，L124–177](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/b1864046b1adfa5101cff3235742b4068aa78ee3/project/experiments/block_v1/linkfix.py#L124-L177)。
- [B10：三份修复副本与全宽结果/限制](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/b1864046b1adfa5101cff3235742b4068aa78ee3/docs/reports/2026-10-29-block-v1-full-bus-driver-repair.md#L69-L99)。

原生产18文件未替换，`repair-results.json`的 `original_production_replaced=false`。不能把该实验说成主线或当前七宏已普遍采用强驱动。S只改ready，未给S读数据输出等其他方向授予任意互联资格。

## 6. 与PR #132的S内loader和pair mux比较

| 对象 | 位于哪里 | 实际功能 | 交付归属 |
| --- | --- | --- | --- |
| `block_feed_s16k` | `block_feed_s_macro`内部 | 真正4×256×128bit标准单元payload存储，宽读用完4个1RW bank，窄/宽访问仲裁；128/512bit响应保持 | S叶宏内部硬件，不是PR133的bank缓冲宏 |
| `block_feed_loader` | 同一S叶宏内部 | 装载描述符/地址合法性检查；真实512bit存储读；两项512bit A队列、一项512bit B槽；拆A128/B512，携带bank/row/tile/half/格式，处理背压和完成 | 与存储共同硬化为S，不是额外独立的通用宏 |
| `block_feed_pair` | 实验集成测试顶层 | 实例化S、M、T；a_allow/b_allow故意注入背压；route_to_t及t_index将选定M读回应答转为T写入 | test fixture；不是已冻结的共同底座或独立硬宏 |

依据：

- [F1：S真正存储bank与窄/宽仲裁](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/4dd994bf256c1a3a16163756a3a486139984ecff/project/rtl/block_feed_v1/block_feed_s16k.sv#L1-L35)。
- [F2：S宏边界显式包含storage和feeder，L1–29](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/4dd994bf256c1a3a16163756a3a486139984ecff/project/rtl/block_feed_v1/block_feed_s_macro.sv#L1-L29)。
- [F3：loader有限队列、地址、握手，L23–59](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/4dd994bf256c1a3a16163756a3a486139984ecff/project/rtl/block_feed_v1/block_feed_loader.sv#L23-L59)。
- [F4：loader状态更新与done条件，L60–109](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/4dd994bf256c1a3a16163756a3a486139984ecff/project/rtl/block_feed_v1/block_feed_loader.sv#L60-L109)。
- [F5：pair的测试声明、外部控制、mux与T写序号，L1–66](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/4dd994bf256c1a3a16163756a3a486139984ecff/project/rtl/block_feed_v1/block_feed_pair.sv#L1-L66)。

loader的done只表示描述符的A/B数据已经交给M，不表示M计算完成。`reuse_b`只跳过B读取，不证明驻留权重的身份/版本正确；软件或未来调度器仍须维护。宽读争用、S容量、响应寄存器及272B数据寄存器均须计价。[供数合同L59–69](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/4dd994bf256c1a3a16163756a3a486139984ecff/docs/BLOCK_FEED_V1.md#L59-L69)。

pair的M→T路径与PR133 bridge差异明显：pair没有2×131bit弹性队列；`mr=route_to_t&&!me?t_write_ready:rsp_ready`保留直接ready组合依赖，并且只捕获op5。它在测试顶层增加route_to_t和写索引寄存器，不能把这些有源成本放到M11/M12导线名下。PR133 bridge增加真正的有限排队，所有M应答经过队列，capture标记决定是否进入T；二者不可当作同一实现的同一资格。

## 7. 物理资格的来源、可复用部分和不可转移部分

已有索引记载bridge、bank、booster的原生M1–M10独立验收包括实际pin/PG/RC/DRC与严格LEC。bridge另以最终门级替换其RTL，配合M/T/S RTL跑15例×三初态协议回归；不是三宏全部最终网表组合仿真。实际验收器实现见[linkclose_accept.py L19–68](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/b1864046b1adfa5101cff3235742b4068aa78ee3/project/experiments/block_v1/linkclose_accept.py#L19-L68)。

源执行版本不能只写发布head。索引明确：

- bridge/bank接收run921的执行source_commit为 `2fa2c01b7a61e00ba26da1629dc04338d9086ac3`；booster接收run916的执行source_commit为 `2014df3e619994885724714a6c8aa2706b99c430`。[原辅助宏源/资源审计](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/b1864046b1adfa5101cff3235742b4068aa78ee3/work/YUZE-LU/121/interconnect-study-20261029/closure-source-and-resource-audit.json)
- M/T驱动修复源run928对应 `3a5c44f5fbf00b2bd054df8fae9a0bde500f29fc`；最终S修补/接收run940对应 `dc411ac466956ad23998b9dce1540f8121c547bd`。[修复源/资源审计](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/b1864046b1adfa5101cff3235742b4068aa78ee3/work/YUZE-LU/121/interconnect-fix-20261029/closure-source-and-resource-audit.json)
- 发布头的源链接用于读懂结构。若重跑，须按索引恢复各次不可变source.tar、工具/配置和输入输出绑定，不能假设不同历史run都执行发布头代码。

可用于Issue151方案的内容：有限队列打断ready组合依赖的方法；数据与capture/error/saturation同包保持；T顺序写索引；真实宽接点与强驱动/返回中继的物理成本；S内专用供数与加载完成语义。

不能直接沿用的结论：

1. 当前七宏所有方向的驱动能力、统一标签/事件/错误协议、任意扇出或共同控制器已经成立。
2. bank可以缓存张量、生成任意写地址、调度访问或做数值/位宽适配。
3. booster/return可以登记数据、跨时钟域、避免协议死锁或形成完成事件。
4. 两条固定摆放/研究RC情景的通过可以替代新版M/S、所有连接对、公共CTS/PG或制造签核。
5. #132的pair mux或#133测试bench可以作为零成本的生产协调控制。

如果Issue151要引入任务/流/tile/epoch标识、通用基址、按字节有效掩码、多输入join、复制/引用计数、取消/排空或通用错误传播，这些是新的系统协议和有源实现工作。应明确放在预制接口适配/协调控制层；是否修改叶宏内部需逐条分析。形成新RTL或改变物理driver/pin后，必须按实际新版本补相关功能、接口与物理证据。
