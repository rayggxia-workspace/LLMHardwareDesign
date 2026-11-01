# S SRAM 独立物理版本

## 当前状态（2026-11-01T20:44:31+08:00）

**完整S尚未布局布线完成，没有完整S最终GDS。** 保留非SRAM S，当前仅推进一套新49级控制候选的真实物理实现，不改主线程/其他宏任务。

原9级银行接点修正后，完整未放宽ORFS Nangate45 DRC=0、晶体管LVS明确匹配，原始全量报告已实收并核对远程SHA，见[bank-eco-001](bank-eco-001/receipt.json)及[接收索引](bank-eco-001/download-index.json)。但原9级晶体管5ns写1/读1失败；真实探针显示写使能在字线建立前过早结束，不能因DRC/LVS或行为模型通过而使用该电路。

94697/delay-probe-002的49级SPICE-only候选保持原5ns输入和原测量，仅更换延迟链：8项Q/Qbar读写及2项输出检查全部通过，耗时706.827秒；[原始日志](delay-probe-002/stages49.lis)和[判定](delay-probe-002/stages49.json)。这还不是匹配新版GDS或完整时序库。31级继续作为诊断收尾，不推进第二套物理实现。

94706/generate-008已实际运行：从完整OpenRAM编译器重新生成49级电路/版图和真实ngspice库，TT/1.1V/25C，16CPU分配、8线程KLU配置。新隔离覆盖逐文件核对仅stimuli.py变化，修正cwd/读取本地线程初始化、选KLU、移除ng_nomodcheck以保留BSIM模型检查，未改刺激/原测量/容差；[实际启动与覆盖回执](remote-launches/generate-008/submission.json)。当前仍在构建新版物理数据，无完成结果。94712/actual-model-008真实afterok:94706，等待实际生成模型后做三初态存储/完整供数回归，不提前认定通过。

原94648及94670/94672/94673/94674旧9级链已按用户/目录/作业名核验后退役，见[回执](remote-launches/control9-retirement.json)。依据是已证实的写入失败及49级通过、新实际生成启动，非因沉默或耗时；10ns在途输入/日志保留，不称其完成或失败。后续必须绑定新实际五种视图、重做接点ECO/完整DRC/LVS，再执行完整S综合/PG/CTS/布局布线/RCX/GDS及最终STA/电气/引脚/功能/严格宏边界等价，不能复用旧银行来假装新版电路。

宏内部时序仍受KLayout wire PEX未实现、上游HL复制LH等限制；外部SPEF不能消除，不宣称300MHz硬宏最终资格。已发布8f49e99b与归档a875f103整树一致；仅独立分支正常快进，未force。Issue155 in_progress，PR158 Draft，审查人待指定；登记pending、看板unverified/同步pending，管理员待指定。

## 历史诊断：20:21 CST 控制诊断与并行候选

[write-controls-001](write-controls-001/timing.lis)的真实5ns探针：40.5ns输入已锁存到约1.1V；43ns字线约0.406V而写使能只剩约0.104V；44ns字线达到1.1V而写使能接近0。写1存储节点仍约3μV。提示控制窗口与字线建立错位，属于待检验的电路假设，不能仅归咎于外部周期。此目录receipt的passed仅指求解器执行，不是读写通过。

94697/delay-probe-002分配16CPU，同时运行31/49级控制延迟的两个SPICE诊断（各8线程KLU）。电路仅替换延迟链子电路，其余电路、输入与原测量保持；尚无候选对应的新GDS，不能接入完整S或冒称LVS匹配。94696/delay-probe-001因诊断脚本漏.ENDS立即报错，日志保留；b3d888cc补回并加入子电路配对守卫后提交94697。94697新增非侵入边沿探针存在DUT前缀错误，原功能测量不受影响；代码已修复，当前运行输入不改、不为此重复计算。

后续生成器已准备显式控制级数、TT/1.1V/25C角、8线程参数。新隔离运行时覆盖只修正ngspice cwd/本地初始化、选KLU，并移除上游ng_nomodcheck以保留BSIM模型检查；实际旧源的精确匹配/语法验证通过，尚未执行新物理生成。不得把诊断成功直接等同于实物、完整库或完整S成功。

以下按时间保留过程记录，历史排队状态以本节为准。

