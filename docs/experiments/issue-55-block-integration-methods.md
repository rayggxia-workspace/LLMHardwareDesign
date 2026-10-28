# Issue #55：可复用方法与适用边界

配套[实际结果](issue-55-full-block-integration.md)。以下成功均限已绑定输入与实际检查范围，不宣称任意Block/LLM通用成功；最终freeze/route尚未实现。

## 1. 完整清单、分区与版本（已验证结构/有限功能）

输入：锁定原真实顶层、参数/文件表、RTL、选定核心层次、实际ODB/LEF/Liberty/SDC/RC。输出：input_manifest、coverage_map、完整叶/状态/存储归属、resource union与case mapping。按最近核心祖先分配全部叶，余项入案例辅助；外部模型单列，不将类别名当实例。直接搬移原JSON叶/端点，不用会隐式清理的submod；唯一自包含mem MEMID允许随层次改名，其他参数/连接/init逐项保持。资源并集允许闲置，不意味着面积收益。

约束/失败：原参数不缩减，不能少算33内部SRAM或把LL外部16bank计core面积。原前端反馈的有限清理归因不等于源RTL形式证明。实际submod未驱动失败、shiftx导出写数据差异均保留；有独立原语资格后才采用官方仿真导出修复，物理模式不使用shiftx替代或RTL回退。

复跑：inventory/integrate入口及已封存driver；新commit/配置/输出，验证输入SHA、原生命令和闭合checkpoint后恢复。Formal Block替换：能力/状态/存储契约、层次选择器、逻辑/物理端口、实际数据库与版本；不能只改名称。

## 2. 完整功能、操作覆盖与独立证据（有限测试已验证）

输入：完整原RTL/实际物理资源网表、原协议/外存、确定刺激/种子、可信数值oracle。输出：逐周期公共控制/请求/响应、有效字节、停顿保持、全内存/计数配对。复用同一trace_check/parse_log/compare_public_trace；不以最终值代替握手/时序。

audit_open_coverage按实际ld_start上升沿与系统reset数启动次数，用真实加载地址/长度、大端$fread规则解析程序；静态opcode存在不是动态退休或数值全覆盖。真实旧20例都单启动的缺口由新三种子各两次host启动补齐，原存储不重载、sys_rst不重拉，只在halt/drain后正常重启sequencer。新回放保留原断言字节。

generate_open_isa_cases先复制五份必要只读原ISA模型源码，使用已有Python/NumPy；原三个完整256KiB RTL结果逐字节校准。再生成54程序×3种子，涵盖20VPU函数/适用广播/OUTER decay/QST/控制及3列对4lane尾块。数值oracle来自校准的位精确模型，协议/周期参考来自真实原RTL；输出按原大小/大小端规则保持。所有162原版/完整物理DUT通过；open_mm_cases适配器另生成40程序×3seed=120例，四WF及合法独立MM/QACT模式、PAIR偶/奇KB、ACT尾端和若干零/次正规边界已实际三方通过，独立1382文件/36858行/899277字段闭合；未穷尽组合、异常数值或中途复位。复用同一生成/回放/独立工具，未复制另一套比较器。

成功条件：类型明确、DUT无回退、全硬件参数/外存不变、同刺激逐周期与完整内存一致。close_open_paired_evidence重验全部输入/协议/数值/源链及1797文件，不重跑仿真；actual ready单bit与内存末byte破坏负例检出。LL复用四个独立单线程组并行、组内30任务不拆；六组180任务/540完整1MiB镜像独立闭合。未执行SDF、四态/全输入证明，不能推广。

复跑：对应*-driver/spec.json，生成/参考/物理/独立阶段均有单独版本与SHA。Formal Block/LLM接入需行为模型、真实协议、输入图/刺激与原数值格式；共同计算/存储/通信表示保留，未扩展完整LLM编译器。

## 3. 实际库状态锥资格（已验证，范围受限）

输入：原综合和实际物理网表、同一真实Liberty/Yosys行为、匹配状态与公共端口。先严格库存/锥比对；图不等保留失败，不立即判逻辑错。整体布尔miter超时不写通过。

qualify_cell_symmetry对最多6输入的实际标量组合master枚举完整二态真值、合法pin置换与驱动族；顺序驱动族还需实际状态/输出图同构。certify_auxiliary_symmetry遍历全部状态输入/公共输出锥，仅允许已资格交换、buffer/反相/常量规范化，未知活逻辑失败。92组合master/1292联合真值行、两辅助全状态/锥及真实D/clock破坏负例已验证。

成功：同库SHA、完整库存/端口与零锥差异；不删除困难锥。约束：同名状态/初值、原存储模型、二态与受支持库语法；不是源RTL或任意逻辑重构形式等价。只读RC测量可显式接收未完成更强证明的失败图证书，但必须标state_equivalence_accepted=false，不能放行M8/freeze；18项来源守卫区分这些类型。Formal Block需提供匹配和行为适配，不改失败状态骗过检查。

## 4. 必要迁线与完整M8接入（几何已验证，新增时序未接受）

输入：实际wire/special/via/PG/PIN/OBS、技术规则、固定原单元和可改目标网。via依真实cut/两侧包围连通，OBS不是导体；空间桶查目标对全部邻近网/PG/pin，新接触为失败。非目标-非目标短路不在增量checker范围，另用原生DRC。

复用已有几何与布局核心，新增native表适配。FIXED DEF导入先证明几何完全一致；真实失败说明FIXED标记不足以防新线接触旧线，需把非目标导体/各层via暂作精确OBS、路后删除且核对原OBS。原逻辑/位置/非目标形状/PG保持、禁止层清空、独立连通/短接和fresh DRC均为必要条件，不能删导体/障碍或改层名伪造。

完整引出按真实轨道、M7/M8导体、via cut及未来M8↔M9落脚做区间图着色，分配共享外围通道。真实71项via7间距失败促使纳入cut规则；原逐端口通道约19倍面积的低效方案保留，紧凑版只改路由不缩端口/硬件。原BPin身份/形状保留，追加真实M8 box；同名/同BPin的孤立形状不凭名字合并。共享物理net的多个term均保留；52项端口/几何守卫覆盖错网、交换PIN归属等。

RC复用实际规则与原SDC，要求每个BTerm锚在声明M8 pad、电阻图连通且正R、全部有效native/SPEF端点对应；旧低层锚点负例拒绝。孤立单端点和未连接输出仅在逐项证明后分类，fanout无有限限制不补造通过。

成功/停止：完整接口、真实via、无新增接触、原生DRC、精确保护及RC/时序范围分别验收；源变化、未知几何、预算不足或未闭合checkpoint立即非零。Formal Block替换实际pad/轨道/方向/层/通孔/RC/SDC，不套当前case数值。

## 5. 公平时序差异与冻结前辅助候选（方法已验证，问题未解决）

同工具/库/约束/单元/提取范围比较；仅改die/track也能产生差异的VECTOR控制已实测，不把所有差值归因新线。以端点身份和未舍入PathEnd_slack列新/消失/持续变化，与WNS/TNS/count交叉验证；总数相同不代表同端点，总数下降不代表无新增。四项差异负例通过，2e-9ns阈值仅数值定位。VECTOR新增两cap端点及最大28.510528ps/3.676171ps单点恶化仍未解。

辅助是本任务新建且未冻结的实现，原约束下修复可调整其原生优化策略，不授权改原核心或冻结底层。绑定实际失败RC/完整覆盖/同CTS前驱后才运行；完整资源、接口、流水保持，新源须重做受影响几何/功能/寄生。单via1_4→via1_3局部修复只在声明坐标/相同cut/M1/M2包含范围的适配器中支持，非通用任意via修复；六项负例及全非目标形状保持已实测。

LL实际最慢ATTN数据路径cell延迟主导，于是只评估关闭强制FA映射的候选，原完整native输入重新综合，不从已映射pre-ABC伪恢复。综合565287单元、floorplan/布局/CTS/完整布线与fresh DRC0通过，完整连通92108及65545state/168074cone92109通过；92112真实3ns setup−2.151527ns、hold−0.547693ns/slew98/cap2548未达目标，不作为改善或当前源。Formal Block需提供原真实约束、基准和允许变更边界；不以降频/缩功能掩盖失败。

## 6. 原生抽象、完整覆盖与单调闭合（两新辅助已验证）

先R0逐端口逐层矩形/尺寸/native ITerm bbox回读；完整routing-metal含master PIN/OBS必须被实际抽象OBS或PIN精确矩形并集覆盖，x-sweep/y区间树检查内部孔洞，非bbox近似。cut/spacing仍非制造签核。当前仅R0资格；其他方向需另验证。

真实反例：原生LEF导出可保留全部pin却漏一段M8 wire。修补只根据闭合完整失败列表补保守OBS、扣除所有PIN；原DB不变。probe_abstract_origin --reuse-origin-export复用同版本完整导出/归一化，重新原生读回修补视图，不重做相同导出。

qualify_monotonic_abstract_patch组合证明：原完整19.5M/23.8M源扫描只缺各1项；两次actual pin roundtrip证明PIN与源/坐标系相同，流式验证新native OBS精确保留旧15.4M/19.1M OBS序列，只增加全部声明patch；精确并集覆盖每个原缺口。保留旧失败，不伪称重跑全扫描。删除旧OBS、错层/缺patch、bbox内部孔洞四负例检出；本轮两例都通过，每个仅多1个OBS。该方法只用于完整已枚举失败且源SHA/PIN不变的单调扩展，源变或障碍重排无法证明时停止/回完整检查。

模型复用同版本真实post-M8提取生成，PG仅在实际角色/零cap声明证明后转pg_pin，信号时序字节不改。两新辅助native链接/全端口通过。write_timing_model的scalar setup/hold、输入slew/长线R/例外限制记录；可读模型不代表父层时序或真实工艺合格。正式Block需真实几何/工艺/模型与方向资格。

## 7. 当前源绑定、常量别名与共同布局（已验证局部阶段）

bind_physical_endpoints按真实bit/方向/宽度/offset/upto绑定全部BTerm和多层pin，支持降序和任意resource名；6项正负例。共享net记录关系，不伪造独立驱动。canonicalize_parent_aliases只接受实际库资格的唯一常量/BUF驱动链，拒绝输入/未知/循环/附加驱动；并查集合并父网同时保留每逻辑位。17输出同值并不等于17驱动；九负例。92004/92005已在两新辅助M8版本重做；原数据证明不能沿用到不同版本。

plan_union_layout复用旧blockflow原算法与SHA：固定优先、ID序、有界网格，真实pin Manhattan增量代价，完整逐位图/尺寸/间距/朝向输入配置化，不用手工模块中心替代。第1轮六资源7851连接/572站点规划实际通过，不代表最优/拥堵/外部I/O/真实布线。prepare-base placement按真实LEF/model构建共同ODB，独立别名避开同basename库冲突；macro-only直接设置die，不凭空添rows。全部source PIN/OBS、端口变换和不重叠检查，实际移动宏负例；完整正例检查点只在SHA闭合后恢复，不重复布局或覆盖旧失败。

正式Block替换尺寸/朝向/引脚/障碍/模型/通信权重/搜索预算。92011对新源尺寸/ID/R0严格一致才保留第一轮坐标；92015新原生六宏/24779端口完整读回及移动宏负例通过。PG/其他基础设施仍须新源重验，不能沿用旧freeze证明。

## 8. 固定PG与控制接入（PG原型通过，控制/冻结未完成）

prepare-base fixed-pg先同时预留全部真实PG stub，再在全宏bbox keepout外构造真实pitch/offset对齐可视网格，M7横/M8纵A*，Manhattan下界+via代价；其他供电和所有cut间距受约束，最多300万扩展。原生via7_0和真实规则绑定，source stub对全部源M8其他网检查。失败反馈包括先路VDD侵占VSS接入、原生BPin FIXED枚举错误；旧失败保留。

实际91954写ODB/DEF并重新读回：全部master/位置/源geometry不变，仅声明PG连接/导体新增。verify fixed-pg从实际native矩形/真实cut-via构图，逐个资源M8锚点到外部源、无导体岛、异电源短接/spacing和同网cut规则；真实源stub删线、反供电复制、删via负例，再新进程check_power_grid要求catch0/return1。91960两电源各6锚点/1连通分量通过；没有IR/EM或完整DRC/RC/STA。原型源为旧辅助，最终换源须重验，不接受freeze。

verify_closed_producer绑定同任务精确submission/job/source和闭合result SHA，afterany只给启动时机，不当成功或豁免。92025/92026已完成当前源PG实际构建/独立几何/native-grid；源变化后重新资格，IR/EM/RC/STA未执行。

probe_fixed_control_access四向直线12中4失败保留。probe_control_dogleg以实际source M8/OBS、父PG/其他宏和原child die为障碍，64k/128k/256k DBU窗口、每次20万状态预算、1600DBU网格、M8横向代价2/纵向1的A*，空间桶查询精确线段spacing；跨资源顺序预留已选路径。原始单元M8 PIN/OBS若存在未知变换即拒绝，不能静默忽略。92020全部12路径联合通过，负例检出真实障碍穿线/异网source-pad短接；失败只证明当前有界/贪心方法未找到，不是全局不可布。输入/输出均可换资源和数量，当前工艺数值适配器需替换并重新资格化。materialize_control_access以同一prepare-base入口生成真实FIXED M8导体/独立代理输入，并检查原实例/master/geometry/PG精确保留、端点导体图和删线/异网复制负例；92028实际ODB/DEF新进程完整读回通过，44个新增形状、12个局部源/代理锚点连通，精确保护原geometry/PG/实例，实际删线/异网导体短接负例检出。局部代理接入不是完整控制树，不改变原active reset拓扑，idle reset polarity不能冒充active驱动。强静默性质失败与合法闲置/活动输出隔离是不同要求，均不能靠免费门控/清零假设解决。

92041确认1共同clock+4不同reset；MXU rst真实源为open辅助bit_23659输出，不能替成外部reset。12sink+该source共13接入。92044联合几何通过，但构建因变量覆盖把方向写成top而失败，原证据保留。86e48b2只按原生ITerm/规范角色恢复已知坏源码的方向元数据，几何不改、未知方向冲突不豁免。92064复用精确同源闭合路径，重新实际构建/读回13端点/51新增形状，保护实例/几何/PG，删线与短接负例通过；不是完整分发或CTS。

固定控制复用plan_routes：合格escape、原生PG/全部local导体及via为障碍；完整5网、M7外部根/M8内部driver。92071发现同一搜索路径内新增via未受旧via集合约束；保守4x2点集又造成偏好层图奇偶X分裂，92085负例重现。新connected_staggered规则：真实pitch1600DBU、索引gx/gy；gy mod8=0取偶X，=2取奇X，=4取gx mod6∈{0,3}作桥。不同via中心Chebyshev距离至少2pitch，并继续检查全部固定PG via。仅该模式加邻近[-4,+4]pitch坐标，默认PG几何不变。92085跨组/间距/障碍负例通过，92087完整5网实际2614新增形状/13端点及4根、原geometry/PG严格保护、真实删线/短接/删via/端点错网负例与重新读回均通过。这是保守启发式，不保证所有可布线图可达/最优；算法搜索失败不直接证明物理容量不足。

merge_identical_modules对完整原物理source逐字节相同body共享定义，实例/连接不改；冲突body/游离上下文拒绝。92063全6资源/33RAM三seed held-reset及实际请求负例通过，检查有效we&&wmask写，非raw未知控制全0。active+idle任务与真实park/隔离仍待验证，闲置父层原内部连线必须保留。固定时钟质量、有源适配/预连线、freeze/最终M9/M10未验收；主要候选1/3，无冻结。正式Block替换真实能力/端口/模型/工艺/规则后重验。
## 9. 固定控制寄生与端点资格（提取/电阻图已验证，时钟质量未验证）

输入：精确闭合实际控制网络收据、同源placement模型与真实RC/技术文件；输出：坐标SPEF、原生模型覆盖、逐网络端点/正电阻图、线电容及负例。verify_closed_producer仅在绑定submission/job/source的实际PASS后生成独立配置，afterany本身不当成功。flow verify --adapter fixed-control-rc复用原生timing_model_coverage、现有严格SPEF解析与resistance_graphs，不另造RC近似模型。

measure_fixed_control_rc只读实际ODB，不写新底层；逐项绑定6宏模型与placement SHA，要求每个控制网全部ITerm/BTerm身份/方向与原生pin bbox吻合、无漏端点、全电阻节点1连通分量且有正R。实际SPEF删除某必要网全部电阻与移除端点必须非零失败。92092实际5网/17端点通过，两负例检出；clock线电容4.57556pF，只是实际提取量，未据此宣称源驱动、slew/skew或周期满足。标准库135个未用cell无LEF与弃用提取API警告保留，实际全部6宏模型链接通过。

复跑使用union-fixed-control-rc-r01-4c-01-driver/spec.json，复制小配置、修改driver/output/source commit；原结果不可覆盖。正式Block需替换真实模型、PG/时钟/复位拓扑、工艺RC与原生接口；本研究典型corner、标量宏模型、pin bbox坐标资格不等于完整时钟树/全设计STA、IR/EM或制造签核。下一步需要真实外部源驱动/波形、原锁定约束、传播时钟和reset recovery/removal检查；需要有源资源时必须在冻结前统一入并集并重验，不能在定制阶段免费新增。

## 10. 共同clock入口传播与真实状态负例（测量已验证，质量FAIL）

输入：闭合实际固定控制ODB/SPEF、原两个完整case SDC/周期、6个同源标量宏模型及真实clock端点；输出：每个入口rise/fall×min/max的arrival、latency、slew、实际max_transition比较与原生传播状态。flow verify --adapter fixed-control-clock复用RC/原生模型资格；只翻译原clock约束，不冒充已建立完整data I/O/全案例STA。

measure_control_clock_boundary按实际原clock声明绑定2.5/3ns，拒绝丢弃显式driver/transition/latency/uncertainty；当前原文件均未给这些项，按原默认边界测量。原生vertex API实际为3参数；native is_propagated与global_auto、SI/UI单位必须实际读回。反例发现raw pin arrival在ideal时钟下仍非零，因此非零测量不能单独证明使用了propagated clock。92101正例原生propagated=1/global_auto=0，实际ideal状态0负例拒绝；单位float误差只给1e-6相对校准容差，物理限制不放宽。

每例6pin/24记录及负例通过测量门槛，独立比较实际模型max_transition得到6/6新违例（0.343–1.746ns vs0.199ns）；入口跨度约1.010ns，不推广为完整register-to-register skew/内部leaf结论。成功的测量工具不代表设计质量通过。复跑绑定union-fixed-control-clock-boundary-r01-4c-05-driver/spec.json，在新driver/output版本执行；历史失败保留。正式Block需替换真实时钟port/负载/模型/约束和工艺，不能直接套0.199ns或默认理想源。

后续修复在冻结前完成共同buffer/合法row与PG，所有原Block与原内部单元保持。92103仅核查已有buffer/sites/native CTS能力，尚未创建或验证新的clock tree；必须实际布线/PG/寄生后重新测量并跑两完整case功能，不能用CTS退出或估算值放行。

## 11. 冻结前共同clock缓冲与真实电源PIN（CTS/放置已验证，物理供电/钟线待做）

输入：实际失败clock传播收据、同源6宏/PG/reset/模型、原2.5/3ns周期、已完整native真值资格的标准buffer、真实row site/LEF/预算；输出：未冻结CTS ODB/DEF/网表/SDC、实际buffer清单和逻辑clock图、保护性原生读回。prepare-base --stage clock-cts把最快原周期2.5ns用于构树；CTS缓冲间距选项250μm、合法化位移边界500×500μm、新buffer上限4096是本次候选参数，不是正式Block规格。

仅接受同库实际全二态真值A→Z的无状态正向buffer；复用已合格两行真值，不以名字或重跑全库替代资格。原6宏内部/坐标及非clock PG/reset/外部pin完全保护，变更仅在task-owned未冻结副本中。native CTS/H-tree与wire repair生成75实例，实际保存后按master/端口/PG角色和footprint无重叠逐项核对；原master PIN/OBS流式hash58,972,634行相同。clock_graph沿唯一外部根、实际buffer A/Z和所有原clock sink，检查单驱动/无环/无无效支路/全可达，实际断buffer输入负例失败。92107通过这些门槛；PG仅logical、实际clock routing/RC/完整功能仍false，不能把构树/放置当物理修复成功。

inventory --adapter clock-buffer-pins在新进程读取同一保存ODB，定向导出实际5master pin矩形及75native实例/ITerm，避免重复审计全部原始Block。用原生instance origin和R0/MX/MY/R180变换实际rect，逐端口与真实ITerm bbox相符，再从真实PG矩形选制造网格内点。92116形成150个M1端点；实际origin偏移和VDD bbox空白中心反例检出。源source layer、via landing/enclosure/spacing和真实M1–M8路径是后续输入，尚未构造。正式Block接入替换真实型号/正向行为/位置/朝向/geometry/PG net映射/技术与预算，未知朝向或非零std master origin显式拒绝，不能默默猜坐标。

复跑使用union-common-clock-cts-r01-4c-01-driver/spec.json与clock-buffer-PG-pin-inventory-r01-4c-01-driver/spec.json，在新source commit/driver/output执行；原失败和新中间结果保持。后续须真实新增PG与clock导体/via、重新独立连通/DRC/RC/两频率及两完整case功能，且同最终底座/资源供两版使用。

## 12. 真实闭合生产者续接（当前native全网/状态/RC链已执行）

verify_closed_producer只接受同任务自己submission的准确job/source/typed PASS和immutable结果SHA；afterany只提供调度时机。不同源的真实旧PASS不能借用，92111实际负例通过。auxiliary-connectivity/auxiliary-logic直接适配既有检查器，measure-auxiliary-rc绑定实际state/全网证书和同一route，生成新driver独立源配置后调用原RC测量，不放宽原消费门槛。92108/92109/92112实际链闭合；它们各自的PASS不覆盖timing/功能/最终布线。schema字段/源路径适配与实际算法分开；源变化使相关证明失效，不复用旧底座证明。

auxiliary-timing-repair续接92121：只有同源actual RC完整覆盖725253网/2325528端点92119通过后，才把实际coverage SHA写入独立配置；原qualify_repair_failure再次核对同CTS前驱/route/measure/coverage后启用既有setup_hold_electrical策略。不是重复raw route或降频/缩功能；仅新未冻结辅助内部实现允许变化，所有新增结果仍需完整DRC/PG/状态/功能/寄生资格，当前未验收。

## 13. 新buffer供电接入与真实PIN边界反馈

输入为已放置buffer的实际PIN/OBS、真实技术层/单cut via、制造网格、现有PG/reset导体和完整宏keepout。局部启发式在全部实际PG矩形而非bbox中心选源点，枚举相邻via到M3、水平/垂直错开后到M8，联合保留150端点的金属/cut间距；通过局部计划不代表实际供电。92124仅选主rail在第118端点失败；92125改为真实PG fingers等候选，150个端点规划及source-enclosure/低层短接/cut负例通过，原宏keepout未放宽。

plan_clock_buffer_pg_backbone逐端点枚举最近实际同网旧PG段，复用现有A*、connected_staggered通孔点集与全部固定障碍；目标是避免把150端点放入同一个巨大坐标图。当前92126仍规划，单线程/4核申请；不是布线结果。materialize_clock_buffer_pg只消费精确同任务提交及typed PASS闭合结果，计划生成真实SWire/via、保存ODB后新进程重开，全源PIN/OBS/实例/端口和原导体保持，通用邻层via图、81锚点/电源、原生check_power_grid与placement及真实断线/低层短接/缺cut负例均为实际接受门槛，目前未执行通过。review_fixed_pg的可选真实层规则/邻层via参数保留原默认M7/M8；92128对原实际PG和真实via1_4 fixture回归通过。

必须额外验证std PIN/OBS包围范围，不只验证cell bbox。92107原生place通过，但实际4个buffer的PG PIN跨入固定VECTOR框，另12个与GEMM/openaux不足最小间距。refine_common_clock_buffers依据实际全PIN/OBS和真实层spacing选同朝向站点/成对行偏移，仅调整本任务未冻结std；原6Block不动。92129仅Y候选无法解决横向间距，明确失败；92131新增X站点候选并重新全量读回。旧源局部/PG规划从此不能为新坐标背书；92130实际失败生产者拒绝证明调度依赖不是PASS。待原生资格和新PIN通过后再重复受影响步骤。该修复不是新主要布局轮次或M9容量失败，不切换M11/M12。

正式Block接入需替换实际native视图、PIN/OBS/供电名、层/过孔参数、布局和站点/行约束；非零origin/未知朝向/多高度行仍要求显式适配。接口命令见对应固定driver/spec；新增prepare-base stage为buffer-pg-local、buffer-pg-backbone、buffer-pg-native，freeze仍不可接受。

<!-- pg-v3-method-refinement -->

92131使用真实全PIN/OBS加真实层spacing修复16个新std位置（12个±0.38µm X、4个±2.8µm Y），完整读回和58,972,634行原宏PIN/OBS/既有导体保持通过，75buffer时钟图相同。92132从新ODB重读150实际供电PIN；旧坐标相关PG计划全部失效。原生单元外框place通过不等于PIN保持安全距离，必须分别验证。

92126单端点最近12目标均落M7限制行phase3而失败；connected_staggered约束新via的规则不得误禁止复用原有合法同网via，但单独允许复用仍未救回原目标。92137在同一闭合94路径前缀上重现失败、改接已连通M8支路，67状态成功。新启发式按M8/M7交替候选以免最近列表被不可接入单层占满，逐端点把已连通支路加入后续目标集；仅已完成至旧根的支路可用，不把未接通局部PG误当目标。PGObstacleIndex按真实坐标箱返回候选，原hit/spacing/keepout谓词不变，动态保留新导体；92136 3002真实查询与整套小图路径完全一致（0.543→0.021秒仅查询环节，不是整布线或硅性能倍率）。92138/92139以修订源重新生成全部150条局部/主干规划，actual native PG资格仍独立。

