最新阶段入口：[实际固定导体与diode](2026-10-29-issue-126-fixed-conductors-and-diode.md)。以下历史原样保留，恢复先读新交接/实际回执。

# Issue126：全量数字合同、真实局部归属及天线修复接续

更新时间：2026-10-29，Asia/Shanghai。仓库rayggxia-workspace/LLMHardwareDesign；[Issue126](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/126) / [Draft PR129](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/129)；负责人huangpingyang04-lgtm；分支task/126-full-block-pin-xy。恢复核实线上head为0f1e43dc59d61005150dc8141c29b288832fa70c，两CI成功。新增驱动commit为9957f1aa7abcdfb3f0909bfbc94c55879f713be5、1d77813aa2dae753bcd368f9f5cb216142016c78、ed81920a56d5e60ab4fb61023b881834e37e59e0、e2b2974e8f25963dda99f3f624e1ebb60a994f49；发布head以PR最新读回为准。

## 最新00:55 CST：VECTOR真实终态与GEMM实际diode作业

新gate-r09/92917、gate-r10/92918只读快照保留；r09原采集规则省略paths.json，r10补齐有界实际关键路径JSON，未覆盖任何历史源。最新HTML/机器矩阵采用r10。

92872已终态FAILED1:0：真实全布线、fresh native0、375675网/1073220端点所检连通、双PG和实际RCX均完成；setup−4.140220ns / hold0.037989ns，83个VIOLATED文字标记。原pin/PG/外框与路由前单元布局指纹保持。相对旧源新增180功能实例、818换型、875移动，master面积+917.700μm²，单列成本，不是XY/面积收益。旧−4.195674ns源和全部失败保留。

92913 VECTOR全量有向相对数字合同PASS：321725原非filler、1076107原信号端点、2246端口、380381原网分量、607个独立NULL保持；180新增identity缓冲、818换型通过。仍是同硬存储合同的相对映射证明，不替代RTL/器件/物理资格。

92914/92915 actual_path_audit/r01/{vector,opentpu_aux}精确重放实际SPEF setup/hold。VECTOR最差p0_r[18]/Q→wr_data_r[18]/D，141 cell arc约6.7401ns、142 net arc约0.1984ns；SYSTEM最差寄存器→bit_22632有8 cell arc约0.4554ns和9 net arc约1.0524ns，末段到port约0.657ns。源JSON有舍入，cell arc含负载/slew，不是零线长下界或架构不可能证明。新actual_critical_path_diagnosis PNG/SVG、数据及原文SHA随报告发布；下一步针对SYS实际输出缓冲位置和引出绕行做保持逻辑的修复，不重复无变量setup命令。

实际GEMM diode92910：驱动d694a7e2d66d59a1708bbaaf6b5f9dea322f32b1，ROOT/antenna_diode_eco/r01/gemm-C。636个真实ANTENNA_X1已插入/合法化、原功能实例位置/连接检查保持，完整GRT已执行，DRT正在运行；不称天线通过。真实库capacitive_load_unit=(1,ff)，每个输入cap0.023429fF。标准单元site面积成本预计169.176μm²，须以原生导出终态核对，不是block面积变化。

92912严格GDS及原deck依赖92910终态（afterany，源无完成路由则明确不执行），驱动6184a8effd0be31cd31830acb35a98fbc1bc0c76，ROOT/antenna_diode_stream/r01/gemm-C。allow-empty禁用，原deck/300:1不改，不伪造器件。92690/92691、92841、92855、92892继续核实，92855原生PDN生成及VDD/VSS检查已完成，固定导体/底层路由尚无终态。

已发布前阶段db2ae1cd442c53a2ef4d2b0f03b6980b75eb2b9e：CI40727062699/40727062697均completed/success，新M6图片GitHub blob与本机一致。当前阶段发布head及CI以最新PR回读为准。整个目标继续active，仍无合格共同冻结、两完整M11/M12功能或系统对照。

