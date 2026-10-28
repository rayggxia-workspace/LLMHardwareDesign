# 完整硬件集成实验（Issue #55）

历史检查点：2026-10-27 11:13 CST；当前结果及唯一最新索引见文末 current-buffer-PG-status。

当前：完整191实例结构有限active＋idle数字回归通过；共同底座完整原生DRC仍在运行，阶段二、三尚未验收。完整固定/定制布线、最终时序和冻结未完成，最新索引及局部证据见文末状态。


本入口承接两个完整原始硬件顶层：openTPU `otpu_asic_top` 的 small 配置，以及 `llaccel_core`（EPILOGUE_FUSION=0）。采用资源并集；现有 ACT/MXU/GEMM/VECTOR 保留为核心输入，未划分的控制、存储与接口逻辑另做案例辅助分区。不是最终团队 Block 规格，也不是 LLM 图编译器。

阶段一清单/基准验收为pass_with_inherited_issues；原完整 RTL 有有限回归通过，两完整物理资源网表有限回归已通过；最终分块时序/物理资格、共同冻结底座和最终定制布线尚未通过。[阶段记录](../../../docs/experiments/issue-55-full-block-integration.md)与[算法说明](../../../docs/experiments/issue-55-block-integration-methods.md)给出实际证据边界。

本轮主路线：M1–M8 固定，M9/M10 及真实 M8↔M9、M9↔M10 通孔定制；M11/M12 只保留为单独后备评估。原始 Block 中已有高层占用，必须先在派生副本真实迁线，不能删除或隐藏几何。

## 环境与运行约定

- 唯一服务器根目录：`/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z`。
- 当前源码：该目录下 `worktree/project/experiments/block_full_integration/`；运行使用每个 driver 目录中的 Git commit 快照。
- Slurm c64/c96，作业名 `hpy-*`。后续新作业统一申请4 CPU；OpenROAD/构建线程最多4，Yosys/open仿真主要单线程；LL可按独立完整测试组并行最多4个单线程进程；进程内存限制与缓存位置见实际 `run.sbatch`。
- 既有 ORFS Singularity 容器：`/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif`；执行 `source /OpenROAD-flow-scripts/env.sh` 后使用现有 OpenROAD/Yosys。
- 原始输入只读。每次新实验须新 `driver` 和输出路径。失败目录也不覆盖。
- 仿真涉及既有 Verilator/Intel 编译器及 FakeRAM 行为模型；模型不代表真实 SRAM 工艺资格。

## 实际入口和范围

| 入口/适配器 | 已执行能力 | 未完成部分 |
| --- | --- | --- |
| `flow.py inventory --adapter native` / `native_inventory.py` | 完整 ODB 实例、pin、wire/via、PG、技术层表；四宏实际完成 | 不等于 DRC/连通/STA |
| `flow.py inventory --adapter rtl` / `rtl_inventory.py` | 锁定原构建、选用源码、21项归属前沿和历史基准 | 归属前沿与完整展开证据结合使用 |
| `flow.py integrate` / `partition.py` | 两个真实完整顶层展开、状态/内存归属 | 两例完整分区结构通过；open完整20例逻辑分区配对通过，两完整逻辑分区与实际物理资源网表有限配对通过；辅助已分别验证完整布线版本，非最终共同冻结底座 |
| `flow.py verify --adapter native` | 完整原生表独立一致性核对 | 不能代替真实几何连通 |
| `native_geometry.py` | 指定目标网端点连通，目标对全部邻近导体/PG/引脚短接检查；ACT原69网通过 | 不检查无关非目标网之间的短路，不代替全部工艺DRC |
| `migrate.py` | 原生 FIXED 路线导入资格；支持复用已关闭准备/路由证据 | 迁线、提取和时序按各次真实收据验收 |
| `baseline_replay.py` | 原完整 llaccel seed0/2 补测 | 不是新集成 DUT |
| `compile_open_observer.py`、`replay_open_observer.py` | 原完整open小配置观察器构建及20例回放 | open逻辑分区20例逐周期配对已通过，非最终物理网表 |
| flow.py verify --adapter router-access-projection | 完整两例投影、7118条nativeTcl literal读回、11种软件PIN/尺寸及11坏输入，92552通过；generic native helper92551工具夹具通过 | 完整case尚未运行；旧08b不得替代新源/冻结；桥线必须实际生成 |
| `flow.py replay` | 验证原生库存输入/代码/工具SHA后在新目录重放 | 目前仅原生库存类型 |
| flow.py prepare-base -- --stage placement / prepare_base.py | 六宏实际ODB/DEF与全端口原生位置、源几何检查 | 固定PG原型已实际通过其独立检查；clock/reset/prewire/idle/freeze未验收 |
| flow.py verify --adapter placement / close_native_placement.py | 新进程读回完整placement检查点、全部引脚/源几何及实际移位负例 | 不替代有源共同底座验证 |
| flow.py route | 未实现时明确非零退出 | 最终定制仍待实现 |

