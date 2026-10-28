# 六块完整覆盖与实际 pin 接入试验（Issue126）

复用 [PR120](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/120) head `4f91e098127b4320ce50dcb29165a7af1fca559c` 的 ACT/GEMM 候选，不重新生成。
本目录将范围补齐到 ACT、MXU、openTPU SYSTEM、GEMM、VECTOR、llaccel SYSTEM。
SYSTEM 复用 Issue55 已存在的实际包装；完整功能归属18项，不把每项都重复计为硬宏。

报告：[中文 HTML](../../../docs/experiments/issue-126-full-pin/report.html)。
阶段必须分开：清单 → 候选几何 → 实际接入 → 连通/DRC → RC/STA/电气 → 父层/完整资格。
24,767 原始信号 pin，三方案74,301行；候选覆盖通过不能替代后续阶段。

## 本地恢复、候选与报告

依赖 Python 3.10+、numpy、pandas、scipy、matplotlib；本次本地 Python3.13.5。
仓库内轻量冻结输入和压缩 CSV 足以核对交付，不足以离线重跑全部物理过程。
大型真实金属快照和 ODB 位于 `sources.json` 指定的授权集群；不能由绘图推断空白金属。

```powershell
python scripts/check_project.py
python project/experiments/full_pin_xy/validate_repository.py
# R 是恢复的独立分析目录，不允许在 ref-project 或历史实验目录原地运行。
python project/experiments/full_pin_xy/inventory.py --root R
python project/experiments/full_pin_xy/bind_interfaces.py --root R
python project/experiments/full_pin_xy/expand_candidates.py --root R --cases mxu vector opentpu_aux llaccel_aux
python project/experiments/full_pin_xy/align_candidate_grid.py --root R
python project/experiments/full_pin_xy/validate_candidates.py --root R
python project/experiments/full_pin_xy/build_deliverables.py --root R --out docs/experiments/issue-126-full-pin
```

恢复步骤：把 `data/*partition*.gz`、层次/输入manifest等按文件名解压到 `R/partition-r02/`（原本gz的graph/jsonl保持压缩）；只读导出到 `R/physical/<case>/`。
保留已有 ACT/GEMM 未压缩 CSV、groups、metrics、meta 和图；可从 PR120 压缩表解压，核对其 SHA，再参与全覆盖检查。
候选生成器只接受新增四块；不会重算 ACT/GEMM。`collect_partition.py` 把已验证冻结顶层连接和物理边界端口提成紧凑图；不包含完整RTL包装实现，原完整代码/证明仍按 Issue55 路径和哈希索引取得。

`inventory.py` 使用 leaf_origin 与 hierarchy 审核全叶归属，生成完整逐bit接口、连接矩阵与pin映射。
`bind_interfaces.py` 对六块真实BTerm与逻辑接口名称、方向、数量逐项匹配，保存真实对端pin原金属层。
对端pin层不等于原父层handoff层；后者仍未知，不补猜M8，也不把连接统一升到M11/M12。

## 只读提取

在授权新任务目录运行；本次根目录为 `/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027`。
`run_exports.py` 配合 `export_job.sh` 从四个ODB导出宏、BTerm、端点、BUF/INV追踪端点、M4以上原金属/PG/通孔和技术尺寸。
`run_supplement.py` / `export_supplement.tcl` 另导出真实 master/block OBS，所有正交实例变换用实际bbox检查。
未把 cell bbox 投影当作金属占用；全体下层路由的真实连通检查由实际接入阶段独立完成。
原数据库以只读bind挂载，并在运行前后检查SHA及源文件状态。导出作业92260、补充92265均已完成。

## 匹配的小区域物理对照

`prepare_trials.py` 从每块已有C中选同一bus的8个局部pin，需有真实端点依据、没有原pin层直接矩形/基础间距/宏碰撞；这不是通孔或DRC保证。
`A` 原始ODB不重接；`A_replay` 同一8pin、原XY，重新接线；`Aopt` 只在其相同原边/层的既有槽位内重排；`B/C` 对应候选坐标。
其余pin原位、全部单元master/位置/方向、宏、外框、CTS和PDN保持。先核对真实 `place_pin` 后的层/尺寸/XY，再只rip相关net的dbWire，实际GRT/DRT；DRT仍可能修其他线路，不能把全块线长差全部归因于8pin。

```powershell
python project/experiments/full_pin_xy/prepare_trials.py --root R --out NEW_TRIAL_INPUTS
```

