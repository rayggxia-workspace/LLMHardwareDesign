# Issue126：严格GDS读取修复与六块门槛矩阵

更新时间：2026-10-28晚，Asia/Shanghai。仓库rayggxia-workspace/LLMHardwareDesign；Issue126 / Draft PR129；本人huangpingyang04-lgtm；分支task/126-full-block-pin-xy。恢复核验head20108f97d27f0f15ad32cf7655d331e5754181da，规则rayggxia-project-collab1.0.0。上一轮属于实际进展：已发布脚本、raw和物理ECO；本轮不是无变化重提。

## 已确认的新失败和修复

92783虽然Slurm COMPLETED0:0，两块merge_returncode都1：Duplicate MACRO name gemm_engine / llhd_opentpu_mxu，发生在读取DEF旁abstract.lef阶段；完整deck未执行，missing_GDS_cells=[]不是宏GDS齐全。原失败在ROOT/streamout/costed-r01保留。

安装KLayout0.30.12的真实API审计92795（tool_api/streamout-reader-r03）证实read_lef_with_def默认为true，会额外读取DEF同目录全部LEF；两份同名顶层导出abstract.lef/detailed.lef因此重复。先前审计92792遇写-only属性、92794遇借用对象生命周期，错误日志保留；修订保留LoadLayoutOptions所有者后取得有效API证据。

9345fd369d1ea1a9e3231d74fb2c318baec74680冻结驱动只禁止隐式同目录加载，原显式标准单元/真实SRAM依赖清单完全保持；保存并重新读回配置，清单和开关实测一致。未删LEF或几何、allow-empty仍禁用、不改原完整deck。新92798在ROOT/streamout/costed-r02：GEMM严格GDS合并0错误；MXU实际检出4个fakeram45_1r1w_64x40/64/72/96缺GDS，严格合并失败。两块原deck继续执行，其中MXU是不完整GDS的诊断，不能称全设计通过。新包装器向Slurm传递失败，仍按每块回执判定。恢复先查92798终态，不重提同一试验。

## 当前实际作业及限制

本人远程ROOT=/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027。92690/92691 LL完整窗口及独立检查，92700旧GEMM父夹具，92714 MXU父夹具，92721新GEMM父夹具，92781 SYS成本ECO检查点完整重布线仍需逐一核实。开始本轮均RUNNING或对应Dependency，未按耗时取消；他人Issue55作业不干预。

GEMM/MXU已通过的成本ECO和eco_views/r02不重做。ACT父夹具hold失败、VECTOR EST-0104及原setup失败、LL PG备选native4与三点修订DRT-1231、完整SRAM GDS缺失、旧deck覆盖/实现问题均保留。用户无额外材料，允许自行补充受控材料，历史逐pin目标层仍未知，不冒充复原历史。

## 本轮正式产物与验证

报告新增latest-physical-gates及机器可核查data/qualification_matrix.json / CSV：六块全部接口与候选、具体已完成物理源、native/完整规则、信号时钟/PG、源RC/STA、父层、原目标层和功能/等价逐项标记；已完成源与较新修复分别保留，未知不写0。GEMM/MXU数字来自实际成本ECO原文，不用旧窗口cap失败覆盖新修复。

新不可覆盖快照ROOT/gate_milestones/gate-r01（92800）已下载至analysis/gate_evidence，正式data/gate_milestones保留原文gzip、原文/压缩SHA、调度状态和远程物理索引。GDS/ODB/SPEF等大文件仍在授权远程目录，由原execution.json索引SHA。原A/B/C和25幅图不改。下一次终态另用gate-r02，不覆盖。

原入口docs/experiments/issue-126-full-pin.md；HTML的latest-physical-gates优先于历史运行中说明。发布前运行管理/业务验证、浏览器及最新矩阵目视检查；实际head/CI/图片读回证据更新PR129和Issue126后再进入下一大阶段。

## 下一条实际动作