## 已实际执行的命令

以下为作业内真实调用的命令形式，`SOURCE` 指对应 driver 保存的源码快照。历史输出目录不可重复写入。

```bash
python3 -B -I -S "$SOURCE/project/experiments/block_full_integration/partition.py" elaborate --case llaccel --task-root "$ROOT" --out "$ROOT/runs/hierarchy-llaccel-03" --seconds 1200 --max-as-gib 24
python3 -B -I -S "$SOURCE/project/experiments/block_full_integration/replay_open_observer.py" --run-root "$ROOT/runs/open-observer-replay-01"
python3 -B -I -S "$SOURCE/project/experiments/block_full_integration/native_geometry.py" --input "$ROOT/runs/native-act-01/native" --manifest "$ROOT/runs/native-act-01/execution.json" --targets "$ROOT/runs/migration-prepare-act-02/targets.json" --output "$ROOT/runs/native-geometry-act-01-driver/original-target-geometry.json"
```

各命令完整环境与选项以 `runs/<driver>/run.sbatch` 为准；对应作业89958、89965、89966。提交器 `submit.py --spec <JSON>` 将指定 Git commit 归档到新 driver 后提交，不使用会变化的工作区源码。

复跑时复制所需小型 driver 配置到本任务新 `configs/` 文件，修改 `driver`、`source_commit` 和输出路径，再调用提交器；输入、层范围或工具改变后，旧通过结果不自动沿用。准备/路由恢复入口还检查相关数据库、原生表和比较报告的 SHA。

配置分为：`native_candidates.json`（实际宏和工艺输入）、`partition_cases.json`（原顶层/文件表/核心边界）、`baseline_extra.json`、`open_observer_*.json`（有限测试与参考结果）。其中案例选择和服务器路径属于适配输入；正式 Block 接入须替换能力、尺寸、实际 pin/障碍/时序模型和目标连接，不能仅改名字。

大型数据库、trace、全部日志保留在服务器。仓库 `results/summary.json` 与少量CSV仅提供索引，不重新包装原工艺或设计源码。

## 当前实现与证据恢复

