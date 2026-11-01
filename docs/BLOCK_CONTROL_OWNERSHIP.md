# 按功能大Block计数：控制、端口与资源归属条件

Issue151 / PR152；本轮输入`a37e37cad757af5bfc94ed65db3e2e728023c251`研究树，叶源沿用PR144 `707878621b2add4ed218b8c43df2e95c9a56e2ba`。本稿只做静态候选计数及控制边界，不写新RTL、不跑仿真/服务器/EDA；正式整合与远端交付见PR回执。用户已有服务器授权保留，后续实际实验按REMOTE_RULES和任务授权执行，本次未提交作业，不把“未执行”说成权限不足。

## 1. 主表：面积优先的串行参考，不是已证明最少或最佳数量

| 功能大Block | M | N | E | G | R | S | T | 本地CTRL | 叶宏合计 | 成立的主要条件 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| A_plain：无输出激活门的完整Attention子层 | 1 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 5 | N依次做输入/头Norm和Softmax，E做RoPE/偏置/缩放/残差；N自身有EXP，不调用G；中间值有真实存储 |
| A_gate：带Qwen3.5式输出Sigmoid门的完整Attention子层 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 6 | A_plain所需功能之外，G执行PV后/Wo前的输出门；门格式/尺度已接收 |
| F：完整dense FFN子层 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 6 | 包含pre/post Norm、gate/up/激活/down/残差；M单上下文按阶段串行，完整mid存储/重算方案闭合 |
| X：完整MoE子层 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 6 | 一次preNorm、router/TopK/selected-logit gather/Softmax、8专家及merge在本地串行；额外宽数值和专家供给必需 |
| D：完整GDN mixer | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 7 | 卷积/SiLU、Repeat/L2、系数、R递推、每head RMS128后门乘、投影/残差；全层old/next与NUM闭合 |
| H：完整Falcon Attention+SSM混合mixer | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 7 | input RMS一次，两个分支共享M/N/E/S/T按合法顺序串行物化，SSM门乘后RMS4096，最后join/残差 |

这里每行是**一个物理包装的一种功能能力配置**。M1表示一个原生M，不是为每个矩阵各放一个M；N1也不是每个Norm各一个N。S1为16KiB、T1为6KiB原生容量，不能解释为完整工作集已驻留。CTRL1是该包装一个本地控制责任域，可以包含多个局部FSM/helper/仲裁器，绝不意味着只有一个很小FSM或零额外逻辑。全芯片母控先按**1个另计**，不是每行再加一个全局母控；它的能力、端口与最终数量仍待实现/后端接收。

这些数可构成串行功能架构候选，不是算法推导的硬件下界。尤其T1是保留原生批次缓冲的比较选择，不是证明所有profile必需T且恰好1个；若未来改用其他输出路径，需另做接口/存储/物理比较。本轮不通过删宏造一个未经验证的新最小方案。

## 2. type、profile和instance必须分开

- **功能profile**：程序语义，如A_plain、A_gate、F、X、D、H；同名profile还有已限定的模型/形状/数值变体。
- **物理type**：固定宏种类/数量、内部route/MUX、CTRL/ROM、buffer、pin和物理视图的包装设计。计数相同不证明type相同：A_gate/F/X只有在ROM、数值、内部路线和存储能力并集都预制接收后，才可合并成一个非R type。D/H同理可合成全七类type。
- **物理instance**：芯片实际放置的某type数量n。242逻辑层或484子层调用不等于放242/484个Block，也不等于六行各必须1个instance。

据主表可研究三种资源向量：B_plain=`(1,1,1,0,0,1,1)`，B_nonR=`(1,1,1,1,0,1,1)`，B_state=`(1,1,1,1,1,1,1)`，向量顺序M/N/E/G/R/S/T。它们只是候选物理type类，不是已经实现/定版的3个硬宏。若B_nonR的预制能力覆盖A_gate/F/X，也可承接A_plain；这样可以不单独制B_plain，但付出G存在而某任务不使用的成本。B_state若预制并接收相应stateless程序/路线/数值/MEM能力，也可执行A/F/X，不把整岛永久锁死为D/H：R-free产品时M/N/E/G/S/T仍可复用，只有未用R等独占部分闲置。但BOM超集本身不证明profile能力union已存在。是否保留B_plain取决于真实产品集合、实例配比和后端，不能仅比较5/6/7个叶的个数决定。

