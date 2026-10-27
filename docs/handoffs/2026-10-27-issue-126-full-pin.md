# Issue126 持续执行入口与阶段证据

## 最新：2026-10-28（中国标准时间）

正式报告复用原14对PNG/SVG和ACT/GEMM6对，不改候选原图含义。最新物理快照milestone-r10含71条trial记录；20份真实SPEF研究叶模型（r02 A/C12份+r03控制8份）在timing_model_snapshots/milestone-r02，旧r01驱动探针失败保留。全部信号bit/方向及SPEF重读setup/hold一致；Lib bus聚合与PG口另计，不增加原始24767pin。所有导出模型仍无minimum_period，系统I/O模型/真实SRAM资格不完整。

VECTOR完整同组：A_replay6797818、Aopt6830343、B6856466、C6908170μm；C约+1.62%，A/Aopt/C独立native0，B4项，电气/时序行59/61/99/103，保持负结果。ACT/GEMM/MXU结论与前述−6.40%/+1.19%/+4.30%不变。llSYS全C已失败；92479只读索引其moved/ripped/global等约3.04GB产物，SHA见checkpoint-index.json，不能当完成route。

父层92441(openTPU r07)/92458(llaccel ll-r01)继续实际P&R，全部端点及前置双PG已通过，尚无完整native/连通/时序终态。92476/92477是最新依赖post-analysis，driver502a327，精确按child物理ODB和clean回执SHA匹配真实模型，分析A/A_replay/叶重布线/Aopt/B/C；旧92467/68/72/73仅在全部pending且无输出后替换，守卫调度证据入库。物理job未改。新基准2.5ns、缺I/O delay/driver/slew/load，始终不宣称系统资格。原SYSTEM物理控制92392/93在核对未启动后只释放调度串行依赖，原job/输入/驱动/目录/CPU不变。

WELL语义92481已完成：150nm单窄井原WELL.4漏检；两个宽井间隔150nm原式报1而width200/space135参考0。实际llSYS A专项92484是早期flat参考，不能与原deep/tiled计数等同；92486匹配deep/tiles1000μm/border1μm并加逐N/P mask检查，宽度200/间距135均0，但原式73006对原72975未精确复现，原因未闭合。原全量报告、deck SHA均保留，不把计数重分类为通过；WELL.2未实现和via enclosure TODO也未通过。初次92483只因输入层提取API不符失败，保留日志，不是硬件错误。

父层固定几何预检92489/90读取placed输入均因GCELLGRID未定义而原生失败，native_count=None，绝不能写0。92496改读openTPU真实global.odb并核对signal dbWire=0，未篡改网格/规则/几何，结果按实际回执收集；llaccel global检查点尚未取得。无论预检如何都不替代最终信号route/连通/完整规则。

本次新增模型/规则发布检查：check_project PASS；业务验证全部74301行、2204文件SHA、89链接PASS；20图加载、24767pin/常量位检索PASS。模型表及WELL专项页面已打开目视核验，Python编译与Git空白检查通过。此结果只证明发布证据一致，不替代物理资格。

恢复先读AGENTS/Skill/远程规则、Issue126/PR129最新head，再核对上述自己的job，收集新的执行回执。不要重新跑r02/r03模型、覆盖原结果、接管Issue55/121，或将原WELL计数/原PG失败藏起来。模型/semantic补充报告后仍需等父层、其余控制/GDS和真实器件/完整规则/系统约束；Issue不关闭。

最新里程碑以本段、HTML及原始execution为准；下文保留早期记录，不据旧“尚未完成”覆盖新终态。新快照milestone-r09共66项trial回执；extensions/milestone-r03含7项已完成stream-out视图。ACT同组全A_replay/B的92455/92457独立native DRC0/所检全块连通已完成；MXU全B独立native DRC0/连通通过但21项电气失败。GEMM/MXU修订C线长分别约+1.19%/+4.30%，目前优先保留边界，不能因已可布通而声称收益。llaccel新父层27050端点/13507网的前置逐bit合同已通过，PG/路由仍独立验收。

