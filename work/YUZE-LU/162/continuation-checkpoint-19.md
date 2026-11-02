# Issue162 continuation checkpoint19

捕获：2026-11-03T00:34:55.694854+08:00；YUZE-LU；[Issue162](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/162) / [PR163](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/163)，持续in_progress/Draft，不合并。规则rayggxia-project-collab1.0.0；登记management-hub PR5 pending；board.json缺失，看板unverified/同步pending，处理人待指定。

[335项源绑定远程记录/329项原文件及2项本地辅助脚本](continuation-proof-19/index.json)逐字节复算SHA；6项大文件仅保存获授权远程路径/大小/SHA。运行中日志及队列状态仅代表捕获字节。原六宏RTL不改，用户授权S内部补驱动并重新验收；其他五宏及原S基线保留；R保留并由并行任务修改。

## 布线及真实ECO结果

四个source118候选均已有真实5_route.odb/6_final.odb，仍在最终报告/等价检查；原完整回执尚未关闭，尚无新S最终RC/全部门通过，不能按文件存在宣称验收。

source127首次GRT探测误用普通ODB Make目标，发现其追溯缺失中间文件重新综合，已仅停止两项错误探测，保留日志。source128新增的dry-run防护误要求展开到global_route.tcl，而实际ORFS有清环境递归Make包装，防护拒绝，未运行实际ECO。经同Slurm容器只读核实Makefile，ORFS明确提供跳过前序依赖的do-接口；source129改用do-grt并核实其计划只发射do-5_1_grt，已真实执行两项独立GRT/ECO，未重跑综合/placement/CTS。

source129的96级BUF_X1链：实际插入5×96个真实组合单元，目标5条AOI复位支路全部min/max为正；hold约+1.301至+1.332ns，setup约+0.753至+0.799ns。但全块电气/setup计数保护拒绝，**失败保留，不是合格S**。初始计数cap11/slew5/setup0/hold60；失败时脚本尚未写出after计数，不能编造究竟哪项增加。

128级：前三条已记录hold约+1.947至+1.960ns；第三条setup−0.004148682ns明确失败，前两条setup仅约+0.000878/+0.008271ns，其他支路尚未测完。该候选过长，不发射正式最终P&R，更不放宽setup门。

下一迭代准备48/64级组合链，针对实测每级延迟和过量hold修复缩短；继续只改实测5条AOI复位输入，其他复位分支不人工延迟。插入后调用同一原生repair_design_helper/repair_timing_helper处理完整全局布线的真实电气及setup/hold。新增诊断ODB/SDC、全部min/max及全块电气/计数在抛错前保存，即使失败也能按实际数据库定位，不丢最后状态。保存失败数据库不是验收；原有目标支路min/max、计数不增保护及后续全部最终300MHz/全端点电气/DRC/功能/严格LEC/固定PG/整机门均不放宽。该新版48/64在本检查点仅准备/本地检查，尚未执行真实EDA。

## 资源及后继

source129实际GRT-only峰值约9GiB，32GiB预测有实际支持。原S最终LEC阶段已实测152035672KiB（约145GiB），超过初始128GiB；索引另保留捕获时实际全部自有step sstat，不能把早期十几GiB当完整流程峰值。source130新控制器允许最高256GiB单项预测，拟用于后续完整S/严格LEC；保护仍为sum(forecast)×1.2+16GiB，每项16核、c96最多6项/c64最多4项。旧控制器、冻结源和既有pending/active/completed spec均未重写，新控制器尚未启动。

c96节点实际内存准入拒绝32GiB探测，未降低保护。为并行探测仅取消自有旧搜索95097.50/95098.55，保留同图1081/1121；随后旧pending抢先补位，已在新probe排队后仅取消自有95098.70/95098.73，保留1140/1130。两项误重综合探测95097.63/95098.68单独停止；以上都有精确UID/任务名/进程命令、输入SHA及停止回执。未取消原S四项、任何父分配或其他任务。旧搜索中断只记incomplete，不当作物理失败。八自有节点继续动态补位。

source126已为两个未来合格S候选各排7项新真实组合后继，复用其他20类精确已验收叶；它们必须等待新S原生/固定PG全部门通过，不读取旧335程序结果授予新组合资格。完整M11/M12全网几何/PG/low-base-high实际RC/300MHz/联合六文件、版图及源绑定索引仍未通过，持续执行。upper-ready脚本仅准备，前置缺失返回ready=false，未发射其完整上层任务。源129正式repair队列也尚未发射（等待原完整回执）；不得把准备称作已运行。

本地实际检查：48/64/96/128配置选择均只选0/2/3/4/5五支路，九项非法证据/参数拒绝；Tcl完整性、py_compile、git diff --check及check_project通过。管理检查不替代硬件验证。审查人待指定，负责人YUZE-LU继续实际修复与验收。
