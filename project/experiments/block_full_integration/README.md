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

检查时间：2026-10-28T17:56:31.417898+00:00（UTC；北京时间UTC+8）。Issue55 / task/55-full-block-integration / 草稿PR58，负责人huangpingyang04-lgtm；整体in_progress。阶段一pass_with_inherited_issues，二/三未验收，四未执行；资源并集底座候选1/3，**未冻结**。

**目标与冻结边界。** 两完整硬件案例共享全部Block、有源/存储/控制资源、位置/朝向、内部实现、固定预连线、PG/clock及M8接点。M1–M8固定，仅M9/M10及实际M8↔M9、M9↔M10通孔定制；M11/M12独立后备未启用。当前必要低层修正仅在本人未冻结派生副本。openTPU保留otpu_asic_top全部33内部SRAM；llaccel保持EPILOGUE_FUSION=0、DMA_MAX_OUTSTANDING=16，外16SRAM bank/DRAM/主机参与功能测试而不计core面积。未缩规模、加流水或放宽3ns。

**新通过：共同父版整片原生几何及独立来源/时钟图。** 92538实际75985s（21h06m25s），4worker×native1，完成4096/4096区、256闭合批次，原生DRC记录0。完整源/PIN/OBS/PG/导体保留，各批前后DEF身份一致。92547独立核验相同源及完整覆盖、76个完整时钟网络/157必要端点，通过PASS_CURRENT_SOURCE_COMPLETE_TILED_NATIVE_DRC_AND_CLOCK_GRAPH_ONLY。源ODB SHA 5429f170d2da4e870e33da3efc8f528737ce3378cc1959b26e24610e96211508。10金属层边界与真实via8/via9负例及缺区/重复区/改源/改box/非零marker控制有记录。**只代表当前共同父版的原生几何和时钟图，不含RC/STA、clock质量、完整功能或制造签核。** 92793实际跳过恢复，没有重复扫描。

**预连线与实际布线。** 14059固定连接原为方案；92548当前 RUNNING，已进入真实详细布线/引脚访问，尚无完整闭合receipt，不能称14059条已布通。原父版DRC0不能继承给新布线结果。每案例841闲置扇出未完成；新固定父版需独立读回/完整连接、固定和非目标保持、PG/clock、fresh native、真实RC及质量检查。

**新通过：AUX单通孔修正。** 92934仅在net _280627_固定坐标(2437130,2084740)DBU将实际tech via1_4换成via1_3：cut和M1落脚不变，只把M2落脚在x两侧各扩70DBU。新完整独立native DRC0，放置/PG拓扑通过；16330527条非目标形状及九类完整资源/端点/工艺表保持，16条目标形状限定差异核对通过。1320s/CPU2249.452s，平均1.704核。新ODB：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/auxiliary-native-repair-single-via-shape-r01-4c-01/repaired.odb，708889986字节，SHA 8ce385e5f7a9cb68eaca80853d651f789091655e173dfd50681d12b422340387。**尚非全网连通、功能或时序通过；原92810仍FAILED。** 旧92797字节身份不能用于含resize/buffer的新源。

**失败和修正记录。** 92922两条M2补线的实际目标图2端点/1分量、无异网接触，非目标及11类表保持（92939独立补核）；但局部native仍1条Metal Spacing，拒绝，未执行其后全AUX DRC/RC/功能。1175s/CPU1176.493s，约1核。随后单通孔候选采用不同修复，不重跑全路由。92937/92938实际宿主COMPLETED0→容器准入→子程序启动，但--output误填文件路径导致父目录不存在，在实质状态/全网计算前失败；保留child日志/continuation，不写成状态或连接失败。r02已改用独立输出目录；92942实际65545状态/168074锥检查仍有5104严格结构差异，状态/端口相同且负例检出，尚未通过。92948随后以已独立验证的实际Lib真值/引脚对称和寄存器驱动族语义，在这份新物理网表上重新检查65545状态/168074锥，差异0，实际状态D反相/时钟模型破坏负例检出，COMPLETED0/4通过限定库语义证书。严格5104结构差异原记录保留；这不是上游RTL/四态/SDF或完整案例功能证明，不沿用旧字节身份。全网92945仍需实际闭合，见current_evidence。

**VECTOR仍质量拒绝。** M8候选真实52形状/41网/3边界、八表/非目标和独立来源通过；原27条native逐条保持/新增0，不是零DRC。原3ns实际RC/STA相对e238 setup恶化0、改善37，却4项既有cap恶化，拒绝；e238本身相对原始仍200setup/26cap恶化。92927只读扫描8896890行发现4个victim网的M4导体均在旧M7/新M8路径投影下方；安装版OpenRCX默认coupling_threshold=0.1fF、context_depth=5、cc_model=10。无直接耦合输出记录不等于无上下文影响；尚未证明排他原因。独立弱耦合诊断采用1e-9fF，仅写net83203、不跑STA，不改生产0.1fF或豁免4项退化。92941因SDC只读挂载缺失在提取前失败；r02/92946修正挂载后实际完成父版提取，但-net_id选网SPEF导出触发OpenROAD SIGSEGV11，新M8版未执行，诊断整体失败。保留原日志；先用小fixture验证替代导出接口，再决定是否另跑，不以安装版help支持等同实际可用。

**阻塞及最小下一步。** 继续92548实际固定布线和独立验证；完成新AUX严格状态锥差异的库语义检查/全网，再以原3ns提取RC、做逐端点质量与最终功能；VECTOR先定位实际CAP差异再做有限修正。各合格物理源合入同一父版仍需统一验证，不能拼不同版本的通过。外部clock rise/fall、open37常量输出负载仍null（用户未确定），不阻止其他独立工作。正式Block/任意LLM未证明；route入口目前固定父层范围、replay目前native清单范围，冻结及最终两case定制未完成。

**追溯与协作。** 唯一任务根 /public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z；本轮review源码 b2991d5cadc340172a9ca312b0fe2d7b2f5045f5，各作业原始commit/配置/工具/输入SHA/日志/CPU在索引。OpenROAD版本字符串unknown，binary SHA 0a4cdf08482bab2d99543e8b32b4b142e013becc7f2c1598afb39ba058193f53。整片检查CPU294872s/墙钟75985s，平均3.881核，约占4核97.0%；新作业均4CPU/native≤4/BLAS1，不停/重复活跃作业、不超额。索引 /public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-state-closure-20261028T175958Z/milestone.json；SHA 2ba969769ad2fe7fb120671f193ec6463daac922b9a7b58b44f03f1555fee7e7。保留历史/封存结果，只更新原六份任务记录；大ODB/DEF/SPEF/全日志/工艺留服务器。

沿用本人账号/Issue55/现有PR58，不新建、合并、关闭。上次核实远端afe2654e254059910a01799b2840021b85413d84；本次发布以独立交付receipt为准。规则rayggxia-project-collab1.0.0；登记复用管理中心PR5 pending（未重核），board unverified/同步pending（board.json缺失），reviewer待指定，保持in_progress。原232939字节方法全文在155133Z归档previous_methods.md及Git历史，本次previous_methods仅保存更新前17KB稿。