提交前先commit驱动，用 `git archive` 打包为全新的 `drivers/<commit>/code/`，写 `driver_commit.txt`，冻结input目录；不能在活动作业读取的代码目录覆盖脚本。
在集群对新尝试名执行：

```sh
sbatch --job-name=hpy-p126-act --export=ALL,PINXY_DRIVER_DIR=/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/drivers/5107f46/code,PINXY_INPUT_SET=trial-inputs-r04 trial_job.sh act NEW_REVISION
```

实际尝试名全新；`time=0`、c64/8CPU、每次最多两个OpenROAD各4线程。使用原工具镜像，不安装新工具。
原四块signal M2–M10/clock M4–M10；SYSTEM保持原M8上限。`set_routing_layers` 是当前版本支持入口，旧DRT `-bottom_routing_layer/-top_routing_layer` 会直接报错，首轮失败保留。

`physical_trial.tcl` 分阶段记录实际布线、fresh native DRC、PSM、RCX、setup/hold、电气/约束/注释覆盖和抽象导出。
`export_access.tcl` + `check_access.py` 对选中网络的**所有**真实ITerm/BTerm访问矩形、各层dbWire与实际via定义做独立几何连通检查，并报告孤立导体；不拿ITerm中心或逻辑net相同当成物理接通。
只验证selected-net不能报告全块/GDS LVS通过。原生 `odb::orderWires` 在此二进制需要未暴露的Logger，失败明确保留；不使用陈旧 `isConnected` 标志制造通过。
`check_connectivity.tcl`、`obs_probe.tcl` 是保留的失败API探针，不是合格验证入口。

基线时序/电气失败继续保留。当前边界SDC没有完整外部驱动、输入slew、输出load模型，即使独立块STA通过，也不能宣称完整系统签核。
父层匹配数据库、真实handoff层/穿层路径、实际macro OBS可访问性、全块连通和适用完整规则仍需独立验证。

## 不可混用的指标

- 最近追踪端点L1、窗口包络、采样密度：几何指标。
- `report_wire_length` 逐层长度、真实via与拥塞：布线数据库/工具指标。
- OpenRCX SPEF、STA路径/电容/slew：实际提取与分析，受原边界与宏模型完整性限制。
- 外框没变：不能宣称block面积节省。没有真实通道/整体边界缩小，也不宣称系统面积收益。

实际发现的RCX状态问题：同一ACT数据库在load/constraint后原样写回仍独立DRC=0，extract后保存再读入报12534项。旧checked.odb/analysis_after_RCX.odb均只作诊断，不作为物理母本。`finalize_job.sh`必须从routed.odb（A用原始ODB）另起进程导出clean.odb，并验证字节一致、独立DRC和全块几何连通；SPEF/STA记录同一提取前来源。该修复不改规则，旧失败保留。

`align_candidate_grid.py`是r01→r02的增量修订，只对制造网格做小于0.0025μm的修正，保留r01坐标/指标/失败；需要从真实数据库取得`R/native_grid/<case>.tsv`，不能猜网格。先恢复r01到全新R目录，再生成r02；已修订目录不重复运行以覆盖历史。`prepare_grid_trials.py`保留相同8pin cohort作修订后重试。

## 增量完整C、严格GDS与实际电气观察

`prepare_full_trial.py --cases gemm mxu vector opentpu_aux llaccel_aux` 支持冻结全部C可移动集合；完整C不保证可布通。B控制只取相同C集合，不能冒充完整B；其他pin不动。

完整C路由92365–92369按afterany串行，后续独立clean检查92370–92374逐项依赖；驱动f08e026，inputs/trial-inputs-full-other-r01。范围GEMM3039/MXU1964/VECTOR1022/openSYS1768/llSYS13184。结果没完成前保持运行/待验证，不推断通过。

`streamout_job.sh <new-revision> <case>` 使用已有KLayout和未修改FreePDK45.lydrc，严格合并所有实际单元，不设置allow-empty，不关闭FEOL/BEOL/off-grid/antenna。ACT原始/完整740pin C的92375已实际完成：两个fakeram无GDS，严格合并返回2；保留下来的诊断GDS不完整，deck报678/770项天线错误，不是完整规则签核。其余五块GDS作业92376/92377/92378/92380/92381由相同实际clean来源继续验证，C仍为各8pin局部。