verify_closed_producer为fresh PIN→local→backbone及actual PG→common clock提供typed PASS/SHA/job/source门槛；92140使用真实较旧但同类型PASS错配新submission，四项均拒绝且无消费/绑定。materialize_clock_buffer_pg支持直接或受约束续接的实际PG producer，并在写入前拒绝实际源PIN侵入宏。92141必须生成真实SWire/via、新进程完整读回、检查81anchor/每电源、真实低层via/cut/原生PG和负例，不能将150计划当供电完成。

route_common_clock/prepare-base stage fixed-clock-route已实现并以92142作严格后续任务，尚待实际运行。原生76clock网只用M1–M8，所有源实例/朝向/端口/PG/reset/PINOBS保持。复用已验证fixed_obstructions临时遮罩保护原导体，结束仅清理本次新增遮罩，原OBS身份保持。写实ODB后新进程native库存、独立DRT DRC、真实多层端点图/clock图、target-vs-all接触及删root导体/短接/固定PG删除负例才可接受布线；RC/slew/skew/全功能另审，禁止自动CTS/新增有源资源/占用M9/M10。源Lib及clock2.5ns来自精确CTS配置，不以降频换通过。

92145实际子源边界审计区分保守bbox裕量风险与真实金属间距违例；选定GEMM附近24个候选，读取精确子数据库native导体并按child→parent坐标/真实层spacing检查，未发现异网几何。该项不覆盖所有child PIN/OBS、不代替全局DRC。算法当前每项的实际状态由最新milestone/source_revision/spec与summary分开给出，不能把待执行模块写成已验证。

<!-- actual-pg-memory-recovery-clock-pipeline -->

完整PG真实原生校验92141先得VDD0/1，再在VSS分配内存时失败：记录总mapped48,986,697,728字节+2,785,017,856字节新块超过48GiB AS。不是新断线证据，亦非节点RAM全部耗尽。materialize_clock_buffer_pg的checkpoint模式只接受精确构造0/native0/native_pg-6及对应allocation日志/原VDD成功/源和结果SHA/同一producer，复查完整原几何/新增PG矩形/81锚点及断线/低层短接/缺cut负例；只读复用已存ODB/native，VDD复用不可变实际成功证据，VSS在新进程运行。92151全部通过，3342/3222导体节点各1分量；旧FAIL和VSS原abort日志不改。未来首次PG按两独立进程逐网检查，避免累积虚拟地址arena。64GiB只是有界AS，实际peak见sacct；4CPU保持。

恢复收据提供output_database_sha256/native_after/native_inventory_sha256明确只读指针，消费端严格核实，不把旧失败目录名称当作成功或失败的替代证据，也不复制数GB数据。程序状态和具体子检查状态分开。实际VDDSUCCESS不得凭空推广到VSS，单网失败后仅消费已明确闭合子检查；无法精确绑定时拒绝复用。

模型来源必须沿正确typed上游检查，不能假定PG直接inputs哈希表已经展开所有祖先。92152全部7模型在CTV92131中有确切SHA，却不在PG浅层map，启动器拒绝；修复为显式绑定确切CTV收据与library-list/RC配置，再逐模型验证实际bytes，没有修改模型/放宽门槛。11个实际master/81实例native模型覆盖随后通过。92158暴露父层仅有几何路径而没有native轨道。ensure_native_tracks只为缺失ROUTING层按真实getPitchX/Y、getOffsetX/Y创建TrackGrid，保留旧pattern；92162对确切真实PGODB在内存预检10层20pattern和set_routing_layers通过，不写源。轨道是工具元数据，不是新增金属线或M11层；route保存后另进程导出tracks_saved，与初始化结果逐项一致，损坏pitch负例拒绝。

measure_fixed_control_rc和measure_control_clock_boundary复用原单线协议并扩展buffered_clock_route：实际80clock/reset网、167端点SPEF/正R图、删R/端点负例；六原宏input、150bufferA/Z传播和native全当前网slew/cap/fanout报告，按原2.5/3ns与actualideal负例。无有限fanout不能标全部规则通过；当前网不含完整case数据，边界spread也不是完整寄存器skew。92150旧源回归5网17端点/两case六pin/全部数值和原失败一致；1e-12只比较回归数值，不放宽物理通过阈值。新buffered模式以92167/92168在实际route PASS后运行，现未验收。required_stage_evidence同时绑定已过回归收据及三个适配器SHA，改代码不能借旧测试。

原生C++数据库diff没有已安装Tcl绑定（92153），没有采用未经验证的快速替代，58M完整native几何检查保留。源码编写/metadata预检/内部DRC0与真实路线的全部独立验收严格分开；92163仅部分完成，不提前冻结。共享facade、常量驱动及inactive完整父内部网络保持、M8→M9/via9接入是接下来的独立输入和门槛。

<!-- logical-common-IO-index -->

## 完整接口到公共IO的逻辑索引（92176已验证；物理IO待实现）

输入：经SHA绑定的原resource-union case_mapping.original_ports、实际canonical连接图、同版固定control拓扑及其物理binding祖先。输出：逐位映射、候选公共位槽容量、固定clock/reset来源、常量/未用位槽未分配项。prepare-base -- --stage common-io-plan通过同一入口调用，真实参数由92176 driver固定。

算法：按原port名排序、bit_lsb递增逐位扫描；以(port,bit)唯一索引，检查driver/sink角色、方向及canonical.logical_source_bits包含原source bit。canonical单电气驱动组保留真实resource端点与内部别名，不把别名当多驱动。固定control只从同版拓扑提取，不按名字猜复位，不把open内部MXU reset误归外部reset。每方向数据槽容量取案例最大值，不相加、不删除未用资源或恒定输出。顺序是可替换置换；没有物理坐标/面积/时序/吞吐量含义。所有case内部连接依然需要实现，不能因闲置而丢弃。

成功条件：所有原external bit各出现一次、源bit/方向/角色一致、独立control计数一致、源SHA结束不变。92176原两case全部通过；实际图删除端点/重复端点/翻方向/抹源位4负例均拒绝。三case改名和1/2/7位夹具亦通过，输入顺序改变不影响逐case结果。92173入口参数漏--失败发生在处理case之前；真实失败保留，92176同commit仅修正命令。

未解决：公共物理引脚位置、实际多边接入/负载、常量驱动/输出隔离、闲置输入合法供给及active+idle整任务。字母排序不能当作最佳物理排列；按端点位置、多边通道容量、两case联合通信和真实via间距另定置换。不得从2627/4915槽推断实际可布通，也不得凭M8端点齐全推出M9访问成功。正式Block替换需更新原顶层port、canonical图、实际binding与control同版收据；程序不硬编码case/模块名/位宽/坐标。No physical freeze or generic LLM claim.

<!-- complete-active-idle-composition -->

## 同底座六资源的active+idle数字组合（编译已过，完整运行待闭合）

输入：同一原资源并集两完整物理parent、闭合编译/准备收据、公共接口/数组打包/固定参数契约、已过全闲置92063配置。输出：原active物理Verilog不变的独立编译单元、另一完整parent模块及端口适配器、只供仿真的共享clock/held-reset/合法空闲输入与请求/存储写监测。原测试平台/外存/刺激不改，不把原parent内部互连删掉或把所有Block单独tie静态。

算法：完整module字节摘要判同；baseline_paths代表已独立编译的active定义，输出只发射伴随parent新增定义。相同库复用，异库/不绑定指令/属性差异拒绝；baseline模型不重复声明。active端口适配器仅在其唯一末尾endmodule之前追加完整companion/监测，原active前缀、实例、端口/参数赋值逐字保持；原body及所有子source SHA闭合。SRAM行为模型全部保留；inactive open时bind33原SRAM有效we&&mask检查。观测计数/force是测试设施，不新增物理状态。

验证：92180/92181两个完整版本实际generate/make -j4通过；原source闭合、原规模/库身份及基线负例保留。run_active_idle_regression复用既有原完整20与6×30 paired算法，独立核验每段实际日志的active/inactive身份、时钟周期覆盖、原RAM实例集合/有效写计数；原二进制强制闲置请求作为运行负例，另实际日志删标记/漏RAM/写入突变要拒绝。92184 host及92187真正容器六parser负例通过；open方向92190完整20例与原设计逐周期/全内存一致、闲置LL1476280次请求检查及真实强制请求负例已通过；LL方向92189的6×30任务、243883行/17769493字段及闲置open33RAM/731361公共请求、真实强制请求负例也已闭合通过；仍非最终冻结物理网表功能验证。未证明所有输入/四态/SDF。

失败及复用：原host3.12有file_digest而实际容器3.10没有，92185/86启动失败；用项目原有流式SHA，不安装软件。零锁定输入时保留最早异常，不以笼统“closurechanged”遮盖。92188保留原刺激全文件SHA拒绝，实际差异只有历史CPUmetadata1→4；显式读取原闭合config，实际运行controller始终4核，不修改原配置或放宽刺激门槛。所有重试只读复用同一闭合完整binary，未重复生成/编译。

复跑入口及完整参数：runs/full-active-idle-opentpu-replay-4c-03-driver/spec.json与LL-replay-4c-02-driver/spec.json。依照README创建新driver/output再提交；父submission/source_revision绑定job/commit，必须实际编译PASS才可运行。正式Block替换时更新完整物理parent/参数/外部接口/存储契约、idle控制与无请求协议、真实输入驱动方案及来源收据，重做资格，不能沿用旧PASS。物理固定预连线/tie/隔离/75clockbuffer真实网表及最终冻结定制回装仍是独立待实现门槛。

<!-- real-route-checkpoint-and-M9-access -->

## 独立clock检查超时的无损恢复（检查点资格过，完整DRC待闭合）

输入：确切闭合92163失败收据/SHA，原bound配置、同原生tool/7模型，三个成功route/savedtracks/native子阶段及所有实际ODB/native/导出hash。仅接受observed3599s freshDRC TimeoutExpired且无完成marker/assessment；不接受坏几何、来源变化或未闭合结果。输出：原不可变路径指针、新独立检查目录，不重新生成原布线/导出；保存旧FAIL，不改写成PASS。

算法：依次核对typed状态/子命令完整性/config/native协议/工具/源及全部checkpoint输出hash，之后重新做全部实例/master/PINOBS/PGreset/端口/轨道/层约束精确检查，freshnativeDRC预算10800s，只有再通过连通/异网与实际负例才可给真实routePASS。92198实际checkpoint资格与7个坏元数据/错来源指针负例通过，完整DRC仍运行。timeoutrun现在记录命令和超时字段，最早错误不遮盖。不是以DRC内计数0或超时为验收。

消费者通过closed_native_artifacts显式解析output_database_sha256/native_after/native_inventory_sha256；完整字段一致，同任务runs路径、每项实际SHA，部分字段拒绝。旧格式仍按原output_sha256解析。92199实际旧源RC/clock数值及旧slewFAIL/ideal负例与原一致；新模板锁新回归和适配器SHA。后续正式Block只替换实际source/config/qualifiedmodels和合法检查边界，不能借旧PASS跨版本跳过DRC。

## 全量M8落脚到M9轨道的准备（已规划；真实导体/DRC未做）

输入：same canonical physical binding的完整源M8pad表、实际native宏位置/朝向、真实via8_0和M9/cut规则。输出：每个必需端点的固定via中心、候选M9短引出、完整约束与选择。统计24767端口，13控制已固定、201原无消费输出保留但不强制access，24553必需落脚无丢弃。不是按模块中心估算。

audit_m9_access_candidates变换存档合格M8pad，核对真实ITerm bbox容纳，直接读native via三矩形，检查制造grid/底层包围、M9和cut矩形间距。初审92197为不同网pair；新版cut规则必须包含同网，92202已用实际全部候选重查为0。源PIN资格继承已绑定原生闭合来源，未再全量scan58M PINOBS，不把bbox包含单独当真实pin证明。

plan_M9_track_escapes保持所有原M8pad和via8中心固定，依据实际H向M9的pitch/offset生成下/上相邻轨道与包含原M9landing的矩形。一/二候选形成布尔变量，每个不同网矩形冲突变成禁止选项对的2-SAT子句，用迭代Kosaraju SCC判可满足并回查全部选择/原中心/轨道/标量间距。停止条件是有限候选完整可满足或带变量/约束索引的候选失败；后者不证明两层全局容量不可行，不自动启用M11/M12。

92202全24553候选规划实际通过（10329原偏轨点，整体引出长度16526400 DBU），via8中心/M8pad未移动、nativeM9轨道/标量间距通过。实际候选间禁配对0，没有案例拥堵求解证据；2-SAT实际只受14224个固定选择约束，禁配对/矛盾/固定选项由夹具验证。仅可行性规划，无最优/通用适配证明。输入无固定module名、数量或人工坐标；正式Block需给可追溯实际pad几何/朝向、canonical连接、via/layer规则和固定/允许修改范围。

下一门槛：在新派生数据库实例化真实via8/M9引出，检查最小面积/EOL/PRL/完整原生DRC/源固定几何不变，再做M10/via9和真正跨Block网络/IO/RC；计划文件不是物理通过。不能假定M8齐全或上轨道规划通过即可全局布通。

<!-- actual-full-native-M9-access-r01 -->

本轮把24k端点规划实际编码为dbWire/via8并保存ODB，独立重新打开全部几何，用原M8pad包含性、精确电气端点、实例/PIN/OBS/既有导体不变式和断cut/错网负例审核。10329个离轨中心以短M9段接真实轨道，原LEF/native AREA=0交叉核实；未默认新增面积规则。独立DRC首次暴露缺GCELLGRID，第二次文本序列化错误，均保留FAIL；修复后同时初始化TrackGrid和从精确封存DEF提取的GCellGrid元数据（与时钟源质量无关），新增TSV往返夹具；第三次已实际通过原生元数据读回，fullnativeDRC进行中，严格解析真实文件和完成标记。成功条件只覆盖局部接入，不代替长线连通、功能、RC/STA或冻结。正式Block替换字段为源PG/接入/规范连接图、真实层/via规则和几何；不得改冻结M8落脚。

llaccel实际修复8556锥的严格图差异复用已有Liberty真值表对称检查后全数一致。原失败保留，只有实际库允许的引脚置换与已验证状态模型可归一化；任意逻辑重写仍保守拒绝。RC可在显式state_pending测量模式运行，但不能因此通过功能或选择新底座。真实命令均在本轮索引指向的不可变driver/spec.json，重新运行须新driver/output/source commit。

<!-- shared-IO-cut-and-fixed-prewire-method -->

## 公共接口、边界容量和固定预连线候选

输入为闭合完整规范连接图、实际M8端点/native层和via形状、固定控制契约与完整公共IO位索引；输出为M8pad候选分配、条件性cut界、精确native固定网/ITerm清单。正式Block接入需替换资源尺寸/引脚/层规则/通信图/原始控制/允许固定的连接政策，不能直接套当前两独立父设计的保留政策。

| 模块 | 实际算法、参数与停止条件 | 实际验证及边界 |
| --- | --- | --- |
| plan_common_io_geometry | 从真实M8/M10共同X和M9的Y网格生成四边候选；via8/via9 landing/cut与原实例bbox/真实导体保守避让；按各case端点bbox距离+边负载罚项贪心匹配。整数case权重、边距/keepout可配；候选不足、缺真实端点/非法常量即非零失败 | 92219保留7542位，7676候选/剩134；三case改名/变数量等夹具通过。原37常量输出只有明确pending驱动，不伪造坐标；规划不是吞吐/布线/物理PASS |
| materialize_common_io | 严格绑定完整plan和源nativeDRC实际成功job/SHA；在新ODB中创建真实M8 BPin，保存ODB/DEF/V，重新打开全部native表，对原81实例/PIN/OBS/ITerm/旧网/导体逐项不变与新增pad精确几何做审核，含删除pad/错方向负例 | 92220等待源92213，尚未执行。无IO到case接线、无tie/buffer bank、无新增pad后DRC或功能验收 |
| analyze_native_cut_capacity | 对每个实际Block外围轮廓，按规范电气网而非端口数计内外跨界；分别算preferred网格模型和允许两层全边/反向的乐观默认宽距上界；记录真实低层data形状跨界候选。未知常量位置显式保留，下界不因此降低 | 92224 LLaux13505>10872，条件缺2633，低层data跨界0；本模型忽略障碍且角点可重复计容量。需要冻结前低层预连线/实际引出，不是整体路线物理失败、非M11后备依据 |
| plan_fixed_parent_links | 当前资源并集政策保留完整active和idle父图；筛出所有跨资源、无外部端口/未定位常量、唯一真实电气driver的内部网，核对实际sourceITerm/net；输出native目标清单和移除这些跨界后的剩余预算。预算/端点冲突/边界计数不一致即失败 | 92225候选7834=open1871+LL5963；尚无导体。LL余7542外部跨界，preferred仍缺2110，必须继续做外部固定引出/真实低层接入。不能泛化为任意共享Block/LLM的固定边选择算法 |
| inspect_parking_cells | 复用已验证Liberty真值表，原库与真实LEF/native精确link/尺寸/PIN/OBS，保留单位和缺失电气上限；pF/fF及未知单位拒绝夹具 | 92216模型/几何目录通过，BUF_X32 maxcap1904.3fF；无实际摆放/PG/负载/RC，常量cell未给有限cap不代表无限驱动 |

实际统一入口已有 inventory --adapter parking-cell-models；prepare-base -- --stage common-io-geometry/common-io-native/fixed-parent-links/m9-native-access；verify --adapter cut-capacity。完整绝对命令、4核申请、不可变source与SHA分别在本轮各driver/spec.json及source_revision.json；入口help仅验证分派，不当作业务通过。重跑必须新spec、新driver/output和固定源码，不覆盖历史结果。

LL新修复版的精确RC及独立728536网/2332094端点覆盖已闭合，3ns质量仍FAIL（setup−1.558247353/hold−.282644527/cap1825），最坏数据路径为crossbar状态到ATTENTION状态，不能因全SPEF覆盖、引脚对称或DRC0就替换资源。原始输入遗留问题、新辅助失败、候选规划和真实物理验证继续分开记录。

<!-- private-IO-fixed-and-full-M8-reservation -->

## 专属IO固定预连线与完整原M8接入保护（规划/接口资格已实际验证）

先保留两个完整父图及互不相交的资源集。公共IO槽若仅一个active案例使用、只对应一个规范电气网且资源端点方向/唯一driver匹配，可分配到固定低层预连线；共享槽仍由定制层切换。输入槽在不使用模式必须由外部主机驱动0，输出槽在不使用模式明确不采样。适配器输出external_private_IO_mode_contract.json，不能把边界条件误作新增onchip常量或门控。92232实际生成14059候选（7834内部/6225专属IO），仅数量与语义规划，尚无实际固定导体；active图cut余额不包含尚未构造的闲置零驱动网络。

native_M8_reservations.py从24553已资格pad推导每资源平移，逐个匹配全24767原信号/控制端口与完整native master PIN多边形；仅支持已验证R0，其他方向非零失败。92233完整58972828行读取及pad错位/删除真实PIN/重复端口/不支持方向4负例PASS。prepare_fixed_parent_input.py复用该资格，先建立完整IO再连接内部/专属网；route_fixed_parent_links.py保留目标网BPIN，给尚未连接的原M8pad和非目标IOpad追加临时M8避让约束，移除临时OBS后必须独立读回。源码路径和配置可复用，不等于新版实际路由已执行。

probe_drc_gcell_sensitivity.py实际9个小型native检查中不同GCell索引marker一致，提供工具性能诊断的有限证据。diagnose_clock_DRC_grid.py只对闭合超时的真实clock ODB在内存调整索引，保留原始routing tracks/几何/器件，检查导出DEF除GCELLGRID完全一致。其完整native检查仍在运行，结果仅diagnostic；不能据小夹具或超时改判整机DRC、clockRC/STA或冻结成功。正在运行的原fine-grid92213不停止、不重复。

<!-- idle-zero-load-placement-and-native-box-method -->

## 完整闲置输入驱动资源与实际放置（负载规划/放置/PIN资格通过，供电与布线未完成）

输入为完整两父图、共享IO分配、真实native ITerm/M8点与原库Liberty/标准单元PIN。按共享输入找出每个inactive案例必须置零的全部物理sink，不缩减硬件；专属输入明确由外部驱动0。流式读取实际OpenSTA Liberty直系pin属性并校验fF单位，缺失/未知电容失败。以资源归属与真实端点坐标排序，顺序装箱满足max32ports与1128.225fF pin预算；该预算来自真实BUF_X32 maxcap1904.3fF乘0.75减300fF假设wire裕量，非提取RC。每组预置一LOGIC0+一BUF，原内部状态不改，不增加流水。92238的1682端点/55组只是本候选；正式Block输入需替换能力、引脚、真实负载和位置资源。

place_idle_driver_cells.py在原资源四周搜索真实site/row候选，按到全部相关PIN的Manhattan和选择，避让全81原实例与宏keepout；只临时固定旧实例防止legalizer移动，保存前恢复原status，独立读取完整原生库存核对全部原PIN/OBS、位置、连接和原导体。实际92244加入110cells放置/原资源保持及真实off-site负例通过；不代表新PG/M8接入/低层导体已实现。所有源clock本来超时未验收，派生原型维持明确false，不能跳过gate。

inventory_added_cell_pins.py复用inventory_clock_buffer_pins.tcl的显式实例选择及既有坐标变换函数，避免以master名称选出旧buffer。110新单元逐本地多边形对照已资格真实库，R0/MX映射与native ITerm匹配；220PG/165signal/55需M8输出已实际核查92251。未知方向、bbox中心空洞/实际PIN外点、错origin与缺端点不得代替真实接入。下一步复用既有M1→M7/8供电escape/backbone规划；必须新增真实导体并做PG/short/native检查，不能把逻辑connect视为供电。

统一入口已加入prepare-base的idle-driver-loads、idle-driver-placement、private-io-fixed-links，以及inventory --adapter added-cell-pins；verify提供native-drc-boxes/native-drc-tile-pilot/original-m8-pads。实际业务命令与输入/源码版本见92238、92244、92251各driver/spec.json和source_revision.json，重跑须另设不重名driver/output。入口的--help派发已实际运行；这项CLI检查不算新的物理/业务验证，故不重复提交相同实验。

## 原生DRC区域化诊断（小夹具已验证，完整设计仍未验证）

安装工具92240实际Tcl API接受-box，参数直接使用native DBU。92245把微米当DBU的失败记录必须保留，不能因空区域marker0放行；92246用实际2000DBU/um、真实M5short与via8_0/M8/M9错误，默认全片、显式全片与四重叠覆盖区的marker并集一致，故具备有限的坐标/边界资格；不是任意工艺局部性定理。重复marker保留原区报告与完整native记录索引。

pilot_native_drc_tiles.py完整保留源ODB全部PIN/OBS/PG/wire/Track/GCell，仅请求原生checker查询区。规则网格64个core区完全覆盖die、每区扩6400DBU guard；92250目前仅先跑2区测量耗时，未完成整片，原source独立DRC依然FAIL/未验收。后续若性能可行必须跑全64区并核对边界/失败，不能把pilot、工具退出0或小夹具通过当整片通过。全局fine/coarse实验继续原句柄，观察超时不重启、不停止其他作业；本轮没有删除几何、proxy抽象替换或换M11/M12。

<!-- actual-idle-PG-local-and-M8-method -->

## 新增闲置驱动的供电、局部连接与固定M8接入（阶段二/三未验收）

本节更新此前“供电/局部线未完成”的历史状态。统一复用PG escape/backbone/materializer：source_kind=added_idle_cells，220真实PG PIN先搜索M1逃逸，再M7/M8共享电源树，真实native保存后对全部191资源检查供电图与OpenROAD check_power_grid。92257实际VDD/VSS各一连通分量、原81PG mask精确保留、全部原PIN/OBS/placement保持及断线/短路/CUT负例通过。新增sourcekind有独立PASS类型，不复用clock接受状态；仍不构成fullDRC/IR/EM/freeze。

route_fixed_parent_links.py复用原完整路由器/检查器新增added_cell_local输入适配：严格从真实端点识别55条零值单元到BUF的全部localnets，保留191资源及24767M8原接入点约束；实际路由、FIXED编码、新进程全native读回、全部保护几何相同及110端点连通/异网接触0/4个负例在92267通过。只有此基础设施局部adapter允许显式deferred_to_coherent_base，返回限定的局部接线PASS并明确fresh_native_DRC_accepted=false；原完整父层正式入口仍需完整freshDRC通过，sourceclock不因此获准。

plan_added_cell_signal_access.py复用PG几何搜索并显式传入真实信号PIN-net映射，防止把同一目标PIN误判异网障碍；55输出385真实via的M1-M8路径计划92270通过。materialize_added_driver_access.py统一native构造、完整源保存检查、真实连通/短路/缺via7CUT负例，92281已实际完成55个输出/1265形状并通过限定检查。固定M8内部导体不新增外部IO，不等同native M9/M10路由器已能访问，完整闲置输入布线/提取负载/功能对照/全片DRC仍须后续实际完成。

电气观察器master_pin_rows在流式验证完整字段的基础上跳过本来不参与该电气导体图的OBS字典构造，保留每一个实际PIN。92266遍历完整58972834条记录、50225PIN逐项等价和既有12几何夹具通过；读取264.246→56.727s，仅这一Python步骤。原始PIN/OBS、native exporter与原生DRC范围不变。独立OBS同yspan合并诊断92269严格核查全部矩形覆盖和增删负例，但记录减少为0；未用于任何底座或检查输入，无加速结论。

最终外部clock rise/fall及37openTPU常量输出load用户已确认未确定；保留显式null并阻塞相应最终电气/边界时序验收，不将默认0当成已确认输入。下一步按实际92281/92235结果继续；不得把超时、规划成功或局部连通扩大为完整底座通过。



## 局部线路RC测量的复用和边界

