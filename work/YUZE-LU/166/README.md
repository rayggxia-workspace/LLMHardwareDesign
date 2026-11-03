# Issue166 — R local-state implementation

Independent branch task/166-r-local-state, based on frozen PR160 delivery 9b3e7248.
Existing accepted R256, PR160, control/S worktrees and remote jobs are unchanged.

Scope: 16-row lane-local DFF state tiles; two versions; 1R1W; registered read
selection/data/merge; shared host read path; original integer arithmetic.
R256 and R1024 require separate complete physical acceptance at original 300MHz.
R256 standalone macro is fully qualified and locally received; see [report](R256_QUALIFIED.md). R1024 remains unqualified and work continues. Dated snapshots below are historical.

First component contract: read E0 acceptance → E1 local selection → E2 local data
→ E3 output. Write E0 acceptance → E1 local write selection/data → E2 storage.
Simultaneous E2 access is read-before-write. Reset invalidates control, not state.

References:
- https://github.com/lowRISC/opentitan/blob/master/hw/ip/prim/rtl/prim_ram_1p_adv.sv
- https://github.com/lowRISC/opentitan/blob/master/hw/ip/prim/rtl/prim_ram_1r1w_adv.sv
- https://github.com/The-OpenROAD-Project/OpenROAD/blob/master/src/ram/README.md
- https://yosyshq.readthedocs.io/projects/yosys/en/0.41/cmd/memory_map.html

Registration: management-hub PR5 pending. No board.json: board unverified,
synchronization pending; administrator/reviewer unassigned.

## 2026-11-03T07:34:05.018564+08:00：#166 标准物理视图往返通过，完整原生与R1024继续

固定上游2eba27b2 checker已在独立Slurm237真实构建成功，binary SHA944848ca2b5181d570e21841fa9c54e53c062b4ebea74cd3955a6c5b30343ee0；使用官方//:tarfile同一CLI目标，保留153因pandoc缺失失败的文档安装证据。228构建后完整源码复核及6组新旧真实规则正反例通过，但源ODB0.141/工具0.139格式不兼容，整块明确失败。未改二进制schema头、源ODB或工艺规则。

249由原工具导出全部LEF库与完整DEF，再由固定checker读回、重新导出。全部LEF及DEF的28456945个字段严格核对通过，数值改写0；仅规范化无序DEF GROUP成员的输出顺序，成员/重复项/全部属性完整比较，其他规则/层/形状/坐标/网络/顺序不排除。完整导出DEF SHA6c0d07b183b6963b5c6677f86255cd0b5b271ce51ae075c51c5caefbcabab4a8与111原最终DEF一致。250/95612重新完整源码核验、全部6组规则对照、相同视图全die检查；251/95613总门、252/95614最终绑定包在其后。原容器095/101/116检查保留。R256111虽已有完整原GDS0、300MHz时序/电气0、精确最终192/192，仍未完成全部资格和本地整包实收。

R1024原179最终提取setup−55.3353ps/2、hold−77.6225ps/600、cap93/slew1，不合格；不能以DRT0或修复器中间hold0替代。202新物理宿主规则的实际GRT初值setup+60.0175ps、hold−9.6807ps/1、cap26/slew1，优于旧179 GRT253/110/5，但仍未过门。192/202均继续实际GRT RC闭环→DRT→最终RCX，未签发资格。253–255绑定202完整原生/总门/包，256–258对应192候选。精确最终功能220→221→222仍依赖205原300MHz/电气前置门，数组每项16CPU、最多36项动态补位；224真实少186项的负例被完整收集器拒绝，失败回执已实收。

实际作业、取消前命令核验与依赖变更见ATTEMPT_SCHEDULER_INDEX.json；所有失败和源保留。取消仅限本任务尚未运行的旧代码链。当前并发受真实依赖和Slurm可用槽位限制，没有宣称内存不足。Issue166 in_progress、PR167 draft；登记PR5 pending、无board.json看板unverified/同步pending，管理员/审查人待指定。不改main、旧交付或其他任务，不自行合并，持续双容量全部成功与六文件/版图/整包SHA实收。


## 2026-11-03T08:14:40.200867+08:00：#166 R1024按真实失败路径和负载约束继续

