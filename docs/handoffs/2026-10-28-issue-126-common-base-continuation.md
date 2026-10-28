# Issue126 接续：真实二维接入与共同十层底座（进行中）

日期：2026-10-28（Asia/Shanghai）。沿用Issue126 / Draft PR129、task/126-full-block-pin-xy；负责人huangpingyang04-lgtm。此前发布2461fa2及PR120未合并成果保留。原参考包、历史产物、其他工作树及Issue55/121活动作业不修改。

## 17时后接续里程碑（优先于下方早期快照）

源码目前包括9561e7a及其前置44ebe2c/45330f9/6114473/5c9b363等冻结驱动；最终发布head须读PR129，不能仅用本文某次源码commit替代。四块新窗口完整试验已独立检查：ACT740/860、MXU1931/2172、GEMM3021/3753、VECTOR1022/2246，native0/所检全块几何连通通过；实际完整9031pin与增量表逐项匹配，单元/原PG/外框不变。GEMM有3项、MXU有1项max-cap失败；VECTOR setup−4.195674ns/118违规行。ACT setup1.255988/hold0.031533、违规0。两个SYSTEM仍未取得这轮完整终态，不能把四块通过扩大到六块或完整规则。

ACT父层修复已实际成功：92719，escape_landing/r01/act-C；原r04仅一项M10–VDD spacing失败，限定PG-via修复92695拒绝改条带，0.8um条带避让92696出现2项信号spacing失败，均保留。根据真实旧信号/PG/OBS筛查，把唯一新增父层M10接点r_data[195]从(144.095,368.07)改至(172.895,374.47)，原叶M6 pin仍(148.495,370.47)父坐标；新native0、860网/1720端点连通、双PG通过，其他859父pin矩形和全部PG几何不变。原叶860pin的层和740个内部位置不改。不要用wrapper M10中间端口替换原叶M5/M6接口定义。

common-topology-r02生成完整构造网表与逐bit图检查：17686固定逻辑分量、两模式各770边、256共享资源计划相同，38个独立常量/闲置clock驱动显式单列。92716在common_native_link/r01原生链接34954端点/17686分量双射通过；使用匹配Aopt物理/Lib视图，仅结构构造，不是布局/P&R/冻结。施工接点须降为保留金属；真实预连、clock/PG/闲置输入约束、M11/12两功能与完整比较尚未完成。

新增正式图4对PNG/SVG（ACT真实父层修复、llSYS PG修订、实际研究12层小例、共同布局proposed），已经打开检查；原有A/B/C保持。HTML是增量阶段快照，原物理milestone-r10也继续保留，当前复制到r12，原始远程/工作目录及Git历史均不删除。大体积几何/逐pin路径用原SHA和远程快照索引，原生文本无损gzip；不能因为未入Git的巨型数据库而虚称不存在。

恢复先查这些本人作业及实际输出，不重复提交：92648/92649（LL PG-only）；92688/92689、92690/92691（两个SYSTEM完整窗口）；92700（GEMM旧C/Aopt父接入，旧C已DRT-0073 bit142失败）；92706/92707（ACT1.6/2.4um条带避让独立试验，不能按耗时取消）；92708（VECTOR A/C成本化ECO）；92714（MXU Aopt/新C父接入，源模型r06已完成92713）；92721（GEMM新C父接入，r06模型已完成92720）；92724（GEMM/MXU新窗口电气专用增量ECO）；92726（ACT Aopt/成功C夹具真实RC/STA，显式同I/O研究策略与2/10/50fF敏感性）。继续收集终态及失败，不能将提交或Slurm0写成物理资格。

新原始回执在本地analysis/continuation_evidence/milestone-r04及正式data/continuation/native同名目录。每次收集器只写新的own snapshot。工具实际OpenROAD版本字符串unknown，以已采集平台binary SHA 0a4cdf08482bab2d99543e8b32b4b142e013becc7f2c1598afb39ba058193f53及原始日志/镜像索引定位；不假称特定release。读取本项目AGENTS/Skill/远程规则后继续。看板仍unverified/sync pending，无board.json/Projects能力；登记PR5 pending，审查人待指定。

