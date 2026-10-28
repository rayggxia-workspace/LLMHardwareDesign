# Issue126：658真实diode终态、全网增量接线证据及770边适配

2026-10-29 Asia/Shanghai；仓库rayggxia-workspace/LLMHardwareDesign，[Issue126](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/126)/[Draft PR129](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/129)，负责人huangpingyang04-lgtm。分支task/126-full-block-pin-xy；此前已发布51bcac124844b344ade86a64031bec14648bfac0，两CI40752386668/40752386573均success；本阶段发布head和CI以PR最新读回为准。整个目标仍active，不能把本文当作全目标完成。

## 新的真实终态

ROOT=/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027。

92975/driver51bcac124844b344ade86a64031bec14648bfac0，ROOT/antenna_incremental_eco/r01/gemm-C：26m41s COMPLETED0。基于严格GDS的37个真实多边形/22条唯一网，定向增加22个真实ANTENNA_X1，保留此前636个diode和两处同功能换型。native实现、fresh DRC和全量数字图导出均0；fresh DRC0，268637网/806643端点/7517145形状所检连通通过。原实例、所有原信号端点/端口/网络、旧636 diode位置/端点、pin/PG/外框保持，源文件未改。真实RCX/原SDC下setup/hold为0.770702/0.039533ns，文字VIOLATED标记0；不是RTL形式或完整制造规则通过。

新增22个master bbox面积5.852μm²，每个真实输入负载0.023429fF，合计658个diode。成本与原3换型、后2换型、636个初始diode分别记录，不能混入纯XY/面积收益。完整GDS由92976/同driver、ROOT/antenna_diode_stream/incremental-r01/gemm-C实际运行，原deck不修改、allow-empty禁用；截至本快照没有终态，不把旧37项说成新版本已清除。

92985/driverce1c79b0c19a68531d455bc418280f0229cb24fe：ROOT/route_representation_audit/r01完成。三份源SHA匹配，全部268637条原始网均纳入WIRE/展开via矩形多重集比较。636diode→两换型有15网表示不同；两换型→新增22diode有77网表示不同（22目标、2条此前636已保护网、53其他网），其余268560网表示完全相同。不同表示可能是切段/重复差异，不等于几何并集、线长或RC变化；不能称只重布22网。两份完整逐网digest TSV.gz各约12.48MB留授权ROOT，有原文SHA索引。

新的gemm_real_diode_access PNG/SVG：区分旧636diode+两换型GDS报项bbox、22个新diode实际位置及一个真实receiver的LEF placement bbox局部。总览符号不是pin/via尺寸，局部不是GDS轮廓，不绘制未提取路径。原3753个信号pin和PG不变以实际字节/SHA证明；当前新GDS资格单独判断。原30图及24767原pin/74301行A/B/C均保留，不从头重做。

## 两模式适配与仍运行项

- 92974/driver51bcac1：ROOT/upper_adaptation_trial/r02。已通过真实1541个M10 hook、两个唯一时钟alias、via10下层0.8×0.8μm占地的前置核验。每模式770条边/1540个实际hook，256条共享导体各用真实A/B两端；只读同一fixed_prewires_NOT_FROZEN.odb。两模式GRT仍运行；adapter-only/unqualified，不是两完整功能或已冻结底座。首轮92969 alias断言失败仍保留。
- 92968/driver53a1b3ed8b535948f4a0e1b1bd8c4e2674c5ca58：ROOT/output_chain_resume/r02/opentpu_aux-C。复用已经完成的r01合法化ODB，不重选/移动buffer；按实际实例名查找修复空句柄导出，check_placement和原合同通过，真实GRT/DRT继续。原92921 Signal11、92925导出失败保留。
- 92690 LL完整窗口RUNNING，92691等待依赖；92841 GEMM父层接点修复、92892 MXU父层修复、92855共同下层GRT仍RUNNING。只操作本人独立ROOT，不按耗时取消、不改活动驱动/输出，不干扰Issue55或其他成员作业。
- 92855已写256条原生FIXED M10资源及1029个父层施工接点、双PG所检通过；下层私有路由尚未终态，仍不是合格共同底座。构造port下降、真实模式共享、规范化M1–M10冻结与完整功能/RC/STA/端到端公平对照均未完成。

## 独立诊断与原始证据

92979/92984只读native GRT能力探针未附加/发信号给活动进程。直接写出的Tcl body完整，实际二进制SHA仍0a4cdf08482bab2d99543e8b32b4b142e013becc7f2c1598afb39ba058193f53。长stdout混排不能当工具源码损坏；没有因此改solver、规则或原活动作业。

VECTOR真实提取关键路径的141个cell arc合计6.7401ns，net约0.1984ns；当前同函数系列FA_X1/HA_X1/OAI33_X1没有更大驱动型号。audit_path_liberty_tables.py以实际Liberty SHA 8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1生成全部141段CSV。各arc独立表格最小值混合不同slew/负载/跳变/条件，不是可同时实现的STA、零连线下界或不可行证明；未改架构、流水、约束或物理输入。

gate-r17由92988/driverb7f9fcf1bd88cbfb12a246957bd1e37592fbe8d1收集闭合native中间阶段，gate-r18由92993/driver80c2747e976f5665bdf71c0a38a8d59ad992f6c0收集最终native回执和全网差异。两个raw/gzip双SHA快照不可覆盖，下载tar SHA分别1a16fff147512622d597de70a03dde287612e8b165940941e3ac28f56286b23d和a9905f477b472e0327144f0c14383332408a872d3bf31bd44c73dc13f2d240b7。大ODB/GDS/SPEF及完整PG表留授权ROOT，通过闭合原生阶段或终态回执SHA索引，不拿缺失本地PG表虚构几何。

## 下一条实际动作及未完成项

完成本阶段上传/在线读回后，执行已编写export_real_diode_view.py/real_diode_view_job.sh，为658diode实际源导出可供父层研究使用的clean ODB/LEF/OBS/DEF/真实网表与非零提取时序视图，逐项保持3753 signal pin、方向、原M5/M6及尺寸，SPEF余量精确重放。本文创建时该视图作业尚未提交，实际作业以runtime_submissions为准。继续92976与其他活动终态；不重复运行已完成native实现。

VECTOR/openSYS原时序失败、LL源native4及完整窗口未终态、ACT父层hold失败/604寄生未标注提示、缺实际SRAM GDS、原deck规则覆盖/模型minimum_period及历史逐pin目标层缺项全部保留。没有完整设计RTL形式证明、合格共同冻结、两完整M11/M12实现或公平系统收益结论。六资源并集/真实共享导体选择已确认，不重新询问。

规则rayggxia-project-collab1.0.0；project_id llm-hardware-design；登记management-hub PR5 pending；缺board.json/Projects能力，看板unverified/同步pending，管理员/审查人待指定。Issue in_progress、PR Draft，Refs #126，不合并PR120/129、不提前关闭任务。