1. 核实并收集92798/92781/92690及父夹具终态，补录deck分类计数，不能用Slurm或命令0替代规则通过。
2. 建立VECTOR EST-0104最小复现/准确API与版本证据，停止无变量反复运行完整试验。GEMM/MXU可独立做映射网表相对原源的完整数字功能等价及实际逐层线长/via统计；不能把cell逻辑子证明当作整个设计形式验证。
3. 用户已新授权可先推进明确未合格的六资源共同集成试验，复用既有逐bit构造/同256共享导体计划；当前尚未启动实际共同预连，不标合格冻结。选择匹配的真实新内部视图，记录每个失败/缺项、idle/clock/PG和原层目标。
4. 未有共同M1–M10实际固定预连/冻结、两完整M11/M12功能或公平系统对照，目标保持完整且active；不能用本轮阶段发布替代总验收。

登记management-hub PR5 pending；没有board.json/Projects能力，看板unverified/同步pending；管理员与审查人待指定。Issue保持in_progress，PR129 Draft，PR120未合并，不自合并。


## 后续已收齐终态（优先于本页此前运行中）

92700 FAILED5:13:40，但GEMM Aopt子试验native0、3753网/7506端点连通和双PG通过；旧C为DRT无AP失败。92714 FAILED4:19:36，MXU Aopt/C均路由0、2172网/4344端点连通和双PG通过，fresh native为5/2项spacing错误。C两项分别M6 inst:u_macro–act_data[12]及M10 act_data[197]–[213]；Aopt五项均M10。原生错误全部保留；旧夹具来源不是新成本ECO的叶视图，后续须精确匹配新视图。

92781 COMPLETED1:39:40：SYS成本ECO已完成全信号/时钟DRT、PG、RCX、STA、独立native0，466332网/1474481端点所检连通；路由前后cells/pin/PDN/die指纹相同、源未改。实际setup−0.462192/hold−0.125999ns，1113个VIOLATED文字标记（不当完整计数），仍时序/电气失败。先修复/合法化成本尚需从before与cell_repaired.cell_cost表独立统计；route前后单元不变不代表相对原始源没有ECO。新物理/研究时序视图尚未导出，不替换成原旧模型。

92798 FAILED51:13：GEMM严格合并0，原完整deck1460项，全部天线（M2 5/M3 108/M4 437/M5 507/M6 220/M7 66/M8 78/M9 30/M10 9）。MXU严格合并4缺fakeram，部分诊断GDS的deck1578项（含1项METAL1.5及其余天线）；不是完整MXU规则结论。新包装器失败传播已实际生效，不删规则、不以原生0覆盖GDS失败。接下来可独立检查真实LEF天线规则/实际diode单元和工具antenna API，再决定合法修复；不得先假设KLayout计数已消除。

59910b08707f20bb5d685990cfda9b310eee189a冻结驱动92812已对GEMM/MXU Aopt应用同C相同3/1处X2换型（ROOT/leaf_eco/boundary-r01），不重复C；开始增量路由/DRT，待真实终态。保存原层/尺寸/原SDC、恢复填充，成本单列，为公平基线准备。

不可覆盖gate-r02/gate-r03进一步保存父层/SYS/GDS终态；报告矩阵将新SYS成本ECO与旧原窗口版分别保存，旧源失败/运行中不能覆盖已收齐的新终态。发布后继续功能等价、逐层成本、MXU父层M6/M10真实接入修复及未合格共同集成；全部原完整目标仍active。


## 最新增量：等成本周边控制与天线只读审计

92812实际COMPLETED：GEMM/MXU Aopt同C相同3/1处X2换型，真实DRT/RCX与fresh native0、全块所检连通通过；setup/hold分别0.772449/0.053582ns、0.249090/0.053253ns，原pin/PG/die及源保持。成本分别+1.596/+0.266μm²标准单元master面积，非block面积收益。尚不是系统对照。

92825只读检查同GEMM源，原生天线0网/0pin而GDS deck1460仍未修复；实际ANTENNA_X1原Liberty存在非零输入capacitance0.023429，单位以源库为准。下一步查规则/连接和diode识别差异，不删除检查或无模型插diode。gate-r04不可覆盖快照保存上述及父层/SYS/GDS终态原文和双SHA。92690仍RUNNING、92691依赖等待，92721仍RUNNING；不重复提交。六块完整资格、共同实际底座/冻结、两个完整M11/M12模式及系统对照均未完成，目标继续active。


## 新阶段：原生天线覆盖根因、全映射合同与SYS匹配视图

