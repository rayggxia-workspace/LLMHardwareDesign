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

当前检查点2026-10-29T01:03:14.503334+00:00，以本段及最新索引为准。完整目标不变，阶段一pass_with_inherited_issues；阶段二/三未验收、四NOTRUN；候选1/3 **UNFROZEN**。

**同一底座边界。** 两完整硬件案例采用计算/状态/存储/控制资源并集；冻结后资源、位置/朝向、内部实现、固定预连线、PG/clock和真实M8接点完全相同。M1–M8固定，只定制M9/M10及真实via8/via9；M11/M12未启用。open=otpu_asic_top及33内部SRAM；LL=EPILOGUE_FUSION0/DMA_MAX_OUTSTANDING16，外16SRAM bank/DRAM/主机参加完整功能、不计core面积。不缩硬件、不加流水、不放宽原3ns。

**固定预连线：实际失败，不是已完成导线。** 92548自然FAILED1:0/4，wall24335s/CPU24357s，约1.001核（四核利用率约25%）。原生先报GRT-0116全局拥堵，未进入详细布线；后续DRC计数查询再报DRT-0002，是次生记录错误。保存2,502,723,609字节ODB仅失败快照，SHA47e51b052c508d4988c89a20aade663892468cbd847bcd2fd9c124227076d793；回执SHA694354b64878322d74b67e6853a4374ef5401fcee6b8eab2c80ac66a3b93f4b8。93104新进程只读完整保存GCell、没有重跑6小时GRT：7层各5,040,025格，总35,280,175层格；M5/M6/M7/M8超容量格分别63,626/236,171/372,529/190,028，总862,354。wall120s/CPU119.319s≈0.994核；回执SHAf91ddbb7e49b87097b7ff191e152c8ba08d97317808b5bb12fbd03c768a22f40。

93107对全部862354行按真实六宏矩形作空间归属：633205格中心位于宏外（约73.43%），5595个宏外中心格仍与边界相交，热点在M7底边、M6左边的64×64网格区域。**完整14059目标中，14059有数据库guides，实际有wire的目标为0**。guides不是导线，统计不是完整物理连通。wall6s/CPU4.877s；回执SHAa729ea6d1ff978201c6a93589e11353db859d63556fdc3bfad8aa72ff0bf6b9d。该归属不等于逐PIN/OBS碰撞或排他根因，不能据此删几何；应反馈公共IO/通道与预连线策略。93103首次读回把DRT的15566信号/clock网数误作native全网数而失败；原生库存实际另含2PG共15568，修复为绑定真实191实例/15568全网后才运行93104，未去掉身份守卫，原失败保留。

**接入点：完整实测部分改善，仍未通过。** 93086完整native PA/GRT实际完成、两诊断DB已保存，但独立读回脚本缺need而Slurm FAILED；93093新目录逐SHA及真实独立读回恢复了完整观察证据，没有重跑PA。13507端口、27014盒、47262AP行一致；5066个M8盒无AP，其中53在选中网。93093回执SHAf9187747c0b938a88569d1a8e80a5a774e4c6c4f0b24728500627d9bf7ba5f65。所有端口有原低层AP不等于全部新M8接口可用。

93095小对照、93100原生helper资格后，**93101完整设计观察COMPLETED0/4**：只按真实pitch/offset补充相邻M9轨道元数据，原52模式保留；不增加M9导线或器件、不移动引脚/内部cell、不删PIN/OBS/导体、不软件补AP，实际布线上限仍M8。完整546459实例/124targets/62splits/15489424保护不减。缺M8 AP从5066降至**1642**，剩余在负X左侧，其中1口在选中网；43862个AP均在自有真实盒内。PA后/GRT后与实际新进程ODB读回一致。**这只是native接入机制部分改善，没有执行详细布线或完整接入/布线验收。** wall961s/CPU3404.059s≈3.542核（四核利用率约88.6%）；源码cedf97f7f1f65a5570da3d2c0cac080f315a0083；回执SHA85f5d98c466134abb8eb041a2e1f3e847419bba7f317446685b4266880940685。GRT后UNACCEPTED诊断DB1,484,948,574字节，SHA74b0b27c315c1d8a80041dcaa2a94a405737bf8bb6473c6140a7739024839e4e。旧93099 Rect对象误作列表在PA前失败保留；新代码按实际阶段闭合才标actual，不沿用旧预设布尔值。