异构也可以符合共同底座：冻结前一次确定所有type、数量n、几何/位置/pin、ROM/CTRL和有源路线；不同产品使用完全相同M1–M10/PG/CTS，M11/M12永久选择已存在入口、表和跨Block合法路线。不能某产品把R删掉、另一产品加R后仍称相同底座；也不能按每个产品重新综合删opcode或插新MUX/buffer。某产品不用的固定instance仍存在，可用预制clock/power管理，效果需测量。

## 3. 各宏唯一owner及单实例串行条件

| 共享资源 | 本地唯一owner必须保证 | 不能由“一个CTRL”省略的真实硬件 |
|---|---|---|
| M cmd/rsp与merged结果 | 所有投影/分数/PV/down/专家调用先后使用；保存旧结果后才覆盖；error/fault_rows处理 | 命令译码/holding、结果物化与必要宽算术；两个输入bank不等于两个执行M |
| M A128/B512 | 本地S loader或已实现适配选路，目标明确且不并驱 | 若S1要喂M2，必须有预制A/B分路、ready回路MUX/仲裁和目标锁；原生S只有一个loader |
| N group/replay | 完成当前统计/EXP/gamma回放后才换组；回访时保留期望计数/phase | raw/EXP/gamma存储/回放、target计数及response保持；ready不等于context可抢占 |
| E/G | 操作数收齐、单位匹配、tail已绑定，G在途全部退休后换任务 | 拆拼/收集、G lane配对和流水计数；E并不是宽S32/64通用加法器 |
| S ordinary/loader | 所有读写都收ACK；普通S响应独立排空；loader A/B/done全部接收 | S helper、仲裁/地址形成、必要1024B loader capture；不能拿busy代替普通口空闲 |
| R | 单context及pending/history规则、先保存op12、等op7 COPY应答再导出新active | 全层old/next payload、根元数据及NUM系数/偏置/单位转换；op8不能回滚已commit |
| T | 同租约顺序填满→commit→读完→release；输出反压保持 | 同T回路spool、对端stored ACK与buffer生存期；last只结束已定义fragment，不自动结束子层 |

单M对F/X/H尤其重要：不能在同一merged里保留down/PV partial时，插入下一段gate/up/QK把它覆盖；原生M没有merged restore。面积参考采用可证明的阶段串行物化，或明确的重算/外部宽累加方案。若完整mid超过片上空间且MEM仍未实现，该profile为**not mapped**，并非M1的参考数已证明能在当前片上完整运行。增加M2也不自动补齐供数口、mid读取、N/S带宽或消除全部重读。

## 4. H主方案：完整一岛R1/M1，串行两个分支

H主表仍是M/N/E/G/R/S/T各1、本地CTRL1。一次input RMS2560得到N，同时保留原X供最终残差。两个分支消费同一N：Attention完成到scaledAttn并实际保存；SSM完成到scaledSSM并实际保存（两分支先后可以按固定程序选择，但最终加法顺序按源图/已接收数值合同）。期间M只归本地一处owner，N的input RMS、Attention Softmax与SSM末RMS4096也有明确串行阶段。

SSM中conv bias须在SiLU前，dt/decay/inject不能凭G/N的名字推定已有任意Exp/宽算术；R负责原生conv和state阶段，外侧local CTRL/版本服务负责完整多tile。先SiLU(Z)门乘再跨4096 RMS，与D的每head RMS128后门乘不同。最后由本地join执行`Mixed=scaledAttn+scaledSSM`，然后`Y=X+Mixed`；若共同单位超过E的S16能力，额外wide add/convert路径必须计入，不能把E1解释成足够做任意精度join。

R的唯一owner和state/history root归整个H任务的本地版本责任域。每tile op12先保存、op7等待COPY、op11/op14导出并收实际存储ACK；所有必需tile和下游门完成后才发布完整root。R/T/KV/输出没有联合原子提交；一支失败时另一支或R可能已经localcommit，必须记录partial并按旧/新版本合同处理，不能直接重跑整个H。

一岛不代表工作集很小：Falcon H2560的S16原X、归一化N、Attention输出、SSM输出各5120B，同时保留四份为20480B，超过S16KiB（具体生存期可消减，须证明，不能把此同时保留算例当强制下界）。SSM4096的S16向量8192B也超单T6KiB。应按真实生存期、分fragment和实际MEM/额外buffer设计；本稿不把这些存储假定存在。

## 5. H拆成两个独立分支：主比较不另增NormJoin岛

若目标是两个分支有机会并行，明确比较以下新包装，而不是拿两个完整子层profile直接相加：

