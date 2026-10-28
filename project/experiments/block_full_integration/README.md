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

检查时间：2026-10-28T19:12:14.154222+00:00（UTC，北京时间+8）。Issue55 / task/55-full-block-integration / 草稿PR58；负责人huangpingyang04-lgtm。整体in_progress，阶段一pass_with_inherited_issues；阶段二/三未验收，四未执行；资源并集底座候选1/3，**未冻结**。

**范围和冻结边界。** 两个完整硬件案例共享全部资源、位置/朝向、内部实现、固定接线、PG/clock及M8接点；主方案M1–M8固定，仅M9/M10及实际M8↔M9、M9↔M10通孔定制，M11/M12独立后备未启用。openTPU保持otpu_asic_top全部33内部SRAM；llaccel保持EPILOGUE_FUSION=0、DMA_MAX_OUTSTANDING=16，外16SRAM bank/DRAM/主机参与测试、不计core面积。没有减硬件规模、加流水或放宽3ns。

**新实测：新AUX回装完整llaccel，现有六组功能测试通过。** 92956从新92934实际修复ODB及既有GEMM/VECTOR原生数据库独立导出/回装：3资源、1851723物理单元、原完整接口和父层连接保持，core内SRAM0（外部16bank保留），无原RTL替代回退。92958用既有观察器实际生成/编译通过，Verilator-j4、make-j4串行，未复用旧可执行文件。92959实际执行六组legacy_seed0/1/2与ready_seed0/1/2，180次连续任务，**243883行/17769493字段/540份完整1MiB外存镜像通过**；六份实际trace与原参考逐字节SHA相同，握手、有效载荷、控制计数及全外存结果对照有记录。
此处是完整规模硬件的这组有限二态/零延迟原父层回装测试，不是所有输入/模式形式等价、四态/SDF、更新后current191公共父版/闲置伴随资源或最终冻结两案例验证。旧open20例/共同6资源测试仍绑定旧版本，不能拼接为新最终版本通过。

**检查器实际破坏对照。** 92971在新实际捕获trace的85行前缀副本中破坏done、dram_req_ready、真实有效SRAM写字节、表头，四项均在对应字段被检出；只改无效DRAM载荷的合法正例仍通过。原trace/参考不改，不重新跑180任务；这是检查器负例，不能代替硬件故障或物理验证。

**时序判断更正及全量定位。** 前18:20记录只读report_checks第一组，把asynchronous组误当全局最差；**该判断撤回，原错误记录保留**。新程序解析全部组、校验MET/VIOLATED与全局原生WNS，并检测组换序/重复组/错模式/篡改结论。真实复位组max +1.775842667ns/min +0.067631237ns均MET；全局最差在clk组：u_attn.og[0]→u_attn.wdata_acc[933]数据setup −1.564345598ns，bit_1352205→u_xbar.rstart[33]输入hold −0.247171298ns。bit_3=rst_n映射本身正确，但不能用该正slack路径解释全局失败。
92965在同一实际ODB/SPEF/Lib/原3ns上重新收集**全部5658个max及35个min负端点**，完整数量/TNS/WNS/单位匹配：max为3421个辅助块输出、2237个D引脚；min为35个D引脚。分类只据实际端点角色，不把所有问题称为复位或继承。
实际最差数据路径当前增量约4.500413ns，其中wire约0.506104ns，8个FA_X1约0.906565ns；当前两条代表路径不含1039项cap违例中的引脚。仅作当前延迟归因，不是零线延迟下界或不可优化证明。旧关闭FA映射方案已有实际较差结果，不重复提交相同候选。r02解析曾错误要求浮点换算因子精确等于10的幂，明确失败；r03改用SHA绑定的原生ns/fF单位标签并记录原始浮点值，无电气容忍度豁免。

**原3ns真实电气质量仍失败。** 新92934局部通孔修复已fresh native DRC0、PG/放置、资源及非目标保持；92945全部623217信号网/1837063端点连通；92948新65545状态/168074锥库语义证书通过（严格5104结构差异保留，不沿用旧字节身份）。92949真实RC/STA测量完成，但max5658/min35负端点、cap1039仍不合格，slew0、fanout无有限约束不算覆盖。92952 active SPEF557931网/1771777端点覆盖通过；65286单端点无互连及9209未连输出单独分类，不豁免质量。AUX0.6ns边界是明确的20%临时预算，不是完整顶层时序。新增/恶化未被当作继承问题，未改时钟/复位/输入延迟/负载或加false_path。