- prepare-base placement：真实六宏ODB/DEF、全部端口/geometry及移位负例91888已运行；旧辅助版本不能作为新源证明。
- prepare-base fixed-pg与verify fixed-pg：实际91954/91960构建/读回/导体图/原生PG和3负例通过；只是旧源供电原型，无clock/idle/freeze或IR/EM/完整DRC/STA。
- bind_physical_endpoints与canonicalize_parent_aliases：92004/92005已在新两辅助M8源版本上重新闭合。
- certify_auxiliary_symmetry：实际库完整真值/对称资格与全状态输入锥，通过91884/91885；原严格图失败和整体miter超时保留，不是源RTL全输入证明。
- generate_open_isa_cases、replay_open_repeat --suite-receipt与close_open_paired_evidence：calibration91973、原91976、物理91980、独立91985均已执行；54程序×3seed、29876行/713277字段/全部162份256KiB内存一致。复用原比较器；原正常重复启动模式仍单独三seed两host任务91949通过。
- probe_abstract_origin --reuse-origin-export与qualify_monotonic_abstract_patch：复用闭合导出，真实新R0读回，再证明旧OBS完整保留/原完整扫描全部缺口闭合。两新辅助91981/91982、91992/91993、91999/92000通过。
- probe_fixed_control_access：四向直线12项中4失败；probe_control_dogleg在真实几何上联合寻路92020达到12/12局部出口，仅几何探测。prepare-base -- --stage control-access92028实际写出新ODB/DEF，12局部端点连通/44形状/原资源保护/删线短接负例均已通过，不当作clock/reset树。
- verify_closed_producer：同任务精确submission/job/source链依赖；92025新增prepare-fixed-pg适配器绑定未来已闭合placement，严格检查未豁免；92026当前源独立PG几何/native-grid已通过，旧源91960保留。
- open_mm_cases与同一生成/回放/独立工具：92033/92035/92040/92042实际120例三方与1382文件闭合，36858行/899277字段/120完整内存一致，无硬件缩减。
- derive_fixed_control_contract：92041从完整图核对1个共同clock和4条不同reset，MXU reset来自辅助输出；continue_control_access绑定准确新源/PG并恢复全部13接入，92044方向元数据构建失败保留，92064恢复后13端点实际读回通过。
- prepare-base -- --stage fixed-controls：复用PG-aware路由器规划并实际生成5条原控制网络；92050默认PG几何保持及新目标/障碍/负例fixture通过，92051来源守卫失败、92071 cut间距和92078断图失败保留；92085带桥接点集fixture与92087全5网实际ODB/DEF读回、2614新增形状/13锚点/4根、受保护geometry/PG和4负例通过。92092另已完成实际RC提取/17端点/正电阻图与2负例，不代表时钟质量或freeze通过。
- 最终freeze/route仍未实现，不能作为已验证运行入口。

flow.py verify --adapter fixed-control-rc及measure_fixed_control_rc：92092只读实际5网/17端点提取与电阻图通过。精确闭合生产者自动续接；既有SPEF解析/原生模型资格复用，实际删电阻/端点负例通过；不跑全STA或新建底层资源。

flow.py verify --adapter fixed-control-clock及measure_control_clock_boundary：92101完成原2.5/3ns下6pin×4记录/例和原生传播状态/ideal负例资格。实际6/6入口max_transition失败，不接受clock质量或freeze；92103现有CTS资源只读核查通过，未生成修复树。

flow.py prepare-base -- --stage clock-cts：92107实际75buffer构树/合法放置/完整原生读回通过；76逻辑网全6clock入口可达，58,972,634行原PIN/OBS与PG/reset保持、断buffer负例检出。新buffer仅逻辑PG，实际供电/clock导体/RC/功能未做。

flow.py inventory --adapter clock-buffer-pins：92116实际150个M1电源PIN/75实例变换与ITerm核对通过，bbox空洞/原点偏移负例检出；不是物理PG通过。

probe_full_union_idle/merge_identical_modules：92063实际6资源/33RAM三seed各256周期held-reset检查、5120请求检查/seed及强制请求负例通过，原body/实例/连接保留；不是active+idle完整任务或物理parking。

真实重跑命令、源commit和所有参数都在对应runs/<stem>-driver/spec.json与source_revision.json。历史目录不可重复写入；复制小spec、更新driver/source_commit/output后才提交。补充ISA不重编/缩小DUT；原版/物理源码、外存和接口不回退；物理模式不执行shiftx替换。

此前执行说明（历史；恢复以文末最新milestone为准）：92018/92107/92108/92109/92112/92116/92119已闭合。下一步依据75buffer/150真实PG PIN构造M1–M8实际供电接入/增量PG，再完成76clock网真实布线与两原周期RC/slew/时序复测；保留原6宏/内部几何、现有PG/reset及全部原始文件。LL ABC raw源3ns失败，不是当前底座源；92121已在725253网/2325528端点RC覆盖及同CTS精确通过后启动现有电气/setup/hold修复，尚无结果。继续active+idle完整任务与新增时序问题；无冻结，远端仅阶段一。

<!-- native-annotation-audit-entry -->

新增只读时序诊断入口：audit_path_parasitic_annotation.py --config configs/current_auxiliary_path_annotation_audit_r03.json --output 新runs目录，92555已实际验证原/当前未标注驱动分类与指定路径SPEF端点覆盖；不做时序豁免。normalize_historical_rc_reference.py --config configs/original_llaccel_matched_current_RC_reference_r01.json --output 新runs目录，92556正在执行当前RC参数匹配的原始全设计参考提取。两者必须使用submit.py固定版本/4核，实际状态见最新索引；不改变源数据、SDC或底座。