| 包装/比较 | M | N | E | G | R | S | T | CTRL | 说明 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Attn_H_wrapper | 1 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 新复合包装：拥有唯一inputNorm、归一化N的fork及原X保活，做Attention branch，收SSM返回后join/residual |
| SSM_H_branch | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 消费同一归一化N，不再做inputNorm、不独自加X残差；仍需N做末端RMS4096 |
| **两包装合计** | **2** | **2** | **2** | **1** | **1** | **2** | **2** | **2** | 12叶；未包含额外NUM/存储/复制/通信/版本服务 |

Attn_H_wrapper不是已有完整A_plain：完整A已经含自己inputNorm和residual，而这个新包装要把其前/后控制延伸到整个H。输入Norm只执行1次；源N数2分别用于两个分支各自后续归约，没有因共享一次inputNorm就能把Attention Softmax与SSM RMS免费并行放到一个N中。E2、S2、T2也是两个真正独立包装各自所有的资源；Norm/join在Attention包装复用其N/E，不再额外算第三套。

母控仍可把两个包装视为一个复合H任务，本地parent负责fork/join并收子分支事件；或母控对H子任务发令但维持一个H版本/输出发布门。要选定一种唯一parent，不能母控和Attn本地同时发布H完成。SSM包装拥有其R原生口与state候选；H parent拥有整H成功/partial门。KV由Attention路径的既定owner维护；SSM与KV发布不自动联合原子。

两个S/T及其握手不是足够的活性证明：N的发送需实际stored ACK；SSM返回的输入槽须提前预约；Attn占任务槽等SSM时不能同时占满其回传入口；T一次租约必须先排空/释放再用于另一fragment。若同一物理包装回用或所需返回空间不足，先真实staging→ACK→release，不能靠等待环“未来会腾出空间”。外存尚未接入时相应完整H映射保持gap。

若坚持Norm和Join再放独立第三包装，可用N1/E1/S1/T1、M0/G0/R0/CTRL1的NormJoin服务作对照；再加两branch后总量M2/N3/E3/G1/R1/S3/T3、CTRL3。它增加一个物理边界和两条路径，当前没有必要把它作为主计数。若要共享N/E/S/T而非复制，必须给它们一个固定唯一owner和预制跨分支MUX/仲裁/holding；这更像一个共享资源H cluster，不能声称两个独立岛仍各自独立执行且不付通信/仲裁成本。

另一个**单H cluster**候选为M2、N/E/G/R/S/T各1、CTRL1（8叶），在一包装内复制M并共享其余资源。它可减少矩阵执行互斥，却仍受一个S loader、N分组、E和T租约限制，且新增A/B目的选择/ready回路和结果收集。它不是12叶split方案的等性能替代，也不是本轮推荐数量或已验证硬件。

## 6. 不调用某opcode与删除一块硬件是两件事

本表默认使用未改动的原生叶宏。A_plain不放G/R是**冻结前固定物理type的整宏取舍**，不是为每产品删除N或M内部某些op。未调用的独占路径、数组/LUT可能空闲；共享datapath仍被其他op使用，不能按op个数比例估面积。

- N的TopK数组/scan逻辑在F里可能不用，但Norm/Softmax还共享group divider/root及部分缩放资源；N1仍是完整N，不能说F只要RMS所以N面积变成若干分之一。
- M的S8/S16路径共享64个S8乘法器、partial/merge/读出，两个输入bank不是两个M；少用一种格式不会使另一整套乘法阵列自动消失。
- G的函数表有各自内容，四级保持/乘法/舍入可能共享；E的op也通过同一FSM与有共享路径的算术/打包执行，不是一op对应一个可单独删掉的宏。
- R不实例化在非状态type时，其专用active/shadow银行确实不在该type内；但这些字节不能转成额外通用S，也不能直接换算PPA百分比。

若未来按固定type预制N_noTopK等裁剪变体，必须先证明该type允许的全部程序都不用该能力，形成新的source/功能/时序/物理资格并固定到所有产品共用底座；还须保留全系统需要TopK的X可用路线。这是另一个候选，不是本表已有优化。逐产品重综合删op违反共同M1–M10约束。

## 7. 七宏计数之外必须另列的账