**检查器与后续实际动作。** 93105只在独立小夹具验证所需M8接口守卫：真实native正例、禁用实际AP方向负例、恢复正例、删除实际M8 AP负例均检出；回执SHA6b0ca82e34402cb23884eb2ae523d573e4d32ab1c727fefa8a8e96d72716f8c4。旧“每个金属盒都有AP”守卫不修改/不放行；新M8接口检查器尚未接入成功全设计源，完整检查程序已写但未执行，因1642真实缺口未解。它不代替原低层物理连接、全DRC/PG、RC或功能。93109实际在native PA启动前失败：旧夹具适配器只接受M6/M8双形状，而剩余左侧实际为M5/M8。故min_access_points=1/2/4三项原生调用均NOTRUN，不能把配置编写当实测。错误回执SHA094c4986134c93dc2f3226e187eea38057f73eb580db95bf9892790f6f4ec098。下一步先按实际低层形状参数修复此案例适配，再测native设置；不据此重复完整PA。

**仍有效的限定通过。** 93016新增62BUF_X2真实合法放置、原546397实例/原导体阻挡保持及off-site负例；93022实际新旧65545状态/168074状态输入输出锥一致及真实状态破坏检出；93058新UNROUTED源placement0/VDD1/VSS1；93056闭合prepare+15来源破坏拒绝；93069完整13507口读取器+8数据破坏拒绝。均不能当新完整整机、四态/SDF/所有输入形式等价、实际线路或电气验收。旧LL六组180任务/243883行/17769493字段/540份1MiB镜像、旧open20例及active+idle只适用各自源版，不能转移为新增driver/当前191/最终底座通过。

**失败、未执行与缺项。** 93067在bit118真实M8盒无AP失败，没handoff/没fresh-detail；93018原DRT1231失败保留。93024/26/29/34/36 child_launched=false，五项实际RC/覆盖/完整LL准备/编译/回归NOTRUN。93053记录器失败与93065只读复核不变更原终态；49旧口AP点相同不覆盖全部13507口或方向/worker可达性。93081拆PORT两项真实DRT0302失败未采用。旧未加62buffer M8 AUX原3ns setup5691/WNS−1.5718422563995755ns、hold36/WNS−0.24845087801435276ns、cap1104/slew0质量拒绝；不是新driver测量。VECTOR新增4cap及e238相对原版200setup/26cap恶化未解，不设epsilon/复位例外/放宽时钟。外clock rise/fall、open37常量输出负载用户未确定/null，不填0。每例841模式相关闲置扇出、当前191统一PG/clock/固定线/完整功能仍未闭合。

下一步最小动作：依据93109及1642端口的真实轨道/层/坐标选择可验证接入处理；依据93104/93107的保存拥堵反馈公共IO/通道/固定连接安排，不缩设计、不把guides当wire。实际线路完成后独立全连接/接触/fresh DRC/PG、同frame RC/完整负端点与电气、新完整功能；统一同源全部条件通过再冻结，再做两完整case最终M9/M10定制。

唯一根：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/；93101在runs/auxiliary-driver-adjacent-track-complete-PA-capture-r01-4c-02/；93104在runs/closed-fixed-parent-route-native-grid-r01-4c-02/；93107在runs/closed-fixed-parent-grid-macro-attribution-r01-4c-01/。
最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-native-access-partial-improvement-and-actual-congestion-20261029T010314Z/milestone.json
SHA-256：**b8962b17db48829974621da22f9ba70c1fb5c6b8f7ba0ecfcc4ae3f02a448f02**。
review源码481d2af73c43c06f756ece9740d2eb552051c93b；所有job spec/source_revision/submission及关键输入/工具/输出SHA按源绑定。OpenROAD版本unknown、binary SHA0a4cdf08482bab2d99543e8b32b4b142e013becc7f2c1598afb39ba058193f53。父索引和上一版六记录完整先封存，不改失败/封存结果。

同一Issue55/task/55-full-block-integration/草稿PR58；前次精选远端b6be911b647331ea24dbf60d7b2864b04391166e已核验，本次发布另有独立delivery receipt。大ODB/DEF/SPEF/完整日志/trace/工艺留服务器，远端仅精选小记录，不冒称完整后阶段源码已交付。所有新job4CPU/native≤4/BLAS1，单线程明确单列，无独占，不超分配，不停/重复活跃作业，不改四个受保护dirty路径、原资料或其他任务。rayggxia-project-collab1.0.0；登记PR5 pending复用未重核，board.json缺失/Projects unverified/同步pending，审查人待指定，Issue继续in_progress。