<!-- matched-RC-reference-and-rich-arc-entry -->

已实际执行入口：normalize_historical_rc_reference.py --config configs/original_llaccel_matched_current_RC_reference_r01.json --output 新runs目录（92556）；timing_path_arc_components.py --config configs/current_auxiliary_rich_path_components_r01.json --output 新runs目录（92557）。新增compare_cross_boundary_registers.py --config configs/original_current_aux_named_register_comparison_r01.json --output 新runs目录（92558，当前实际状态见索引）。三者通过submit.py按固定commit/4核运行；复用既有compare_timing_endpoints.py完整列表/单位校验和原生脚本，不削弱其同上下文守卫。新的跨边界适配器仅用于数值定位，未验收时序。原始输入只读，历史SDC不变；未知外部波形和负载不补零。

<!-- source-alias-slow-geometry-and-reroute-entry -->

新增入口均须submit.py固定版本/4核及不重名新run：trace_state_alias_endpoints.py --config configs/current_aux_unmatched_state_alias_trace_r01.json --output 新runs目录（92559已实际测量）；slow_path_net_geometry.py --config configs/current_aux_slow_net_native_geometry_r01.json --output 新runs目录（92560已实际测量）；reroute_slow_auxiliary_nets.py --config configs/current_aux_slow_net_M7_M8_reroute_r01.json --output 新runs目录（92561真实修复试验，当前调度和结果见索引）。重跑前必须先查已有状态和有效证据，禁止重复仍运行的试验。只读诊断不等于硬件通过，修复试验物理通过也不等于RC/功能/时序/冻结通过。

<!-- mode-dependent-idle-fixed-custom-boundary-entry -->

新增已执行入口：audit_idle_custom_boundary.py --config configs/current191_idle_custom_boundary_r01.json --output 新runs目录，经submit.py固定版本/4核的92562实际通过输入边界检查。它连接既有全部idle分配、原生固定归属、全案例接入及软件路由manifest，不创建导线；每case841个mode-dependent闲置sink仍属于M9/M10定制连接，禁止永久在M1–M8接零。局部tie/buffer/PG/M8接入固定。闭合来源、四个负例、命令和SHA见92562 spec/execution。仍须实际完整布线、功能和电气检查，不能把本输入检查当物理通过。

<!-- selective-aux-source-gate-and-measurement-entry -->

新依赖链入口均须submit.py固定版本/4核、先核查已有作业避免重复：qualify_selective_auxiliary_source.py --config configs/selective_aux_slow_net_source_gate_r01.json --output 新runs目录（92563宿主机依赖92561实际终态）；measure_selective_auxiliary_rc.py --config configs/selective_aux_slow_net_RC_comparison_r01.json --output 新runs目录（92564容器内依赖92563实际成功报告）。两者当前仅已实现、已提交/PENDING，尚未验证通过。前者真实SACCT和全部封存物理报告/ODB门控；后者显式新来源类型复用既有实际RC/STA/完整endpoint脚本，保持旧SDC与frame、旧census及闲置driver分类，失败源不启动EDA。新测量也不等于时序/功能/冻结验收。92561原8-target几何检查已实际通过，后续准备/重布线未验收；精确命令、源commit和失败保存见索引。

<!-- selective-aux-named-ERC-entry -->

新增待执行入口：compare_selective_auxiliary_electrical.py --config configs/selective_aux_slow_net_named_ERC_comparison_r01.json --output 新runs目录，通过submit.py固定版本/4核的92565依赖92564真实成功新测量。它复用既有严格ERC parser/difference，接收两种实际producer证据索引，完整finite cap/slew逐pin核native计数，输出新增/消失/持续恶化，不只比总数。原fanout无限值仍不算覆盖，所有原始负增量保留，打印精度标签不作验收；新类型仅是测量对照，无电气/功能/冻结签核。92565目前PENDING，程序尚未实际验证，结果以闭合execution和最新索引为准；不得重复提交仍在运行或依赖排队的同实验。

<!-- current-buffer-PG-status -->

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