| 项目 | 本轮参考数量/处理 | 不能当已具备的原因 |
|---|---|---|
| 全局母控 | 全芯片串行/有限并发参考1个，另算 | P2母控是固定MST程序，不是完整模型依赖调度器 |
| local CTRL/ROM | 每物理Block 1个控制责任域；完整ROM容量未编译 | 内部原生owner/helper/arbiter/回放/phase状态均有实际面积 |
| ingress/egress、PACK/LAYOUT | 每包装1套逻辑服务候选，共享或内联均须真实实现/预算 | payload保持、拆拼、n-major、Repeat/Gather/tail、route选择不是M11金属能加的 |
| ordinary S helper | 每S普通端口1个单owner服务候选 | 读写ACK、loader竞争与返回保持独立推进 |
| NUM | D/H需系数/范围/宽bias/转换能力，X需宽加权merge；可先以每包装1个串行NUM服务槽作实现候选 | slot不是已实现宏；opcode、精度/范围、吞吐和局部共享还待设计。A/F是否需额外宽能力由逐边数值证明决定，不能统一填0便假装问题消失 |
| MEM/PHY/仲裁与每岛端点 | 系统级串行参考可研究1个共享服务，但控制器/通道数/带宽及所有权尚未冻结；每包装仍需真实端点 | 系统有外存，不等于共享服务、容量、ACK、晚响应/错误和布线已实现 |
| capture/spool和大张量区 | 一般loader导出最多1024B新capture；同T回路最多6144B spool；输入/输出/EXP/mid/state/KV等另算 | 未证明生存期可复用就不能删；fragmenting数据不代替完整数学归约及状态版本 |
| root/state/history/KV版本 | 按真实layer/root数量及old/next payload计算，不按一个R tile推全层 | GDN每层2MiB/版本、Falcon SSM每层4MiB/版本，超S；有localcommit仍未root发布 |
| 物理支撑 | MUX/arbiter/route lock、中继、PG/CTS/reset/CDC、隔离/可选电源管理全部另算 | 未跑后端，七宏个数不能推出总面积/速度/功耗或布线通过 |

NUM1和MEM1只是可讨论的串行服务数量算例，不能作为待定算术/外存功能已实现或吞吐足够的证据。所有bit extraction能复用既有op时优先复用，如M op5已经合法量化后再取位/重排，不能为了统一形式强制另造通用转换器；实际缺宽算术时也不能用E S16冒充S32。

## 8. P2 wrapper迁移和下一步验证

1. 保留当前真实S/M/T与ordinary ACK helper；把P2的M_CLEAR/SCALE/LOAD/EXEC/M_STORE/T生命周期抽成**本地基础核服务**。当前P2 u_mother的21×16 ROM可作为本地顺序器起点，芯片上另设计global mother；不能把现成MST母控直接算成完整模型母控。
2. 固定程序不变、外部tensor数据可变：替换literal初值、硬编码S448/452/456、0x9884和T4字的单fixture限制，定义有界shape/format/地址/fragment入口。已有完整profile尚未编译；新参数不会启动装载新程序。
3. 每包装保持唯一port owner，先集成M/N/E/G/S/T并完成一个完整F或A参考，再加D/H/X所需R/NUM/状态及专家数据。各profile准确Norm/残差/门顺序和模型数值参考先锁定。
4. 独立RTL依次验证ACK守恒/输出保持、格式与tail、跨M bank/scale与N phase重用、局部stage存储、同S/T竞争、有限反压/取消排空；完整H重点测一次inputNorm、两支同token配对、R不可取消窗口、partial失败和发布。split再测双包装独立停顿/回传槽不足/恢复，不能借完整H7叶的计数证明split活性。
5. 对同一固定type/instance布局编译两个不同产品的完整ROM/层表和路线；核验M1–M10及PG/CTS一致，M11/M12只被动绑定。同步做本地控制/端点/供数与存储反馈及后端表征，再接收实例配比与性能；服务器实际运行需固定源码/工具/配置/输入SHA、作业追踪和结束回执。

本轮`python scripts/check_project.py`管理结构检查PASS；`check_block_control_sizing.py`执行20项JSON算术/计数一致性检查PASS，回执见`block-control-checks.json`。复算为`python -B -X utf8 work/Melodydt/151/check_block_control_sizing.py --directory work/Melodydt/151 --report docs/BLOCK_CONTROL_OWNERSHIP.md --receipt work/Melodydt/151/block-control-checks.json`。它们不代表新RTL、全模型数值、MEM或后端通过。不擅派其他成员负责人或截止日期。

## 来源与协商

只读来源为本包integrated的`COARSE_BLOCK_MODEL_MAPPING.md`、`COARSE_BLOCK_CONTROL_CONTRACT.md`、`COARSE_BLOCK_RESOURCE_STUDY.md`、`PHASE2_MST_IMPLEMENTATION.md`、`SAMPLE_MODEL_FAMILY_SPEC.md`及真实七宏RTL。模型agent已确认H split的M2/N2/E2/G1/R1/S2/T2（12叶）及一次Norm/单残差边界。资源agent的全芯片B_nonR+B_state算例为13叶/G2，因为nonR同时覆盖A_gate/F/X；它与本稿只覆盖H内无G Attention分支的12叶算例范围不同，不矛盾。