measure_fixed_control_rc.py新增source_kind=added_cell_local适配（旧clock/control门槛不变），只接受已封存真实55localnet连通/几何保持证据；使用同一真实DB、全部191资源和原七份已绑定Liberty，复用原生extract_fixed_control_rc.tcl、SPEF端点/坐标及电阻图检查，按输入regex和准确55数量选择完整localnet集合。92291实际55网/110端点及删除电阻/端点负例通过，输出数据库未写入；全部线路真实RC纳入记录，最终BUF输出分配负载另验，不能把局部RC当驱动能力或STA通过。显式full_native_DRC_accepted=false、full_timing_accepted=false、final_driver_load_accepted=false；未知用户边界继续null，无理想边沿/0负载假定。

<!-- coherent-current-IO-and-net-preparation -->

## 同一实际原型的公共IO与完整预连线端点准备

输入为原完整两case逐bit图、真实technology via8/via9与轨道、原24553数据M8端口目录，以及最新同一191资源PG/local/M8 savedODB/native库存。plan_common_io_geometry.py可选current_native适配先证明原81实例/master完整子集不变，并在当前全部58.9M导出记录中逐个核对原M8 PIN多边形，再按实际全部191实例边界/PG/clock/local/M8导体重做周边候选及加权端点bbox距离+边负载贪心分配。92307完整7542slots、7676候选通过，改名/变数量及容量不足/未知端点夹具通过；距离不是吞吐、时序或可布线证明。

materialize_common_io.py复用同一原生构造与全库存保持检查，新增显式unfrozen_powered_added_M8来源，只接受上述当前实际M8证据/对应完整计划；原qualified_M9_access路径的成功freshDRC来源门槛保持。92308真实生成7542M8外部BPin、保留191资源/6原PGcontrolBTerms及所有mask，完整新进程native导出与真实异网接触/删除pad/错方向/short负例通过。与规划相同via包围/层宽间距候选留出未变，但不能将此限定检查当fresh全DRC；新adapter状态与正式合格状态不同，full_native_DRC_accepted/source_clock_DRC_accepted=false。

prepare_fixed_parent_input.py可选existing_unfrozen_powered_IO适配复用实际已有7542pads，不重新生成/移动；逐层核对其191PG/local/M8原始PG证书祖先与完整7834internal+6225privateIO候选的一致性，重验所有24767原M8端口多边形，要求每个专属IO候选坐标仍等于真实已有pad，所有目标ITerm原本未连接，唯一归属且无覆盖旧infra。只建立实际网与ITerm连接元数据，保持所有原位置/master/PINOBS/保护导体；实际数据导线另验，绝不把接网当已布线。92325当前状态PASS_UNFROZEN_COHERENT_FIXED_NET_ASSIGNMENT_AND_PROTECTED_MASK_ONLY，其完整命令、不可变源码9c75c01和配置fixed_parent_input_current191_r01.json在driver记录。

原生92312暴露dont_touch保护拒绝接网而不是几何容量失败。确切API92319为isDoNotTouch与setDoNotTouch(bool)；native_instance_guards.tcl在授权冻结前记录全部原flag、仅对实际目标接网临时置false、保存前完全恢复。独立native读回再比全部flag，并在已读回内存对象翻转真实flag生成负例、不重写正式DB。原全几何/位置/端点约束不变，原formal-clock路径仍需既有freshDRC验收，不因该准备原型释放任何正式route/freeze条件。

## DRC性能诊断边界

完整源fine/coarse与大区域pilot均未获得完整通过结果；92235在真实4核上10800s超时，不能判工艺容量不可行。92331全部父层primitive与6macro bbox存在135相交配对（不同via层形状可分别计数），仅几何位置观察、不是135错误。由此简单“child互不重叠所以只复用内部证书”不足，还需全父子几何交互的完整规则覆盖。92332保留完整源几何，仅对一个32kDBU实际线路附近方框进行600s性能/marker观察；即使完成也不代表全片，仍不能代替原完整nativeDRC门槛。没有删除/替换OBS、改模型或遗漏区域后宣称完整通过。


实际92325终态已核对14059网/21926ITerm、24767原M8端口、全部191原实例保护标记与真实反向flag负例；保存DB几何/位置/track完全保持。此结果仍仅为接网元数据，没有数据导线。实际92332完整源局部32kDBU方框169s/0marker，证明小区域原生检查可完成，但不证明完整设计通过。后续同进程重复区域缓存诊断仅测性能和marker一致性，不降低最终检查覆盖。

<!-- native-parent-escape-and-full-control-scan-method -->

## 真实父层出口修复与完整控制端点扫描（局部已验证，完整底座未验收）

先读取真实原生marker，再将相交master OBS同原child带网名的M8导体逐项对齐。只有证明属于实际同一端口，才把真实PIN多边形视作合法出口；其他OBS和原导体均保留。repair_parent_pin_escape.py的参数给出来源收据、目标net/resource/term、真实工艺宽距、替换窗口、搜索边界与既有join；在实际全部障碍上作有界Manhattan A*搜索，以线长为代价、Manhattan距离为启发式，最多200000扩展，失败明确退出。仅在新副本替换精确计数的父层段；不修原Block、不删OBS、不加逻辑或改时钟。

92342实际6段换7段、局部完整窗口加guard原生DRC0；新进程完整读回后，全部实例/保护flag、PINOBS/master与非选导体的精确集合保持、目标连接/其他网接触和真实short负例通过。局部0不能替代整网/整片DRC，也没有证明新版本完整功能或时序。当前适配器只接受锁定的coherent fixed-input收据和已证明的原生contact trace；多次串联修补须明确扩展并重新验证完整保护比较，不能直接篡改已封存来源。

probe_native_control_pin_regions.py从原闭合native收据派生全部原有已接非PG宏控制ITerm，核对当前实例/端口/网/bbox，逐个bbox扩guard，对同一完整源数据库运行原生DRC；不删除宏内几何。92334实测初始化167s、同进程热查询约9s，故复用初始化减少重复开销；这只是查询执行优化。92343实际13/13区域完成，5区域/9原始marker，保留重叠报告，未验收完整时钟/底座。失败先做真实child/parent几何归属追踪，不以颜色、bbox相交、工具退出或性能缓存代替电气结论。

bind_idle_driver_connections.py把真实55BUF.M8出口与完整1682闲置sink清单连接到模式约束，核对native实例/ITerm、实际M8多边形及真实库负载，产生可独立替换的分发输入；92339实际三负例通过。该清单仍不是物理分发线。原全固定数据路由入口的full-clock/full-DRC门槛保持，不能借原型局部PASS绕过。

原始全llaccel物理参考现已找到并核对锁定RTL。对历史SDC/SPEF的端点测量只能提供历史模型参考；原始综合优化可能改变或删除状态名称，因此指定起点不存在时必须报告不具备同路径比较。原全局最差VECTOR裕量不能解释新辅助路径；逐状态映射、约束可比性与完整覆盖尚需验证。未知真实外部时钟边沿/输出电容保留null。

<!-- batch-native-parent-escape-method -->

## 批量父层出口修补与完整源区域性能诊断

输入为合格source收据/ODB/DEF、原M8真实reservations、child/parent带网名接触追踪及独立配置。配置给出精确原段矩形、替换窗口、search bounds、保留join与工艺宽距/步长。一次读取全部58972834行master，按实际PIN/OBS构造障碍，复用有界Manhattan A*（线长代价、Manhattan启发式、最多200000扩展）。互相重叠的独立搜索窗口明确拒绝，不能独立修补后假设无冲突。

只有真实同child端口来源已证明，才允许从实际PIN窗口合法退出；不删除或隐藏OBS。只在NETS区精确替换选定原段，保护同名外部PIN与非选join分支；首FIXED被换时把第一条保留NEW转换为+FIXED。92354窗口内含相邻分支的写库前失败，证明单靠窗口计数有歧义；新版本用实际7个矩形身份与负例检查，不扩大删除范围。

输出一份实际新ODB/DEF/网表、局部DRC、完整新进程native读回、所选矩形精确差分、连接与真实short负例。成功必须原191实例/位置/master/guard、全部PINOBS、非选导体和连接精确保留、目标网络完整连通且异网接触0。92356实际7段换12段、四局部DRC0，完整读回尚未闭合；4595条floorplan/row/track/GCell metadata已有独立相等证据。局部结果不替代整片DRC、最终功能、RC/STA或冻结。

统一prepare-base -- --stage parent-pin-escapes实际命令在92356driver/spec.json；正式Block需替换资源/端口、真实几何、技术规则、允许修改边界与网络需求，程序不内置案例名/数量/坐标。verify --adapter control-pin-regions新增显式complete_die_tile_pilot模式：仍要求实际producer资格与DBU金属/via负例，按真实die生成完整覆盖网格，仅抽实际宏中心/四角作有界性能试跑，返回独立诊断状态。规划全覆盖不等于执行全覆盖，不放宽正式路由的完整检查门槛。

<!-- complete-clock-and-tiled-checkpoint-method -->

## 完整钟线与可恢复的整片原生检查

verify_parent_clock.py输入闭合当前191资源来源及原CTS/真实route库存，复用C.clock_graph与G的实际导体连通/接触检查；先证明全部原75buffer/master/实例/clockmask相同，再覆盖76网/157端点/6入口。92359三类真实破坏负例通过；该结果不包含native DRC、RC或未知边界下的时序。所有数量来自锁定来源而非重新缩减硬件。

native_tiled_scan.py输入实际ODB及闭合source、全部控制区域0marker、完整钟线图、真实全10层/两via资格与参数（tile pitch/guard/batch/worker数/时间/AS限制）。按真实die生成不重叠core的完整覆盖网格，查询框向外加guard，所有worker加载同一完整source geometry。实际有限负例证明DBU/重叠查询行为，不当作任意foundry规则定理。输出逐块原始报告和hash、按16块闭合且实际before/after DEF相同的批次、全部完成/剩余索引及失败原因。重复marker保留来源，完整覆盖与0marker是不同条件。

每worker仅native1线程，最多4worker，总线程合计不超过4CPU affinity；32GiB AS/worker且先按MemAvailable保留余量选择worker数。首批只有一个批次，实际1worker，不声称四倍加速。每个完整批次查询完才检查停止标记；任意marker使其他worker在自身批次边界正常退出，无外部杀作业。处理自身预算超时后只收纳已经封存的批次，未闭合部分不计完成。

恢复合同绑定ODB/工具/程序与helper SHA、die、pitch、guard、batch和线程模式；不能跨改变几何/工具/规则的版本复用。检查点通过实际报告SHA、query框、唯一tile、before/after DEF等值验证。source改变、框错、重复/未知tile负例均被拒。resume_native_tiled_scan.py必须位于准确afterany依赖之后，读取真正终态/输入保持的无违规partial收据，再写出含实际SHA的resolved配置；不能事先填不存在的成功收据或观察超时重启。

92363实际完成16/4096块、0marker、闭合DEF保持，且12真实负例native1/4线程marker一致；作为故意partial返回非零，随后92364实际从其检查点继续剩余4080，不重复首批。92358的10个性能查询与首16块都不等于最终整片通过。全量运行源码/配置/真实命令在各driver/spec.json、source_revision.json和resolved_full_scan_config.json。正式Block接入需替换真实ODB/资格适配器、工艺/规则、输入端点与资源配置；网格和检查点算法不依赖模块名、固定坐标或数量。正式clock/fullroute/freeze门槛与最终功能/RC/STA验收仍独立保留。

<!-- native-extents-alias-and-resource-recovery-method -->

## 全部几何覆盖条件、原生别名与资源限制恢复

whole_geometry_extent.py输入闭合当前ODB/native inventory及绑定其SHA的完整query计划，流式处理全部master几何，汇总完整bbox和每个PIN bbox，复用已资格R0/MX/MY/R180变换逐项对照真实ITerm，并验证每个父层wire/via/BPIN及所有实例几何都在query die内。92400实读58972834行、191实例、25464端口、26755父层shape，无越界/转换差异；实际错MX和移到die外的bbox负例被拒。未知方向直接失败，不通过裁剪/删OBS/忽略边缘来宣称覆盖。这个条件不等于执行完全部DRC。

historical_alias_paths.py使用已有Yosys原生解析器读取只读原始elaborated RTL、输出RTLIL，按声明宽度/offset/方向解析直接wire等式；合法fanout可有多个wire别名，再在真实原物理ODB查唯一实际存在的寄存器pin。配置提供逻辑wire/bits、物理命名适配和目标pin；不凭名字猜地址或把并列wire当多个driver。原始rstart[24..27]→_23121_[0..3]实际核对及未知bit/重复记录负例通过。只对这四条原始路径保留历史SDC/SPEF测量；不替代原版-新实现状态/上下文可比性和完整端点比较，不将少数原始负slack扩展为所有新增问题均继承。

92364实际在32GiB worker虚拟地址限制失败：mapped32947679232+allocation1610612736>34359738368，物理RSS约17–19GiB；这是可追溯资源参数失败，不是布线不可行或DRC0。recover_native_tile_batches.py要求准确afterany终态依赖，严格验证原FAIL_INCOMPLETE/输入保持/全部worker SIGABRT的实际mmap证据及不等式；用原来完全相同的query executor/helper重新检查所有封存report SHA、query框、唯一tile和DEF等值。只产生独立partial checkpoint证书，保留source_native_run_status=FAIL，native_DRC_reexecuted=false；不修改或掩盖原始失败，不纳入未封存query。92405真实复核128块/8批通过。

后续92406仍执行同一查询程序及合同，仅把AS64GiB/worker、task core0纳入新配置/driver，实际/proc已确认四进程AS/CPU affinity生效。start/completion用不同独占文件名修复附带的回执错误；该wrapper变化不触及query executor SHA。正式Block输入改变ODB/工具/规则/查询算法时，原检查点仍必须失效；不能借资源恢复跨几何版本复用。当前全量仍运行，正式native/clock/RC/STA/功能/freeze检查没有放宽。

<!-- complete-negative-endpoint-census-method -->

完整负端点普查：复用compare_timing_endpoints.py/.tcl，输入单一已闭合ODB/SPEF/原SDC/Liberty、精确active RC覆盖收据及原native时序汇总；对max/min枚举所有负端点，以唯一身份、有限数、原生数量、WNS、TNS联检确认没有截断及单位混淆。输出完整normalized_endpoints.json及按实际端点后缀分组的endpoint_pin_groups.json。单输入状态为PASS_COMPLETE_NAMED_TIMING_ENDPOINT_CENSUS_ONLY、comparison_performed=false；两份以上保持既有同frame/context严格比较，不削弱门槛。分组只说明实际引脚名字，不自动判定setup/recovery、原有/新增。92425实际枚举5635/30端点且四类负例检出；时序仍fail。报告有多个path group时应按实际slack排序，不能把首条当全局最差；原始复位恢复条目+1.839ns与最差ATTN数据−1.526ns已核对。原完整设计同名精确状态路径的测量92427仅补齐历史参照，未证明新旧可比或给予豁免。复跑：python3 -B -I -S compare_timing_endpoints.py --config configs/timing_endpoints_llaccel_auxiliary_census_r01.json --output <本人任务下全新目录>，通过submit.py申请4CPU且使用固定commit；无需安装、重提取或改变几何。正式Block替换variant收据、ODB/SPEF/metadata/coverage和context；缺任一封存来源或完整端点数量/TNS不符即非零失败。最新证据索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261027T130003Z/milestone.json，SHA-256=ff9e1b479ad7e3aadb207a7ba0775d9174fdbaec6f01fdc3d07546c5805f8e3f。

<!-- current-clock-rc-without-source-acceptance -->

对待验收时钟底座进行独立RC测量：复用measure_fixed_control_rc.py与extract_fixed_control_rc.tcl；新增显式source_kind=unaccepted_current_clock_measurement适配器，原buffered_clock_route的真实完整DRC gate保持不变。输入精确current ODB与独立完整时钟mask/拓扑/实际引脚连通收据、封存库列表、技术RC规则；按原生CLOCK类型遍历全部声明网络，提取带坐标SPEF并逐网核对完整端点/方向/实际bbox及正电阻图。只输出MEASURED类型，全部DRC/clock质量/时序/冻结标记false。实际76网157端点的两类提取负例和7类来源完整性负例通过，92432额外断言typed状态。92429首次已完成的提取因Python变量遮蔽导致错误旧PASS类型；旧产物保留，修正变量后严格绑定相同技术、Tcl、工具、完整库、ODB、原SPEF SHA及旧命令成功，只做新review而不重提取。统一入口必须在--adapter fixed-control-rc后使用--再传适配器参数。正式Block替换收据、库/RC规则及声明网络/端点数量；引脚缺失、RC断开或来源/数量不匹配即非零失败。该测量可在完整native DRC运行期间独立开展，但绝不能用于放行原要求完整DRC的boundary/freeze接口；未知外部边沿/负载不设为0，最终slew/skew/STA仍未执行。最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261027T131439Z/milestone.json；SHA-256=36cef30df3c8eba214b540d81f3e917451699d43df1117c2fed5deb381009cc7。

<!-- complete-clock-static-load-screen -->

静态clock负载上界筛查：输入已闭合的待验收来源RC收据、同一实际native CLOCK网络/引脚清单、封存Liberty和配置中的网络/端点/内部驱动数。先核对原SPEF明确PIN_CAP NONE以排除pin cap双计，再逐网计算C_upper=C_wire+Σmax(C_pin,C_rise,C_fall)，与该实际driver的库max_capacitance比较；缺限值/未知单位/非有限负载显式失败或未验证，外部clock入口不虚构驱动能力。92433覆盖76网157端点、75内部驱动均未超上界、5类负例检出；外部root仍未验证。输出clock_static_loads.json和characterized_clock_pin_models.json，源几何不改，不提取第二份RC、不运行native STA。此结果只在研究RC/标量macro模型条件下证明静态上界不超库值，不证明有效C、动态slew、skew、DRC、时序或冻结。统一入口：flow.py verify --adapter clock-static-loads -- --config configs/current191_clock_static_loads_r01.json --output <本人全新目录>，实际spec使用4CPU，主算法单线程/封存hash核验至多4并行。后续Block替换收据、模型及显式计数，不依赖特定实例名或坐标。最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261027T132427Z/milestone.json；SHA-256=93503167bddabf4922fbf86088e7a267572374b552d7424ec67233c51a75fab3。

<!-- complete-native-source-qualification-gate -->

完整父层来源资格核验：输入精确scan生产者submission/spec、相同ODB/query合同、完整die grid、完整clock图和全几何范围证明；afterany等待真实扫描终态COMPLETED，然后重生成覆盖表，逐一核对全部唯一tile、报告SHA/实际marker、batch前后真实DEF相等、固定工具/算法版本、12原生1/4线程负例，保持完整范围而不靠progress推断。输出仅当前父层模型的完整tiled-native-DRC/clock图来源几何资格，clock质量/STA/function/freeze仍未验收；工具/tech/有限盒上下文资格限制不扩张为foundry签核。92435实际测试4个纯元数据正例、7种记录变异和实际128partial拒绝；该测试不调用native DRC，不能作为整片成功。真实92436已依赖92406等待，尚未执行来源核验。host-only后处理不执行EDA工具，重新校验task-local实际输入；容器工具/LEF使用封存生产者的历史SHA，明确未在host重测，不冒充新工具运行。配置化合同/grid/source路径替代坐标与案例名；不同技术或执行器不兼容旧证据，非零拒绝。统一命令flow.py verify --adapter complete-source-native-qualification -- --config configs/current_source_complete_native_qualification_r01.json --output <本人新目录>；自测额外--self-test-only；必须通过对应4CPU/真实afterany spec执行完整模式。最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261027T133915Z/milestone.json；SHA-256=4903dc7aa306134f33fda87759f5d4b52160a7fd37c554d2fdfa004253535c88。

<!-- current-retained-parent-source-bridge -->

当前来源到固定数据布线桥接：原完整分配/当前派生ODB/许可的先前控制修补网/完整source qualification作为配置输入。实际比较十类immutable native表、TRACKS、普通线FIXED编码及除许可修补网以外全部shape Counter；核对完整目标集合/实际ITerm分配与unrouted状态，再以精确afterany和typed full-source资格确认相同ODB/完整覆盖。92439完成14059网/21926端点/7542IO的真实structural audit，不生成导线、不放行source；92445测试10类不合格来源拒绝与统一入口转发/未知kind拒绝。source资格通过后复用原route_fixed_parent_links.py的完整native router/读回/连接/异网接触/层范围/保护性/负例/新鲜完整DRC门槛；旧retained_parent与added_cell_local门槛不削弱。统一route.py只转接已实现的input_kind，最终case定制仍需后续实现。实际92447已以4CPU依赖92436等待，尚无native route结果；AS128GiB并在实际节点检查≥160GiB内存余量，native线程4、core0、所有文件仍在本人目录。正式Block替换原分配/当前source/资格收据、目标计数与明确修补白名单，不依赖模块名/固定坐标；byte表/目标/来源不一致或资源不足非零失败，不能用未验收来源得到route PASS。新输出还必须完成完整native DRC/RC/功能/时序/冻结条件，绝不拼接旧原型局部通过当整体验收。最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261027T141141Z/milestone.json；SHA-256=964512c99964cf1e6a6860fe05e2d2044de55158f36b04aeb5430cb416ad5a0f。

<!-- mode-free-constant-output-lowering -->

按metal版本复用恒值资源：输入原constant-output requirements、实际native cell/PIN/net/M8导体、原闲置驱动分组/模式义务、真实LOGIC0与BUF模型、current-source保持性证据和可调每driver输出数。原37位(a_wdata32/a_we1/a_be4)恒0；已放置55组真实驱动器在opentpu版本有28组不承担原有闲置输入义务，可用作候选0源，且不能连到本版活跃inputs。每bank按metadata声明的原模式义务保留，原目录/参考图不改；这不是免费常量或新增有源器件。启发式按端口位置排序，在兼容值/空闲模式/研究slot容量内选择Manhattan最近driver，输出单driver物理分支和不可接active-input清单。此轮max2仅研究政策，得到19组37端口，不宣称最优、最终Block或电气可行。逻辑constant0可复制到独立物理分支，但不能把多个BUF输出以canonical0之名并接。每组约束为C_wire_total+ΣC_external≤实际BUF maxcap；未知量保持null，整个driver预算只计一次。8类元数据负例（漏/重输出、复用预算、多驱动、错mode/active输入、无slot/未知常值）和case改名fixture通过，尚无实际上层布线/RC/功能验收。92451空组查询副作用被严格检查拒绝，92452修复后完成分配；92456校验相同源、allocate/review AST和所有输入后复用封存groups，只补原端口/位CSV，未重分配。统一入口flow.py verify --adapter constant-output-reuse -- --config configs/current191_constant_output_driver_reuse_lineage_r02.json --output <本人新目录>，按实际4CPU spec提交；输入或算法变更与封存证据冲突即非零失败。正式Block后续接入替换source/模式、模型/PIN/native适配与研究slot参数，当前仅案例native-schema adapter；最终冻结版本变化后必须重新绑定/验证，不能把旧候选当最终mapping。最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261027T151001Z/milestone.json；SHA-256=ffe1bbbe06ae765e1d52fa1c1d14ce80d563a5e6f78af344fca4ac5508368759。


<!-- complete-custom-demand-compilation -->

定制连接需求编译：读取同源current191 native原生端点表、原M8预留点、原canonical连接、固定预连线候选、控制合同、公共IO、真实闲置驱动和独立物理常量分支。先将每个原canonical网归属为固定候选/固定控制/共享可变/常量拆分/无接收端原输出；漏项、重复分类及意外private端口即失败。可变网保留其全部真实端点与单个电气源，按case选择闲置输入银行，再复用已有恒值分组；只输出M9/M10+via8_0/via9_0连接义务，不操作冻结层。无接收端输出完整记录而不构造单端待布线网，不减少原硬件。独立语义核对从原图及bank合同重建必需端点/driver角色，不从生成分支自身推断需求；实际不同bit互换必须拒绝。几何/层/负载合同检查另行执行；未知负载保持null。此轮真实两案例92461通过（open1325/LL1345分支）；变模块名的通用化尚未额外验证，不宣称任意Block成功。后端必须明确合并哪些原native component并保持原固定几何，禁止把不同constant BUF驱动并接；实际native materializer、详细布线、完整回归、RC/STA/冻结验收仍待完成。统一命令：flow.py verify --adapter case-custom-demands -- --config configs/current191_case_custom_demands_r01.json --output <本人新目录>，经submit.py固定源码、4核提交。配置更换所有receipt路径与SHA即可输入其他同schema案例，图和几何语义变更必须增加适配器。最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261027T152104Z/milestone.json；SHA-256=54bb58903123af217c1385088e0928bce2f0e532f8dfc1c4599a53cc15eb0334。


<!-- native-case-terminal-materialization -->

未冻结ODB端口落地适配器attach_case_custom_demands.py（92464进行中，未验收）：两案例从同一源ODB独立读入，只改变共同接口/闲置输入/常量分支的端口net归属。每分支至多包含一个已有wire component；不创建net或主动器件、不改已有wire，若存在多个wired component/额外消费者/同component被多个driver复用则拒绝，避免将不同恒0 driver并联。已有M8输出wire保留原net名，公共BTerm几何仅声明net alias。原DNT临时解除以连接端口、写DB前恢复并独立读回验证。完整原PIN/OBS/instances/技术/wire attachments/virtual connections/metadata比较以及实际导体counter比较；只允许声明的BPin net归属变化。真实坏ODB交换两个input bit或断开input，再新进程读回端点；这些检查不生成物理导线，不能作为连接可达或DRC/功能证明。统一入口flow.py verify --adapter case-native-attachments -- --config configs/current191_case_native_attachments_r01.json --output <本人新目录>。后续verify_native_parent_netlist.py已实现、尚未业务执行：仅在生产作业真实COMPLETED0:0与hash-bound typed成功receipt后，读取原生writer导出Verilog、用同版Yosys导入，比对191cell/master、所有signal端点net、外部port、live-net隔离；真实错bit坏ODB重导出并拒绝。仅支持scalar parent net及从0起连续master bus，其余显式失败；不会把Verilog解析当完整仿真。最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261027T154331Z/milestone.json，SHA-256=e1d159d17118accc1372c1fe323ccdfbf2d6a10d3309ab78b514a1bc341f5ecc。


