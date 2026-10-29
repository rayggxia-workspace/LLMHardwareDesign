# 完整硬件集成实验（Issue #55）

历史检查点：2026-10-27 11:13 CST；当前结果及唯一最新索引见文末 current-buffer-PG-status。

当前：候选1/3未冻结；旧AUX完整布线最终失败，新58buffer位置/全部首过孔局部检查通过，完整14059固定线仍运行。阶段二/三未验收、四未执行，证据见文末。


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

更新时间：2026-10-29T04:13:47.859996+00:00（UTC；中国时间加8小时）。本段为当前结论；历史快照与上版六份记录完整归档在下面索引中。

**目标与冻结边界。** 两个完整案例使用同一资源并集。冻结后实例、位置/朝向、内部实现、M1–M8、固定预连线、M8接点、PG/clock和有源资源必须一致；只定制M9/M10及真实via8/via9。M11/M12未启用。open为otpu_asic_top及全部33内部SRAM；LL保持EPILOGUE_FUSION=0、DMA_MAX_OUTSTANDING=16，16外部SRAM bank/DRAM/主机仅属功能环境。不缩规模、不加流水、不放宽原周期。当前主要候选1/3，**UNFROZEN**；阶段一pass_with_inherited_issues，二/三未验收，四NOTRUN。

**实际完成与失败：**

| 实验/作业 | 终态及严格证据边界 |
| --- | --- |
| 旧完整AUX详细布线93116 | FAILED1:0/4。完整546459实例、124目标、62拆分、15489424保护保持。独立新进程全片DRC **89**（44 M2 Short、45 M3 MetalSpacing）；目标对全量导体 **55个异网形状接触对**，不等于55个唯一短路位置。原实例/master/PIN/OBS/非目标导体、PG/clock保持；placement/PG拓扑通过，但信号物理失败。原DRT内部48标记不是最终89的替代。 |
| 公共端口复核93131 | FAILED1:0/4。独立读回完整源/13表，**61/61公共M8端口存在未连接物理岛**；旧逻辑端口连通检查漏项不能作放行依据。 |
| 接入感知位置规划93160 | COMPLETED0/4。2220个候选姿态，62个既有新buffer中58个位置需调整、4个保留。按真实行/轨道/PIN/OBS/过孔及完整原导体检查；规划自身不是native接入通过。 |
| 实际新放置93162 | COMPLETED0/4。新位置实际写入派生ODB并独立读回；原546397实例全部保持，仍为546459实例/62新buffer。原导体与PIN/OBS保持、实际DPL0、离开合法site的真实负例检出。**只通过放置，不是布线/RC/功能。** |
| 全部新buffer首过孔93165 | COMPLETED0/4。完整原设计背景下实际写入124个via1_4；全部62区域native DRC标记0，重新读回124个via身份/位置，真实异网短接负例检出。原新UNROUTED源placement/PG拓扑通过。诊断副本仅移除声明的124条可变普通信号线；非目标导体保留。**这是全部新buffer的局部首过孔接入，不是全片信号布通/最终DRC。** |
| 保留固定线方法93164 | COMPLETED0/4。小型真实N45夹具中，将原固定导线投影成临时障碍、实际布新线、精确合并回原几何；全部11原形状保留，公共物理岛连通，新进程DRC0，实际删线负例检出。**只证明工具方法，未完成全61引出/完整124网布线。** |
| 完整固定线93130 | **RUNNING/4**，已完成native track assignment、进入详细布线；没有最终结果。14059固定目标/6225真实公共PIN，未重跑PA/GRT；使用旧版AUX来源，后续新58位置版不能直接继承。 |

旧93157（guide单位DBU误用导致分配失败）、93159（直接保留FIXED线未补通）、93163（增加ROUTED端点seed仍未补通）全部原样保留；未采用这些失败方案。新方法93164实际使用DBU和精确固定几何合并。旧93123临时重复M8端口漏检方案未采用。软件AP候选/路径规划/guide均不等于实际完成布线。

**资源与耗时。** 所有新任务申请4核、原生线程≤4、BLAS1，总进程受实际cpuset约束；未停止、在线变更或重复提交任何运行中实验。93116 wall6718s/CPU18413s，平均2.741核；93160 128s/127.450s≈0.996核；93162 951s/952.567s≈1.002核；93164 7s/3.721s≈0.532核；93165 640s/638.029s≈0.997核。这些规划、放置及局部检查主要单线程，**申请4核没有被写成4倍加速**。93130运行中CPU快照见索引，不将未结算TotalCPU=0当作无运行。

**未完成/阻塞。** 新124网完整布线、完整61固定引出保留/回装、全片连接/DRC、实际RC/时序/新版本完整功能均未完成；旧AUX/VECTOR新增或恶化的电气/时序未解决。14059项固定预连线仍未取得实际布通验收，841闲置sink/每case、当前191父版统一PG/clock与active+idle尚未闭合。外时钟rise/fall和open37常量输出负载由用户确认未确定，保持null而非0。旧功能/状态锥证书只对绑定版本有效，移动/布新线后不得自动继承寄生和功能验收。

**下一步最小行动。** 保留93130自然运行；以93162新源和93165接入证据，适配93164已资格化方法，保留原61条M5/M6→M8引出，在新独立目录实际重布完整124目标。所有原保持性/严格公共物理岛/异网接触/全片fresh DRC/PG门槛仍必须通过，之后才做当前版本RC/电气及完整功能；仍不冻结或进入阶段四。

服务器根：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z
当前实现源码：aafb7a5593c6bb74d2dba12dfda72ea6b4abda7d。各作业source/spec/submission、输入/工具/输出版本、大小和SHA见不可变索引。
最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-closed-failure-and-qualified-first-via-20261029T041347Z/milestone.json
索引SHA-256：938cb2b23fca5489ad697ba85205a1273c198e2136bc2631fef3a27e7050d7f3
关键回执：旧AUX FAIL 1ba9fba9ccfb8c3da7e1b48009026b5a58e11a6faaaa7d680eb61364c81a7f9b；新放置 6eafb75bfafdbd863d7b57da81d2618a3458832a8791c875f1ba5668778c5c52；全部62首过孔 c638f76850c9cc5addfd2f2cfbeabe567aa918860caf1e4b638b3419108d4fc4；固定线工具方法 7157b67d8b733b3ce5516a72717c5fe9f01437ca366eaaefc64a7e3950daaf72。
旧失败实际ODB：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/auxiliary-fixed-position-driver-route-r04-explicit-M8-4c-01/route/migrated.odb（872526222bytes），SHA 001b06bc9d0ed2578c8f3f3c884428c02e77bf043ae47b4c72f8f83e85d3ecc1。
新UNROUTED放置ODB：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/auxiliary-access-aware-driver-stages-placement-r01-4c-01/driver_stages_placed_UNROUTED.odb（710445317bytes），SHA e6e350524915f2d64866ffffa1cad40218d376df7f7d372e12e7c775e17acbc2。

仅六份精选既有记录入库；大型数据库/完整日志/工艺继续只在服务器。rayggxia-project-collab1.0.0；登记复用管理中心PR5 pending；board.json缺失/Projects unverified、同步pending；审查人待指定，Issue55继续in_progress。本次结构检查通过，不代替以上业务验证。
