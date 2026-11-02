# Issue166 — R local-state implementation

Independent branch task/166-r-local-state, based on frozen PR160 delivery 9b3e7248.
Existing accepted R256, PR160, control/S worktrees and remote jobs are unchanged.

Scope: 16-row lane-local DFF state tiles; two versions; 1R1W; registered read
selection/data/merge; shared host read path; original integer arithmetic.
R256 and R1024 require separate complete physical acceptance at original 300MHz.
No physical qualification is currently claimed.

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