<!-- qualified-native-attachment-and-export -->

92464已验证完整双案例的端口归属落地、全PIN/OBS和固定几何保持性；92474将实际native writer Verilog用同版Yosys导入，再按原生master及端口逐bit比对，并验证不同live net不被合并。端点范围必须包含CLOCK而非只按SIGNAL分类；PG不在默认Verilog接口中单独校验。各个连续0起master bus按native bit名重建，不支持的bus范围明确失败。只允许已有非wired IO net转归一个预存wired component，已有导体不动，空原net保留；net alias与几何冻结分开记录。前置host核验实际sacct COMPLETED0:0、immutable producer命令/源版本/任务身份及成功typed receipt，生成SHA约束证书后才在容器执行。检查器拒绝实际坏ODB经原生导出再解析所得错bit连接，不以编译成功替代语义一致。统一入口flow.py verify --adapter native-parent-netlist，host阶段--prepare-host --driver <本人immutable driver>，容器阶段读resolved_config.json；真实运行配置见current191_native_parent_correspondence_r01.json及92474 spec。成功只证明原生端口与导出网表一致，不能替代叶模型完整性、真实导线、功能/RC/STA或冻结证明。新增原生输入完备审查暴露旧LL15个ACT输入遗漏，原因是含外部输出的原网仍有内部sink，不能随inactive输出一起断开。需求编译器已在92478独立加入inactive case的原resource→resource子网，并对全部native INPUT/INOUT建立来源覆盖，原旧native文件和去掉retained分支均重现相同15项失败。修正后open1325/LL1346需求，但LL新ODB尚未写出。此类原内部子网的原driver必须保留，不得改接新zero bank或新增底层逻辑；先补原生附件对无已有component的合法内部子网建逻辑net及输入覆盖门槛（不添导体），再以新LL实际ODB验证。真实parent下一步需链接已存在的六资源完整功能库，四个物理master到旧logical model的纯端口别名必须核实；原共享/专属IO和inactive reset条件在外部测试适配器落实，不再创建另一套虚拟inactive副本。最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261027T162134Z/milestone.json；SHA-256=51ba06d5e1c461ba364cd1826f745e17fe2838255757f26fbbb319f529644156。


<!-- retained-inactive-native-repair -->

混合外部输出/内部接收端的原网不能在inactive模式整体断开。92478从原canonical保留resource→resource部分（original canonical:1321的17个同源alias端口、15个ACT输入），排除LL模式改作其他功能的2个共享外部输出；不改原逻辑源、不接新zero bank。native适配器现仅允许显式配置的retained原内部子网在所有端口未分配时创建逻辑net，名字避免碰撞且数量严格匹配配置；它不是新cell/新导线。metadata只允许net_count相应增加，净表只允许声明的新SIGNAL无wire网，其余实例/master/PINOBS/导体/wire附件/保护状态必须保持。新进程实际读回后用同一全输入门槛检查，实际断开retained sink必须检出。修改不改变主候选资源/位置或原主源DRC任务。未改变case可复用封存证据，但必须exact source+branch dict一致、旧原生表/导体及输入归属复核、源SHA匹配；实际负例可引用并用新门槛重查其已保存原生断线数据，禁止重跑相同EDA导出或复制整套大表。每case显式保存verilog/native表的path+SHA，导出对应检查器不猜测这些引用位于本次新目录。92480正在实际运行、92482排队，本段是已实现方法而非运行通过；下一步看真实终态。配置current191_case_native_attachments_r02.json、current191_native_parent_correspondence_r02.json；运行沿用flow.py verify adapters case-native-attachments/native-parent-netlist、同一4核immutable submit入口。最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261027T163749Z/milestone.json；SHA-256=7a691a91f561a73d3b24fc61fca0316ab3d565bba5da93c36935922c3277925a。


<!-- source-bound-native-functional-frontend -->

已实际验证：92485将当前native191实例中的6资源及185基础设施映射到既有完整物理功能模型的已编译namespace，检查当前placement/master/pose、原child与模型的exact源ODB或闭合additive-M8来源关系、Liberty SHA一致，输出只含4个纯模块名alias的SV与可读模型索引。Yosys读回alias必须仅有一个既有child、端口direction/width/bit完全identity且无过程/存储；解析JSON的缺pin负例拒绝。模型库和原33内部RAM行为只读引用，不复制或发明行为，不将catalog成功当完整native编译。92487将两案例原public bits通过现有IO分配和实际native BTerms连接至唯一真实native parent；逐bit覆盖1320/7544bit，所有7546个native非PG端口都有显式处理。原control端口由配置绑定，inactive reset严格复用原极性；unused private input0/unused output不采样只属于外部测试环境。active37恒零输出仍走实际native driver，不用HDL常值替代。LL原数组顺序复用同版frontend实际probe，并由原未改helper发出unpacked adapter；源码层是案例专用前端，未证明任意Block适配。生成simulation sources列表只引用实际native parent、既有完整leaf/model library、alias、public适配器及原memory模型；library中可能存在的旧原parent定义不得被实例化成DUT回退。下一步需要新的typed native compile derivation与原observer/完整回归衔接，不能放宽旧compile/replay gates来接收未验证输入，也不能重复添加inactive companion。idle状态/33SRAM写保护及实际负例仍须在新native仿真核实。统一入口flow.py verify --adapter native-functional-models/native-public-adapter，配置current191_functional_model_catalog_r01.json/current191_native_public_adapter_r01.json；实际92485/92487证据及下一步见：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261027T170941Z/milestone.json；SHA-256=45ed7a90608a680327912a64e78ad2954697015593758b34a495f28323e6389c。


<!-- strict-native-compile-consumer-and-format-limit -->

新增native_parent_compile_input.py作为compile_partition_observer_v2.py的显式typed输入分支，绑定public preparation→实际native correspondence→完整输入repair、同源模型catalog和原合同/原数组顺序，不修改旧physical replay/shiftx proof验收。源清单必须恰为actual parent、两个原模型库、4纯alias、packed/unpacked适配与原全部memory模型；新native资源已含inactive，禁止重复添加companion。92497实际5个metadata负例拒绝wrong-kind、少公开bit、固定参数改动、旧parent fallback与unclosed preparation，正例只证明真实LL输入消费。两个新native编译首试因7546端口单行导致Verilator token上限失败；92493只分行后与旧文件除空白完全一致且实际Yosys原bit/port/负例再核对通过。源类型检查与代码生成器/仿真器限制分别记录，不把前者PASS或格式修复当功能通过。支持原完整编译-j4/make-j4，解析阶段实测约1核，不能声称4倍提速。native idle运行期检查、完整paired replay以及actual custom wires/RC/STA/冻结仍缺口。最新实证：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261027T172111Z/milestone.json；SHA-256=216e339ad869457bb6df2a5a5bd73c822226fdba782c150bb47544772317bddd。


<!-- actual-native-alias-self-assignment-failure -->

92494/92495实际新完整native elaboration均FAILED（353s/350.581CPU秒和376s/374.492CPU秒，各申请4核）。各16个错误为opentpu_aux输出alias的wire x=x：同一bit_115945的16条direct assign，与原已证明单driver/17输出alias分组吻合；完整native父层将这些真实同源端点连接到同一net，暴露旧物理parent适配未触发的前端表示问题。保持错误与全部原source/hash，未生成模型/未仿真。不能改错误级别、移除真实独立driver、用HDL0代替完整状态/逻辑或将单driveralias当多个可合并driver。后续若产生simulation-only归一化，必须有独立typed派生证明：exact native源与source-model alias方程、单真实driver、除声明同源输出alias表示外全部inputs/sinks/cells/masters/外部ports保持，真实完整parsed-parent对应与故意删真实driver/改input等负例；原ODB/导出网表不变，不能称派生表示是原文件字节直编译。该归一化当前尚未实现或验证，功能/物理验收未解。最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261027T172800Z/milestone.json；SHA-256=2044b7c23bc71855333f6687858f75ffede92b1feba46993e6ebc4600434b8e8。


<!-- qualified-native-alias-actual-idle-complete-replay -->

92500实际证明仿真表示中的同源driver别名规约：读取typed canonical的一真实driver/17输出端点组，查原未改功能模型16条直接identity方程和原source association，确认当前两ODB父层同net；仅在新simulation parent空置16冗余输出关联，保持真实代表driver/所有sinks/inputs/其余191cells与每个native net。新Yosys完整parent比较对原native端口表进行严格声明差分；另存真实坏Verilog断开代表driver再读回拒绝，input/meta负例也拒绝。源ODB/导出/原完整leaf模型未改，不把派生表示称原始字节直编译。native_parent_compile_input.py显式消费qualified proof，与旧physical/shiftx证明分开。native_idle_observers.py从原canonical/no-request合同自动取真实inactive source bit，观察现有native层级，不加另一套硬件；LL模式bind原全部fakeram类型，运行时核实33真实实例/周期/零有效写入；负例force真实inactive资源输出而非monitor wire。原paired脚本通过显式--native-parent/严格typed编译/实际scheduler完成证据复用全部原stimuli、trace、memory比较；旧证明/编译类型门槛不混同。原config仅CPU元数据1->4时需SHA绑定原文件并逐字段证明其余完全一致，实际分配4，改stimuli/规模/其他预算/未获CPU的负例拒绝。实际92508/92505在新191native union上完成20open/180LL全部有限active+idle回归及真实请求force负例、33RAM观察。仍需实际低层/定制导体、独立DRC/RC/STA与固定资源冻结；用理想网表连接的数字功能不能代替真实金属连通。统一入口flow.py verify --adapter native-alias-derivative，compile_partition_observer_v2.py --native-public-preparation/--native-alias-preparation/--native-idle-config；run_active_idle_regression.py由配置DUT_input_kind=native_parent_alias_derivative驱动，沿用原20/6组规模。当前案例前端/原RAM类型仍case-specific，不声称任意Block/LLM通用性已证明。最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261027T181040Z/milestone.json；SHA-256=7250284cb8b703f9d37a65d3fa50f37258c9ab60fada36d46b369478573f530c。


<!-- case-access-and-native-fixed-mask-route-qualification -->

当前检查点：2026-10-27T19:20:04.877606+00:00。阶段一已交付；二/三仍fail未验收，四未执行，候选1/3未冻结。此前92508/92505两完整191资源native父层有限active+idle功能对照已通过（open20例、LL六组180任务，原33内部RAM及外部16bank范围保持）。本轮92512完成open1325网/3514接入点、LL1346网/3535接入点的M8→M9规划，全部来自实际native引脚/固定M8导体，0标量间距冲突；尚未生成案例导体或证明长线容量。92513重新打开两实际ODB，确认M9/M10宽/间距1600DBU、pitch3200、AREA与MinStep0、真实via8_0/via9_0；RC原始字段只记录未推断单位/完成提取。92514–92518标准路由proxy资格失败保留：弃用参数、无GRTguide、DEF缩进、setRC改变基准层表均定位；修复前端后实际fixedmask通过，但DRT虽然exit0/内部0DRC却没有生成上层路径，独立连通检查拒绝，标准路由组件未通过。92519直接写入真实上层折线的独立夹具，fixedmask/连通通过但缺GCELLGRID使原生DRC未执行；补齐后92520通过。92521强化实际短路负例后通过：2段M9+1段M10、via8_0×2/via9_0×2，所有原低层导体/原端口/层表保持；新进程读回连通/异网接触0、fresh native DRC0；真实非法新增M8线/新增cell被拒，真实短路由几何接触1与原生DRC1独立检出。只证明两端点工具组件，非缩减案例替代，未证明完整多网寻路/拥堵/真实宏ITerm适配或完整两案例布线。实际14059固定网仍未布出；92406源全片DRC=RUNNING，92436=PENDING，92447=PENDING，均未停止/重复提交。新增作业均4核；92512耗时87s/CPU86.494s（约0.99核），92513为20s/CPU17.192s，其他实际账单见索引，不把申请4核当四倍提速。用户再次确认外部时钟rise/fall和37输出外C未确定，继续保留null；辅助/VECTOR新增时序、最终RC/STA/冻结未通过。源码14e90c6702e0e9369986960183cb881a11444532；最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261027T192004Z/milestone.json；SHA-256=50d4981042a7d028c8b4a7fd2f0951f3c546c6dd9f3021b489a336b41cbfce66。无远端上传/提交；原始、其他成员和封存成果保持。

方法：access planner复用既有2SAT与原生几何变换，按实际端点和实际DEF轨道生成参数化接入方案，保留所有不同物理落点的同源alias。custom_route_mask.py逐表检查所有实例/master/PINOBS/端口/层与via定义不变，原native导体多重集不可少；只允许目标网新增M9/M10导线及native via8_0/via9_0，via8下包围必须落于既有M8pad。native inventory/geometry与fresh DRC在新进程读回，另有实际坏ODB负例，不以脚本或路由器退出码替代连通。custom_route_proxy_qualification.py --config <配置> --output <新runs目录>为当前组件入口；configs/custom_route_native_orthogonal_qualification_r01.json驱动两端点fixture，输入含技术/库SHA和坐标，midpoint按native格点取整，不是完整多网算法。标准router对partialFIXED网的限制仍缺可用解；不能删除/隐藏低层几何获得表面成功。未来正式Block需替换catalog/endpoint/technology约束与目标通信输入，完整case/freeze/RC/STA门槛保持。


<!-- complete-trunk-family-failure-and-additive-native-notch -->

当前检查点：2026-10-27T19:35:15.722299+00:00。阶段一已交付；二/三fail未验收、四未执行、候选1/3未冻结。92508/92505两完整191资源有限active+idle数字回归仍是既有来源的有效证据，不能替代实际金属/时序。92522处理完整open1325网/3514端点和LL1346网/3535端点，两种贪心顺序各评估128个候选主干X；open仅371网、LL507网规划成功，剩余954/839网失败，独立标量间距扫描对已选子集0冲突。完整58,972,834条PIN/OBS逐行扫描、原native parent上层形状检查均确认M9/via9/M10无原占用，没有忽略障碍或缩减硬件；这是单竖主干候选族失败，不是两层不可行证明，也没有实际案例导体。完整源DRC92406在worker3/batch167/tile2805真实发现idle_zero_bank_35_output的M3间距报错1处；全源不可接受，非继承问题。源真实两个via封装间60DBU凹口由140宽线桥接、两侧金属280高，独立定位明确。92524已新建派生副本，先以全部原PIN/OBS复现同区1marker，再追加两段M3填充，保留全部原导体/端口/实例/连接；当前状态=RUNNING_UNACCEPTED，尚未完成整片重新资格，不能冻结。55个真实driver检查还发现组19有40DBU同形候选，尚未nativeDRC确认，后续必须先复现再写金属。92406调度状态=FAILED，其worker已触发原程序DRC失败停止信号，其他worker将在批次边界自行结束，未手动终止；92436/92447保持原依赖门槛，失败源不能放行。新92522/92524均申请4核，规划主算法单线程，真实CPU/elapsed见账单；不宣称4倍提速。用户时钟rise/fall及37常量输出外C仍null。辅助/VECTOR新增时序、真实14059固定线、RC/STA/冻结未通过。GitHub本轮只读重新核实本人身份、Issue55open/self/in_progress、PR58open/draft/head09f1876、评论0；未上传未改远端。源码73d5fcde52603afebb854276d5aa099f63aab9e2；最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261027T193515Z/milestone.json；SHA-256=27ceebddf7bb3b4c1cb2fd4b077f91e4d7ba21ec4a807cfa5bb5a83f84191e9c。

算法经验：plan_case_custom_trunks.py由实际原生接口与轨道驱动，保留每个端点；每网有限单M10主干＋M9分支，空间哈希检查候选与所有既有M9接入段/已选上层线，最后独立矩形间距扫描。候选不足的失败报告逐网记录，不推广为全局不可布。配置current191_case_custom_trunks_r01.json指定候选数/顺序/源SHA；程序非零退出保留全案例结果。repair_same_net_escape_notch.py只在任务自建未冻结线中从真实native via框/中心桥推导狭窄凹口，先同完整原DB复现目标M3marker，再追加两根原宽度平行线填满，不删原金属、不动via/单元/逻辑；新进程全native表/几何加法、连通/异网接触、同区域nativeDRC分别验收。已实现后继additive-source typed输入和预测凹口入口，但后继分支尚待真实运行；预测必须新鲜复现1marker才允许创建金属。任何局部修补都使sourceDBSHA改变，不允许无证明沿用旧完整DRC/冻结证书。完整源后续覆盖仍须完成。


<!-- dual-channel-cut-spacing-and-actual-additive-repair -->

当前检查点：2026-10-27T20:01:24.630461+00:00。阶段一已交付；二/三fail未验收，四未执行，候选1/3未冻结。92524现已COMPLETED0:0：原M3组35同区1marker被复现，新增两段M3填充后同区native DRC0；新进程完整58,972,834行原PIN/OBS及实例/master/端口/全部逻辑net/层/通孔/附件保持，全部原导体保留，目标连通/异网接触0。新数据库SHA=af6d3d0e4e5d81b5a9b4da88cb269a4d7d78a6512d286e2852006c9c1795cf58，这是局部修复资格，非整片DRC。它未回写封存案例或原始资料。92532按4核在新目录从严格闭合的92524 source继续检查组19：先实际复现同形M3marker1才允许添加金属，当前状态=RUNNING_UNACCEPTED。原92406全源检查已FAILED：4096区完成1312区、1marker；92436资格与92447固定布线均拒绝旧失败源，没有实际14059线布出。新修复DB不能无证明使用旧sourceSHA的检查点，整片新来源检查尚未提交。92528完整双向通道候选规划处理open1325网/3514点、LL1346网/3535点，增加横M9主干/局部M10腿后成功规划553/716网，剩余772/630网失败；已选子集独立几何连通和标量金属/cut间距检查通过，仍非完整case或实际导体。92527因发现真实via9cut spacing1760DBU、不同于M9/M10metal spacing1600而失败；修正后分别使用真实cut规则、含同网via间距，不能按3200金属pitch直接密铺via9。完整MG上层无占用审计按完全相同输入SHA复用92522的有效局部证据，不复用其路由失败为成功。92531从已封存同名FF报告分解得数据延迟+0.362936675ns、时钟skew改善+0.029561459ns、capture调整-0.000939607ns，合计slack恶化约0.334314823ns；原/新存储模型未统一、原报告有95960未注释driver，不能据此归类继承或签核。92529换行解析失败及92530错误Qpin被接受的检查器负例失败均保留，修正后实际精确Q/D/CK与错误pin/改slack负例通过。92524实际24m34s/CPU24m40.520s，平均1.004核（四核约25.11%）；92528为107s/CPU105.701s，约0.988核，非4倍加速。新92527–92532均4CPU；未停止其他或本任务进程。用户外部clock rise/fall与37常量输出外C仍null；原完整191资源有限active+idle回归证据保留，但真实完整固定/定制线、时序/寄生/冻结均未完成。源码c690b4a5992036b4335b13c13289cbae353c6594；最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261027T200124Z/milestone.json；SHA-256=159a565788ba2fa6b1fcee1dbe493e67d1664f879b2f24450e747ea4249263f0。无远端写入/上传，所有原始/其他成员/封存成果保持。

方法增量：custom_channel_candidates.py提供垂直/水平两种有界候选，按真实M10 X/M9 Y轨道和原M9接入mask避让，逐网记录未找到候选的具体原因。所有成功子集必须再由native_geometry.py既有contact_graph独立检查规划矩形和via上下层链接，缺via9负例必须断开；另独立扫金属间距及native via9 cut间距1760DBU（包括同网distinct cuts）。这些都是规划几何，不是实际ODB/DRC；任一原网失败即整体非零退出。配置current191_case_custom_channels_r02.json，真实执行92528spec固定对应源码/128候选/完整规模。repair_same_net_escape_notch.py的后继输入只接收已闭合typed additive-source，要求原全部表/几何保持、原局部1→0、未冻结未整片通过；预测入口同样必须先fresh原生复现再动金属。timing_path_components.py读取两封存同名max path，严格验证实际Q/D/CK和报告算术，独立分解data/skew/capture项；1e-6ns仅native浮点报告重构容差，不改slack验收或3ns周期。两模型没有统一时不能把分解诊断当新增/继承最终分类，不能拿时钟改善掩盖慢数据路径。正式Block接入需替换资源/引脚/实际via/RC规则/计算通信图；全局多弯寻路与最终case route adapter仍缺，主线M1–M8固定/M9M10定制不变。


<!-- multibend-astar-and-two-notch-full-source-recheck -->

当前检查点：2026-10-27T20:39:06.369234+00:00。阶段一已交付，二/三fail未验收、四未执行，候选1/3未冻结。92532现已COMPLETED0:0，组19原生同区1marker→新增两段M3后0，完整原native表/PINOBS和全部原导体保留、连通/异网接触0，且保留先前组35两段修复；共同新ODB SHA=5429f170d2da4e870e33da3efc8f528737ce3378cc1959b26e24610e96211508。它仍是局部修补来源，不是整片通过。92536在该同一新源上重新执行完整clock检查：75buffer、76nets、157端点、原clock mask/图/实际连通与破坏负例通过；92537同源重新检查全部13个原control区域，native报错0、DEF前后不变。qualified_additive_source.py显式核验闭合调度证书、保存的真实before1/after0报告、实际geometry、全部原表保持和5个坏receipt负例，仅允许进入这些fresh checks，不绕过原完整门槛。92538已按4CPU启动新源完整4096区原生检查，不复用旧来源08b的1312个闭合区；实际4个OpenROAD worker均日志Using1thread，各1024查询，原全PIN/OBS保留，AS64/worker、CORE0、6400guard/200000pitch/16原子batch不变。新批次分配轮转X四分区以缓解旧左右密度不均，合成4096区不丢不重/1–4worker/分区均衡夹具已在启动门槛执行，未宣称实际加速；新查询合同中记录policy与源码/helper SHA。当前原生整片结果未出，不可冻结，也无14059固定数据线实际布通结果。新增多弯A*真实跑完整1325open/1346LL：92534最好554/729网规划成功；92535在同样15000节点与5秒/branch预算下加入必需via数的可采纳下界和equal-f更小h优先，最好621/809，其余仍失败。成功子集均独立标量金属/cut间距及几何连通检查通过；三交替障碍夹具实际需6via，缺via/堵M10负例及150状态独立Dijkstra下界检查通过。它们仍是规划，未写实际case导体，不能当完整布通/功能/制造签核；保留既定上层通道及有界搜索也不能证明两层不可能。92535实际256s/CPU801.424s，平均3.131核（四核78.26%）；92534为230s/CPU789.269s，平均3.432核；92532为1468s/CPU1473.283s，平均1.004核。没有4倍提速宣称，新任务均4CPU且未终止任何其他/本任务作业。辅助/VECTOR新增或恶化时序、真实完整固定/定制线、最终RC/STA仍未解，clock rise/fall与37常量输出外C仍null。源码5073ad383d06e3fcca0fe19fa8c1eaf77b31ad9e；最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261027T203906Z/milestone.json；SHA-256=089c172a6196d9302382149f012f8ea78332dd7dad1a578b2cf0a61ba9933927。无远端写入/上传，原始、其他成员和封存成果保持。

可复用方法：custom_maze_candidates.py在真实两层轨道上搜索(state X,Y,layer,距上次via的直线步数饱和值)，M9只水平/M10只垂直，native via9=1600宽/1760 cut间距独立于1600 metal间距；连续via需至少两轨间距，非连续自靠近via由独立检查拒绝后有限重试。启发式为Manhattan加通往M9目标所必需的最少via成本，有限状态独立反向Dijkstra验证无高估；这属于已有A*框架的工程实现，不宣称新算法。初始既有候选通道不拆除，两个case×长短网两顺序是4个独立1进程任务，受同一个4CPU allocation限制。每网候选闭合写checkpoint，超时/搜索预算/不可达均明确失败，不删原网络；最终再次调用既有native_geometry contact_graph核对规划连通与独立spacing sweep。入口plan_case_custom_maze.py --config current191_case_custom_maze_r01.json --output 新目录；真执行规格/版本见92534/92535。native_tiled_scan.py保留全部旧fresh clock/control/12原生跨层负例门槛，新增的additive_m3_notch输入必须有实际source completion证书和局部完整保持证明，随后仍重查该新source的76clock网/13controls/整片4096区。分配policy加入query contract，轮转group位置只影响负载、不改任何query box/geometry或接受条件，改source时不套旧checkpoint。正式Block需替换资源/引脚/工艺与计算通信输入；完整native route adapter/拥堵及底座内部时序问题仍未通过。


<!-- fixed-lower-source-separate-M9-routing-net-native-qualification -->

当前检查点：2026-10-27T20:56:29.516056+00:00。阶段一已交付；阶段二、三未验收，阶段四未执行，候选1/3未冻结。新增92539真实原生GRT/DRT小夹具通过：两个真实BLOCK的M8 ITerm、初始无父层目标导线，保存后独立native读回保持全部原实例/PINOBS/端点/不相关M8导线，只新增M9/M10和via8_0/via9_0；实际连通、异网接触0、fresh及router DRC0，真实坏低层导线/新单元/短路负例被检出。92540在同一夹具加入原有FIXED目标M8导线后失败：native GRT没有产生guides，不能推广为两层不可行。92541软件适配初版因OpenDB不接受FIXED放置枚举失败；92542改为实际FIRM后路由完成，但严格中间metadata对临时对象计数报错，均保留。92543明确核对仅+1软件net/+2软件instance/+2软件master后通过：所有原端点/原固定低层导线/原PINOBS在布线视图中完整可见且未变；让独立软件M9宏引脚网络求上层线路，将原生实际wire追加回原target并补原M8垫上的via8，再删除临时软件实例和网络。最后独立fresh读回原native表全部相等，原导体行无丢失，原生路由几何转接完整；新增M9一段/M10一段、via9两只/via8两只，实际两个原ITerm连通，无漂浮，无异网接触，fresh和router DRC0。坏低层线/新增BUF分别拒绝；真实短路得到geometry1/nativeDRC1。软件宏仅是求线适配器，不是新增主动底层资源，最终无软件实例/网络。上述是工具与输入类型资格，不读取或缩减原硬件case，不能当作完整case布通、功能、RC/STA或冻结证明。完整新源5429的4096区原生DRC92538仍RUNNING，4CPU/4个单线程worker，保留全PINOBS，原作业未停未重提；记录的是当前部分进度而非整片通过。14,059固定数据线和完整定制线仍未实际完成，辅助/VECTOR新增或恶化时序未解。用户再次确认外部clock rise/fall及37常量输出外部C未确定，维持null，禁止代0；最终电气验收仍缺这两类输入。新92539–92543均4CPU，小夹具主要启动/检查时间，92539用7秒/CPU3.096秒（平均0.442核、4核容量11.1%），不宣称4倍提速。未调整或停止任何live旧作业及其他成员任务。源码305ccf7cc190749f99e9fa80d085905167665503；最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261027T205629Z/milestone.json；SHA-256=58a8ddbab9b9cfd0308682fbb95ded71c9740cbcc5ed1f33f993077f0803ea36。仅服务器本人目录和本地commit，未上传远端；原始、其他成员和封存文件保持。