后续实际终态补充：92726的ACT夹具分析在remove_from_collection（当前OpenSTA无此命令）处失败，提取/STA未执行；原目录不改。0ec2e5a驱动用原生Tcl列表修正后，92732在escape_rc_sta/r02对Aopt/C真正完成RCX/SPEF/三负载STA，源物理ODB SHA不变。native单位1fF；10fF时Aopt setup1.424290/hold−0.074562，C setup1.353438/hold−0.073476，均hold失败，C另有4条VIOLATED标记，50fF标记数分别305/228。604个物理同层零长度接触网仍提示未标注driver；不得用假RC/删检查消除。该I/O策略是新增且两方案相同的研究bench（0.2T/0.05T max/min、BUF_X4、clock slew0.05ns），不能说成原叶约束或完整系统实际收益。raw数据新增milestone-r05；92724的两块电气ECO与其他活动作业继续收集，不因Slurm成功或DRT0宣称检查通过。

cb945271阶段报告/4对新PNG/SVG已实际推送并由GitHub读回head；CI40669214019/40669213933成功，API列出全部8个新图片路径（PR超过3000文件，REST列表有截断，不把该列表当完整文件清单）。之后新增openSYS 92689终态：native0/460503网/1462823端点连通、原pre-RCX字节保持，setup−1.779887/hold−0.389230、2016标记失败；11260个新实际pin逐项核对。补录原生原文/index到terminal_updates/openSYS-r01，不改milestone-r05。LL PG-only92648已结束，92649独立检查；LL完整窗口92690/92691仍执行/等待，恢复先查实际状态。

92708和92724也已终态并保留失败：VECTOR成本ECO A/C setup−4.136094/−4.162278（native0、连通通过），仍远不满足原约束。GEMM/MXU电气ECO r02均native0/连通及pin/PDN/die原样，但cap3/1项仍失败；GEMM无新功能单元，MXU加1buffer、标准单元master bbox面积+1.862um²而未解决目标。分别删除345005/258099个CORE_SPACER，仅新拷贝操作；没有block面积收益，若后续复用必须先恢复填充/适用规则和功能等价检查，不能作为已合格叶视图。首次ECO结果只能记录实际成本/失败，原源文件完整。

LL PG-only备选终态92648/92649现已收齐：13184移动/13507信号pin实际布线，725253网/2325528端点/28517823形状所检全块连通通过，pre-RCX clean字节一致；fresh native DRC4失败（bit_1382013–VSS/M5 spacing、bit_6907–VSS/M6 spacing、bit_1389626自身M6 spacing、bit_6907 M6 NS Metal）。直接PG接触0证明仍成立，但不足以证明间距/线宽。补录terminal_updates/LLPG-r01；全13507实际pin再对照PG增量CSV，不能与新的access-r03候选混比。主窗口版92690/92691仍执行/等待，父层92700/92706/92714/92721未有终态前不重复提交或按耗时取消。

## 用户本轮确认的范围

用户明确选择六块资源并集、交错共同布局，并要求两种功能真实复用同一批固定预连导体；不要求共用同一计算实例。本轮包含研究性M11/M12技术建模。此前M1–M8/M9–M10的Issue55仍独立活动，只读复用源码/输入，不接管其作业。没有冻结共同M1–M10，没有通过M11/M12完成两套系统，不把原两父层当共同底座。

## 新取得的实际证据

- 旧父层已终态：openTPU r07/92441多端几何连通3207网通过、双PG通过，但独立native DRC11项失败；llaccel ll-r01/92458在GRT-0116拥塞失败。92476/92477后续RC/STA被物理来源门槛阻止，未执行；不是STA通过。
- 完整边界控制已收齐。openSYS同组A_replay/Aopt/B独立native0、所检全块连通通过，setup/hold仍负；完整C实际线长16429522um，对同组A_replay15416246um约+6.57%。llSYS边界三控制native0/所检全块连通通过，仍有时序电气失败。完整GDS旧A/局部C共12视图终态已收集，原规则/缺宏/天线/WELL问题不删除。
- llSYS完整C的26pin/44对固定PG接触，已作局部XY修订且保留13184内部移动pin。92648/92649是新布线及独立检查；截至本次收集仍在执行/等待。已从实际place_pin回读验证全部13507信号pin匹配修订表、PG指纹不变、同层固定PG直接接触0。它不等于完整DRC/布线通过。源码prepare_llsys_pg_repair.py，输入/实际证明在本任务analysis目录，远程trials/llsys-pg-r03。
- 研究M11/M12模型已实际跑原生小例92650，独立读回92653：2网/4端点，真实metal10/11/12和via10/11，native0/所检几何连通通过，新增下层金属均包含在原M10接点内。原十层及via1–9层规则块哈希保持。模型明确外推原M9/M10规则：0.8um宽、1.6um pitch，完整PRL间距表；via cut0.8um、间距0.88um、研究LEF零包围；高度14.09/18.09um、厚度2um及RC均为研究假设。无12层制造签核、校准RCX或完整系统结论。
- 原五个失败叶视图的精确RC/SDC诊断92651全部复现原最差setup/hold；VECTOR最差路径为块内寄存器到寄存器，约-4.17ns，不能靠接口XY或放宽时钟冒充修复。新的数据/时序失败仍保留。

