# Issue121 继续入口（2026-10-31 05:38 CST）

本轮目标保持两份20261028审阅建议：五宏各一个基础实现、连续吞吐和300MHz、内部M1–M10固定、真实M10接点、2µm几何演示的全部接口引出与有限RC，以及逐宏最终布局布线。裕量版、阵列和整模型产品不加入本轮。Refs #121 / PR #122；负责人YUZE-LU。

## 实际新增

- 新只读几何连通helper源87b34df61a101edacd6ab8fd53b0941287746f66；776归档SHA0072c74f368d60a6f84f7329c381474c2ab66e466071d4607cc35f38a7d00d77，362成员。94006在node17实际运行，不改源ODB/DEF。全信号wire/via/pin/独立DEF RECT、真实cut跨层、同端口电极、悬空金属片段均纳入；每网流式、16进程、有界队列完成即补。不得把该方法或RUNNING称为连通PASS。
- 正面积/正边、点触拒绝、间隙拒绝、缺via拒绝、同端口与异端口、缺失端口、RECT桥共9个确定性对照，100组随机与朴素全对比较；本地实际解析/进程池RECT桥存在和移除两个对照通过。实际数据结果尚待检查。
- 767新的独立物理验收PASS，`v-767-physical-777/index.json`封存33份原始和7份实际服务器大文件SHA，358归档Git blob及receipt输入/稳定输出复核。原630资格没有转移。最终源receipt为f06b8e147dfb8bde4e5cdd662bfbbad97b873e661b3b47c9667a6386a6d06005。
- `live-779-v.json`在allocation内实测767 KLayout与Verilator编译、776 OpenROAD进程CPU增长和各自16CPU掩码；`live-779-r.json`实测原R PID1987219 CPU增长100ticks/秒，93555/node21，原GRT extra46。没有因静默或耗时重启。

## 未完成，不得提前接收

V：776全宏物理信号几何连通结果；767完整未改GDS DRC、三初态最终功能、严格LEC、六文件/完整原生几何和人工查看；768全部端口和有限RC。旧自动四门交付不含新增776证明，不能仅凭其native_leaf_accepted把当前总接收改为true；必须另绑定该证明。当前V accepted=false。
R：原404布局布线继续，405/406按真实前置。M/S/T已有结果保持。五宏当前最终交付尚未齐。

## 恢复第一步

先核实94006和94002的sacct与allocation内实际进程，再读776/767各task receipt及node-queue-state；只有终态才封存。776只读证明若失败保留实际失败和全部几何，诊断是否确有断开，不能放宽几何规则来通过。原R93555继续。769控制器仅跟766/767/768，634仍跟原R；不重新部署控制器或重复提交活任务。

远程base：`/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121`。c96每节点6×16独立队列、即完即补；本任务上限8个allocation（含旧/PENDING/UNKNOWN），其他Issue不计入。新增连通证明目前仅一个真实就绪任务，不复制EDA占位。

此前原生0、fresh RCX/finalreport及439原始文件核验见[775](CHECKPOINT-775.md)。登记management-hub PR5 pending；无board配置，看板unverified/同步pending、管理员待指定；PR122 OPEN/draft，Issue121 in_progress，独立审查人待指定。