任务：[Issue #155](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/155)。负责人：YUZE-LU。

本次验收包含完整 S 的远程布局布线及最终物理结果，不能以本地接口仿真结束。
保留标准单元 S、原供数器和其他宏的现有结果与任务；四个256×128bit真实1RW SRAM替换16KiB有效载荷存储。

原始本地接口证据位于[143/s-sram-variant](../143/s-sram-variant/README.md)：严格lint及三初态存储/完整供数测试通过。原S接口源在本地基线`9a248b38`与PR144远端基线`d1f26884`逐路径比较无差异；本分支仅重放独立SRAM修改，不向远端发布未关联的主线本地提交。

## 远程执行记录

根目录：`/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155`。
固定ORFS镜像SHA256：`49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a`。
EDA仅在Slurm分配中执行；任务名为`yzl-sram-*`。单个SRAM银行生成一次、实例化四次；在真实视图产生前不启动依赖它的P&R。

| 目录 | 作业 | 实际结果 |
| --- | --- | --- |
| probe-002 | 94535 | COMPLETED0:0：Python3.10.12/KLayout0.30.12/Yosys0.68+post；无OpenRAM/ngspice；平台SRAM GDS列表为空 |
| generate-001 | 94536 | FAILED2:0：归档导出CRLF使bash拒绝pipefail；已新增s_sram目录LF属性 |
| generate-002 | 94537 | FAILED1:0：计算节点DNS不能解析软件源；改用离线包 |
| generate-003 | 94538 | FAILED1:0：跨平台下载未带Python3.10条件依赖exceptiongroup；已补齐并重新封存离线包 |
| generate-004 | 94540 | 工具准备阶段CANCELLED：在进入SRAM编译前补齐显式OPENRAM_TMP/TMPDIR目录约束；已安装Python依赖复用，未取消其他任务或已运行的SRAM编译 |
| generate-005 | 94543 | 独立c64/16CPU；离线依赖哈希与精确版本检查通过、ngspice45实际编译成功，真实SRAM编译已开始；最终结果待接收 |

离线包v2：`/public/home/yuzelu/opt/eda/issue155-offline-v2/offline.tar`，SHA256=`8cbdf1046ed3c101429de04790caba6184e92fe32d7b624020cd6dee2e63d886`。
OpenRAM1.2.48、numpy1.26.4、scipy1.13.1、scikit-learn1.5.2、coverage7.6.1及官方ngspice45源码，使用包内逐文件SHA256SUMS核验。
工具目录：`/public/home/yuzelu/opt/eda/issue155-sram`；不修改公共镜像或其他任务的工具。

## 当前验收边界

真实宏配置为FreePDK45、TT/1.1V/25℃、`analytical_delay=False`、显式ngspice/KLayout、保留临时日志。
准备阶段原始回执、日志与Slurm终态已实收至[remote-preparation](remote-preparation/receipt.json)，逐文件SHA256保留。尚无真实SRAM完整视图、宏DRC/LVS、完整S P&R或300MHz物理通过结论。工具安装、宏生成、完整宏物理验证分别记录，不能相互替代。

完整S物理入口为`project/experiments/s_sram/physical.py`，需在分配内提供真实`generation.json`且五种实际视图哈希一致。它排除仿真替身，检查四个真实银行实例，固定银行与M10内部接口，沿用300MHz边界/原生输入保护/电气修复预算，执行新综合、PG/布局/CTS/布线/RCX、完整GDS合图、完整GDS DRC和版图渲染。当前仅完成Python语法检查，尚未运行该流程，不代表物理通过。原生独立检查、最终功能和严格等价仍为单独验收项。

完成后需要接收真实宏V/Liberty/LEF/GDS/SPICE、完整S最终V/SDC/DEF/ODB/GDS/SPEF、版图图像、面积/时序/电气/DRC/连接证据、SHA256及最终功能/等价检查；若失败保留原始报告并说明具体障碍。

## 已提交的后继及中间几何

- 原94551/`physical-001`仅在PENDING状态取消，由94581/`physical-002`替代，源码`313be504`，仍`afterok:94543`。补上OpenSTA兼容的signed元数据处理、逐单元/逐引脚位重读证明及一位变坏的拒绝控制；未中断宏生成。
- 实际生成模型功能作业94555，`actual-model-001`，归档源码`2af5282d`，`afterok:94543`；使用生成器实际Verilog，保留默认3ns读延迟/1ns输出保持，并显式推进仿真时间。较慢时钟下检查协议与数据，不能作为300MHz通过证据；可与P&R并行。
- Git HTTPS push连续reset后，已通过本人GitHub API发布相同源码树`4e062cd8`，与归档源码`2af5282d`整树严格一致，见[publish-functional-tree.json](publish-functional-tree.json)。仅对齐本独立分支，未改主工作树。
- 检查点`checkpoint-002/intermediate.gds`位于本任务远程根，14,826,244B，SHA256=`8976d2910679b46cc4866f8a65fbc0ad934800426bef52550f8528f038542e2d`，140层次单元、0.0005μm数据库单位。读取前后源文件与快照SHA完全相同、GDS ENDLIB完整，KLayout可读并渲染。当前外包框`(-44.055,-9.85;405.47,108.225)`μm，为最终坐标平移/电源完成之前的中间布局，不作为最终宏边界或合格GDS。

![SRAM中间布局，仅过程证据](intermediate-bank/intermediate.png)

读回元数据与图片哈希见[checkpoint.json](intermediate-bank/checkpoint.json)。真实几何已存在；当前仍在宏内布线，不能因此宣称宏DRC/LVS、表征或完整S P&R通过。

草稿：[PR #158](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/158)，base为PR144分支。侧会话调用应用附件挂载返回`thread not found`，在线PR可用；未改其他线程附件。最终审查仍待指定。

规则版本：rayggxia-project-collab1.0.0。项目登记复用已有pending证据；本地未配置config/board.json，看板事实unverified、同步pending，管理员及审查人待指定。PR158保持Draft，Issue保持in_progress，不标done。

## 2026-11-01 17:30 CST：原生接点候选和最终接收

94543默认周边逃逸布线继续运行。源码8292bbf7增加显式`--internal-pins`，同一256×128bit/1RW/四实例规格，仅关闭可选的信号周边逃逸；电源布线、DRC/LVS、真实ngspice表征全部保留。已查实际生成器route_layout调用顺序，该选项不关闭内部功能连线。能否接入仍由实际LEF/布线/DRC决定。

- 94582，`generate-006`：独立c64/16CPU，原生信号接点，复用逐版本核验的工具，实际配置单独保存。
- 94583，`physical-003`：源码8292bbf7，afterok:94582，生成成功后新做完整S P&R。
- 94584，`actual-model-002`：源码8292bbf7，afterok:94582，与P&R并行检查实际模型的协议/数据。
- 源码3b1b9585新增`inspect_final.py`及`run_actual.py --physical`。分别独立读取真实最终ODB/Lib/SPEF、精确300MHz边界并检查时序/电气/RC/PG/引脚/DRC，以及导出所有信号单元（含真实SRAM和保护负载）重跑完整S供数测试。仅完成Python语法检查，尚未运行。

当前无完整S最终GDS或通过结论。两种引脚策略最终仅收敛一种实现，原S和其他宏保持原状。

## 隔离的生成器性能处理

非阻塞调用栈采样确认94543位于supply_router→graph.remove_blocked_nodes，读取到140个电源接点中已有11个完成；94582同样进入图清理。没有进程等待外部工具、宏无GDS或内存不足的证据。

94592/`generate-007`（源码43a26058）在独立工具副本中仅替换graph.remove_blocked_nodes的列表删除循环：保持原来的逆序邻接处理，最后原位线性过滤列表，不改变搜索图/路径规则或原邻接方法。实际源方法对照1000组图，所有剩余节点/邻接顺序及列表对象身份一致；30000节点微基准原2.9396355748秒、线性0.00517403055秒，仅代表该循环。逐文件比较确认安装副本仅compiler/router/graph.py变更；原安装及两个原作业未改。完整包哈希清单及原始前置检查见[graph-overlay.json](remote-launches/generate-007/graph-overlay.json)。宏本身仍须实际布线/DRC/LVS/SPICE表征通过。

94593/`physical-004`与94594/`actual-model-003`依赖afterok:94592；94595/`final-003`依赖afterok:94593，仍为20CPU内16+4并行接收/最终功能。原默认引脚链的最终接收为94586，原生引脚链为94587；所有后继尚未运行，不作为通过。完整提交脚本、源码commit/归档SHA和原始诊断见[remote-launches](remote-launches/received.json)。

## SRAM边界形式检查的实际前置控制

`formal_banks.py`将四个实际银行的全部时钟/控制/地址/写数据提升为待比对输出，读数据为任意独立输入；并非凭银行名字或把未知读数据接零就宣称等价。最终ODB功能仍保留全部信号单元，形式视图仅有单独证明的无函数ANTENNA_X1投影。实际最终S证明94599/`formal-001`（源码d1ef7706，afterok:94593）尚未运行。

在真实Yosys/Kepler中已执行`formal-control-002`：四银行符号夹具、正例插入BUF、反例地址位反相/银行时钟接错/读响应换源，正例明确UNSAT/IDENTICAL且全部输入输出匹配，三个实际反例均明确检出差异。工具对差异也可返回0，因此接收器检查正面判词和完整边界计数。所有cut前后结构重读逐位一致。原`formal-control-001`正例为同一带BUF图的恒等对照，也通过；002增加直接地址与缓冲地址之间的真正正例。原始脚本/正负网表/工具日志/接收回执见[formal-boundary-control](formal-boundary-control/receipt.json)，这些只是检查器控制，不是最终S形式或物理合格。

## 2026-11-01 18:16 CST：真实银行布线与独立晶体管LVS

94592的银行布局布线实际完成，Routing耗时1314.4秒。已生成真实14,802,360B GDS，SHA256=4c92003044fc72e407b978ae26139e7b7d5b1c49e4e6adba172bb610d6893f4c；晶体管原理网表2,667,547B，SHA256=1f25c1f7fd6e231ff98c35c384120e721222b811279af27364aa5bd1e73fe4f3。当前是验证使用的routed视图，最终输出银行视图仍待产生并核对身份。

在同一分配的独立4CPU step并行执行unchanged FreePDK45 KLayout LVS，未传connect_supplies，显式CONGRATULATIONS/Netlists match且无ERROR，命令0:0、36.62秒；实际LVS数据库16,264,161B及提取晶体管网表3,276,686B留远程。小型原始回执、日志、脚本及规则文件已接收到[macro-lvs-001](macro-lvs-001/receipt.json)。这是该份routed银行的真实晶体管连接通过；DRC、时序表征、最终银行文件身份及完整S P&R仍未通过，不转移资格。


## 2026-11-01：银行原生DRC通过，时序表征调用修复

`generate-007`完整原生OpenRAM DRC已结束，XML实际items=0；随后编译器自带LVS明确Netlists match。失败发生在真实ngspice表征入口：上游stimuli.py无条件激活不存在的Conda目录，忽略use_conda=False，未产生timing.lis，因而不能视为库生成成功。原始DRC报告/日志和失败日志见[native-bank-drc](native-bank-drc/receipt.json)。原作业94592实际FAILED，其依赖94593/94594/94595/94599无可满足的成功前置，已清理这些本任务未运行的排队项。

以已布线并通过LVS的真实GDS/SPICE为输入，独立`views_from_routed.py`重建并核对表征电路，保留原生实际LEF/GDS，仅重做模型和真实ngspice库。隔离的simulator_overlay.py只让启动器遵从use_conda=False，不改变测量、器件或验证规则；原安装和运行中的基线不改。

OpenRAM库写入默认还会添加标称1.0V及其他角点；新入口显式use_specified_corners=[('TT',1.1,25)]，并记录有效配置。views-001/94625因此取消，替代views-002/94628；其依赖physical-005/94626也取消。views-002/94628与views-003/94636均因重建电路与实际GDS的LVS不匹配被真实拒绝，未生成可用库。额外核对发现原生最终输出GDS与已验证暂存GDS只有时间戳变化；views-003加入逐记录流比较，只归零BGNLIB/BGNSTR的24字节时间戳，其他全部字节须一致。实际两文件归一化SHA均cae9c593f708935096ae8c8d64ae9307aba07ccf86381dca1b97fa0cd3d9a937，141条时间记录；保留实际原始SHA，不转移到不同几何。完整S新链继续基于此输入建立，尚未完成。

额外完整ORFS Nangate45银行检查`macro-native-drc-001`原先作为94592的重叠step运行，父作业在表征失败后自动终止该step，因此不认定通过。独立4CPU Slurm作业94627/`macro-native-drc-002`使用未修改完整ORFS deck（FEOL/BEOL/OFFGRID/ANTENNA全开）重跑，不与父作业生命周期绑定。

时序证据限制：当前OpenRAM的KLayout PEX入口未实现；实际晶体管网表没有显式连线R/C。真实ngspice库属于原理图级表征，不是SRAM内部布线寄生后的时序证明。完整S仍须实际外部RC提取、精确300MHz时序/电气/PG/引脚、最终功能和严格银行边界形式检查；这不能替代内部PEX。保持未合格，不能将其描述为已完成300MHz硬宏验收。


### 表征电路身份的真实负例与修复候选

views-002与003重建采用netlist_only=True，实际晶体管LVS均明确Netlists don't match，禁止继续表征或物理流；失败原始回执/日志见[views-received.json](remote-launches/views-received.json)。单网表模式确实改变部分布局相关的控制单元构成，不能把新生成电路的时序表拿给旧版图用。

源码7cdd5fca的views-004/94648改为按原布局模式构建子模块电路，仅将顶层版图构建替换为对既有版图的复用；不产生替代GDS，原GDS/LEF仍是唯一物理输入，电路身份仍须与其实际LVS通过才可继续。此候选尚在构建，不能提前认定修复。旧002/003的未运行依赖94631/94632/94633/94635及94639/94640/94642/94644已清理，原因是前置明确失败，无可满足的成功依赖。原始作业与失败结果保留。