R256完整资格/本地实收保持，见work/YUZE-LU/166/R256_QUALIFIED.md。R1024尚未合格。270对179最终SPEF只读诊断：全部600个hold失败中519个来自15外部输入、81个内部；两条setup失败同源dot[3][5]→failed/rsp_error长组合路径。271从同一165 CTS按这15个实际输入添加53个延迟单元和15个驱动，实际审计及输入路径绑定已实收；内部/最大延迟失败不被忽略。272–280依赖同一候选完成全部物理/几何/192最终用例/包。260分离setup150ps优化目标与hold修复setup保护0ps，保留hold60ps目标与逐轮真实ODB/SDC/路径；192/202老对照继续。原最终300MHz/IO与全部非负/零计数门不变。

281用完全相同RTL SHA进行显式驱动BUF_X2、每组合边界50fF、时延目标3000ps的ABC综合对照；容器实际help先核验参数，官方依据https://yosyshq.readthedocs.io/projects/yosys/en/0.47/cmd/abc.html。综合/完整选择锥通过，mapped JSON SHA583ccecb4aca725d02e9424beed4d03d625bf2ea30563c9659d81920fab9d4be。面积790663.188µm²，比原703543.134约增12.4%；ABC无布线WireLoad时延2844.62ps不是物理通过证据。282严格全状态ABC等价与283实际1800µm/0.35/原16区布局并行，284新CTS→285完整路由→286–294全部验收/最终192数组/包；不借用原映射的证明或最终功能资格。

当前在依赖允许时运行独立物理/形式任务，最终功能数组每项16CPU、最多36个动态补位，8个允许c96节点、每节点最多6个；实际proof/placement及最终时序依赖未完成，未声称内存限制。完整源、作业和取消回执见ATTEMPT_JOBS/ATTEMPT_SCHEDULER_INDEX，所有失败与原始源保留。Issue166 in_progress、PR167 draft；登记PR5 pending、看板unverified/同步pending、审查人待指定。不动main、旧合格包或其他任务，不自行合并，继续R1024完整成功。


## 2026-11-03T08:50:12.484755+08:00：#166 依据缓冲上限失败改为有限批次后重测RC

R256完整资格及816文件本地实收保持，R1024仍未合格。192/202真实失败均为RSZ-0060：在同一272340/D端点约14ps停滞，分别插入68374/68342个hold缓冲达到上限。完整原日志保留，失败回执、原日志SHA及末尾见work/YUZE-LU/166/evidence/CLOSURE192_202_FAILURES.json。260/271分离setup保护后也观察到相同端点停滞，作为对照保留。

297/95673、298/95674从同一165 CTS独立执行每批最多200次hold修复，再合法化/真实增量全局布线/重测RC；298另含270实测输入修复。实际容器296/95672帮助已确认-max_iterations，生成策略绑定192/202失败回执与完整日志SHA；最终原300MHz/IO及全部零门不变，达到迭代上限不算通过。source297-runners.tar冻结20742cf0代码，正式生成钩子和实际策略随包绑定。300–308对应297、309–317对应298、318–326对应新映射299，均串联原完整GDS、完整原生、几何、严格最终LEC、精确最终192数组与交付包。

281新映射的283布局实际成功，面积838393µm²（placement统计，不是最终面积）。282完整状态等价仍在实际solver；284新CTS不必等形式证明，核验283成功及实际3_place.odb后仅修改调度依赖，源码和原SUBMISSION不改，DEPENDENCY_REPLACED记录保留。最终294/326包仍必须接收282完整证明。285原优化和299有限批次对照均依赖284真实CTS。新旧映射不借资格。

约08:18起主登录新SSH认证停顿，08:38已通过已知主机node15正常SSH通道恢复，只改变连接路径，账号/主机校验/作业未改。已关闭本任务冗余本地重连循环。16个依赖192/202明确失败的尚未启动旧下游作业，逐项核验Command/状态后取消并保留完整scontrol/原因/失败源SHA；不按时长取消，不动其他任务。最新调度回执继续同步。动态最终数组每项16CPU、最多36任务，8个允许c96节点内每节点最多6项；限制来自真实依赖/槽位，无内存不足声明。

Issue166 in_progress、PR167 draft；登记PR5 pending、无board.json看板unverified/同步pending，管理员/审查人待指定。不改main、PR160旧包，不自行合并，继续直至两容量完整成功及本地整包实收。

