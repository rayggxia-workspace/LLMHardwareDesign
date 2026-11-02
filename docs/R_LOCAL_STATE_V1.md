# R 局部状态存储实现（Issue166，验收进行中）

任务：[Issue166](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/166)，[草稿PR167](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/167)。本文描述本分支的新实现，不授予物理资格，不替换 main 或 PR160 的合格交付。

## 实际电路和容量

| 参数 | R256 | R1024 |
| --- | --- | --- |
| 每版本 S32 状态元素 | 256 | 1024 |
| 两版本合计状态字节 | 2048 | 8192 |
| 每版本 256bit 行数 | 32 | 128 |
| 每版本 16行分区数 | 2 | 8 |
| 每分区计算 lane | 8 | 8 |
| 每个 lane 的状态阵列 | 16×32bit DFF | 16×32bit DFF |
| 独立读选择触发器位 | 512 | 2048 |
| 独立写选择触发器位 | 512 | 2048 |

这些容量只计两份算法状态，不含选择寄存器、读/写流水、读回FIFO、key/query、乘积和归约上下文。全部采用 Nangate45 标准单元触发器与逻辑门，没有 SRAM 宏。两版本共同支持同一行读取；每周期最多一个版本、一个行掩码写入。

`r_state_store.sv` 拥有状态数组、局部16位读写选择、每lane写数据寄存器、局部读数据与分区汇合寄存器。`r_stream_local.sv` 拥有指令状态机、原8路整数算术、点积/错误上下文、key/query、卷积历史/taps、读事务标签和四项128bit读回FIFO。

## 边沿合同

存储读请求在 E0 接受，E1 捕获局部选择，E2 捕获局部数据，E3 产生分区汇合数据与有效位。写请求在 E0 接受，E1 捕获局部选择/写数据，E2 写阵列。同一个E2读写同一行，返回写前状态；掩码控制独立32bit lane。

外部读请求使用 `rd_valid/rd_ready`；存储输出在 E4 被控制器放入读回FIFO，`rd_rsp_valid/rd_rsp_ready` 交付128bit。信用计数包括在途与已排队响应，总数不超过4；背压时响应保持。指令优先于同周期读请求，指令和装载等待已接受读事务全部消费；装载还等待写流水排空。计算仍为原流式ISA，延迟有所增加，不是原R的逐拍替换。

reset 清空控制、标签和队列，不清空状态阵列；已排队/在途读取被取消。调用方必须先装载将被读取的状态、参数及历史。结果错误/回滚和跨分块事务沿用原整数参考语料，不用延迟相等作为结果相等的判据。

## 结构与物理约束

仅使用RTL `keep` 属性的初版被Yosys合并，256的读选择产生512扇出，实际审计拒收。当前综合分支显式实例化保留的DFF_X1；仿真分支为同边沿行为。双容量新映射的读写完整组合选择锥均最多32个时序端点、锥内最大扇出32。最终验收仍须验证映射到物理期间保持功能，并测量真实负载/布线。

`local_regions.py` 从真实映射JSON追踪局部寄存器和组合扇入，将跨分区共享逻辑留在外部；生成左右两个版本、垂直分区的OpenDB EXCLUSIVE region及PHYSICAL_CLUSTER group。必须同时建立group成员，否则当前GPL只布局top-level，不能把数据库存在region误当约束生效。最终数据库逐实例检查实际位置。

物理输入从映射JSON重新输出 `-norename` 网表，保持真实实例身份；OpenSTA数据库中的bus括号转义也逐名核对。信号接点放在M10内部，内部布线限制M1–M10。300MHz和I/O SDC沿用冻结合同，未通过不得扩大时钟周期或减轻负载。

## 重跑入口和验收

运行器位于 `project/experiments/r_local_state/`，重型任务必须经Slurm提交；容器与源码先核SHA。组件 `component.py`；整机六独立16核槽动态补位 `engine_v2.py`；按容量读取三个成功回执后 `synthesis.py --capacity CAP --functional-root PATH`。后续依次运行 `physical.py --capacity CAP --mapped PATH --die SIZE`、`evaluate.py --physical PATH --capacity CAP`、`netlist_test.py --capacity CAP --netlist PATH/6_final.v`。`rtl_equivalence.py` 是完整RTL/单元网表顺序等价诊断入口，目前未获得证明，不能声称已通过。`preroute_lec.py` 独立保留Yosys RTL lowering过程，严格验证所有实际状态边界的ABC映射逻辑；最终物理LEC仍单独必验。两者证明范围不能混用。