可复用的适配思路：先完整保留原端点、原固定目标导线和所有其他物理几何，在实际M8接入垫的上方提供临时软件M9宏PIN（不把它们当物理Block）。其独立临时net不含任何原目标的低层FIXED导线，交给标准GRT/DRT在M9/M10求线；保存routing_view.odb并独立比较原实例、原导体、原连接、全PINOBS、技术层和via定义仍存在且不变。将该net实际native wire按decoder opcode逐条append到原target，原M8垫处新增via8_0；不删除/隐藏原导体，不回写原master。移除临时软件net/instance后再做最终原表完全相等、原形状多重集合保持、上层路由几何完整转接、via8下垫包围、真实端点连通/所有异网接触、fresh原生DRC和实物ODB破坏负例检查。当前fixture只支持明确的原生wire op0/1/4/5/7和丢弃软件端点引用9/10，其他opcode严格失败而非悄悄漏几何；不能假定任意复杂分支/patch已支持。入口custom_route_proxy_qualification.py；route_mode=macro_fixed_proxy；配置configs/custom_route_macro_fixed_proxy_qualification_r01.json；完整命令、固定源、层技术SHA和输出见92543 spec与execution。所有固定坐标仅限工具夹具；真正通用适配应由已核实的M8 access catalog生成软件PIN/网络，真实完整case容量仍需独立验证。直接原目标含FIXED低线的92540失败不被软件适配小夹具抹去；本方法不代表最终共同底座/两case已经物理通过。


<!-- two-notch-full-source-input-qualification-dependency-chain -->

当前检查点：2026-10-27T21:03:47.952383+00:00。阶段一已交付；二/三未验收、四未执行，候选1/3未冻结。92543实际原生GRT/DRT软件M9接入小夹具已通过：所有原固定M8目标线、原端点、全PINOBS和其他导体在路由视图及最终ODB均保留，只增加M9/M10及via8/via9，临时软件net/instance最终移除，actual连通/异网接触0/fresh和router DRC0；真实坏低层线/新单元拒绝，真实短路geometry1/nativeDRC1。仅为输入适配工具资格，不是原完整case/冻结/RCSTA通过，92540直接含FIXED目标net无guides等失败保留。新源5429新增完整范围检查92544已COMPLETED通过：58,972,834条全master PINOBS几何、191实例、25,464个全部ITerm变换及全部父层导体都在4096查询域内，无超界/变换错误，实际错bbox/错MX负例检出。92546也已COMPLETED通过：新源与原完整固定网络分配比较，原native表/全PINOBS/191资源/原轨道一致，导体差异仅已核实的4个control网和2个M3notch网；全部14,059个待布net和21,926个ITerm仍完整、尚无目标导线，没有启动router或放行DRC。新代码显式qualified_additive_retained_parent复用闭合M3来源证书及坏receipt检查，实际布线仍必须获得完整source qualification；audit_only配置禁止启动router。92538完整新源4096区原生DRC仍RUNNING4CPU/4个1thread worker，全PINOBS保留；并未停或重复。已实际排队92547（4CPU，afterany92538）独立复核全部闭合查询、4096覆盖、12原生坏样本、相同source5429与freshclock92536/extents92544；必须实际COMPLETED且所有检查通过。已排队92548（4CPU，afterany92547）全14,059固定低层数据线，只有实际完整source proof通过才启动native布线，失败则保留拒绝结果，不当作成功；目前两者PENDING/未执行，不是已布线。92544实际176秒/CPU174.840秒，平均0.993核（四核容量24.83%）；92546为41秒/CPU42.523秒，平均1.037核（25.93%）；92543为8秒/CPU3.079秒，平均0.385核（9.62%），没有仅申请四核就声称加速。尚需真实1682闲置分发/固定网络、解决aux/VECTOR新增恶化时序、共同PGclockRC、冻结和两完整case定制布线/完整回归；用户确认clock rise/fall、37常量输出外部C未确定，仍为null不能代0。源码6319001868bda6f3df1403f0a99980d51d75e380；最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261027T210347Z/milestone.json；SHA-256=83ae2dd5c354b6fbf2948cd5e117cc9bbae17ba72433d09cec0d22cfc49edaea。新成果仅本人服务器目录；未上传远端，未动原始/封存/其他成员文件。

来源版本与执行依赖方法：whole_geometry_extent.py新增显式additive_m3_notch来源，复用qualified_additive_source.py的实际作业终态、原生前1后0局部报告、全表保持及5坏receipt检查后，仍完整流式读本版本所有PIN/OBS和父导体，重新核对查询域和引脚变换，不能套旧版本extent结论。route_fixed_parent_links.py新增qualified_additive_retained_parent来源，结构差异只允许配置中明确已验证的原4control网和2notch网；实际router依旧必须消费独立完整4096区source qualification，不能仅凭局部补线/输入审计启动。audit_only配置在程序入口强制拒绝非审计调用。92538→92547→92548是实际Slurm afterany链，后两步独立读取前序实际COMPLETED及PASS证据；afterany仅保障前序终态，程序本身不接受失败、partial、错来源或非零marker。记录pending与actualwirecreated分开，保留所有以前失败，没有新建重复全扫描。配置与实际运行命令见current_two_notch_source_complete_native_qualification_r02.json、fixed_parent_two_notches_input_audit_r03.json、fixed_parent_two_notches_qualified_lower_route_r03.json和对应固定源spec。


<!-- complete-case-parameterized-software-router-projection -->

当前检查点：2026-10-27T21:17:17.558875+00:00。阶段一已交付，二/三未验收、四未执行，候选1/3未冻结。92538完整4096区新源5429原生DRC仍RUNNING4CPU/4个1thread worker；92547独立source复核、92548全14059固定低层数据线仍PENDING依赖，未停或重复。新增92549/92550已COMPLETED通过：参数化软件布线接入投影完整保留open1325net/3514anchor/3514端点、LL1346/3535/3535，每例原16个driver_alias均保留。通用core不固定case名称、数量、坐标，原格式转换独立在normalize_case_access；native单位/范围/metadata、实际via8三矩形、M8垫/中心、M9轨道与接入矩形核对。813open/796LL个非零M9短接入桥明确保留为实际转接后必需导线，软件PIN不能代替导体。软件网络只选primary作为routing-root OUTPUT，其余含alias为软件INPUT，原真实端点方向/连接不改。实际nativeLEFparser核对两例各4种和改名平移夹具3种，共11个软件master的尺寸/方向/PIN矩形。改名、平移、3net/69端点多分支与别名、输入倒序同结果及11个坏输入均通过。92550由统一flow.py verify --adapter router-access-projection真实调用；新桥接校验及统一入口改造前后正例manifest/LEF的SHA保持完全一致。92549实际4秒/CPU2.534秒（平均0.634核、四核容量15.84%），92550为4秒/CPU2.598秒（0.650核、16.24%），均申请4核，主要单线程元数据+短native解析，无四倍提速宣称。这些只是完整布线输入转换与nativeLEF解析，不读/改原caseODB、不运行实际caseGRTDRT、不新增实际case导线或DRC/功能/冻结通过；来源仍旧08b/原caseSHA，不重标为新5429。尚需通用nativeinstaller/wire转接/短M9桥实现验证，以及完整source/固定数据线/1682闲置分发/aux和VECTOR新增恶化时序修复/共同PGclockRC/冻结/两case最终定制验证。clock rise/fall与37输出外C未确定仍null。只读重核本人API与Issue55/PR58，仍self/open/in_progress，PRdraft未合并/head09f1876，两处comments0，远端只阶段一无上传。源码f951eedb67ce7c5fa962fe1ab95e5e789a385b5a；最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261027T211717Z/milestone.json；SHA-256=1bb8e4e6bf556e19b04f911693193ddf0a04c5f58dd608391caa37e6286f86d8。

算法与接口：prepare_router_access_projection.py读取闭合access_plan/native_rules/native_attachments及native metadata；case专用normalize_case_access将原M8垫/中心、实际via8下垫/切孔/上垫及M9上轨道矩形转为共同port描述。router_access_projection.py::compile_projection仅处理net、branch、portgeometry、原endpoint角色和实际die/grid/units/层名，按原net/point排序，确定性生成临时软件net、每anchor的软件实例，按方向/宽高复用PIN master，保留全部原端点和alias，不增加主动器件。emit_lef用Decimal把DBU精确转微米，独立原生parser核对全部输出。required_custom_bridge显式列出实际转接必须追加的M9线，genericcore再独立检查层、Manhattan、grid及软件PIN包围；临时PIN不代表实际导体。当前原生installer、通用wire转接与真实case桥线尚未实现/验证。统一入口：python3 -B -I -S flow.py verify --adapter router-access-projection -- --config configs/current191_software_router_projection_r01.json --output 本任务runs新目录；固定源码、4核提交与复跑见92550spec。该算法是数据规范化和确定性投影，不宣称新布局/Steiner算法或完整LLM编译器。正式Block需提供实际物理access、能力/时序和工艺数据及source-boundcatalog；不能只改名称/坐标或套旧08b结论。


<!-- generic-native-projection-selected-net-transfer-and-literal-records -->

当前检查点：2026-10-27T21:32:58.218682+00:00。阶段一已交付，二/三未验收、四未执行，候选1/3未冻结。92538完整新源5429的4096区原生DRC仍RUNNING4CPU/4个单线程worker，92547独立source复核和92548全14059固定线仍PENDING；未停/重复提交。本轮92551通用native投影安装/选网/GRTDRT/转接小夹具实际COMPLETED通过：原有3个BLOCK ITerm的部分FIXED目标网+原无导线的2个BTerm目标网，另保留不相关固定M8线和一个不应布线的无导线网。软件projection core及统一serializer安装5个临时实例/2个net，只选择这2个软件net求线；原导线、原端点、全PINOBS在route view保持不变，原无导线的第二目标网和不相关网均未被native router顺带布线。实际router上层导体逐条append回两个原net，原M8垫新增5个via8_0、4个via9_0，新增M9四段/M10两段（含1个实际非零M9接入桥），再删除5个软件实例/2个net。保存后独立native读回全部原表/端点/导体保持、实际3端/2端两网连通，无漂浮/异网接触，fresh与router DRC0；实际坏低层导线/新BUF被拒，实际短路geometry1/nativeDRC1。此为独立工具夹具，不读原caseODB或以缩小case替代完整验证；本次实际wire opcode0/4/5/7，JUNCTION1实现但未出现验证，其他opcode严格失败。92551实际10秒/CPU3.225秒，平均0.323核（四核容量8.06%）。新92552完整两case参数化projection+LEF/Tcl实际COMPLETED通过：仍保留全部open1325net/3514anchor、LL1346/3535及各16alias，M9桥需求813/796不漏；向原生Tcl写入并读回全部7118条record/原endpoint引用（含独立69端点改名/平移夹具），名称、坐标、尺寸、桥终点和alias引用完全一致，特殊方括号、美元符、空格引号及Unicode名称保持字面值。11种native软件master几何/方向保持，11坏输入检查通过；新serializer前后实际两case manifest/LEF SHA完全相同。92552实际5秒/CPU3.097秒，平均0.619核（15.49%），均申请4核，不宣称四倍提速。两完整case来源仍旧08b/原caseSHA，未运行完整case路由，不能作为新5429/finalfreeze证明。现已实现通用native helper与serializer并在工具夹具/完整输入转换验证，但实际完整case source/freeze绑定及调用仍待完成。只读旧case net表也确认open46partial/1279无父导线、LL28partial/1318无父导线；扣除14059规划固定网后未另见多端无导线SIGNAL网，此不表示14059线已布。仍缺真实固定/1682idle分发线、aux/VECTOR新增恶化时序修复、共同PGclockRC/冻结/两完整case最终验证；clock rise/fall及37常量输出外C未知仍null。源码cfbdd6842eb28b38acdd95e3f932da79a074916a；最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261027T213258Z/milestone.json；SHA-256=57b39c4443e15904bab7e9c74c52f05efef0197b2be7c96839ecffd1b44ff59f。仅服务器本人任务目录、本地commit，无远端写入，原始/其他成员/封存文件不变。

