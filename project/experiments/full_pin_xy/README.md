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

`collect_extension_snapshot.py`只收集已完成严格流片视图探针的日志、规则分类、原始报告/SHA与已完成电气观察。大GDS与大型lyrdb保留远程。可用deck全部执行成功仍不等于LVS、真实父层可达或生产工艺签核。