`audit_abstract.py`只统计真实导出LEF的同层PIN/OBS正面积交叠。它不区分同网金属语义，不能据相交数宣布父层无法接入，也不能据无相交宣布可接入。

`summarize_path_electrical.py`以有界内存解析native OpenSTA JSON路径，原值单位为F/s，保留来源SHA和观察范围，不能当作全部net的负载/转换覆盖。`run_electrical_audit.py`使用已完成、SHA匹配的报告；完整ACT C另与标准JSON解析交叉检查count和最大负载。首轮旧回执无selected_pin_count导致驱动KeyError，保留92382失败；r02从原始冻结Tcl恢复精确cohort后由92383重试，不更改物理结果。

`collect_extension_snapshot.py`只收集已完成严格stream-out视图探针的日志、规则分类、原始报告/SHA与已完成电气观察。大GDS与大型lyrdb保留远程。可用deck全部执行成功仍不等于LVS、真实父层可达或生产工艺签核。

## 新增完整C修订和受控父层

`prepare_electrical_revision.py`从实际GEMM失败驱动/写strobe关系恢复完整字节29/30，共18pin；原3039重接cohort不变，实际3021移动。`prepare_mxu_repair.py`按真实lane0恢复33pin并修复两处signal-to-VDD内部M5点；1964重接cohort，1931移动。完整逐pin补充表与原ABC独立。两次实际重布线后的独立native DRC/所检全块几何连通通过，现有模型电气报告0；不是完整资格。

`stage_incremental_evidence.py`复用已执行修订输入，GEMM发布副本只修正恢复位的几何指标，强制Tcl SHA与实际执行版一致。`validate_repository.py`把两份完整补充表与clean ODB的所有实际信号pin逐项比较，不把图或局部样例当全块证据。

```sh
python project/experiments/full_pin_xy/make_physical_summary.py --root R
python project/experiments/full_pin_xy/stage_incremental_evidence.py --root R
python project/experiments/full_pin_xy/build_deliverables.py --root R --out docs/experiments/issue-126-full-pin --keep-figures
python project/experiments/full_pin_xy/validate_repository.py
node project/experiments/full_pin_xy/qa_report.mjs docs/experiments/issue-126-full-pin/report.html QA_OUTPUT_DIR
```

`prepare_controlled_parent.py --root R --out NEW_INPUT_DIR --design opentpu --focus act`（或llaccel/gemm）从真实冻结三叶图生成**新受控父层**；其历史handoff仍未知。真实Verilog/Liberty bus映射由`verify_parent_graph.py`在PG/路由之前验证全部端点、方向、目标层和bit↔native net双射，拒绝把同值常量并网。端口Liberty未表征，仅链接/路由使用，禁止父层STA/电气资格结论。

`parent_job.sh INPUT_NAME NEW_REV [A A_replay A_child_replay Aopt B C]`从真实已核对的叶clean ODB导出详细OBS，不删除原OBS。`filter_parent_pg.tcl`对**新父层**PG通孔检查真实M7–M10各层障碍，安全位置选择后仍必须通过PG/独立native DRC/所检全块几何连通。各变体冻结A的外框/PG/TOP_IO/单元位置；A不通过不晋级。r07 openTPU92441核对6618端点/3408网，PG通过后DRT运行；llaccel92458独立27050端点。早期halo/PG/bus失败按各原目录和stage_failure_actions保留。

GEMM严格GDS92376已自然完成，A/8pin C合并成功但1346/1358项天线违规。其余四项原GDS任务经核实全部尚未开始且无输出后，整合成92430（16CPU，4case×4deck threads），没有耗时中断活动任务。ACT/MXU分别缺2/4个fakeram器件GDS；不得用伪造几何替代签核视图。

`verify_fixed_pg_contacts.py --root R --case llaccel_aux --actual ACTUAL_FINGERPRINT_DIR --out NEW_PROOF_DIR`对真实移动后全pin回读、输入ODB SHA、未变PG指纹和真实导出PG金属做精确同层直接求交。llSYS完整C确认26pin/44对直接接触，不是间距猜测。`stop_known_invalid_pg_trial.py`是只用于识别92369新无效变体的严格守卫，核对job/name/source/driver/cohort/实际文件SHA后才能停止，不按耗时，不修改其他job/原始数据库；此脚本不作通用取消接口。完整失败检查点仍留远程，局部C8检查不代表全C通过。

## 实际SPEF叶模型与独立父层RC/STA