llSYS完整C92369已在确认实际26pin/44矩形对固定PG直接相交后，仅停止该新无效变体。driver cc92773，`verify_fixed_pg_contacts.py`核对实际place_pin后13507信号pin全C一致、原/新PG指纹字节相同，并与原ODB SHA匹配的真实PG金属逐层求交；`stop_known_invalid_pg_trial.py`核对唯一job/name/source/driver/cohort/实际指纹才scancel。保留moved/ripped/global ODB，未完成完整DRT/RC/STA，不是耗时取消。原始源/其他作业未改。证明和实际回读发布在data/fixed_pg_rejections；原26个风险现已是实际移动后几何直接接触证明，仍不冒充完整DRC。

最新extensions/milestone-r04含9份完成GDS视图：VECTOR A/8pin C严格merge0，但均36项天线；openSYS A缺4宏，诊断deck52486（含46014 WELL），C和llSYS继续。较早snapshot中的“待完成”只表示当时状态。全部大型原始JSON和工具文本无损gzip并提供storage_index映射，源字节SHA验证，不把数百万行逐net数组重复塞进HTML/PR diff。

本轮发布验证：check_project PASS；仓库业务验证6块/74301行/1689文件SHA/79链接通过，含两份增量完整表与实际clean pin逐项对应；浏览器20图全部加载，24767pin及常量位检索通过、无JS异常/页面溢出。新增cohort/GDS/增量/父层截图与完整层次图已打开目视核验；Python编译通过。新增Full pin candidate evidence CI只校验候选合同/文件证据，不代表物理规则通过；实际远程检查门槛仍逐项保留。

- ACT完整740 C通过当前native/几何门槛；GEMM原3039 C有2项电容失败，增量electrical-r03实际3021移动、92423/92424已完成独立DRC0/全块所检几何连通/现有STA电气0。MXU原1964 C有3项PG短路及5项max-cap；增量mxu-repair-r03移动1931、92437/92450已完成独立DRC0/所检全块连通/现有电气0。
- VECTOR完整1022 C独立DRC0/所检全块连通，但setup−4.166987ns、违规103行；openSYS1768 C同门槛通过但setup/hold−1.765776/−0.400698ns、违规2101。llSYS13184全C的92369仍运行，92374依赖检查，不取消。
- 完整cohort控制：GEMM Aopt电气4项、B独立native DRC9项均保留；MXU A_replay/Aopt独立native0/所检全块连通，B21项电气，独立终态待收。ACT全A_replay/B增加独立clean92455/92457；92454因本地shell展开远程PWD失败，日志保留，不曾改变物理输入。
- GEMM严格GDS原始/8pin C合并无缺失，但1346/1358项均天线；MXU A/8pin C缺4个fakeram，不能资格化。原92377/92378/92380/92381只在核实全部尚未开始且输出不存在后合并为16CPU的92430（4×4thread），原取消原因留证；不是耗时取消。92376已自然完成。
- 受控父层r06的PG虽通过，原标量bus映射却只接上3607/6618端点，已停止该新无效变体并存证。r07/92441真实bus位序合同在路由前完整6618端点/3408网核对通过，VDD/VSS连通通过，详细布线运行；inputs/parent-inputs-opentpu-act-r04，driver a33330d。llaccel父层92458独立新基线，输入parent-inputs-llaccel-gemm-r01，driver3d88200，27050端点。路由Liberty未表征，禁止父层STA结论。
- 一次控制打包guard发现原MXU92390已运行，正确拒绝变更；后续PowerShell未自动停止，误提交重复92448，已立即只停止新重复并留证。原92388–92399未覆盖或中断；第二次guard发现VECTOR92391运行后退出，未提交。恢复时不要再合并这些活动控制。
- 先取新快照，重跑make_physical_summary、stage_incremental_evidence、build_deliverables --keep-figures、validate_repository，再更新同一PR129。图表已入库，不新增重复PR，不关闭Issue126。完整GDS/LVS、父层可访问性及完整系统RC/STA电气未资格化。

仓库：rayggxia-workspace/LLMHardwareDesign；[Issue126](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/126)，负责人huangpingyang04-lgtm，in_progress。
分支 `task/126-full-block-pin-xy`，在PR120 head4f91e098之上，不擅自合并PR120；当前物理驱动commit在每次execution.json里精确记录。