92834真实只读审计：M1–M10所有default/oxide2天线规则均无，tech LEF天线关键字0，macro LEF无ANTENNAGATEAREA。原GDS deck300:1检查不变；原生天线0缺覆盖，不是通过。92837/92838对比原始ODB与成本ECO，GEMM226775非filler实例/826710信号端点、MXU179887/635434全量网络/方向/实例/时钟复位常量保持，仅3/1处等Liberty逻辑状态换型；相同未修改存储黑盒合同下相对数字功能保持，非RTL形式验证。

92835导出SYS2229位匹配新ODB/SPEF的物理/研究时序视图并准确重放原负余量；实际成本为新增5829功能实例、980原实例换型、1168移动、标准单元master面积+6918.128μm²，存储宏/全部pin/PG/外框保持，时序电气仍失败。不是纯XY收益或面积节省。

92721已FAILED，GEMM新版父夹具route/连通/双PG完成，但fresh native1：M10 gemm_a_rdata[128]/[129]间距。92841按真实异网M10/PG/OBS筛选父pin128新位置并实际重布线中，原叶层/尺寸与PG保持待核；不算通过。92690 LL完整窗口仍运行、92691依赖等待。

新图equal_cost_leaf_margins.png/svg比较实际Aopt/C提取余量，明确相同3/1处换型成本及完整规则失败。gate-r05不可覆盖原文/SHA保存上述终态。新模型准备92846/92847导出等成本G/M Aopt视图；92848为VECTOR全窗口及LL PG-only4错误源导出真实非零研究模型，其中LL明确标记UNQUALIFIED_FAILED_DRC_SOURCE，不放宽物理门槛、不把模型导出视为DRC通过。将用于用户授权的未合格共同集成，非合格冻结。

上一发布5fa66e0已核实GitHub head/图blob，CI40706845419及40706840681均success，Issue126仍in_progress/PR129 Draft。完整技术目标继续active，未实施实际共享底座/冻结、两完整上层功能及系统对照。


## 六资源实际集成与VECTOR排序对照（仍非完整验收）

3eb6bb957146be5535f6630a92241611c9458afa已从GitHub读回，CI40709632122/40709632132均success，新等成本PNG/SVG blob与本机一致。新增真实逐层DRT指标直接复用旧原生终态日志，不重新路由：GEMM同ECO C相对Aopt实际总线长−0.547%、via−0.102%；MXU+2.133%/−0.092%。这些是工具报告精度下的叶块实测，不是几何L1/提取RC或系统收益；仍保留内部方案，继续系统总成本验证。

92846/92847 G/M Aopt完整匹配视图导出成功；92848 VECTOR2246/LL SYSTEM13507位真实模型匹配与SPEF重放通过，LL原生DRC4完整保留为UNQUALIFIED_FAILED_DRC_SOURCE。固定线API92853失败（BPin不接受FIXED枚举），92854改用FIRM后原生ODB/DEF实际写出FIXED M10线及两端接入矩形；这只是API探针。

六块集成92855已实际执行，冻结驱动6b6dd8b912a6ceff59d3ecf63b5ee0140380d1e5，ROOT/common_integration/r01/C；实际六宏+38基础设施放置已导出，完整详细OBS/真实模型读取完成，PDN生成中。新图common_placement_actual严格来自placed.instances.tsv，未绘制虚构信号路径/PG/共享导体，背景不等于空白金属。复用256×32μm实际共享导体拓扑/预算，但尚未实际写线/完成底层布线，不能称共同冻结底座。原LL DRC4、GDS/STA/目标层等缺项保留。

VECTOR92861冷隔离无GRT/增量/SPEF仍EST-0104。实际411821个filler；仅把删除filler移到估算之前，92867（7c89d88ce212a3fcece0ca73b70ad491c9feda28）成功，14处换型/17缓冲，检查点位于estimator_diagnosis/r02/cell_repaired_NOT_LEGALIZED_OR_ROUTED.odb。不重复这轮电气修复；下一步从该实际检查点继续setup/hold修复、独立合法化/填充恢复、原层完整路由和全部原生/RCX/STA检查。上游固定commit82552e4的EST guard为参考推断，安装二进制仍unknown、源树不存在，不冒称版本匹配。

恢复先核实92690/92691、92841、92855实际终态；不重提同一试验/覆盖驱动。gate-r06/r07保存模型/API/排序对照及放置原文和双SHA。完整目标active，未有合格冻结/两完整M11/M12模式/公平系统对照。