**物理主线继续。** 当前共同父版92538已4096/4096区/256批native0，92547独立76时钟网/157端点资格通过，仅绑定源5429f170，不含电气/完整功能或制造签核。92548固定接线实际布线当前RUNNING；14059条仍未有完整布通/独立验收，841闲置扇出/案例未完成。原父版DRC0不能继承给新布线结果。
新92966完整M8几何、92992独立PG/精确有限功能资源复用及92980/82实际RC覆盖已经闭合，详细结果见下方本次增量；电气质量未通过、未采用为最终底座。原四核心不改。新源尚未汇入统一current191父版，不能拼不同来源局部通过来冻结。

**VECTOR和其他缺项。** M8候选物理/来源通过、setup对e238恶化0/改善37，但4cap项恶化，仍拒绝；e238本身相对原始200setup/26cap退化未验收。92953按网名接口实际完成父/新M8低阈值单网诊断，仍未导出四victim直接耦合，原因未排他查明；生产0.1fF及拒绝判据不变。原net_id导出崩溃和有限候选失败保留。外clock rise/fall和open37常量输出负载仍null（用户未确定），不按0处理；其他独立工作继续。

**资源、版本、目录。** 新作业均4CPU/native≤4/BLAS1；编译生成与build阶段串行，仿真4个各单线程worker，总数≤4。92956 wall164s/CPU162.733s；92958 wall322s/CPU449.290s；92959 wall468s/CPU1337.783s，平均2.858核；92965 wall119s/CPU158.206s。原golden recipe历史cpus1为来源SHA保留，实际新spec/CLI已覆盖4CPU/4worker，不声称单线程4倍提速。不停止/重复活跃实验、不改封存结果或四个保护中的dirty文件。
唯一服务器根 /public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z；review代码1aace9b1c42127ef60f57550dee24e8aecdce8f0，每个driver保存精确源码/配置/输入/工具和关键产物SHA。OpenROAD版本unknown，binary SHA0a4cdf08482bab2d99543e8b32b4b142e013becc7f2c1598afb39ba058193f53。最新索引 /public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-physical-LL-replay-20261028T191214Z/milestone.json，SHA 41ea0187987f76f83f576edf2e844958aa65afc8ced0eceba6a26219163e6a7e。大数据库/完整trace/日志/工艺留服务器；六份既有记录继续维护，新实现源码目前只在服务器固定快照，不把文档更新写成完整代码交付。

GitHub沿用本人账号、Issue55/任务分支/PR58，上一核实head7c5723b0ac82ac23ce701256d2be6eae2c535fac；本次新提交以交付receipt为准。规则rayggxia-project-collab1.0.0；登记复用管理PR5 pending（未重核），board unverified/同步pending（缺board配置），reviewer待指定；继续in_progress，不新建/合并/关闭。
下一步：读92966完整实际结果和92548终态；新M8/统一父版须重新连通、几何、PG/clock、RC/质量及完整两案例功能，不能借原源证明。针对实际ATTENTION数据与边界输入/负载问题做有依据的有限修正，保持原规模与3ns；满足全部条件后才冻结。

**本次完整M8闭合（2026-10-28T19:51:26.039270+00:00）。** 92966已COMPLETED0/4，全部13507信号口及2PG桥连通，新增159528形状对23367025节点检查672560次、异网接触0；9类原资源/逻辑表精确保持、原导体删除0、fresh native DRC0、实际32新track pattern和13509 BPin数量/状态保持。新ODB710410981字节、SHA f128a3cd05ea3c1469be1f7c2ce0aa0f29805403afd9db49fce6beff1ac94d2c。不是完整共同父版或制造签核。

92992又用新进程读取该ODB：放置0、VDD/VSS实际连通。新导出完整AUX Verilog与已通过92959测试的resource_0.v逐字节同SHA94116af9aa49f88fb4e5e68ac9a3ac081bc2a3fda6218962b3aa275da4597afa；原完整功能测试的全部输入重新核验，5项身份/PG/闭合破坏负例被检出。**没有重新仿真**，只在GEMM/VECTOR/原父层/测试环境不变时精确复用六组180任务有限二态零延迟证据；不是current191及闲置六资源或最终冻结回归。

