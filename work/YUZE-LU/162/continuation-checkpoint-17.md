# Issue162 continuation checkpoint17

2026-11-02 23:12:43 CST；YUZE-LU；Issue162 / PR163，in_progress / Draft，继续执行，不合并。规则rayggxia-project-collab1.0.0；登记management-hub PR5 pending；缺board.json，看板unverified/同步pending，处理人待指定。

[32项远程源绑定原文件及3项本地辅助脚本](continuation-proof-17/index.json)均逐字节保存并复算SHA。运行中日志、native-flow及queue-state仅代表捕获字节，不要求后来可变路径仍同SHA。辅助脚本不是EDA已通过的证据。

## S全局布线修复的真实结果

捕获时1181/1182/1183已结束全网电气扫描，进入全局布线RC下的setup/hold修复；1180仍在扫描。1182该轮未发现setup违例，但hold修复最终明确报告“Unable to repair all hold violations”：1249个初始hold违例端点、插入569个hold缓冲后，最终WNS约−0.633ns、TNS约−2.992ns，最差端点仍为slice666741/D。该次迭代失败保留，不把总负裕量下降或后续流程继续当成时序通过。

当前捕获没有新版S最终数据库/完整门通过。后续须取得完整物理结果、重新检查全部实际最终驱动/新鲜RC/300MHz/DRC/功能/严格等价，再完成固定PG和新组合。CTS只读诊断见checkpoint16；此次post-global-routing估计也不能替代最终RC。不会修改SDC、加入假路径或放宽门。继续定位reset过快路径；目标是实际数据支路的组合延迟修复，须先核对同支路setup裕量并重新验证。

788个内部输出级的插入表继续保留，最终ODB保留证明仍待运行。原六宏RTL不变，其他五宏及原S保留。R保留并由并行任务修改。交付表已明确其原S、309个Link8和335实例仅是保留基线，新S不能继承资格。

## 新组合后继

在source121已有6项真实组合后继之外，追加1项精确新S SPEF地电容＋上层乐观线电容诊断，必须等新S原生/固定PG、实际新图及严格原生STA通过。诊断0违例仅是必要条件，不是物理或时序资格。实际spec/config及SHA已收取，没有改写已有队列规格。

本地upper-ready辅助脚本已保存，准备在上述真实前置结果通过且所有low/base/high必要界清零之后，追加4个独立全网候选及每个6项实际几何/PG/三角点RC/联合六文件后继。此次运行仅返回ready=false/缺少前置回执；未追加这28个上层任务，不能把准备好的脚本称作已经运行的布线。脚本使用新组合的实际最终单元三程序，明确不引用旧335组合功能结果；实际实例数从新图提取。

八个自有节点继续c96 6×16/c64 4×16动态补位。sstat记录的是自有95204/95119；四个S当时已执行阶段峰值约13.8–13.9GiB，不是完整后续编译/验收峰值，未据此降低128GiB全流程预测。node25原预检因aggregate480GiB、含保护需求592GiB而暂缓；小RTL16GiB预检已实际通过。没有新增节点、操作其他任务或合并PR。全部最终M11/M12/PG/三角点RC/300MHz及源绑定六文件仍须完成，持续执行。