成果入口：[中文报告](../experiments/issue-126-full-pin/report.html)；[脚本](../../project/experiments/full_pin_xy/README.md)。
六块24,767个原始信号pin、74,301候选行；18项功能归属，外部设备/存储范围明确，原参考包不修改。
候选覆盖不代表物理实现：各块的实际接入、DRC/连通、RC/STA/电气状态分别见 `data/physical_summary.json`。

远程独立目录 `/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027`，所有原Issue7/55数据库只读bind。
驱动按commit封存至 `drivers/<commit>/code`，结果在 `trials/<revision>/<case>-<plan>`；大体积ODB/DEF/SPEF与完整路径报告保持远程，以execution.json的SHA索引定位。
ACT8pin试验r02、原XY重布线控制r03；GEMM r01及重布线控制r04；MXU/两个SYSTEM r03；VECTOR首个驱动配置发现失败r03保留，正确vec-config.mk后r04。
ACT完整740-pin C对照fullC-r01采用相同C可移动cohort，B也是该740-pin子集，不能称为完整B859-pin方案。

恢复第一步：读取AGENTS/Skill/远程规则和Issue/PR最新head，核对squeue/sacct，仅收集本任务作业，不碰Issue55/121或他人任务。
用 `collect_trial_snapshot.py` 创建全新snapshot名、下载后 `make_physical_summary.py` 汇总；先确认所用whole-connectivity的source ODB SHA与提取前routed.odb（A为原始ODB）一致，不能使用RCX后checked.odb。
全块几何连通可用 `full_connect_job.sh <case> <revision> A C` 对实际终态独立检查，必须使用新输出目录；旧API失败不是通过证据。
完整原父层handoff/实际层序还未知；逻辑对端和对端原pin层已补齐但不能替代该证据。完整工艺规则/GDS/LVS及系统边界RC/STA/电气仍待验证。

登记：管理中心PR5 pending；Projects未配置board.json且无工具，unverified/同步pending；处理人待指定。不得把文件上传写成在线协作接入完成。
本记录用于持续执行与审查，不表示任务完成、暂停或已验收。新的结果在同一Issue/PR增量更新，所有失败与基线未通过项保留。

在线交付：[Draft PR129](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/129)，首次发布fbac83836ecc7767a929639265b67b31d74902db；图表已上传。ACT740完整C的独立clean DRC/全块几何连通通过；新增四块制造网格r02已修订、8pin重试grid-r05。旧RCX后ODB重读失败保留，物理母本统一从提取前routed ODB生成。当前运行/后续独立检查按最新execution与Slurm读回，不根据旧snapshot猜终态。

本轮C局部验证现已六块全部完成：ACT740完整C、其余5块各8pin；独立clean native DRC均0，全块多端OpenDB几何连通均通过。RC/STA当前模型：ACT/GEMM/MXU预算满足；VECTOR及两个SYSTEM失败，不能资格化。最终收集snapshot milestone-r05，独立检查92344–92347均COMPLETED 0:0 / UNLIMITED。仍需逐项完成真实父层目标/可达、GDS/LVS/完整规则、完整系统模型及其余全C实现，不能关闭Issue。旧LL辅助边界试验若仍在运行让其自然完成，不取消/覆盖。

增量持续验证（不停止活动作业）：