92980/92982已实际提取和独立覆盖：557955 active网/1771801端点、13507口全部落到真实M8接点并检查电阻图；旧层锚点负例被检出。65262单端点无互连与9209未连输出另列。原3ns后M8质量**仍FAIL**：setup WNS−1.5718422563995755ns/TNS−6831.768325758097ns/5691负端点；hold−0.24845087801435276ns/TNS−4.321174651520412ns/36负端点；cap1104/slew0，fanout无有限限制不算通过。此处PASS仅测量/覆盖，不是质量通过。与raw源不同die/track范围，**尚未接受前后恶化归因**；92994仅改die/track、所有源导体/单元/连接保持的匹配范围对照已完成（最新逐身份结果见下文），不是新布局候选或已完成布线方案。

92986复用已封存原始完整负端点清单，未重跑原提取/STA。新5658max/35min中，2099个同名D端点数值更差（2048个wdata_acc），22个未更差；3421边界口、115未匹配D及1个原负表缺项仍未解决；min为6个原查询未覆盖、12负表缺项、17未匹配。原/新边界与clock不同，不能把数值比较当继承豁免或排他因果证明。
资源实测：92966 wall2606s/CPU3531.653s，平均约1.355核；92980 292s/341.688s约1.170核；92982 300s/299.462s约0.998核；92992 186s/194.561s约1.046核；92986 8s/8.286s约1.036核（墙钟秒取整）。均申请4核，native≤4、哈希最多4worker且阶段串行；没有停止/重复活跃实验。92548仍RUNNING，14059固定线尚未闭合，841闲置扇出/case未完成；底座1/3未冻结，阶段二/三未验收、四未执行。
当前review源码e3108ad649131ecb252ac27bbb577bf532c2e568。新索引 /public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-post-M8-closure-20261028T195126Z/milestone.json；SHA-256 1cea67d39e995d396860ee55ef1ae503d46422b4ecb78c2846f604e07d22e723。上一远端a6e54083d09e07d499d8a74b8f0a22fdad4e5e27；本次上传以交付receipt为准，仅六份记录，小型新实现仍在服务器快照。下步先读92994实际匹配范围及92548终态，再做完整端点/电气身份对照、统一父版及最终两完整案例验证。外部clock/37负载仍null，不放宽约束。

**最新同范围判定（2026-10-28T20:16:37.713362+00:00）：当前AUX M8接口候选明确拒绝采用，几何/PG/有限功能资源身份通过不等于电气通过。** 92994/92999对照已完成：仅改die/track，12类原生表全部精确、实际postM8轨道集合相同，557931 active网/1771777端点覆盖。未加M8导体时测量为5679 setup/35 hold/1097cap；这说明不同范围的raw值不能直接归因于新增布线。
93002现已在同一范围/Lib/SDC/RC/3ns下逐身份比较全部负端点：**新增12 setup、1 hold；原5679 setup中3836数值恶化，原35 hold全35恶化**，无负端点消除。93001逐pin确认**新增7cap、原1097中55项恶化**，无cap消除；slew0，fanout仍无有限约束。并未以WNS近似不变或微小差值作豁免。新M8的5691/36/1104完整失败与原始core/自建raw遗留问题仍分开。
方法实际复用：93002只新收集对照源端点，postM8的92998完整原生TSV/metrics复用后由当前解析器重新做count/TNS/WNS/单位核验，**没有重复postM8原生STA**，没有写回旧输出。新明确类型同时绑定全M8来源及匹配范围控制，不靠宽松状态白名单。
93005已把全部62电容退化pin对应到真实native driver/net/placement/master及M8计划路径：全为BUF_X1，其中61直接属于M8引出网，另1为内部place202727/Z。这是修正依据，不是已确定尺寸、合法替换或修复通过。93004只读定位曾因错误使用masters表name字段失败；实际表头为master，原失败保留，源码修正/新目录93005通过，未重复硬件实现。
固定父层92548仍RUNNING，14059真实导线未闭合；841闲置扇出/case及统一最终父版功能/质量未完成。候选1/3未冻结，二/三未验收、四未执行；M1–M8固定/M9/M10+真实via定制不变。
当前源码81c76f15a7f92bce13aab09683fb3e9841aefeeb；最新索引 /public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-same-frame-M8-rejection-20261028T201637Z/milestone.json，SHA ad69b45e5a4a99a2a0f7030fafcd68d833ab3d738557427bed288aeb540f2332。92994 wall742s/CPU796.969s，92999 293/292.494s，93002 115/153.980s；均申请4核、阶段限核匹配，主要串行如实记录。下一步只读核实这62个驱动的真实Liberty、尺寸/引脚及保持原位置的合法性，再决定有限驱动/引出修正；不擅自改原文件或把规划当结果。上一远端51417e286883199ee6a5822abbfa867d4778ab35，本次远端以新交付receipt为准。