## 已收集的新终态

- 92886，ROOT/buffered_equivalence/r01/opentpu_aux：实际原始与ECO映射数据库导出、所有原端点/方向、Liberty状态/逻辑、5829个新增identity缓冲和980换型逐项检查。438852原非filler、1539803原信号端点、2229顶层端口、529989原网分量、9723个独立NULL端点保持；有向同原驱动可达、无环、无新增多驱动/孤岛通过。5个正反向/循环/改网/NULL反例测试进入CI。固定相同硬存储合同条件下的相对网表证明，非RTL/存储器内部形式等价，原SYS提取setup/hold失败仍保留。
- 92891，ROOT/parent_region_audit/r01：旧MXU父层和旧/成本ECO叶块真实3×3μm局部几何。原生M6 act_data[12] marker重叠OBS 0.0238μm²完全由真实同网叶金属覆盖，旧/成本视图局部M6矩形及网标签相同。最近已导出异网M6几何gap 0.42μm，不是规则通过；各叶源仍有2条OBS变换未核对。新assets/mxu_M6_actual_ownership.png/svg已打开核验，实际pin/父via的M6落脚0.14×0.14μm不是切孔或整栈占地。原父层native2保留，不删OBS、不豁免报项。
- 92901，ROOT/antenna_netmap/r01：1460个原deck真实GDS金属多边形与原生全块导出正面积相交，全部唯一关联636网。后续库存解析错误导致SlurmFAILED，原失败保留。92903，ROOT/antenna_netmap/r02仅修正实际deck polygons/input解析并按输入/产物SHA复用上述完整关联，成功；没有重路由。
- 实际Nangate ANTENNA_X1 GDS存在，原deck `(nplus & active)-nwell` 识别面积0.0081μm²、与contact正交叠0.004225μm²。GDS bbox含well/implant，不能与0.19×1.4μm LEF site混淆。原Liberty输入cap非零0.023429，单位须读真实库头。636网关联不是LVS或修复；原1460项仍未消除。

原始证据在不可覆盖ROOT/gate_milestones/gate-r08（92906）及仓库data/gate_milestones/gate-r08，原文和gzip双SHA；大ODB/SPEF/GDS仍留授权远程路径由原回执索引。ROOT=/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027。

## 本次恢复核实的活动作业

92690 LL完整窗口、92841 GEMM父层单个新增M10落脚、92855六块共同集成、92872 VECTOR从真实检查点重布线、92892 MXU单个新增M10落脚均RUNNING；92691 PENDING Dependency。不重复提交、不按耗时取消、不改活动driver/输出。Issue55及其他工作树和任务不动。

VECTOR已从92867实际14resize/17buffer检查点继续，先去filler避免EST-0104，再时序修复/独立合法化/恢复filler；最终提取时序尚未取得。中间placement估算setup仍负，不当作修复成功。

## 仍失败或未验证

六块原24767信号pin/74301行ABC与完整功能归属不重做。GEMM/MXU C成本ECO已通过native/连通/源RC电气门槛及相对数字合同，保留内部分布；等成本Aopt同样实际完成，块内线长差异不代替系统比较。ACT父层hold失败、SYS源setup/hold失败、VECTOR原setup失败、LL PG-only native4/时序失败、缺匹配SRAM GDS及原deck覆盖缺口继续保留。旧父夹具不冒充新成本叶视图已验证。

六块共同集成92855仍是明确未合格研究试验，不是冻结底座。尚无实际合格M1–M10固定256共享导体冻结manifest、两完整M11/M12模式、全系统功能/RC/STA/电气/公平对照。研究12层两网探针不能替代完整系统。原叶pin层/尺寸/语义/允许布线层不变，新增父层M10中间点另列。

## 恢复后的第一条实际动作