- 完整C路由：92365 GEMM3039、92366 MXU1964、92367 VECTOR1022、92368 openSYS1768、92369 llSYS13184；顺序afterany，驱动f08e026，full-other-r01。独立clean92370–92374分别依赖对应路由。结束状态必须重新读回，不能把提交当通过。
- 完整cohort边界控制：92388 ACT Aopt740集合（698实际换槽）；其余92389 GEMM /92390 MXU /92391 VECTOR /92392 openSYS /92393 llSYS，均A_replay/Aopt/B。驱动bbc859d，inputs/trial-inputs-full-controls-r04，实际Aopt在既有分束/边/层槽位中优化C中心代理，非全局最优。独立clean92394–92399依赖各自路由；失败仍会释放下一块。
- 严格GDS：92375 ACT已完成，未豁免两个fakeram缺失，A/C合并返回2；不完整诊断GDS上的原样FreePDK45 deck为678/770项天线错误。其余92376 GEMM、92377 MXU、92378 VECTOR、92380 openSYS、92381 llSYS按afterany继续，来源是已完成的原始A/8pin C，不能与后续全C混同。
- 电气观察：92383已完成14组原生JSON路径汇总，F/s单位，完整ACT C与标准JSON解析交叉核对通过。只为已报告路径点最大负载/slew观察，不是全部net覆盖。92382旧回执字段缺失的驱动失败保留，新版从原冻结Tcl恢复cohort。
- validation_extensions/milestone-r01 为新增严格GDS失败和真实电气观察快照；raw GDS/大型lyrdb留远程。ACT原始/完整C导出LEF同层PIN/OBS相交782/777（含PG）只作矩形诊断，包含可能的同网形状，不直接判不可接入。
- 原始匹配父层handoff/层序及缺失宏GDS已向用户询问位置；现有资料中继续保持未知，不指派目标层。根因未完全定位的RCX后ODB问题仍在，隔离流程不等于已修复工具或证明绝对RC正确性。

用户已明确回复没有其他材料，“如果必须，请你自行补充即可”。当前独立补建父层试验见决策0004；历史handoff未知不改写。`prepare_controlled_parent.py`从真实frontier生成完整三宏父层，所有层级/坐标/连接/资源合同固定。openTPU原TOP_IO37个常零声明位新增独立tie驱动实现（不是新增硬宏），原六块接口不改；routing_only.lib只是物理链接端口占位，禁止用它报告STA/电气通过。

- 父层inputs/parent-inputs-opentpu-act-r03；macro原点按0.28μm轨道相位对齐；新父层2228.735×3409.335μm。
- r01/92407 因宏halo和未切行冲突实际失败（原驱动catch导致Slurm0，不作为通过）；r02/92408切行后在ACT的M7→M10 PG接入被OBS阻塞；r03/92409中间M8/M9条带仍被默认抽象阻塞。失败均保留，后续方案拒绝越过基线门槛。
- r04/92410，驱动b611975，详细OBS从真实clean ODB导出bloat_factor=0，保留所有信号/PG pin行、尺寸与占用层。默认Tcl bloat_factor=10已实际读出。PDN生成能执行，但PSM发现新增局部M8/M9条带与原宏信号冲突，未通过；不能报告父层访问通过。当前作业按实际读回，不因耗时取消。
- 下一步优先尝试详细OBS+原直接M7→M10 stack策略，并对新父层PG via按实际M7–M10各层原宏OBS做安全站点选择；原H1 filter_pg.tcl只适合无M10宏OBS，本次必须扩展或另建，不能原样调用/跳过M10。不得删源宏OBS或源金属。新增PG有短路时后续驱动应在PG gate失败就保存并停止该变体，不继续无效DRT。

新独立物理回执snapshot milestone-r06已下载，make_physical_summary已更新52项：GEMM完整3039pin C通过独立native DRC0/全块多端几何连通，setup0.771186ns、hold0.041430ns，但有2项max-cap失败：output3424/Z→gemm_wr_wstrb[29]，output3425/Z→gemm_wr_wstrb[30]。原C与失败保留。

按新证据冻结额外C_electrical_r03（不改PR120 A/B/C）：把完整真实写字节29/30各8data+strobe共18pin恢复原边界，其他C坐标不动。全部3753pin保留；同一3039pin重布线cohort，实际移动3021。`prepare_electrical_revision.py`从实际选网连通报告确认驱动/strobe关系并核对原byte组。驱动ad9678f，inputs/trial-inputs-gemm-electrical-r03，路由92423、独立clean92424（afterany），均UNLIMITED；未完成前不写修复通过。

MXU完整1964pin C的路由92366已COMPLETED0:0、独立clean92371已COMPLETED0:0，尚需下载最新回执并核对真实终态，不只凭Slurm推断。VECTOR全C92367进行；openSYS92368/llSYS92369依赖等待。完整边界控制92389 GEMM中A_replay/Aopt已返回0，B尚运行；其余control/qual依赖不改。