可复用实现：software_projection_io.py::emit_tcl_records接收通用manifest、使用既有auxiliary_physical.tcl_word逐值转义，生成只含数据的Tcl列表/字典；prepare_router_access_projection.py现同时输出完整case的manifest、software LEF和records Tcl，用实际native解释器再读回7118条records/端点引用，UTF-8转hex避免输出分隔符歧义。software_router_projection.tcl提供hpy_projection_install、hpy_projection_copy_upper_wire、hpy_projection_transfer：先校验全部原net/端点与临时名无碰撞、master类型/尺寸/方向；只新增软件对象，显式set_nets_to_route，仅对软件net进行GRT/DRT；保存中间route view独立比较全部原表/导体，然后append实际native编码（目前0/1/4/5/7与软件端点9/10，其他严格拒绝），按manifest追加实际via8和非零M9桥，删除仅临时net/instance。92551实际观察0/4/5/7，不能因函数含1分支就宣称JUNCTION已验证。set_nets_to_route选网语义参照[OpenROAD官方文档](https://openroad.readthedocs.io/en/latest/main/src/grt/README.html#set-specific-nets-to-route)，本机实际guide集合与未选无导线网保持已独立验证。三个原ITerm的实际分支连通不依赖软件PIN留在最终硬件；无导线原target由真实dbWire_create后转接，原固定线不删除/隐藏。此helper仍须被严格源资格/最终冻结wrapper调用，不能仅source一个Tcl就放行完整case。已有92551真实坏低层线/新单元/短路负例；断线/错接/特殊分支opcode、复杂拥堵与全case容量还需实际资格，完整状态保持与源/最终时序仍未通过。


<!-- native-inactive-annotation-and-selected-path-exact-source-coverage -->

当前检查点：2026-10-27T22:08:52.248339+00:00。阶段一已交付，二/三未验收、四未执行，候选1/3未冻结。92538完整新源5429的4096区原生DRC仍RUNNING4CPU/4个单线程worker，92547独立source复核与92548全14059固定低层数据线仍PENDING，未停或重提。本轮转向时序模型数据：92553因report_units不支持重定向写法实际FAILED；92554修正后导出原95960驱动，但在原STA显示RTL寄存器名与OpenDB字符串名不一致处FAILED；两失败保存，不当作硬件失败或通过。92555使用精确STA regexp及sta::sta_to_db_pin指针转换（保留requested/native名称，不删括号或反斜杠）后实际COMPLETED，两个真实版本都完整测量通过其限定范围。原95960未标注驱动=85120个单端无互连网+10840个未连接输出；当前辅助74073=65262单端无互连+8811未连接输出。每个端点实际native方向/类型/net/负载数/普通和特殊wire状态核对，遍历原SPEF全部1,131,217段、当前558,748段，确认这些孤立网没有SPEF；未将主动漏RC误作孤立豁免。已知ATTN同一og0/Q→wdata_acc998/D路径：原94个路径pin/91net及全部329个网络端点，当前208pin/104net及全部496端点，与原各自SPEF名称/方向/成员完全匹配；原/当前报告字段格式不同，pin行数不同不等于逻辑规模变化。新进程同源重新复现原slack−1.191561580ns、当前−1.525876403ns，仍是各自历史模型、非统一模型；差异−0.334314823ns未豁免为继承，未知clock rise/fall和37输出外C仍null。92555实际294秒/CPU375.035秒，平均1.276核（四核容量31.89%），申请4CPU/两native阶段串行各最多4线程；前失败92553为112秒/CPU111.411秒、92554为118秒/119.061秒，不宣称四核提速。基于实际新证据已提交4CPU作业92556并确认为RUNNING：只读完整原始LLcore，用当前aux相同Liberty/工具/setRC/RCX规则新提取参考SPEF，原始1.622GBODB和1.316GBSPEF只读引用不复制，生成结果仅新run；先复现旧同FF路径，再新进程加载新SPEF测量、核查实际原层栈与当前工艺物理宽度/方向、无新增未标注端点。该任务尚无完成结果，RCsetup统一也不等于时钟/边界假设全面统一或最终时序通过。仍需全5635setup/30hold/1087cap同源对照、aux/VECTOR新增恶化问题修复、固定与1682idle线、共同PGclockRC/冻结及两完整case最终定制/功能/物理检查。源码5bc51c15b389802a968aa092b750cca305358f0f；最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261027T220852Z/milestone.json；SHA-256=a6c035faf64e8308c376d4aa2b1110a2641a16c5daba71f7c6492a4593ea84df。新增文件只在本人服务器任务目录，原始/其他成员/封存文件保持，无远端上传。

方法：audit_path_parasitic_annotation.py复用timing_annotation_review的严格annotation解析及SPEF端点规则，timing_path_components的精确FF路径/打印算术一致性检查；原生脚本先真实报告全部unannotated，再以native实体的方向/信号类型/实际net成员/普通和特殊wire标志逐个分类。读取原NAME_MAP和全部D_NET段，保留指定路径网络的原始段及必要name token，随后复用既有解析器与这些net的全部native成员/方向逐项对照，不靠只数端口或猜测缺失寄生。选定STA路径名若和DB字符串不同，只用唯一精确regexp得到STA pin并通过[官方OpenROAD pin指针转换](https://github.com/The-OpenROAD-Project/OpenROAD/blob/master/src/pad/src/pad.tcl)取得实际native对象，记录两种原名称，不自行合并转义差异。report_parasitic_annotation的语义参照[OpenSTA命令说明](https://opensta.readthedocs.io/en/latest/Commands/#report_parasitic_annotation)，本机通过实际原生报告/计数证明。未标注驱动总数不能直接当主动RC缺失，也不能不检查就免除；本次实际95960与74073全部独立分类后才报告其闲置性质，其他新来源仍需重查。指定91/104个path网络的完整SPEF成员覆盖不推广为全部设计/全部最差端点/所有时序质量通过。新增normalize_historical_rc_reference.py/.tcl按cfg明确原数据库/SDC/旧SPEF、当前模型producer及相同Liberty/setRC/RCX文件SHA，序列执行实际全原设计提取和新进程重测；原约束不变、不补0波形或负载、不改数据库文件、不改共同底座，只写本任务新SPEF和日志。当前92556待结果，RC参数匹配仍不能替代完整时钟/边界条件匹配与全部新增失败的逐项判定。复跑命令/源commit/工具hash/输入hash以92555、92556不可变spec与execution为准。


<!-- matched-RC-reference-rich-arc-and-named-state-adapter -->

当前检查点：2026-10-27T22:42:23.698600+00:00。阶段一已交付，阶段二/三未验收、四未执行；共同候选1/3未冻结。92538完整新源5429的4096区原生DRC仍按4CPU/4个单线程worker运行，完整源独立资格92547和全14059条固定低层数据线92548依赖排队，未停或重复提交。92556现已实际COMPLETED：只读原始完整llaccel的1.622GB ODB及历史3ns SDC，使用当前aux完全相同Liberty/原生工具/setRC/RCX规则重新提取1,216,337网，新SPEF为1,482,482,191字节，SHA a56450ec843ce136c19066fa0e7b87d49884381f2f806250fd9f434c4ddbcdc9；原始文件不变，原M1–M10实际物理宽度/方向匹配，完整实例2,458,158及网1,216,339数量不变，未增加未标注驱动。新进程读新SPEF后，同og0/Q→wdata_acc998/D路径仍slack−1.191561580ns，与旧RC完全相同，不能用RC参数差异解释当前−1.525876403ns，约−0.334314823ns差距继续未解决。92557实际COMPLETED：复用92556原始旧/新rich报告和91921当前rich报告，用真实Liberty方向逐步拆分CK→Q/组合单元/导线延迟；当前比原匹配参考数据路径多0.362936675ns，其中导线多0.324116940ns、CK→Q多0.027936995ns、组合单元多0.010882740ns，约89%增加在导线。原70/当前75个组合输出、FF起点X1/X2及Q负载9.303/20.735fF实际记录；这是不同实现的测量，不是孤立因果证明。原端点/打印Delay/Liberty方向四项实际报告破坏负例均检出，1e−6ns仅打印算术一致性不是时序豁免。92556实际543秒/CPU649.498秒，平均1.196核（申请4核容量29.90%）；92557实际17秒/CPU15.764秒，平均0.927核（23.18%），不称四核加速。已用新源码提交92558四核作业：保留92425当前5635setup/30hold完整端点清单，实际读取完整原设计的新匹配SPEF，收集原max/min完整负端点并以native计数/WNS/TNS核查，使用官方all_registers-data_pins及sta_to_db_pin匹配当前寄存器D端。不同物理边界和时钟仍明确不同，3397个顶层端点保留为未解决，原负列表缺失不当成已知正slack，不能据同名就认定状态等价或继承问题；92558现已实际COMPLETED，212秒/CPU289秒，平均1.363核（申请4核容量34.08%），最大RSS9,846,468KiB；完整原设计负端点计数6659setup、0hold，native数量/WNS/TNS与逐端点清单一致。当前2268个唯一D名中2135个对应到原native寄存器数据引脚，133个未匹配需真实来源映射。当前setup分类：3397个不同边界端口保留未解决；116个bit_*寄存器D名未匹配；2122个真实原ATTN寄存器D名中2079项数值恶化、42项未恶化、1项不在原负列表（正slack或未约束尚不能区分）。最坏同名数值差为wdata_acc1391/D的−0.589769583ns；这是历史时钟/不同边界下的数值差，不能直接当最终因果或继承判定。当前30个hold端点中13个匹配原寄存器名但原负列表无项、17个u_xbar.rstart相关名未匹配，全部保留未解决。没有把不同名字猜成等价、没有将原缺负项当已知正值，也没有删除3397个边界端点以降低验收范围。用户最新回复确认外部clock上升/下降时间和37个常量输出外部负载均“未确定”，继续null，不补0，最终外部电气验收未通过。仍需aux/VECTOR新增恶化问题修复、全固定与1682idle线、共同PGclockRC及同一冻结底座两完整case最终布线/功能/独立读回；本轮没有修改/冻结底座。源码843c69b5d5f5ea8c76863685c97c094867a7c0c8；最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261027T224223Z/milestone.json；SHA-256=a37756c55ad810ce5a3fd3c7c6cace90d94d557f6e77dbd2cafa77f4d04aecc2。新增文件均位于本人服务器任务目录；原始和封存文件不变，未下载大结果或上传远端。

方法：先将实际原始完整物理ODB按当前RC模型重新提取，再新进程读回，对同名FF路径复现旧基准和新参考；不用全局最差值代替同端点比较。timing_path_arc_components.py以同一真实Liberty方向解析rich path，按相邻真实时间戳分别累计首CK→Q、同单元输入到输出和网络输出到下一输入；总和必须精确闭合，原报告Delay仅用于逐步打印一致性验证，格式负例使程序失败。原始与当前70/75个组合输出的单元延迟基本接近，而当前网络延迟明显增加，因此下一步优先查驱动扇出/线长/负载，尚不能据相关性宣称具体线路是根因或已修复。新compare_cross_boundary_registers.py复用原有完整negative endpoint收集与native计数/WNS/TNS单位闭合，不修改原比较器同SDC/同frame守卫。原完整设计和当前aux边界不同，适配层明示这一差异：按[官方OpenSTA all_registers -data_pins](https://github.com/The-OpenROAD-Project/OpenSTA/blob/master/sdc/Sdc.tcl)一次遍历真实寄存器数据引脚并用sta::sta_to_db_pin取得实际master/方向/原native名，与当前完整清单的精确D名对应；两边均负可做数值差分，缺原名或原负列表缺项仅记未解决，不能自动判新违例或正slack。当前非D顶层端点仍完整保留为不同边界未解决，不能从最终门槛中删除。缺失正时序/约束证明、全状态等价、1087cap及VECTOR新增问题、未知外部波形和负载，仍分别保留。配置均显式来源路径/SHA、实际源版本和命令见92556/57/58spec；本轮不重做已有current92425census，不改任何实际硬件或时钟约束。


<!-- state-alias-native-geometry-selective-physical-repair -->

源码别名与物理候选：trace_state_alias_endpoints.py只复用真实mapped/export JSON、原先Yosys解析的RTLIL及闭合92558端点清单。将实际FF的Q位沿同名wire的真实位号/offset/upto映射到源位，要求唯一源位；源网表中的别名及原RTLIL声明/直接connect作为可追溯候选。新native进程实际遍历原数据库的all_registers-data_pins，只选择真实存在、同FF master族且唯一的对象；记录原STA/native名、master、Q net和源证明编号，重复同pin可去重，两个不同候选或错族必须拒绝。源位合并/无物理候选保留未解决；不借名字证明状态转移等价。92559共116个唯一候选、17个未解决，证据和限制见索引。

路径到真实几何：slow_path_net_geometry.py按92557实际net增量排序，通用配置top_net_steps=8，不写死模块/坐标。精确连接报告driver/sink与92555原生pin/net名，再流式读取同一f739全部native ITerm/shape表，保留选定网的全部成员和WIRE/WIRE_VIA记录；native源、表、报告均SHA绑定。计算真实bbox/层分布/报告的via位置，不将bbox间距或矩形长边和当实际路径长度/RC模型/连通或DRC证明；实际wrong-net与wrong-direction元数据负例必须失败。92560完整扫描16.52Mshape/2.93MITerm，选8网全部139端点与1687shape。

有依据的物理试验：reroute_slow_auxiliary_nets.py只从已闭合92560的实测摘要取8条完整网，不改原先migrate.py的目标选择接口或任何已有封存脚本；复用其stage/nets_only_def/native/compare/几何/固定导体保护/新鲜DRC，避免复制第二套实现。原源保持只读，原target实际几何先通过，然后在新副本中用原生NETS-only DEF往返建立真实FIXED编码，全实例/master/PINOBS/net端点和全部几何必须精确保持；只有选定完整普通线可拆除后真实重布，其他普通线/过孔矩形逐个添加临时保护，移除时只删除本轮新对象并核对原OBS身份。M7–M8是本次GRT候选，允许M1–M8原生接入；不得使用M9/M10或新增逻辑。保存后独立native全表/非目标几何比较、目标opens/shorts/contacts和新鲜原生DRC分别检查，即使工具成功退出也不能代替这些检查。实际内存/磁盘余量预检，申请4核/工具4线程/主要Python一步一线程；不占整节点。成功仅记尚未提升的物理候选，必须新RC和完整同边界端点/电气/功能对照后再决定是否进入公共底座；其他源的旧DRC/冻结证明不可挪用。失败保留具体阶段/实际数据库与日志，不当成M9/M10路线不可能的证明。

当前检查点：2026-10-27T23:00:10.598304+00:00。阶段一已交付；二/三未验收、四未执行；共同候选1/3未冻结。本轮上一轮为实际进展（92556/57/58完成RC参考、路径拆分、完整负端点对照），本轮继续新增实测与真实修复试验。92538完整新源5429的4096区原生DRC仍运行4CPU/4worker，92547独立完整源资格、92548全14059固定低层数据线依赖排队，未停或重复提交。92559实际COMPLETED，复用封存的mapped/export JSON和原生Yosys RTLIL，不重新综合；133个未匹配D端点中117个源位关系唯一，116个经真实原物理数据库查询找到唯一同族寄存器候选，主要为bit_*到u_perf.perf计数器别名。107项两边均负可做数值比较：57项更差、50项未更差；另9项原负列表无项，仍可能正slack或未约束。其余17个xbar端点保留未解决，其中16个有多个原源位合并，不能猜选或称功能丢失。唯一候选/错误master族/重复同pin三类检查器夹具通过；源别名和物理存在不代替完整状态转移等价或时序归因。92559实际48秒/CPU47.432秒，平均0.988核（申请4核容量24.70%），MaxRSS4,208,580KiB。92560实际COMPLETED，只读同f739封存native表，读取2,927,139个ITerm和16,519,607条shape记录，选定8个实际慢net step，与139个真实ITerm/1687条实际几何记录对应，源ODB/报告/驱动/接收端/完整网络成员数核对；错误net和错误方向负例检出。最大net219371为0.142692328ns、46负载/218.545fF、两引脚bbox最小L1间距310.755um，实际普通导线仅M2/M3/M4；几何距离和矩形长边之和未当电气路径长度或RC因果。92560实际27秒/CPU27.062秒，平均1.002核（四核容量25.06%），无四倍提速宣称。基于以上实测已提交并核实四核92561：只在新辅助块副本，把这8条完整普通信号线尝试经M7/M8全局路由、M1–M8合法接入，保持逻辑/单元/master/位置/所有net端点及其他几何不变；复用已有migrate的实际FIXED DEF往返、全部非目标导线/过孔精确临时保护、实际GRT/DRT、移除仅新增临时保护、独立native读回/全保持性/目标连通/新鲜DRC检查，不重复维护另一套路由器。实际MemAvailable至少192GiB和任务盘64GiB余量预检，AS192GiB不是RAM申请；脚本和运行快照固定。92561当前实际状态见索引，未报告修复通过、未提取新RC或验收功能/时序，也未将新辅助候选纳入公共底座，92538来源完全不变。后续若物理试验通过，仍须新源类型适配、全实际RC/端点/电气变化对照及功能检查，解决其他aux/VECTOR问题并补全固定/idle线后才可冻结。外部clock rise/fall和37常量输出负载仍用户确认“未确定”/null，不按0处理。源码6ef5e00b88e569f3440964da3bb178946d1c62ec；最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261027T230010Z/milestone.json；SHA-256=a588f3f6d82b32d77eb2ec868681369948d3374a1af1742c6d9658c6d507b087。本轮原始/封存/其他成员文件保持，未下载大结果或远端上传。


<!-- mode-dependent-idle-fixed-custom-boundary -->

固定/定制边界采用mode-dependent端点分类，避免把“固定底座需要合法idle处理”误作“全部idle输入永久接零”。输入为已闭合真实driver-bank与完整sink分配、共同固定网目标表和native ITerm归属、各mode完整接入计划及同源软件路由manifest；程序audit_idle_custom_boundary.py依据bank.active_in_modes构建每个mode的预期集合，不写死模块名称、bank号或坐标。每个sink须唯一对应正确bank驱动/M8点和pad、实际INPUT且不属于共同fixed target，完整定制投影中同net同sink恰好一次；其他mode中同一原资源端点须恰有正常非parking连接，不同时接零。错误bank、遗漏sink、投影遗漏以及固定低层误绑四个实际元数据负例必须失败。92562实际核完841+841个sink、27+28组bank及841+841个其他mode正常对照连接，固定数据目标仍14059条且不包含这些条件接零对象。M1–M8仅固定局部tie-buffer/PG/M8接入，park fanout留给各case M9/M10+真实过孔。程序只验证当前已存在old08b来源的一致性，保留source版本不改标5429或冻结源；后续真实数据库读回仍须逐网验证实际park导体、连通、短接、电气和闲置功能。本方法不增加硬件资源或创建导线，不将规划/输入通过当作真实物理完成。

当前检查点：2026-10-27T23:07:33.635224+00:00。阶段一已交付，二/三未验收、四未执行；共同候选1/3未冻结。上一轮完成92559/60实际别名/慢线几何分析并提交92561真实辅助块8-net修复试验，属于进展。本轮已从调度器重新确认92561仍RUNNING4CPU：目前在原始完整目标几何预检，尚未产生重布线或物理修复通过结果；保留其运行，不因日志未增长重提。92538完整新源5429的4096区原生DRC仍RUNNING4CPU/4worker，92547独立完整源资格与92548全14059固定低层数据线仍依赖排队，所有作业未停止/重复。独立实际完成新作业92562（源码84ffd20ab1518e297557e05328681b56cff6f440）：把已闭合idle分配、原生固定网归属、两案例完整M8→M9接入计划和92552软件路由manifest逐端点核对。open模式27个零驱动bank覆盖841个闲置输入，llaccel模式28个bank覆盖841个闲置输入；每项真实ITerm为INPUT且不属于14059条共同固定数据网，M8引脚点/落脚pad与原分配一致、零驱动bank正确、在完整定制路由输入中恰好出现一次；每项在另一模式都有一条正常有效连接而非接零。删掉闲置sink、把sink接入固定低层、改错零bank、从路由投影漏掉sink四个负例均实际拒绝。92562真实6秒/CPU5.906秒，平均0.984核（申请4核容量24.61%），主要单线程，不宣称四倍加速；MaxRSS会计返回0，不能解释为不占内存。明确布线边界：M1–M8固定的是已有tie→buffer局部线、PG、零输出和Block引脚的M8接入；两案例各841个、合计1682个随模式变化的接零端点，应属于M9/M10及真实via8_0/via9_0定制分发，不能永久在低层拉零，避免启用该资源的另一模式被短到0。此前“尚需1682 idle连接”不表示应新增1682条共同固定低层零线；现补充显式机器可检的边界，保护后续实现。该检查复用old08b封存分配/接入/投影来源，没有替新5429做完整物理验收，也没有创建实际闲置分发导线。下一步先继续92561和92538至真实终态，物理修复通过后才接新RC、全同边界端点/电气和功能检查；固定线后还需同底座全部case-specific闲置/功能线布通、PGclockRC及aux/VECTOR新增恶化问题解决后冻结。clock rise/fall和37常量输出负载仍“未确定”/null，不补0。源码84ffd20ab1518e297557e05328681b56cff6f440；最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261027T230733Z/milestone.json；SHA-256=d97e4354aeed62d6b42e8a4acee80f9e755dcf4075e30bb1685fa70b963f73f9。本轮只新增本人任务代码/配置/实验/索引并维护六份既有记录，原始/封存/他人文件和未提交四项变更保护，未上传远端或下载大结果。


<!-- selective-auxiliary-source-qualification-and-matched-RC-handoff -->

实际输入基线：92561先复用既有native_geometry对完整原辅助源的8个完整目标网做连通和与全部邻近电气形状接触检查，已闭合原节点23,402,814/ITerm2,927,139，目标连通/异网接触0；同pin多个分离接入形状不偷偷连通，普通线/via/全部变换后的真实PIN计入，OBS不作导体。随后实际原生DEF NETS-only FIXED编码导入，准备保持性比较尚未完成时不得称已安全重布线。

新源门控：qualify_selective_auxiliary_source.py是宿主机独立typed adapter，输入固定source submission/SHA/commit、候选收据位置和原ODB，先从SACCT取确切job终态/exit/分配4核，再核对实际原/新目标几何、准备与最终完整native表/非目标几何保持、新鲜DRC和预留层空、实际ODB以及输入闭合。只有全部通过才输出PASS_CLOSED_SELECTIVE_AUXILIARY_PHYSICAL_SOURCE_ONLY；RUNNING/失败/partial绝不提升成成功，失败保存具体原因。坏终态、非零exit、partial收据、实例表改变、非零DRC、坏连通、预留层占用7种元数据负例随真正执行检验。92563当前仅排队，不能提前算这7项已通过。

新RC适配：measure_selective_auxiliary_rc.py直接识别上述新来源类型，不复写或伪造旧aux_route/access收据，不改变旧measure_auxiliary_rc及相同context比较器。输入真实资格链、新ODB/metadata、旧f739完整RC测量/92425端点census/92555未标注分类、原时钟SDC、Liberty/RCX/工具/API证明。复用既有extract_access_rc.tcl、timing_precise_review.py/tcl、compare_timing_endpoints.py/tcl和串行4线程CommandPool，分别实提取、新进程精确计数与公共报告对照、完整named max/min端点数量/WNS/TNS单位闭合；比较的资源/抽取frame/SDC必须相同。旧unused驱动全名字集合只能在native端点/资源保持且新集合完全一致时复用分类，任何新增漏项都失败。完整ERC原报告保留，逐pin电气变化和功能回归未完成仍不可验收。92564尚待依赖，无新SPEF/时序结果；即便以后测量完成也只是可比较证据，不自动成为质量、继承豁免、公共冻结或两完整case成功。初次依赖配置错误在sbatch之前被拒绝的回执保留，修正另存新launch配置，不把前置配置错误当物理失败或制造调度job号。

当前检查点：2026-10-27T23:17:35.937185+00:00。阶段一已交付，二/三未验收、四未执行，候选1/3未冻结。上一轮92562实际完成全1682mode-dependent idle输入边界核查，本轮继续实际推进修复验证链。92561仍RUNNING4CPU，新增闭合证据为original_target_geometry.json：完整原辅助块23,402,814个电气节点、2,927,139个ITerm参与，8条完整目标网连通、目标与异网接触0。它是原f739输入检查通过，不是重布线成功；接着已真实执行原生FIXED NETS-only DEF导入，日志显示更新624,012条网/1,824,756个连接，正在导出准备后完整native库存，准备保持性比较和实际路由尚未验收。92538完整新源5429的4096区DRC仍RUNNING4CPU/4worker，92547独立源资格与92548全14059固定低层数据线仍依赖排队；未停或重提任何运行作业。本轮已提交两个新4核依赖作业：92563（源码640dd52ee02713826d13535859dcbae217410891）在92561自然终态后，以宿主机真实SACCT COMPLETED0:0/4CPU、固定提交SHA、原f739输入及封存报告/实际ODB核查新typed物理候选；要求原/新目标连接、完整实例/master/端点与非目标几何保持、新鲜原生DRC0、M9/M10无占用；7类坏状态/坏报告副本检查会在实际执行时检验，当前尚未执行。92564（源码6af4b3c73ded2676c0280b46aa1da81b52ce0890）在92563之后，必须读到实际成功资格及同源实际ODB才启动任何EDA，复用既有extract_access_rc、timing_precise_review、compare_timing_endpoints和92425旧完整端点清单，串行最多4线程提取新SPEF、新进程精确setup/hold/ERC测量及新完整负端点清单，以native数量/WNS/TNS核对完整性。要求同旧历史SDC/Liberty/RCX规则/实际frame及资源数；与92555原闲置未标注驱动名字集合完全一致才可复用其非主动漏RC分类。该新源适配不伪造旧aux_route收据，也不放宽原比较器同context门槛；ERC逐pin变化、功能及最终质量仍需后续核查。两个后继当前均仅依赖排队，代码/配置写好并提交不表示执行或验证通过。首次资格作业提交配置把依赖字段误写为path，submit.py在调度前拒绝，未生成job或driver；错误spec和失败回执完整保留，另建launch-r02配置改为receipt后才实际提交92563，没有重复运行。92562证明仍有效：每mode841个idle sink为case-specific M9/M10+真实过孔连接，局部tie-buffer/PG/M8接入固定，不能永久在低层接零。未创建实际1682条idle分发导线，未提升任何新公共底座版本。外部clock rise/fall和37常量输出负载仍用户确认“未确定”/null，不补0。源码6af4b3c73ded2676c0280b46aa1da81b52ce0890；最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261027T231735Z/milestone.json；SHA-256=6651740b0a09046bc9e81f04438c9e66d5e6e418289e7ba72158c223556309e7。所有新增代码/配置/调度日志和结果只在本人任务目录，维护既有六份记录，原始/封存/他人文件与四项未提交内容保护，未向远端上传或下载大结果。


<!-- selective-auxiliary-complete-named-electrical-comparison -->

compare_selective_auxiliary_electrical.py为新typed selective测量来源提供证据适配，继续复用compare_electrical_violations.py的parse/difference，不另写电气报告解析器，不伪造旧producer。宿主机先检查真实新测量作业终态/exit/4CPU以及闭合typed成功收据，再要求同历史SDC和精确frame已由92564验证、旧测量SHA确实是新测量输入。旧artifacts和新output_sha256分别绑定实际报告；所有有限cap/slew违例行必须严格解析、与实际native数量闭合，两边检查种类/finite范围/单位相同，否则失败。按pin身份比较新增、消失、共同项，分别保留9位打印精度下的assessment和严格数值slack_delta<0标志；不把细小负变化静默接受，也不把旧违例总数减少当作没有新增问题。原fanout未给有限上限时明确不算覆盖。使用等总数但换一个pin身份的实际报告副本作为检查器控制，必须得到一项新增和一项消失。没有过去所有passing pin的正裕量，不能给其完整margin对照；所有新违例只能按完整实际列表变化报告，不能以缺旧项填0。92565已排队但未执行，上述程序和控制当前未验证，后续以实际结果为准；不替代功能/物理/质量/冻结验收。

当前检查点：2026-10-27T23:33:18.942175+00:00。阶段一已交付，二/三未验收、四未执行，候选1/3未冻结。上一轮为已核实运行等待，本轮读回新增实际进展：92561的prepare_comparison.json已pass，实例、master、完整master PIN/OBS、层、via定义、ITerm、BTerm、net八张表全部相同，所有原始导体/引脚/阻挡几何分组完全相同，changed_nets和forbidden_changes均为空；FIXED编码准备未改变单元/master/位置/连接或几何。原8目标网连通与异网接触0的前置证据继续有效。随后实际生成15,519,488个非目标普通导线/过孔精确保护矩形（含3,920,358个cut矩形，558,740个被保护net），未简化、膨胀或删除原几何；保护清单已闭合，route/openroad.log已由原生OpenROAD进程启动并显示4线程。92561仍RUNNING，尚无新重布线/独立读回/连通/新鲜DRC通过结果，临时保护最终移除及所有非目标几何保持仍需实际检查。本轮没有为等待再创建同一实验。完整source92538仍RUNNING4CPU/4worker；新索引仅诊断读取已写BATCH结束标记的592/4096个分区原始报告，其中非空报告0个；没有进行全batch DEF/source闭合资格核查，不能把这些局部原始报告当整片DRC通过。每个worker的闭合batch/具体tile及原报告位置、stop标记均留新观察索引，未改写worker文件。92547独立完整源资格和92548全14059条固定低层线仍依赖排队；92563修复源资格、92564新SPEF/完整setup-hold端点及92565逐pin ERC同样仅排队4核，代码存在和排队不表示执行通过。保持原3ns/既有SDC，未知clock rise/fall和37输出负载仍null，不补0、不将本轮新增恶化豁免为继承。各841个idle sink属于两case各自M9/M10定制分发，局部tie-buffer/PG/M8接入固定；未创建实际1682闲置分发线。下一步继续运行中的真实路由及整片DRC，按已有严格依赖链读实际终态，完成RC/逐端点和逐pin质量/完整功能后才决定是否采用辅助候选，补完共同固定/定制线与PGclock后才允许冻结。源码42e812c5cd6d06584296d0216e17d172e0668242；最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261027T233318Z/milestone.json；SHA-256=7c6fecd46dfa9e4020a53b1253df9402495a9782b34b64719257be224b0cc8f0。本轮只更新本人任务证据索引和既有六份记录，所有原始/封存/他人内容及四项无关未提交改动保持，未下载大结果、未远端上传。


<!-- named-ERC-native-geometry-diagnostic -->

新增电容违例的原生几何定位算法（已验证诊断范围）：先用已有逐pin比较选择全部新增cap引脚，绑定同一闭合最终ERC报告及native producer；通过精确native实例/端子名称找到驱动与net，核齐所有ITerm成员、唯一OUTPUT、端口数和原版/当前端点位置；流式读取全部对应WIRE/VIA行，输出分层矩形统计和via数。名称不匹配必须提供显式绑定，不去掉转义字符猜测；输出的矩形长轴和包含重叠及端帽，不当作中心线长度或RC因果。程序命名/数量/坐标由输入和原生表决定；92566两个完整网实例通过并拒绝wrong_net/wrong_driver_direction破坏。驱动未改线仍可能产生新ERC，须保留邻近网络/耦合调查，不以旧线保持作为电气豁免。

入口：在submit.py新4核不可变快照中运行 python3 -B -I -S named_erc_net_geometry.py --config configs/vector_new_ERC_native_geometry_r01.json --output 本任务新runs目录。该任务已COMPLETED，不重复提交相同证据。结果类型MEASURED_NEW_NAMED_ERC_NET_NATIVE_GEOMETRY_ONLY只表示只读定位，不能替代连接/DRC/时序/修复或完整案例通过。

当前检查点：2026-10-27T23:54:55.117560+00:00。阶段一已交付，二/三未验收、四未执行，候选1/3未冻结。新增4核作业92566实际COMPLETED0:0，79秒墙钟/78.094秒CPU，平均0.989核、四核配额利用约24.71%，主要为单Python线程；源码f2bec406b6c2d6bb1c9ee375b85ddc49f095a655。程序named_erc_net_geometry.py从封存逐pin ERC结果选择全部两个新增cap引脚，核对最终实际58项cap报告、原版/当前native精确名称、全部网成员/驱动方向/位置及所有选中WIRE/VIA形状；wrong_net/wrong_driver_direction真实元数据破坏均被拒绝。定位_461984_/ZN→_133774_，NOR2_X4、9端子，属于原40迁线目标，原有M9导线现主要M2/M3/M4；_467762_/ZN→_139520_，NOR2_X2、4端子，不属于迁线目标。原迁线严格比较与M8接入additive比较的闭合证据再次核对，两阶段均未改动_139520_导体；因此不可把所有新增电容超限都归因于该网络被重画，周边导体/提取的影响仍需源匹配SPEF证据，尚未证明具体原因。本轮是只读问题定位，不是布线修复通过，原22处持续cap恶化及setup恶化仍未解决。92538完整4096分区源DRC和92561辅助8网路由仍RUNNING4核，未停止/重复；92561日志已完成一次353710组pin-access并继续后续阶段，尚无实际新路由通过。92547/92548、92563/92564/92565继续依赖排队，不把排队或程序存在当通过。14059固定数据网络及各case841条件闲置分发仍需真实接线；闲置分发属于case M9/M10定制，局部tie-buffer/PG/M8接入固定。用户再次确认外部clock rise/fall及37常量输出负载未确定，继续null、不补0；最终外部电气项未验证。最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261027T235455Z/milestone.json；SHA-256=ca156cb7712ae95165f1df688cf8f639135cf7d8de410271d60c0cef554ebe80。仅本人目录增加源码/配置/诊断结果并维护六份记录，不更改原始/封存/他人或四项无关改动；无下载和GitHub写入。下一步继续现有路由/DRC严格依赖链，并以新定位检查VECTOR寄生原因，质量/功能/物理门槛满足后才冻结和进行两完整case最终定制。


<!-- selected-SPEF-coupling-diagnostic -->

源匹配选中网络SPEF电容分解（92568已验证）：从闭合逐pin ERC→native几何诊断获取精确网络和全部端点，以同一SDC/Liberty/提取规则/native工具的原版、当前实际SPEF作输入。流式NAME_MAP与D_NET/CONN/CAP扫描，所有端点角色和名称须与原生表一致；分别累计对地/全耦合电容和按邻网分组变化。内部节点由net token解析；耦合到单元引脚时，必须在对应完整native ITerm表中解析其实际net，不能丢弃该项。保留D_NET原声明值及声明值与逐项和的数值差，不用打印残差作时序/电气豁免。输出仅作选修复目标的诊断；矩形未变不能推断提取电容未变，耦合变化也不等于排他物理因果。92567格式限制失败保留，修正版的单位/端点/电容节点归属破坏负例与内部/外部引脚正例通过。

入口：selected_net_spef_capacitance.py --config configs/vector_new_ERC_SPEF_capacitance_r02.json --output 本任务新runs目录，在submit.py不可变4核快照内执行。92568已完成，复用有效证据不重复提交。实际结果及原失败见最新索引；正式Block可替换producer、SPEF、native端点表及上下文绑定，无固定模块名/数量/坐标。未覆盖外部BTerm/非标准delimiter或单位时明确失败，尚无修复/完整DRC/时序签核。

当前检查点：2026-10-28T00:02:49.856661+00:00。阶段一已交付；二/三未验收、四未执行，候选1/3未冻结。本轮完成只读源匹配SPEF分析92568：源码5fcd6371907bd5f53edeb15a4830aeb3d1f6e11c，4核申请、单Python线程，COMPLETED0:0，墙钟63秒/CPU62.683秒，平均0.995核、配额利用约24.87%，MaxRSS556740KiB。绑定92566封存完整native网成员与原版/当前SPEF，逐连接方向和精确名称核对，匹配相同SDC/Liberty/RCX规则/setRC/native工具；*CAP中邻网单元引脚通过完整实际ITerm表解析，不猜测或删去。原网络_133774_（迁线目标）的D_NET总电容增加20.316fF，对地+1.96214136fF、耦合+18.35371669509fF；未改几何_139520_总电容+1.4256fF，对地-0.821678fF、耦合+2.24724317fF，最大新增耦合来自实际迁线目标_135943_，+2.53999fF。这提供修复目标与邻线影响的实际线索，不是排他物理因果证明、修复成功或ERC/时序通过。原22处持续cap恶化及setup恶化仍未解决。92567原读取器不支持邻网引脚节点，FAILED1:0/5秒记录保留；92568补齐精确native解析后运行新版本新目录，单位/成员/电容归属破坏负例及两种节点正例通过，未修改任何硬件。完整源DRC92538与辅助8网重布线92561仍在运行4核；完整DRC仅已闭合原始报告656/4096（非空0），未完成全source/DEF闭合资格，不能称整片通过；92547/48、92563/64/65依赖队列未重复提交。仍需14059实际固定线和每case841定制idle分发、PGclock/RC/质量/完整功能才冻结，再做两个完整case最终定制。未知外部clock转换时间及37常量输出负载继续null，未补0。下一步利用实际耦合结果选择VECTOR必要局部迁线修复，并继续当前长作业严格核查。最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261028T000249Z/milestone.json；SHA-256=55ebc08b59e23f1b447f2982588dfb8a34e203530a73697642a66cf2678553c4。本轮新增/修改仅本人代码、配置、结果和六份主要记录；保护原始/封存/他人/四项无关变更，无大结果下载或GitHub写入。


<!-- selected-wire-repair-capacity-and-preparation-reuse -->

证据驱动选择性重布线：复用reroute_slow_auxiliary_nets.py/migrate/native geometry/固定导体保护机制，增加独立选择适配器，从测量慢路径选8网，或从实际新ERC/耦合诊断绑定原40必要迁线目标。仅完整普通信号导线可变，原单元/master/位置/连接/PGclock/非目标普通与特殊导体/完整PINOBS必须保持，M9/M10空置、目标几何/全新DRC独立检查；物理候选通过仍须新RC、逐pin和完整setup/hold及功能后才采用。capacity_preferred_migrate.tcl在独立新工具进程中对set_routing_layers调用附加有界容量偏好，不修改既有migrate脚本或工艺。M2-M6减少0.75全局可用轨道只是启发式，M2-M8范围保留低层接入；不能宣称限定主干实际层或必然降电容，需native几何/实际提取核实。

闭合准备恢复：qualified_wire_preparation.py只接受已终态FAILED且仅route阶段失败的指定旧来源。宿主在同一4核作业内实际sacct，记录任务/原来源/配置/源码SHA与时间；容器验证该记录、原始ODB/全部native输入、共同底层助手版本、原目标几何、完整准备相等比较、准备ODB、全部13张native准备表与精确保护文件。只读复用已闭合准备，所有新route/native保持/连通/新鲜DRC仍重新执行；不把旧失败路由改标pass。92570因容器缺sacct安全停止，92571宿主前置与完整准备复用已实际通过，布线仍运行。submit.py新host_preflight_commands在taskset和4CPU限制之后、容器之前执行；默认无前置命令的旧作业行为保持，其不可变快照未改变。

实际失败边界：92561M7-M8最小层试验DRT-1231缺pin access；92569VECTOR导入选中网仍有FIXED路径，原mark_def已设置net级ROUTED，说明需要核实逐path编码，不能凭metadata设置成功猜测已修复。原始和失败文件均保留；原source gate/RC/ERC拒绝失败源已实际生效。当前M2-M8修复方案只算运行中，不是质量接受。

入口：92571使用configs/current_aux_slow_net_capacity_preference_r03.json，由submit.py固定8fc5f05...快照，host前置运行qualified_wire_preparation.py --config 同配置 --output driver/predecessor_scheduler.json；容器运行reroute_slow_auxiliary_nets.py --config 同配置 --output 新runs目录 --scheduler-proof driver/predecessor_scheduler.json。92571仍在运行，不重复提交。正式Block接入需替换native来源、目标选择证据/端口、固定层、技术范围和资源约束；现容量偏好是明确候选参数。

当前检查点：2026-10-28T00:17:28.094198+00:00。阶段一已交付；二/三未验收、四未执行，共同候选1/3未冻结。新增失败：92561自然FAILED1:0，3987秒墙钟/9530秒CPU，平均2.390核/四核配额59.76%，MaxRSS54717800KiB；原完整几何/准备保持通过，但详细布线DRT-1231多个PIN无接入点，未生成通过的新route。92563实际严格源门拒绝FAILED，92564未启动RC、92565未作有效ERC比较，三者失败如实保留，不绕过。VECTOR92569源码f920f91a4aa6591fed2f870a09b4f615a221a301，4核实际378秒/375.622秒CPU，原40目标几何完成，但import_fixed在vec_rd1_rdata[92]检测到FIXED路径，未满足ROUTED；mark_def已设置net级ROUTED，故不能仅重复该设置，需查实际DEF/path编码，尚未进入容量偏好布线，未认定线路或性能成功。辅助92570在布线前因容器无sacct而FAILED，8秒/6.120秒CPU，错误和原结果保留。修正将真实调度查询放到同一个4核作业的host_preflight，生成本作业号、配置/执行/提交/助手源码SHA及时间绑定的前置记录，容器逐项核验、不省略门槛。92571源码8fc5f05d751f6cac1b9d5bacc92d76c6fcee9253，已实际通过旧92561闭合准备的重用核验（13张native表、原目标几何、原/准备全部几何与连接相同、准备ODB及精确保护层均校验），只读复用准备，不重用失败route；未重做整个准备实验。92571保持原8目标/单元/位置/逻辑不变，改为允许M2-M8引脚接入并将M2-M6全局容量减少0.75以偏好M7/M8；原生工具已执行并记录该设置，现RUNNING4CPU，尚无新route/DRC/RC/功能通过。运行中92538完整源4096分区DRC保留，92547/48依赖未重复。两运行作业均4核、线程总数不超申请；原92561未被停止，其自行失败后才新运行。仍需解决全部新增/恶化电容与setup/hold、真实14059固定线/每case841定制闲置分发和PGclock、最终完整功能后才冻结，再验证两完整case。外部clock转换时间和37常量输出负载未确定，继续null不补0。最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261028T001728Z/milestone.json；SHA-256=62f751b699ced00944e56b4c34f7f1ba7a1b0962a83e86838945fb7a295612f3。仅本人源码/配置/结果和六份记录变更；migrate.py/migrate.tcl及原始/封存/他人/四项无关改动未修改，未下载大结果、未GitHub写入。


<!-- native-DEF-selected-path-route-status-preparation -->

选择网络的路径状态准备（92572实际诊断、92573部分前置已验证）：从失败来源封存nativeDEF和完整native net名表读取，严格解码DEF标识，不删除bus转义猜名称。逐条对照40目标marked/netsonly记录SHA及全部route属性；混合ROUTED/FIXED是path级状态，net级setWireType不保证抹除旧分段属性。def_route_status_preparation.py仅将已声明目标中的FIXED路由状态token改为ROUTED，比较去状态后的所有字节必须相同、非目标记录原样输出；不修改任何坐标、层、via或连接，不永久/临时删除导体以腾层。接受输入只来自实际终态FAILED的指定import来源，同job host预检和配置/提交/执行/助手SHA/时间绑定，原geometry/nativeDEF诊断闭合。旧有效原目标几何可重用，但失败import/route不算通过。

92573仅转换2token后，真实native import已解码40目标ROUTED和376265非目标FIXED；这只解决原报错前置，完整native保持性、最终目标route/独立新鲜检查及RC/功能/时序仍是必需门槛。输入正式Block可替换source/targets/native名字表和诊断证据；该normalizer目前支持本nativeDEF NETS格式，遇到未知/歧义名字或其他route属性显式失败，不暗自转换。

运行入口：inspect_native_def_route_types.py --config configs/vector_native_DEF_status_r01.json --output 新runs目录（92572已完成，复用结果）；reroute_slow_auxiliary_nets.py --config configs/vector_ERC_upper_preference_reroute_r02.json --output 新runs目录 --scheduler-proof 同job driver/predecessor_scheduler.json（92573实际运行，禁止重复）。不变的后续source/RC/ERC算法已对92571通过r03配置重新绑定，92574→92575→92576各4核依赖排队；严禁将旧失败源改状态或将这些排队程序写成验证通过。

当前检查点：2026-10-28T00:28:44.953519+00:00。阶段一已交付；二/三未验收、四未执行，候选1/3未冻结。92572只读DEF诊断源码921b3c8069d8d8e8c714815a765eaec942091ffb实际COMPLETED0:0，4核申请、单Python线程，墙钟19秒/CPU17.797秒，平均0.937核、四核配额23.42%；MaxRSS计数0为未取得有效测量，不声称零内存。完整native marked.def与NETS-only的40目标记录逐条字节/SHA相同，38目标仅ROUTED，vec_rd1_rdata[157]/[92]各含1ROUTED+1FIXED，明确不是NETS复制丢失；旧mark_def本已setWireTypeROUTED，不能只重复net级设置。新92573源码c5b986e13b4f171df6a7b0471996092f1e8f627d仅在本人新DEF转换这两处目标段FIXED→ROUTED，其他字节保持；没有删除导体、坐标/层/via/端点字段不变。用实际同job host调度终态和绑定SHA核验92569旧失败，只复用其有效完整原目标几何与nativeDEF，不重用失败import/route。92573实际native导入已过原报错，解码40目标全部ROUTED、376265其他普通导线网FIXED；全native库存与几何比较仍PENDING_FULL_NATIVE_COMPARISON_NOT_YET_ACCEPTED，未把flag转换/导入通过当布线成功。92538完整源DRC及92571辅助8网重布线继续4CPU运行，未停止、未重复；92574严格独立源门、92575新寄生及完整setup/hold端点、92576完整逐pin ERC均已按新92571来源提交4核依赖排队，源码与真实submission/job/SHA固定，程序与排队不是执行通过。失败92561/63/64/65/69/70均保留且未豁免。主migrate.py/migrate.tcl原工具逻辑与原始/封存/他人文件保持；当前前置导入仍须完整保持性、目标连通/异网接触/新鲜DRC/上层空置，再新RC/电气/时序及完整功能，才能采用任何候选。仍需实际14059固定线/每case841定制idle分发与PGclock/完整最终验证后冻结，再两个完整case最终定制；外部clock转换和37输出负载继续null不按0。最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261028T002844Z/milestone.json；SHA-256=28c4fcb114c9a24be0ce108929cfd59e03c2c5aa01444358a7c228be04b90755。仅本人任务源码/配置/结果和六份记录改变，四项无关改动保留，无大结果下载或GitHub写入。


<!-- typed-selective-source-gate-eight-native-tables -->

独立选择性物理来源门的案例适配：qualify_selective_auxiliary_source.py保留同一检查引擎，route_kind只允许auxiliary_slow/measured_ERC两种已知producer状态，不能从配置任意填写成功状态。新VECTOR使用不同PASS_CLOSED_SELECTIVE_ERC_PHYSICAL_SOURCE_ONLY输出类型，避免伪称旧辅助模型。接受之前须实际Slurm COMPLETED0:0/4CPU、不可变source revision/已封闭execution与ODB、全部六类几何/DRC/层资格报告。prepare/route比较须恰好八张原生表：instances、masters、master_geometry、layers、via_definitions、iterms、bterms、nets，各equal且added/removed=0；准备changed_nets必须空，目标几何须完整集一致且无异网接触，DRC0且保留层空置。代码追加缺master_geometry表的实际报告副本负例；仅在实际正例来源闭合后执行这些负例，本轮没有把未执行夹具计通过。92577依赖92573运行，程序仅语法/管理检查通过，物理资格尚未验证。

现有辅助队列92574/75/76继续使用各自不可变旧快照，不因本轮编辑root脚本而静默改变。下一步VECTOR RC应通过独立内部上下文适配，复用已闭合fullaccessRC与完整端点census，而不创建假辅助producer或降低sameSDC/frame/完整annotation规则。此适配尚未实现；旧VECTOR完整覆盖/闲置driver分类可作为输入，不能直接作为新候选测量通过。

当前检查点：2026-10-28T00:35:58.094158+00:00。阶段一已交付；二/三未验收、四未执行，候选1/3未冻结。上一轮完成实际DEF诊断/状态修复，本轮已核查92538完整源DRC、92571辅助8网重布线、92573VECTOR40网准备/重布线均仍RUNNING4核，未停止/重复。92573已完成完整native库存导出和内部一致性review（inventory_complete/pass_inventory_consistency_only），两份闭合报告留索引；原始与准备版本全部几何/连接对照仍FULL_ORIGINAL_VS_PREPARED_COMPARISON_RUNNING_NO_CLOSED_RESULT，不能把内部一致或flag导入当几何保持/布线通过。新增4核92577独立VECTOR源资格任务，源码75c72358bdacd3d1142d341ee6ff362667643224，绑定实际92573提交/源码/原ODB与原40目标；与辅助共用qualify_selective_auxiliary_source.py，只通过显式ERC producer类型适配，保留实际COMPLETED0/全部闭合报告/全目标连通与无异网接触/新鲜DRC0/M9M10空置门槛，并要求完整八类原生表齐全、每类equal且added/removed=0、准备changed_nets为空。新增partial_native_table_set破坏负例代码，尚须真实合格来源后执行，未宣称测试通过。92577及92574/75/76仍仅依赖排队4核，不把写好/排队当验证。无需新取输入：旧VECTOR完整accessRC证明已有376305实际active net、1073670端点精确SPEF覆盖，4683未标注driver已分为4076无互连单端点/607未连接输出，完整postM8负端点census亦闭合；本轮只核验并记录可复用来源，尚未实现新VECTOR RC测量适配或提取，后续复用共享提取/精确STA/完整逐pin比较，不重跑旧有效结果、不伪造辅助producer。任何新辅助/VECTOR视图采用后，旧共同底座/固定线的源SHA不得继续冒充新来源资格，需重新组装并核验受影响的完整源。仍需实际14059固定线、每case841定制idle分发、PGclock、所有新增恶化质量与最终功能后才冻结，再两个完整case实际最终定制；外部clock转换和37输出负载null不补0。最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261028T003558Z/milestone.json；SHA-256=baa080c5a7bb747a2d25497204cfc3f7c9c44db9f5fbdc5b84c7763d05a9b545。只在本人源码/配置/结果和六份主记录更新，原始/封存/他人/四项无关变更保留，无大结果下载或GitHub写入。


<!-- full-access-reference-runtime-shared-RC-ERC-adapter -->

统一RC/完整端点/逐pinERC流程的fullaccess参考适配：full_access_rc_reference.py只读核验实际FULL_ACCESS证明、其真实coordinate extraction、同扩展frame原始控制和完整三版本端点census。ODB、SPEF、SDC、Liberty、native工具、wireRC/RCX/tech、真实clock约束与闲置annotation须版本绑定；原始与postM8 frame/资源数一致。返回的model字典仅为内部接口视图，没有伪造辅助producer状态。92578的只读输入适配已实际通过；不等于新候选或提取通过。旧有效数据不重跑。

共用measure_selective_auxiliary_rc.py原辅助默认语义保留，新增已知ERC类型，实际来源资格仍先于任何新提取。新source extracted SPEF→precise max/min/ERC→完整负端点census串行调用已有三个Tcl，各native最多4线程；相同旧约束/frame/library、严格annotation身份集合和完整count/WNS/TNS交叉检查保留。除了对修复前postM8比较，还将新端点完整对照原始同frame版本，单独输出same_context_original_endpoint_changes.json。compare_selective_auxiliary_electrical.py复用既有严格parser/difference，接受实际fullaccess输出索引，另外与原始实际报告逐pin对照，输出original_reference_named_ERC_changes.json及新增/消失/持续恶化/所有数值负增量。避免“比坏版本改善”被当成“消除了本轮新增问题”；所有输出仍仅测量，不自动质量/功能/冻结验收。92579/80依赖排队尚未实际验证，身份破坏负例仍待真实新结果后执行。

入口：full_access_rc_reference.py --config configs/selective_vector_capacity_preference_RC_comparison_r02.json --output 新runs（92578已完成，不重复）；measure_selective_auxiliary_rc.py 同配置（92579排队）；compare_selective_auxiliary_electrical.py --config configs/selective_vector_capacity_preference_named_ERC_r02.json（92580排队）。各通过submit.py固定源码与4核，未来Block替换实际来源类型/producer绑定、参考配置、scope/frame/接口/clock/tech资源，未知项显式失败，不临时放宽。现有辅助队列快照未被本次root代码更新改变。

当前检查点：2026-10-28T00:51:17.012042+00:00。阶段一已交付；二/三未验收、四未执行，候选1/3未冻结。本轮真实新增闭合结果：92573完整原始/准备native对照pass，八表instances/masters/master_geometry/layers/via_definitions/iterms/bterms/nets逐表equal且added/removed=0，changed_nets与forbidden_changes均空，全部导体/引脚/阻挡几何保持；2处路径flag归一化未改物理资源，后续实际详细布线仍运行，未宣称新route/RC通过。92578源码e28c7eb9d7b75c8c6c3ad7f54093b5b32b5d5f18实际COMPLETED0:0，6秒墙钟/4.314秒CPU，平均0.719核/四核配额17.975%；MaxRSS0为未取得有效值。仅只读验证已有fullaccessRC、同扩展frame原始参考及完整postM8/original端点census的ODB/SPEF/SDC/Liberty/技术/工具/clock版本绑定，4683原未标注driver仍有已核实闲置分类。full_access_rc_reference.py返回内部运行上下文，不伪造辅助producer或重提取旧SPEF；未接受新候选质量。共用measure_selective_auxiliary_rc.py已增加显式ERC参考适配，保留完整新提取/precise STA/max-min census/精确unused身份门槛，并另输出相对原设计的全部端点变化，避免只比修复前坏版本。共用逐pinERC程序增加原版与修复前双参考、完整finite计数/单位/身份核查和所有负增量保留。新4核92579依赖实际92577与参考92578，92580依赖92579，现仅排队，未执行的新RC/时序/电气/负例不能计通过。新增失败92571自然FAILED1:0，墙钟1979秒/CPU7406秒，平均3.742核/四核配额93.56%，MaxRSS33689912KiB；M2-M8仍同类PIN无access，说明降最小层不足以解决，尚无合格新route。92574/75/76实际拒绝失败源、未启动RC/有效ERC，全部留证。下一步需精确核对报错BPin、固定导体保护区域与合法via几何，不盲目重试、不删原几何/阻挡。92538与92573继续运行4CPU，未停止或重复；旧common源/固定线若换新master必须失效重核。仍需14059实际固定线、每case841定制idle、PGclock、全部新增恶化质量与完整最终功能后才冻结，再两个完整case最终定制。clock外部转换及37输出负载仍null不补0。最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261028T005117Z/milestone.json；SHA-256=8d18d3dbb7115d115aa3cb605ca047c946bd3cf0db97664867e2c254f88e35df。仅本人代码/配置/结果和六份记录更新，原始/封存/他人/四项无关变更保留，无大结果下载或GitHub写入。


<!-- native-failed-BPin-overlay-and-saved-AP-forensics -->

失败反馈的可复用流程：pin_access_forensics.py按封存的实际失败execution/log提取精确BTerm名，连接同源码ODB绑定的BTerms/nets/nativeBPIN形状、真实导体、技术via footprint与实际匿名保护overlay。只读流式扫描完整相关表，核查自己net导体与匿名保护矩形的几何同一性；允许层范围显式输入。可选前次失败仅在真实同源绑定存在时比较；无前次为null，不假造0。错误native net与缺失pin形状实际负例拒绝。该表不能证明因果、连接或DRC合法。92581 AUX与92582 VECTOR均已实际运行，49/5失败端口全部非目标，因此不能把目标网自身via bbox检查冒充问题已排除。

probe_failed_BPin_api_tracks.tcl用安装的0a4原生OpenROAD查询实际dbTrackGrid、dbBPin/getAccessPoints和AP坐标/层。输入ODB与精确失败端口独立配置；不移动/删除几何、不写数据库。92584暴露getPoint返回Tcl双元素list，92585修正并实际读回五端口15AP全M5、M8双轴轨道存在，原ODB前后hash相等。opaque SWIG对象与getAccesses参数失败不视为方向/via内容已解码。可选HPY_PIN_PROBE_REGENERATE=M2-M8-no-added-overlay仅在内存原始完整几何上运行pin_access，用于基线诊断；不添加额外overlay，不删除已有真实obstruction，也不进行任何route。92586已提交4核，尚需读回真实结果并与含完整固定导体保护的控制对照，才有理由决定修复；不能将M5旧AP或overlay重合直接写成已证实根因。每版源码固定commit，失败日志保留，不在封存快照打补丁。

92586实际完成无新增overlay的prepared-source接入点重生成：每个失败BTerm增加1个M8AP。因本控制保留40目标旧线、没有正式路由时的额外保护overlay，只支持隔离AP生成事实；92587以相同源/目标线/设置加入同一额外overlay做下一因素对照，不直接重复整套路由，也不把AP点存在当作可合法连接。对照必须绑定原ODB及overlay前后SHA、精确计数、AP层坐标与真实终态；原几何或原obstruction不可删除。首轮API getter失败及opaque方向/via仍未验证，不掩盖。

92586与92587已形成实际隔离因素对照：同一prepared9ae、原40目标线保留，单独pin_access在有/无同一8582427额外overlay时均生成完全相同15M5+5M8 AP，5个端口/层/坐标逐项一致；原ODB及overlay前后SHA相等。不能把已有overlay重合当作根因，当前不支持通过过滤保护来修复。下一步probe_pin_access_route_handoff.tcl显式包装原生PA/GRT，保留原migrate.tcl与capacity适配器，记录五端口在BEFORE_PA/AFTER_PA/BEFORE_GRT/AFTER_GRT/BEFORE_DETAIL的AP，复现原40目标撤线及全保护，进入详细布线前明确退出0，仅为交接诊断不生成候选DB。92588已4核提交待实际完成。所有原始/非目标/PG/PIN/OBS保留，不用诊断退出码代替路由成功。首轮API getter失败及opaque方向/via未解码仍记录。

92588在实际原流程40目标撤线及全保护下，PA后→GRT前→GRT后→DRT入口前五端口AP逐项不变，详细路由显式未执行，排查转向详细路由读入/内部PA容器或worker空间筛选，不能以公开master源码推断本机0a4未知版本的根因。新增可选route_process_adapter=fresh_native_ODB_and_guides，两阶段顺序执行而非并行：首进程复用原migrate/capacity执行PA/GRT、保存handoff与真实guides及原OBS身份/几何；第二原生进程独立读回相同库/SDC/RC/range与全部几何/精确保护，再完整DRT。保护全过程保留，结束后仅清理新加overlay，原OBS逐身份/坐标验证。现有完整native目标/非目标/几何/连接/新DRC门槛仍由原adapter执行，默认单进程与其他队列快照不变。92589仅已提交/开始，双进程策略是否改善原DRT1231以及新质量仍待实测。

准备复用增加显式VECTOR已知失败状态与三阶段集合（import_fixed/prepared_inventory成功、route失败），原辅助四阶段集合不变；只接受同作业新鲜SACCT FAILED1:0/4CPU证明、完全同原ODB/目标/13原生表/8底层helper SHA、实际DRT1231日志、exact全部八表及每表added/removed=0。92589已实际读回受保护的92573准备证据；4种元数据毒化copy拒绝已验证，不能算完整physical/gate新阳性。正式输入替换必须重新生成生产者证明与物理/功能/质量证据，不得把未知生产者当已知类型。

独立物理来源门禁增加双进程受控适配：expected_routed_ODB_relative只接受已知single/fresh枚举且与真实producer一致，fresh仅可绑定route与route_detail均完成、对应两已知Tcl、封存handoff/guide/原OBS清单和route_detail/migrated.odb；旧单进程仍绑定route/migrated.odb。完整原8表、masterPINOBS、原始/新目标连通与全部邻近导体接触、新nativeDRC、上层空闲和实际4CPU成功终态不变。输出路径元数据helper旧阳性与合成fresh阳性及5种错误copy已实际测试，实际完整物理来源阳性/8个门禁负例仍需92589成功后92590真实执行，不能提前计过。92591/92复用已有共用RC/精确max-min census/逐pinERC程序和同frame原始与pre-repair双参考，只改真实源/measurement提交指针；固定3ns与技术库/RC/annotation身份，不放宽验收，失败源不得提取。各snapshot不可变/4核；当前仅队列接入，完整后续工具和新质量尚待实际验证。

同一fresh-native适配器已配置到完整辅助8目标来源（92593），保留原f739源及全量15519488固定导体保护；仅case配置/实际生产者/targets/reference/容量参数替换，没有复制第二套路由实现或缩减网表。92594/95/96沿用同一严格来源门禁/RC端点/逐pinERC程序，通过真实依赖串联、每作业4核，失败源禁止提取；没有把VECTOR首轮局部进度推广为AUX已通过。两者均等待全部实际native/连接/新DRC/质量/功能后才可能采用到新共同source。

92589完整试验真实失败：fresh DB读回后内部再次PA与详细routing，最终同5BTerms报DRT1231，92590/91/92正确拒绝来源且没有新RC。已有AP坐标存在、GRT前后不变、fresh进程读回均不能推出worker内部有可用AP；新进程本身不是已验证修复。现有原生detailed_route帮助/过程提供-no_pin_access，后续若研究复用已完整生成的真实PA，须记录其一次生成/保存/输入闭合及实际当前API，不省略任何资源保持/连接/DRC/RC/功能验证；该新策略尚未实现或验证。公开master代码只支持研究worker区域筛选线索，不证明本机0a4版本根因，不能按猜测修改工艺/引脚/阻挡。

355bbc1实现可选native_pin_access_policy=regenerate/reuse_saved_native_PA，默认不变。后者首阶段实际完整PA只执行一次；completed_native_PA_summary要求已完成、唯一noAP=0、唯一正pinCount，首日志hash绑定。freshdetail进程读回实际DB/guide/完整保护后再核本机Tcl支持-no_pin_access，检查所选目标BPin每个已保存AP的层/坐标确实落在自身真实矩形，才省去第二次生成；所有连通/几何/源保持/原生新DRC/RC/完整功能验证仍保留，不把工具前处理选项当作豁免规则。实际旧完整PA摘要阳性与4项日志毒化负例/Tcl语法已完成；92597当前仅首进程运行，真实复用分支、路由和全部质量仍待验证。92598/99/92600引用真实前置提交依赖，沿用完整原始+pre-repair同frame参考，不重复旧有效提取或放宽约束。92593封存快照仍旧策略，未被原地修改。


<!-- native-worker-control-API-capability -->

92601只读查询实际安装OpenROAD的detailed_route_debug与内部worker/step控制，前后ELF SHA同0a4；接口支持按net/pin/box及-dump_dr/-dump_last_worker/-dump_dir等诊断标志。只确认实际help/Tcl入口与命令存在，未运行导出或worker回放，不用当前公开master源码冒充此未知版本的行为。未来失败定位可在新任务目录保存实际worker状态并审计其AP/区域；调试局部输出不能代替完整设计的全部覆盖/连接/DRC/功能验证。


<!-- explicit-required-boundary-access-and-repair-partition -->

外部固定接口不能沿用标准单元多形状任选其一的访问语义。原native_geometry不隐式连接同名pin，但允许一个terminal的任一形状连通：92597中M5形状仍接通，M8形状孤立，旧目标报告仍pass。新增独立guard读取真实接触图的endpoint_component_count，对选中BTERM要求原/新均只有一个物理分量、身份与目标范围一致；不伪造导体。92606双原生读回确认实际无M8导线/通孔，92608/09真实输入正例与失败反例证明检查差异，不能泛称整个物理实现通过。

固定外部接入线必须进入明确不变量。令V为全部待验证迁移网络，P为已有真实固定外部接入的完整网络，R=V\P为本轮可变内部修复网络。由原生BTerm所有者与原接触图交叉求P，要求P与配置一致、必要电容问题网仍在R。准备时全部非R线编码FIXED，完整八表/所有导体几何与原输入相同后才允许进入route；只允许R导体变化，V全部目标接触与外部access仍须验证。这是修复范围分区，不是省略P或缩减硬件，也不代表正式冻结后可改M1-M8。当前真实输入V40/P2/R38，4个分区负例被拒绝；新92614完整布线及独立验收仍待终态。

独立native规则检查与router内部自计数分开保存。92607原准备输入与92597结果按同工具/同frame进行实际检查，保留type/layer/net/bbox原文多重集比较：0→28，新增28，无继承豁免。原始native0不是制造签核。后续仍须追踪几何/规则原因并修复，不能凭工具成功退出或改变检查语义清零。


<!-- native-wire-status-visibility-control -->

DRC差异定位必须区分导体变化与检查属性差异。92618在两个独立native进程只读解码原准备输入与失败结果的28个marker所属网络，输入ODB/工具SHA前后相同；27条非目标网络导体和FIXED路径类型/分层数量均未变，仅选中net157847路径数量随重布变化且两次都是ROUTED。这个控制排除了这27条网自身FIXED→ROUTED变化的解释，但未确定与其他目标网络的几何相互作用，不能以该诊断直接判继承或通过。保留完整28marker，后续应读取其邻域和规则对象，不修改导体/OBS来消除报告。实际结果留服务器索引。


<!-- native-DRC-neighborhood-and-grid-comparability-controls -->

输入为关闭的原生前/后库存、完整原始DRC标记、精确目标范围和实际单位；输出为按marker的原/新同层形状多重集、明确窗口内新增目标形状及检查上下文。算法流式读完所有native shape行，以0.5um研究窗口保留附近实际矩形，按net/kind/layer/box/via比较，窗口不是工艺规则，也未覆盖master PIN/OBS规则对象。92621实际28marker自身局部形状全部未变，仅1个窗口有新增目标形状且距marker980DBU；这提供下一步定位，不证明因果或合法。当前测量入口严格适配ERC失败来源，未声称通用于AUX或正式Block。复跑用对应封存spec/source配置及四核submit入口，替换输入路径/SHA、目标/marker数量、DBU与诊断窗口，不修改原资料。

独立检查的可比性除了工具/几何/芯片边界，还须记录粗GCELLGRID、guides及层范围。92626同实际整片DBU与默认检查的各自报告一致，但原/新网格原点/数量不同；0→28只是原生标记差，不足以直接判物理新增。92633确认当前0a4原生resetGrid/addGridPattern API；92634实际网格副本5384417行非GCELLGRID DEF逐行相同，check却因原有M1guide与层范围冲突退出，因此没有获得网格对照结论。92635只读比较原/移位网格时，两边在内存清除抽象规划提示并设置同一M1-M10检查范围/整片DBU，不改变导线、端点、阻挡或源文件；待实际结果，不以选择某个grid得到0报告豁免几何失败。正式Block需替换native视图和可比上下文，仍须全部范围/规则与真实负例，而非复用本诊断为通过证明。


<!-- matched-original-grid-marker-attribution -->

可比规则归因须区分真正项目原始输入、迁线后待修复输入和修复结果，不能把只在待修复输入复现的marker统称输入遗留。输入为三份真实视图及来源/SHA、实际grid/层范围/全dieDBU/抽象guides上下文；输出为精确native规则记录多重集的继承/新增/消失和仍未证明事项。只在新诊断副本调整粗网格，用完整DEF除两个GCELL记录外逐行相等证明未改物理，检查时统一无规划guides及M1-M10，不改导体/PINOBS。92635实际0→28证明网格本身影响报告，92636与待修复输入samegrid28精确相同；92637真正迁线前设计同grid27，因此当前是27已有marker、1新增net157847。这个结果不清除marker、不证明制造合法，也未放宽当前sourcegate的rawDRC0要求。

局部marker覆盖检查显示28个矩形都落在同net原生WIRE内，26个对应M3两via landing间隙；需要继续检查真实规则对象/表示和新增处，而非自动写falsepositive豁免。若使用现有合法via变体修复，需锁定技术定义、保持cut/相邻层接入、独立检查所有新增几何/引脚/非目标保持及完整RC/时序；不自行变更PDK。AUX已用同一流式诊断实现的auxiliary_slow适配器实际测量53个窗口，0新增目标形状，仍须92639完整上下文对照和项目原始来源验证。复跑使用各封存spec和来源commit；正式Block接入替换物理视图/规则/上下文字段，不能复用个案27/1阈值或网名当通用验收。


<!-- closed-full-source-local-via-candidate-screen -->

冻结前局部互连修复先筛查现有技术via，不能默认换一种外形就合法。输入为关闭的完整原生候选、唯一DRC失败、实际40网连接与外部BPin通过证据、via_definitions/layers/all shapes/master_geometry及明确替换位置；输出仅是空间筛查与拒绝理由。screen_native_via_enclosure_candidates.py校验原生source/sourcejob/输入SHA、真实via实例方向、两变体cut与相邻层完全相同，再流式检查改变M3的landing矩形与全部异网实际导体的L∞距离及互相间距；该层若存在master PIN/OBS则拒绝简化资格。参数来自真实native基本spacing，未覆盖完整EOL/PRL/复杂规则，不替代完整nativeDRC/RC/功能。92641实际两个既有变体使M3邻距只有70DBU而基本规则140DBU，6个形状冲突，拒绝且没有写几何。这是有效失败反馈，后续需要小范围via位置候选与所有影响层/真实连通筛查，不复制全规模重布以碰运气。

92614闭合副本已证明保留两条完整固定外部网络能恢复2个M8BTerm连通，全部40目标/非目标保持通过；仍有与原始matchedgrid对照新增1条net157847native标记，因此没有放行。AUX92639同物理输入grid-only0→53、相同grid前后53一致仅说明修复前存在，不能错误套用VECTOR已核实的27输入遗留阈值。正式Block替换native源/接口/技术字段并重跑这些证据；未知规则或局部筛查不通过即保留未验证，不改PDK、不绕开sourcegate。

## 局部过孔位置修复与独立资格门槛

输入是完整原生数据库、实际工艺via/layer定义、来源作业与SHA、目标网络/外部接入清单、同上下文原始DRC记录。算法先枚举制造网格上的小范围移动，筛查M2/via2/M3/via3/M4邻距、同网cut与不变导线的正面积重叠；仅对通过初筛的候选进行一网DEF导入。普通导线和单元不改，限定精确的三层via形状变化。原生DRC与原始记录按完整身份多重集合比较，不能用计数相同代替记录相同，也不能把未知标记直接归为继承。

92642实测10候选/6初筛通过，92644选择一个via向左35nm，完整八表/非目标保持、40网/两M8接入和新增原生DRC为0通过；92645独立适配器校验完整来源、同原始27条记录、实际差分及失败反例。旧零DRC来源门槛保持不变；local_via_relocation_v1仅接纳有精确原始记录证明的宏级候选，不等于整机验收。

成功的几何检查之后必须继续RC/电气/时序。92646/47证明即使没有新增失败身份，190个原有时序端点和27个电容超限点仍可变差，故候选不能冻结。完整失败清单保留，不设置随意质量容差；路径报告的格式一致性阈值也不能转为验收容差。92652暴露总线端口精确查找问题，保留失败并修输入适配，不通过删掉该端点获得通过。复跑以封存spec/source_revision为准；正式Block替换数据库、合法via和端点字段，不能固定使用本案网名、坐标或27条豁免数。

## 用真实失败反馈驱动少量局部修复

输入是封存的完整端点恶化清单、三版ODB/SPEF、精确端点身份、原生几何和真实Liberty。先从最显著的少量端点诊断，完整190端点/27电容清单不变。报告器复用已闭合原始报告；从完整native负端点清单取精确STA pin对象，避免总线转义的端口查询歧义。报告中Endpoint头可能是寄存器实例名，须另查数据路径的真实D引脚，不能直接字符串相等或删除端口。六条路径逐段按真实Liberty区分CK-to-Q、cell、net；寄存器到外部输出单独建模，不虚构capture FF。只有引脚/master顺序一致才按单步相减；打印一致性阈值仅检查重构，不是质量容差。

92656/58/60实际将最大的28ps恶化联系到net83203的30ps网段变化和明显新增耦合，并识别_173404_与net157645的耦合变化。selected_net_spef_capacitance.scan及slow_path_net_geometry.scan被复用，三版source/endpoint/单位均有SHA；矩形长轴之和不等于唯一布线长度，寄生关联不等于孤立因果。由诊断提出修复范围，而不是反复重布整个宏。

批量via筛查复用native_via_relocation_screen，使用一个完整shape流覆盖53个实际标记窗口，输出每个候选、阻塞和明确CLOCK类型。默认普通WIRE接入规则保持；额外显式模式允许与不变同网via landing正面积重叠，仍完整检查cut邻距和异网导体。旧48/53与新53/53的实际报告按候选身份比较；后续必须执行完整原生DRC、所有61相关网连通/异网接触、八表/非目标保持、精确via差分及CLOCK RC。不是新增53个单元，也不改变PDK。92663字段类型误用、92657竖线覆盖识别失败均保留。

路线复用算法将实际原始完整信号路线、层/via映射、轨道偏移列表作为输入。检查真实层方向与via上下层兼容；在原上层线两端调整同网连接，输出一网NETS-only DEF及明确预期形状，对完整当前非目标导体做简单间距筛查。92665实际9候选中1个初筛通过，0偏移11冲突；选择3.2um偏移的完整原始路线下移M7，仅是待原生验证的proposal。停止条件是没有合法候选或完整物理/质量失败；不能以文字DEF生成完成为布线通过。此方案可接正式Block的实际工艺层、信号网、接口和物理视图；当前仅支持两via端点的一段原始水平高层线，其他拓扑明确拒绝，不宣称任意Block通用。

declared_macro_repair_v1已实现两种明确类型的共同来源资格适配：自建AUX要求原生0标记，VECTOR要求与真正原始标记逐条一致；均检查实际闭合作业、八表/非目标保持、完整目标分量、M8边界和精确声明差分。当前独立资格与后继完整RC/端点/电气对照仅已排队，不能报告为已验证。旧complete_wire_reroute_v1和local_via_relocation_v1门槛保留，measure_selective_auxiliary_rc仅增编译声明的producer类型，不放宽模型、资源、约束或质量。

实际复跑入口为各driver的封存spec.json/source_revision.json；源码、配置、命令和输入SHA均绑定。需要新实验时设置新driver/output与固定commit后由submit.py申请4核；不能原目录覆盖重跑。当前通用方法仍是案例辅助适配器，非完整LLM编译器或最终冻结流水线。

## 完整物理资格后必须继续真实质量反馈

declared_macro_repair_v1已在两种完整宏修复上实际验证：自建AUX要求全层原生0标记，VECTOR要求与真正原始27条记录逐条一致；两者都独立核验实际COMPLETED0/4CPU、精确源码和输入、全部八表/非目标保持、完整目标分量、M8接入、精确声明差分，分别11个真实报告变异负例均拒绝。AUX是53个via/159层形状、全部61网，VECTOR是一个完整网/58形状、全部40迁线目标与两M8访问。各自资格只覆盖完整宏的声明范围，不能拼成完整共同底座。

同一个measure_selective_auxiliary_rc和compare_selective_auxiliary_electrical入口完成两宏新SPEF、全量max/min负端点、真实有限slew/cap引脚身份与旧参考的对照。VECTOR的关键额外恶化28.407ps→3.607ps说明该次路线策略有效，但191端点/26cap恶化仍拒绝质量采用。AUX虽native0且WNS改善，305setup/1hold/31cap仍变差，5635setup/30hold/1087cap失败保留；自建辅助实现不允许套用输入继承豁免。没有放宽3ns、增加pipeline或用未定义外部rise/fall/C=0掩盖问题。

saved_signal_restore_v1是共同路线试改框架的输入适配器：从实际耦合增加选择候选aggressor，绑定保存路线来源与当前限定修复祖先，检查完整net成员/引脚位置、技术via定义、die与资源相同，只提议这一条完整信号网。92678实际恢复net157645时与固定net151699发生6处M3接触，正确拒绝，无ODB试改。conflict_guidance据真实冲突自动导出单一水平带及X范围，生成±1至4个真实pitch的节点偏移；所有相接低层WIRE/via节点同步变换，M1和pin接入禁止移动；先用实际native475形状核对不变DEF的几何重构，再检查当前全部非目标导体和同网cut。92679/92681实际完成8/16个候选筛查，全部0合格，未执行ODB试改或质量修复。AUX路径诊断复用同一入口支持实际pre_repair/repaired两版；92692因工具字段适配失败（EDA前），4a000696修复为源模型实际工具/SHA后提交92694，待读回终态；不伪造第三个项目原始视图。该适配器明确只支持有限水平局部冲突，其余拓扑拒绝，未宣称通用LLM适配。

### 最慢路径切换、候选反馈与相邻质量检查点

输入：来源闭合的实际ODB/SPEF/SDC/Liberty/完整端点census及工艺几何；输出：有限路线候选、真实独立物理门槛、提取后完整端点与按引脚质量变化、失败原因。saved_signal_template_adapter共用模板/坐标/via/实际形状roundtrip；案例仅更换提名证据和配置。AUX的own_auxiliary_zero强制native0，VECTOR的original_record_multiset逐条保持原27条，不能互相套用豁免。

saved_route_conflict_closure用实际完整导体流构建阻挡图，限定普通信号候选池/保护网/数量与比较预算，闭包碰到保护网即拒绝；92715实际8896677行/246876比较，32条采样对标完整标量，并复现750形状/9冲突，7网闭包仍被保护网挡住。component_trunk_adapter保持真实via锚点，只换旧M3冲突岛7条普通线；92717九项均失败，最好485形状剩一处M5交叉。route_crossing_bridge_adapter精确复现该基准，仅替换冲突区段；92723三项M6桥被固定M6长线挡住。92725使用真实两平面阻挡、M5/via5_0/M6竖spoke/via6_0/M7横桥，9项3项初筛通过；随后92727/28才实际写ODB并完成限定物理来源检查。**筛查合格与实际布线是两个阶段；实际物理来源合格与RC/时序合格又是两个阶段。** 全程不删除保护线、PG或器件，不占定制M9/M10。

measurement_checkpoint_context要求相邻测量配置的SDC/RC/原参考census/坐标框架精确一致，3项实际上下文负例、同数异名负例检出；同一compare_selective_auxiliary_electrical入口已实际复用AUX92718与VECTOR92731。原始参考、修复前同宏参考和相邻候选参考同时保留，不能只选择变好的WNS指标；任何负数恶化都保留，无数值豁免。

path_sequence_alignment只在同一有证据的上下文按真实pin/master/方向/转换沿及前驱对齐。跨原完整core与自建AUX的symbol诊断必须显式使用cross_boundary_symbol_diagnostic类型，保持原各自SDC和未归一化/未状态等价标记；92733/34实际4条路径及破坏负例通过，但路径不同、匹配arc为0，只能比较观测组成，不能宣称因果、继承或整体等价。

失败反馈：局部路线恢复后完整质量仍不合格，且跨原实现数据路径含约0.33ns组合单元与0.18ns网络延迟差，因此另在同floorplan/0.35密度/3ns下评估现有placement repair；仅自建未冻结AUX标准单元允许调整，原四核心与存储/接口约束保持。92735真实来源比较代码错误在native前被拒，d5fda98按路径+SHA修正并42单测通过；92736新快照运行。停机条件仍为实际终态/预算失败，不通过放宽时钟、减小硬件或额外流水改变目标。该分支若完成也须重新CTS、详细布线、实际RC、完整功能与整片检验，不能把placement估算当作验收。

新增适配经验：已封存selected native报告通过selection中的端点身份而非位置复用，只有ODB/SPEF/Lib/SDC/RC/tool完全相同、原阶段成功且报告hash封存才允许使用；原始完整端点census保持权威。输出网新增适配显式核对native BTerm名称、方向及实际SPEF *P，原内部网模式仍严格；六个解析负例检出。

native_def_signal_paths把本次真实FIXED路径的端点延伸0、同一路径多via后的层转换及换行，展开为可逐条核对的记录。普通线按真实端点延伸重建矩形；必须回对完整原生route形状Counter，92745还对原已接受的501条内部形状回归。分段track以实际三个区间的并集限制候选，不能从pitch推造不存在的坐标。所有原core route和M8接入导线必须保持；4个真实候选破坏负例分别检出删原线、改M8、占M9和via越界。完整导体标量筛查仍不能代替native DRC、实际BPIN连通、独立源资格和RC/时序。后续控制器需显式支持边界网及全41目标范围，当前未实现/验证该物理准入。

本轮实现纠正：边界输出网已由显式task_added_output_access_v1适配器处理。必须绑定真实单驱动BTerm、真实失败寄生/端点证据、原始route子集、全部BPIN与M8导体区域，目标40→41受保护；默认内部网规则不放宽。写DB前强制闭合输入破坏测试和两条旧模式回归，写后新进程核对全部41连通、八表/非目标、原DRC逐条及预留层，再由独立资格检查器执行15项真实报告破坏负例。准入成功只证明物理来源，实际新RC若任何端点恶化仍拒绝；92760/63物理通过而92764/66质量失败是实际反例。未来其他端口、Block或技术需各自输入适配，不外推全部支持。

新AUX CTS逻辑检查复用同源库资格：先保留严格图差异，再仅使用实际库已验证的布尔引脚对称与状态驱动族归一化，比对全部状态输入/公共输出锥，并真实反相状态输入检验检查器。92771未调用SAT、不证明上游RTL或四态/SDF，最终网表变化后须重验或精确证明逻辑网表身份。完整新路线未闭合前不得将此证书转写为实际布线/时序/完整case验收。

本轮新增可复用适配：output_original_tap_adapter从真实原始via/导线和保留上层stack的坐标枚举有界同Y低层tap，层名、via、跨度和数量来自配置；当前仅支持明确的连续两级上行via及水平原导线。替换集合必须严格等于任务新增的那一条接入wire，全部原route、两BPIN和M6以上已有栈保持；实际native形状往返、全导体/cut预筛、破坏测试、真实ODB/41网/独立来源及实际RC各自验收。92784是过严规则误拒绝via落点的输入适配失败，92785修正；92787/88物理通过、92789/90单端点改善但全量质量失败，说明不能用局部改善接纳整个宏。算法实际支持当前case形状，不外推任意Block。

closed_native_tile_checkpoint复用原扫描器的validate_batch，逐条实际报告、精确覆盖box、前后DEF和完整source contract核对已闭合区域；真实旧16区/8破坏测试通过。恢复器仅在精确afterany终态、同代码/helper/source合同下才让原引擎重新验证并续查未完成区域；完整前驱无操作跳过，不把旧pilot或部分覆盖当当前全片通过。当前条件续查尚未执行。最终网表身份适配器实现以完整实际.v和native八表字节一致复用现有状态证书，不是跳过功能证明；实际新输入/消费分支待闭合验证。

当前检查点：2026-10-28T13:14:49.821883+00:00。Issue55/PR58、task/55-full-block-integration；负责人huangpingyang04-lgtm。完整目标保持：openTPU small（全部33个内部SRAM）和llaccel_core（EPILOGUE_FUSION=0、DMA_MAX_OUTSTANDING=16，外部16个SRAM bank/DRAM/主机在测试环境）共用同一冻结底座。阶段一含遗留输入问题已交付，二/三未验收，四未执行；主要候选1/3未冻结。按现行Issue55，冻结后M1–M8、资源/位置/朝向/内部连接/PG/clock/接入点相同，仅M9/M10及真实via8_0/via9_0定制；M11/M12后备未启用。当前修改仅本人冻结前派生副本。

**新实际结果：VECTOR原M3引出方案物理范围通过，并改善一个端点；整体质量仍未通过。** 先前M7输出支线92760/63物理检查通过，但92764/66实际测量使目标再恶化0.517586ps，d32版本已拒绝。新方案从原实际M3导线选有限接点，保留全部原15条内部route、两处BPIN、完整M6/via5/via6/via7/M8上层接入，仅把本任务新增一条长M5wire替换为M3wire及真实via3_2/via4_0。坐标由原生记录生成，非程序内手填；此为案例输入适配，不是任意Block通用成功。

92784因过严保持规则误拒绝必需的via4 M5落点，在全导体扫描前失败；原记录保留，不作为物理不可行结论。d498修正为保留全部原线和现有上层via，允许明确声明的新通孔落点。92785真实源DEF/native与原501内部形状回归、完整导体/cut标量预筛1/1及4破坏负例通过，仍仅提案。92786完整41目标/原线/BPIN/M8保持准入和4实际破坏负例通过。

92787随后实际生成并在新进程读回ODB：精确33route+2BPIN=35形状，全部41相关网、3处真实边界端口形状连通，异网接触0；八类资源表和全部非目标保持；M9/M10预留为空；原始27条native DRC逐条保持、新增0/遗漏0。92788独立来源资格与15实际报告破坏负例通过。**这些只接受限定物理来源，不是零DRC、制造签核、共同底座或功能/时序验收。**

92789原3ns/同库/同RC/SDC/提取范围实际提取：setup WNS−4.173063790419197ns、native TNS−1057.7092852062ns，287负端点；hold WNS+0.02439915005763723ns/负端点0；cap56、slew0，fanout无有限约束不算覆盖通过。92790复用同一比较器分别做原始/历史postM8及紧邻2bf完整端点与逐pin ERC对照：相对2bf无新增/消除/进一步恶化的负端点，只有vec_rd0_req[24]改善0.489164278ps；cap清单与打印精度也未恶化。相对真正原始仍200setup/26cap项恶化；该输出额外恶化仍3.118172475ps，当前最差额外恶化转为wr_data_r[95]/D的3.131717196ps。**有实际改善，但不能将当前宏或整机质量写成通过，也未并入共同底座。** 旧全局WNS相同不代表端点相同，保留所有严格数值差异，不用容差豁免。

新ODB：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/vector-output-original-tap-physical-r01-4c-01/patch/patched.odb，SHA-256=e23827eea06a8f74bbab2f49ed87d75d2bb83741a829b5735de0a28454f94102。实际SPEF426150353字节，/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/vector-output-original-tap-RC-r01-4c-01/extraction/extracted_coordinates.spef，SHA-256=94bfcbb5b7e41942e98fe4093959b9f248ad8489a213af943359f5f652a3f56a。92801按全清单选新最差wr95，精确复用原始/历史两份封存路径，实际只测当前e238，已闭合；新的路径组成分析状态见索引，不预先宣称因果或修复。

**新版AUX完整路线与后续检查。** 92750为RUNNING。实际完整DRT子步骤运行结束，已观察到独立fresh DRC0、放置0及VDD/VSS各自原生连通通过；仍须等完整native库存和输入闭合收据，不能以子步骤或日志替代生产者终态验收。原完整规模、3ns、M8上限保持；updated_clks.sdc4.6506仅诊断文件，DRT实际读取5_1_grt.sdc为3.0000。旧place off/route on与新place on/route off不是单变量A/B。92796全信号网独立连通为PENDING；92797真实最终.v字节+完整8类native表与已资格CTS身份比较为PENDING，仅完全一致才复用92771限定状态证书，否则须新证明。新身份适配器已实现，18项原来源守卫在e771快照通过；e1d只纠正不同封存源码路径的SHA匹配并要求准确5种破坏角色，实际新分支消费仍待真实输入验证，不把写好脚本当通过。

CTS92746放置/PG/资源检查与92771全部65545状态/168074锥规范化匹配0差异继续有效；严格图92769的3696差异失败保留。该证书只适用映射网表→本CTS、相同命名初态与原存储模型；没有本支线SAT、上游RTL全等价、四态/SDF或最终完整case验收。新路线尚无实际RC/STA结论，不能借旧AUX结果接纳。旧AUX5635setup/30hold/1087cap失败、原完整core比较边界未归一化也继续保留。

**整片检查和无损续接。** 92538为RUNNING，本次2592/4096区闭合，仍仅部分覆盖，92547/48依赖保留。92791用真实历史92363的16区干净检查点、12个原生线程对照报告、全部实际tile/前后DEF哈希，检出8种破坏；仅为检查点资格，不是当前5429源或4096全片通过。92793为PENDING，只在92538自然结束后决策：已完整则跳过全部native查询，干净partial才核对当前源/引擎/helper/box合同并让原扫描器重新验证源/clock/control/12夹具/canonical DEF后仅续查剩余区域；非零marker、坏检查点或来源变化拒绝。没有停止现有作业、没有重复已闭合区域，当前尚未执行真实续查。

14059固定连接仍是方案，尚未完成实际低层导线；每案例841闲置扇出未完成。旧92508 open20例/87160行/2317514字段、92505 llaccel六组180任务/243883行/17769493字段的有限完整active+idle回归仅对应当时版本，不能替代新AUX、最终物理网表和两个最终案例。共同PG/clock/固定连线/全局检查/最终功能电气、冻结与两个完整案例定制仍未完成。外部clock rise/fall及open37常量输出负载用户确认未确定，保持null而非0。

**资源与证据。** 全部新作业4CPU、native≤4、BLAS1；单线程步骤如实记录，不声称4倍提速。92787 wall1749s/CPU2441.397s（均值1.396核）；92789 wall201s/CPU252.113s（1.254核）；92785 wall78s/CPU76.182s；92791 wall2s/CPU0.312s，主要读既有文件；92790两项报告检查在同一4CPU作业内串行完成。运行中账目未结算，不拿0CPU字段当真实利用率。

服务器根目录：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z。归档源码dc8d4e9090ffd8a78795eeed1f2e487de4a31597；每作业各自source/config/tool/输入和成果SHA均在索引。最新索引/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261028T131449Z/milestone.json，SHA-256=4bce46faf11f25e8834b16ec20b0227fd93d3f2c523e5e62bf9b0bc868d9008d。上一已读回GitHub提交c1d97b05f723ab21a78d1f68a8835da9d2aded7b、PR58/Issue55评论6468891719、结构CI40687269155 success，本次上传以新交付回执为准。仍仅上传六份既有文档和小索引，运行代码快照/大DB/完整日志/工艺留服务器，非全部算法源码交付。登记沿用管理中心PR5 pending（未重核），看板unverified/同步pending（无board配置/已验证Projects接入），审查人待指定。整体in_progress，不合并/关闭/标done。

下一步最小动作：从新wr95真实组成证据选择有依据的有限修复；读回92750实际闭合，完成独立全网与限定状态资格后做新RC/电气及对应完整功能；保留整片检查/条件续查和实际固定布线主线。仅有单端点改善不能缩小两完整案例目标。