`timing_model_job.sh NEW_REVISION case... [--variants A A_child_replay Aopt B C]`在8CPU分配内最多2×4threads，从独立clean ODB与对应原已提取SPEF导出模型。复用项目`write_timing_model`流程，源ODB/SPEF/SDC/Lib锁SHA；重新读入模型并检查全部信号bit/方向，bus聚合声明及PG口另计。SPEF重读的最差setup/hold必须与原报告在1e-5ns内一致；未知额外port、丢bit或重读不符均失败。现有目录拒绝修改。调用前按本目录native运行约定指定冻结PINXY_DRIVER_DIR，不能复用已存在的NEW_REVISION输出。

实际r02的六块A/C12份及r03的ACT/MXU三控制、GEMM两控制共8份均完成，20份逐bit/重读校验通过；全部仍是研究导出模型，不是SRAM器件表征签核库。llSYS C仅8pin局部，原全C失败保持。r01的旧元数据字段和bus/PG分类探针失败保留。`collect_timing_model_snapshot.py NEW_NAME`收集原始Lib/port/report/日志及来源SHA，未完成导出不列为通过。

`parent_rc_sta_job.sh PARENT_REV DESIGN FOCUS NEW_ANALYSIS_REV A A_replay A_child_replay Aopt B C`只分析通过独立native DRC、所检全块连通及双PG门槛的实际父层。按真实child view物理ODB及clean回执SHA查找已导出模型，禁止用其他XY版本或路由占位Lib替代；只改派生Lib的library/cell声明名匹配实际macro alias。新父层2.5ns是固定研究基准；外部I/O delays/driver/slew/load仍缺，模型也缺minimum_period，内部叶块失败必须单独保留。即使某报告为0也不输出完整系统资格。RCX在单独分析进程执行，验证物理输入SHA未改，不写提取后ODB为物理母本。

92476/92477为目前未执行的依赖作业，分别等待92441/92458实际父层和对应模型任务。更早四个post-analysis仅在全部pending、输出不存在的守卫后由`supersede_pending_parent_analysis.py`替换，保留前后Slurm和命令证据；物理任务/冻结驱动不修改。`release_pending_controls.py`只释放两个尚未启动SYSTEM控制的调度串行依赖，不新建/取消物理job，不变输入/目录/CPU；原活动VECTOR/父层不变。

## 2026-10-28 接续（历史状态不替代最新回执）

旧父层已终态native11/GRT失败，92476/92477受物理门槛阻止，未执行RC/STA。用户已授权研究M11/M12，并确认六块资源并集/共享实际固定导体；不是两套独立父层并排算共享底座。

- `prepare_act_access_revision.py --root R --out NEW --case CASE`生成全pin增量表与真实相邻层轨道接入窗口。使用已提交冻结驱动、完整信号重布线和独立finalize，原层/尺寸/语义/单元/PDN/OBS不变；新方法不与旧局部rip直接算纯XY收益。
- `prepare_common_base.py --root R --out NEW`只编译交错布局及256段有限M10预连提案；`compile_shared_topology.py --root R --preparation P --out NEW`实际执行两模式完整逐bit图校验，声明37独立原常量及1个idle clock驱动。`common_link_job.sh INPUT NEW_REV`原生链接/`verify_common_native.py`核对全部34954端点/17686逻辑分量。均不等于实际共同布局/布线/冻结。
- `prepare_escape_landing.py`从真实信号/PG/OBS选择新的父层M10中间点，`escape_landing_job.sh INPUT NEW_REV`实际重接并核验其他859父pin/所有PG不变，原叶ACT M5/M6不抬层。92719当前几何门槛通过；初始及失败变体保留。
- `escape_rc_sta_job.sh NEW_REV`对已接受的ACT Aopt/C真实夹具做RCX/SPEF和同等新增I/O研究策略下的2/10/50fF敏感性。92726工具兼容失败与92732真正执行后hold/电气失败、604零线长接触网未标注提示全部保留；不保存RCX后ODB。
- `run_leaf_eco.py`另存重定尺寸/缓冲/布局的成本、全部pin/PG/die指纹、native/连通/RC/STA。不能将无命令错误视为电气修复成功，不能把删除filler说成面积节省或纯XY收益。
- `extend_upper_tech.py`原M9/M10规则/RC外推研究M11/M12，原十层规则块SHA不变。实际两网小例及独立native/连通通过，仅验证工具/接入；制造deck、12层校准RCX及完整系统仍未验证。
- `collect_continuation.py NEW_NAME`只写新快照，运行中与未复制大文件分别记录；`refresh_continuation.py --root R --out REPORT_DIR`仅刷新新增节/PNG/SVG与SHA，原ABC和旧物理发布命名空间保留。`validate_continuation.py`由主验证器调用，检查24767候选及已取得9031个新实际pin的逐项对应、层/方向/网络/尺寸/坐标、常量、重复/越界和原生快照字节哈希；不是物理资格证书。