`resume_placement.py` 复用已冻结GPL/resize结果，真实时钟树生成后才进行hold修复；镜像优化后再次合法化，最终围栏逐单元检查仍必须零越界。`resume_hold.py` 只在真实负裕量的DFF数据端点插入有审计记录的恒等延迟链，所有新增电源连接、最终布局、RC/时序/等价均重新验收；优化顺序不改变原SDC或最终门槛。

单元网表编译两个可执行文件，使用2×16核；完成后`netlist_queue.py`动态补入用例。初始单线程构建以`--case-parallelism 96`使用六组16个独立用例；已启动长用例通过`--reuse-queue --wait-inflight`保留。092实测新增`--threads 16`构建与同源单线程的3项代表结果一致、约1.7–2.1倍加速，因此后续R256最终回归采用6×16槽。队列核验实际Verilator编译命令线程数不得超过每槽CPU；不能将16线程二进制放进96个单核槽。

109独立完成R1024同源对照，三个用例的单线程/16线程耗时分别为1.157/0.634、4.215/1.891、36.750/17.657秒，加速1.82–2.23倍，结果逐项一致。后续R1024最终回归也采用6×16动态补位；这只是仿真调度证据，不增加硬件验收资格。

每个attempt冻结代码、输入、容器、命令和输出SHA。功能组件通过、映射结构通过、布局完成、原生router DRC为0都不能独自授予资格。最终需要提取setup/hold均非负，所有时序/电容/转换时间计数为0，严格LEC和真实故障对照成功，最终原单元网表三初态语料/协议通过，PG/接点/实际局部几何通过，完整未修改原GDS规则检查0，实际LEF/Liberty及六文件绑定全部一致。两容量分别验收。

## 参考与采用范围