先读回上述作业及execution.json终态，不复做已通过证明。发布当前中文HTML/机器矩阵/新图/原文快照并读回GitHub head/图片及CI。随后对636个已关联GEMM网按真实ANTENNA_X1、输入cap和原规则做单独成本化diode接入试验，原有实例/接口/PG/边界保持并重路由、fresh DRC、完整所检连通、RC/STA及严格GDS原deck；不虚构ANTENNAGATEAREA，不删天线规则或使用占位库。其他独立作业继续；新终态用gate-r09，不能覆盖gate-r08。

规则rayggxia-project-collab1.0.0；project_id=llm-hardware-design；登记management-hub PR5 pending；没有board.json及Projects能力，看板unverified/同步pending，管理员及审查人待指定。Issue保持status:in_progress，PR保持Draft，Refs #126；不合并PR120/129，不标整个目标完成。

## 01:05 CST新失败与恢复入口

新92921（driver3e6a10233f419cc508679a61c3a072014705e75e）已FAILED：1244个输出port全部考虑，772条私有链/1262个现有identity buffer生成真实重排，不增单元/不换型/不改网。Diamond报告1262 moves后Signal11，implementation=-11，未完成合法化检查或布线；全部源SHA保持。ROOT/output_chain_placement/r01/opentpu_aux-C/moved_NOT_LEGALIZED_OR_ROUTED.odb有完成SHA，禁止重做同一移动选择。gate-r11/92924新原文不可覆盖快照保留失败。计划中的恢复脚本resume_output_chain.py分离无Lib/SDC的几何合法化与原SDC/Lib的布线/RC/STA进程，复用该检查点及真实源状态；假设是STA观察器/进程状态，准确崩溃根因尚未证实。SYS原无filler时不添加新filler，check_placement仍执行。恢复作业须以新发布回执核实，不能把脚本存在说成已运行或通过。

## 01:07 CST：同一检查点独立合法化实际成功，布线继续

92925（driver e151247a7cd59c082e578d13c06575801e265b51），ROOT/output_chain_resume/r01/opentpu_aux-C：没有重复选择或生成1262个buffer坐标，复用92921有SHA的moved检查点。原source状态独立导出、无Lib/SDC几何进程Diamond及check_placement通过，1262 moves全部成功；原功能master/逐端连接、非选中原实例位置合同与92921移动前source字节相等。原SYS没有filler，未添加filler，检查未删除。随后独立新进程恢复原Lib/SDC和signal M2–M8/clock M4–M8，正在完整重布线。未终态DRC/PG/连通/RCX/STA不得填通过；准确崩溃根因仍是未闭合假设。

新gate-r12/92926保存不可覆盖原文、当前调度状态和已关闭原生合法化阶段的placed ODB及两份实际合同文件SHA，实际合同SHA对source比较；不对活动写入ODB做哈希。新report/矩阵的SYSTEM_output_chain_resume与原92921失败分别保留。

恢复首先核实92925、92910/92912、92690/92691、92841、92855、92892；不重做成功的VECTOR/SYS数字合同及GEMM关联，不改活动driver或输出。共同集成92855在原双PG检查后仍推进筛选/固定线与底层接入，没有合格冻结或完整M11/M12模式。下一次新终态使用gate-r13，不能覆盖r12。

管理回执：e151247的证据CI40731981497已读回success，结构CI40731981494仍以前次读回in_progress为准；后续head/CI须重新查询。登记PR5 pending、Projects配置/能力缺失看板unverified/同步pending、审查人待指定；Issue126保持in_progress，PR129 Draft。

采集器r12新增阶段文件循环曾复用name，导致远程gate-r12.tar.gz内根名为placed.nonselected.tsv；原ROOT/gate_milestones/gate-r12及原文记录/双SHA不变。本地核验归档全部成员和manifest后仅恢复目录标签为gate-r12，代码已改用stage_file避免覆盖快照名。此前r11检查通过不当作r12已发布；修正后重新生成/验证最新r12矩阵。