## ACT实际父层接入发现与修复

ACT256-bit原层到父层M10接入夹具保留所有860个宏信号pin，原宏M5/M6层/矩形不改；只有256个父层中间接点位于M10，不是把原pin重定义到M10。非选中父层端口与原宏端口真实同层重合，单独标记为零长度连接。

- 首轮92655边界Aopt和C均GRT拥塞失败。92661允许拥塞guide进入DRT，全部工艺规则/OBS/层集合不改，GRT拥塞仍保留；Aopt有1项fresh DRC，旧C出现实际DRT-0073：u_macro/r_data[342]无access point。
- 找到并修正独立检查器把UNROUTED诊断占位行误当导体的问题：真正同层接触的两个端点可无需dbWire，分离/异层无via仍失败。5个实际几何边界用例通过。原检查回执保留，不据此删掉实际DRC失败。
- 新ACT C将740个移动点按实际相邻层轨道修订，临时保留M6/M7接入窗口，实际完整信号/时钟重布线；原单元/连接/PDN/OBS保留，只移除本轮新建的临时路由约束。92666/92667完成：独立native0、4819条多端信号/时钟网/15659端点所检几何连通通过、source clean与pre-RCX字节一致。原pin数量860/层/尺寸不变。此为全信号重布线，不能混入此前同740-pin rip控制的纯XY线长收益。
- 92671从该精确ODB/SPEF导出新的ACT模型r04，全部860信号bit/方向通过；原20份模型不覆盖此新版，均与新模型分别保留。模型仍非器件表征库、minimum_period/外部模型仍不完整。
- 接入夹具改为89.6um R0平移（11.2um的整数倍），保持实际0.28/0.8/1.6um上层轨道相位。92672的Aopt已通过native0、双PG及860网/1720端点的所检几何连通（256实际引出、604真实零长度重合）。C被精确来源SHA门槛拦住，发现ACT选择器仍硬编码旧C；已修复并仅重跑C，92677。原driver_failure不删除。92677结果须继续收集，不能先写通过。

## 共同底座准备，尚未实现/冻结

prepare_common_base.py已编译两设计的完整原始逐bit图、24767原信号pin和独立37个常量TOP_IO声明，以及六块交错布局候选。256个共享有限M10导体的计划绑定选取原ACT r_data[0:255]及原GEMM gemm_a_rdata[0:255]，不改变读总线语义；这是预连研究切分，不说成新硬件lane。两功能必须实际绑定并使用同一导体集合才可验收，不能仅凭CSV集合相同宣布完成。

preparation_contract.json明确frozen=false，原始硬块资源、待实现idle/clock/常量基础设施和成本分别列出；未有共同底座实际私有连接/共享预连布线、冻结manifest和两个完整M11/M12定制。原两父层/小例不代替这些阶段。边界对照保留已实际优化的Aopt及原XY控制，内部C即使块内线长增加仍继续，不退回边缘就结束研究。

## 恢复与交付

远程根/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027，冻结drivers目录不可覆盖。先查92648/92649/92677及后续本任务作业、收集终态；不重复模型r04/已通过Aopt夹具。ACT的接入窗口方法已扩展到其他五块的完整清单，候选与实际PnR门槛仍分开，失败时继续独立块。

原HTML/14对新PNG/SVG仍对应此前发布快照；本轮新增实际数据/图与完整中文阶段报告继续增量提交，不把代码上传视作完整物理验收。运行管理检查、真实几何/候选业务检查、打开新图，再推送同一PR129；Issue保持in_progress，不合并PR120/129。

规则rayggxia-project-collab1.0.0；project_id=llm-hardware-design；登记management-hub PR5 pending；无board.json/Projects工具，看板unverified/同步pending，管理员/审查人待指定。当前不满足完整系统完成标准。