- [OpenTitan prim_ram_1p_adv](https://github.com/lowRISC/opentitan/blob/master/hw/ip/prim/rtl/prim_ram_1p_adv.sv)：分块地址选择与读回流水；此处采用分块/流水组织思路，没有引入其具体工艺存储宏。
- [OpenTitan prim_ram_1r1w_adv](https://github.com/lowRISC/opentitan/blob/master/hw/ip/prim/rtl/prim_ram_1r1w_adv.sv)：明确读写端口与时序合同。
- [Yosys memory_map](https://yosyshq.readthedocs.io/projects/yosys/en/0.41/cmd/memory_map.html)：寄存器映射存储的选择/写入逻辑来源。
- [OpenROAD RAM](https://github.com/The-OpenROAD-Project/OpenROAD/blob/master/src/ram/README.md)：规则阵列布局参考；未引入三态或锁存时钟方案，也不继承其验收资格。
- [OpenDB类型](https://github.com/The-OpenROAD-Project/OpenROAD/blob/master/src/odb/include/odb/dbTypes.h)和[GPL区域处理](https://github.com/The-OpenROAD-Project/OpenROAD/blob/master/src/gpl/src/placerBase.cpp)：实际region/group接入依据；以容器预检和日志为最终证据。

## 完整原生检查的分区诊断（尚未签发资格）

原生全片分区报告出现单网Metal Spacing，而同一实际GDS的几何检查没有对应错误。`native_complete.py`保留原ODB和分区报告，在内存中只将GCELLGRID改为完整die单区，重新运行同一未修改OpenROAD/技术规则。必须先通过合法几何正例，检出真实短路、异网间距和同网凹槽负例；完整检查前后非GCELLGRID DEF逐字节一致，恢复原网格后整份DEF一致。`receive_native.py`重新核验全部身份与负例。计算未结束或报告非零都不能通过。

这是完整规则计算的诊断，不删除或过滤标记，也不修改工艺规则。[上游TritonRoute原生检查实现](https://github.com/The-OpenROAD-Project/OpenROAD/blob/master/src/drt/src/TritonRoute.cpp)仅为分区机制参考，实际结论以固定容器/二进制和本轮真实对照为准。独立完整原版GDS deck始终必需。`complete_evaluation.py`允许GDS/STA与完整原生计算并行收集，但除原生计算外所有原检查必须已经成功；任何时序、电气、PG、GDS错误都会拒收，不能靠合并回执覆盖。

111候选最终提取setup +10.2522ps、hold +1.91164ps，时序/电气计数0；117的1024个完整物理选择锥与DEF/SPEF审计通过。115完整原版GDS已完成，原规则全部0项，除原生全片计算外原验收检查均通过；116原生检查、119精确最终网表192项仍在运行，因此尚无完整资格。原生095运行超过一小时的实际调用栈位于`initNet_pins_polygonCorners_helper`反复进行Boost多边形扫描；[上游缓存优化94fe8d17](https://github.com/The-OpenROAD-Project/OpenROAD/commit/94fe8d1778a21deacbe154cd3967abba087b2353)与该位置对应。独立固定上游2eba27b2的工具验证正在准备，不改共享工具，不替换物理源，不把上游优化说明当本项目已完成的正确性或性能证明。计算节点DNS/外网实测不可用，故下载与计算分开，编译仍经Slurm；工具源码/子模块/归档绑定见`work/YUZE-LU/166/UPSTREAM_CHECKER_SOURCES.json`。

073→082的完整GDS天线违规实际53→1，剩余M9天线位于clock输入长接入。`short_clock.tcl`只将原有BUF_X16时钟根移到实际M10接点附近，记录旧/新坐标并核验其他单元位置、时钟连接和逻辑不变；随后重新布线、RCX、全部时序与完整DRC。096虽已实际setup/hold均非负，但仍待完整GDS/原生及最终单元回归；111为修正后的时钟接点候选，完整GDS已0项，仍需原生全片及精确最终网表回归全部通过后才有资格。

R1024候选132（1800µm）使用同一逻辑与原SDC，全局布线已获得0拥塞，正在进行布线后修复；不能据此宣称详细布线或300MHz最终通过。路由器依据076实际拥塞推荐上层预留从25%降至12%，独立比较底层50%/30%预留。该设置调整估计轨道资源，不改变LEF/GDS几何规则；不允许拥塞退出，详细布线、完整原生/GDS、电气和最终时序门不变。126/127因仅修改FASTROUTE_TCL未作用于复用CTS数据库而被拒作有效实验；129起在PRE_GLOBAL_ROUTE实际重施并通过真实资源表确认。

111精确最终单元网表119已192/192通过，原始回执SHA d3e11cd8d99c561b20c1de163979bd57c0091314381473a19947d2452acef5c4 已本地实收；原生全die与最终包仍未完成。132真实GRT完整指标setup+55.0449ps、hold−66.5333ps/247项、cap295/slew65，不能合格。150对全部295个电气驱动的实际ODB审计完成：161个仅一个负载，186个连接跨度>250µm；数据表SHA ae5544a34d4fab8739cca0bf421a56f3482d80937fa0348814804c438aaf2871。由此新增lane局部4列×2行放置对照，同一RTL/映射/原SDC，每个16行tile分8个实际lane围栏（1024共128个）；最终围栏验收严格匹配声明的全部名称与数量、逐实例零越界。原大围栏候选继续详细布线，不转移资格。

## 插入缓冲器的物理归属与修复保护

150对132全部295个GRT违规驱动的完整实际ODB记录进一步定位到：同一围栏内相邻AOI/NAND，经区外未分组的hold30573形成约500µm往返线路。只有一个负载也可出现大电容。`buffer_locality.tcl`在每次详细合法化前，给未归属数据缓冲器建立实际EXCLUSIVE region/PHYSICAL_CLUSTER成员：原逻辑/FF后的首级靠生产者，剩余局部链从实际同区消费者反向归属。全局共享分支、时钟、已固定接口驱动不盲目塞入状态围栏。输入延迟链在其真实M10引脚宿主区合法化后固定。

159与162分别在完整132全局数据库、151已完成resize数据库验证：Verilog逐字节不变、原ODB SHA不变、第二次运行0新增归属；分别修复3192/5619个原未分组缓冲器。仍须新布线/最终网表/全部物理门重新通过。重跑入口：`buffer_locality_probe.py --odb PATH`，`resume_locality_place.py --source PATH --capacity 1024`；CTS用`resume_input_cts.py --buffer-locality --strong-clock --cts-only`，路由用`resume_protected.py --buffer-locality --short-clock`。原16区和128 lane区并行比较，不改变状态/算术。

165原16区CTS已成功，166接入新IO驱动时3个BUF_X16重叠，原所有单元始终LOCKED；174仅将新驱动水平合法化搜索从10µm增至50µm，垂直10µm、原位置不动检查、最终几何/电气门不变。OpenROAD `-max_displacement`单位为µm；174冻结的旧CLI/JSON误写sites/rows，实际命令一直是`{50 10}`µm，原始记录不改写，最终包附生成Tcl和明确单位更正；新CLI采用`--io-search-um 50`。

174之后遇到RSZ-3006：局部选择FF负载中有被dont_touch保护的hold延迟单元，阻止电气修复插入局部驱动。179只在`repair_design`调用期间解除这些hold单元保护，随后恢复；原延迟实例必须全部保留，任何尺寸变化写`BUFFER_REPAIR_GUARD.tsv`，原生错误继续传播。最终hold/setup、电容/转换时间、PG、全部DRC及功能仍逐项完整验收，不因保护修复获得豁免。

新冻结归档可只包含实际运行器、RTL及所需参考输入，保留Git archive commit和每个成员SHA；FILES.sha256必须与所选归档全部成员精确一致。源范围缩小仅避免反复复制无关参考资料，不替代源/输入/输出绑定。


### 2026-11-03：全局分发与局部叶级的物理宿主

193对179全局结果的全部110个电气违规驱动取实际ODB/负载，101个为无围栏NOR2_X4译码门；其两个缓冲分支可分处相对两bank，跨度超过1mm。不能将全局根及中继按消费者反向整链拉入远端围栏。新的buffer_locality保留真实局部生产者首级归属，对原生选定位置已落入围栏的中继赋予实际物理宿主并保留坐标；消费者归属仅允许直接非缓冲叶级，或输入来源与消费者已有相同归属的局部链。时钟及接口仍排除。先对实际132 DB验证网表字节不变、原ODB不变及幂等，再新CTS源165全流程迭代，不转移任何资格。

179的修复器中间hold已0，但DPL与增量布线后的真实GRT仍hold253、电容110、slew5；因此192新增基于实际布线RC的有限修复/合法化/增量布线闭环。132原GRT到最终RCX的实际损失约112ps setup/37ps hold，为150ps/60ps优化目标提供依据。它们是修复目标，原最终300MHz/IO、非负slack及零计数门不变；闭环到第六轮仍有负裕量或电气违规即拒绝，不让详细布线掩盖已知失败。所有实际闭环轮次、物理宿主和源证据进入最终包。


### 最终功能回归的跨节点动态补位

`netlist_farm.py`复用原C++整数/协议参考、原63语料×3初始化及3协议测试，不更改用例或容错条件。prepare绑定原最终网表、完整build输入、Liberty单元模型、两个实际binary及Verilator命令与原始C++ SHA；worker为每个用例单独16CPU Slurm任务，数组0–191并发上限36，在本任务8个获准c96节点内由Slurm动态填槽，每节点最多6个独立任务。使用`srun --cpu-bind=threads`并实际要求亲和集合恰好16CPU；容器cleanenv只显式传入5项SLURM调度身份字段。collect必须收到所有192个真实成功结果和完整用例集合、逐logSHA与不变输入，再生成兼容最终交付接收器的receipt；任何缺失/失败均拒绝。源绑定索引保存prepare/worker/collect/实际build的所有归档、Slurm脚本/提交回执和源核验日志。

219对3初始化协议及3数值样本的真实最终111单元运行均与119完整结果完全相同，仅为包装器试运行；不能代替任何宏的完整192项或物理验收。215 cleanenv丢失任务编号的失败保留。1024正式数组依赖精确205 build和成功试运行，仍必须先通过原最终300MHz/电气门；未启动旧单节点206/209由新220–223替代，不删除原证据。