源码/当前作业及恢复入口见`docs/handoffs/2026-10-28-issue-126-common-base-continuation.md`。不覆盖原参考、其他工作树、冻结驱动或活动作业；每次提交/复用前重新核实远程状态。

`collect_terminal_leaf.py CASE REV NEW_NAME`只补收已经产生终态的原生回执、timing和pin表，不再运行P&R，也不替换旧快照；`refresh_continuation.py`会把这些新增终态补入阶段表，实际完整资格始终由各项检查决定。当前五块11260个新实际pin核对通过，llSYS完整窗口仍单列为执行中。


## 10月28日晚恢复：真实失败、驱动修复与估算模型

`prepare_local_pin_patch.py --root R --out NEW`生成LL完整13507点表，只增量修改真实四项native marker涉及的三点。`local_pin_patch_job.sh INPUT NEW_REV`实际重接线；92747因另一未移动bit_4812无AP失败，不能只检查坐标就宣称修复。

`constraint_audit_job.sh NEW_REV`只读原始LL/PG-C及GEMM/MXU窗口视图，核实实际NDR/驱动/dont-touch/矩形宽度与源SHA；不代替via、NDR spacing或完整规则。API查询失败的r01-r03原样保留，r04/r05取得原生结果。

`run_leaf_eco.py`可用`PINXY_ECO_TARGETED=1,PINXY_ECO_ELECTRICAL_ONLY=1,PINXY_ECO_INCREMENTAL=1`运行精确三处GEMM/一处MXU X2换型，`cell_semantics.py`核对Liberty逻辑和触发器状态，原端口网络单列检查，恢复原master种类填充。这是成本ECO，不是纯XY；设计形式等价仍待独立执行。

支持的原生GRT估算排查用`PINXY_ECO_FRESH_GRT=1,PINXY_ECO_PLACEMENT_HEURISTIC=1,PINXY_ECO_INCREMENTAL=1,PINXY_ECO_C_ONLY=1,PINXY_ECO_HOLD=1`配合`leaf_eco_job.sh NEW_REV vector opentpu_aux`。精确源SPEF重放与修复阶段GRT估算分开；末端必须真实DRT/RCX/STA。SYSTEM保持M2–M8/clock M4–M8；r06/r07的EST-0104/Signal11不删除，r08支持diamond合法化并保存NOT_ROUTED检查点。不得把估算slack或中间合法化0错误写成最终通过。

`collect_resume_progress.py NEW_NAME [JOB...]`在本人Slurm资源内补收版本化证据；`resume_report.py`由refresh自动生成中文接续节及真实PG/旧pin/native marker/proposed局部图。`validate_repository.py`增加全部13507局部候选的不遗漏、不重复、层/尺寸/网络/方向/越界、恰好3点变化及原文SHA检查，仍非物理资格。


`eco_view_job.sh CASE SOURCE_ECO_REV NEW_VIEW_REV`仅接受已完成native0/所检全块连通、pin/PG/die原样的定点ECO，复制预RCX ODB并导出LEF（含详细OBS）、DEF、实际网表、匹配SPEF研究时序模型；检查全部位/方向/PG/外框及SPEF重放。92776/92777已导出GEMM3753/MXU2172位r02视图；完整规则/形式等价仍待验证。`checkpoint_legalization_job.sh NEW_REV`只在隔离进程复用SYS已有修复检查点，保持原PG/pin/die、恢复原种类填充并保留check_placement；输出NOT_ROUTED，不能冒充接入/DRC/STA完成。

`checkpoint_route_job.sh NEW_REV`从SYS已检查的隔离放置继续真实完整重布线/PG/RCX/STA/fresh native DRC；逐原OBS ID及几何核对，新增OBS须恰为原临时接入窗口，详细布线后只删新约束。`PINXY_STREAM_ECO_VIEW_REV=r02 streamout_pack_job.sh NEW_REV gemm mxu`只针对新成本ECO视图做严格GDS合并与不改deck的全量规则检查；不再重跑旧A/C。
