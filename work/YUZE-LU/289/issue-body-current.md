用户授权YUZE-LU执行并使用子代理。两套2026-11-17归档方案排除P相关，取C/U接口及C.G-F.S接口端口并集。锁定真实物理版本，逐实际末级驱动升级至X8或保留更强；无逻辑等价型号时单列缓冲ECO。固定外形、端口、M10坐标，重新合法化/布线/提取；原频率、原库、原规则下验收setup/hold、电气/PG/连通、完整GDS DRC和等价/功能。子宏改变先更新视图再验父block。单Slurm节点6–8任务，CPU/内存不超配，保留失败与哈希。只声明宏/block级，不自动宣称A/B顶层长线通过。Refs #287。独立审查人待指定，登记PR5 pending，Projects配置/同步待核验。

## 2026-11-18 已验收里程碑

G/S 叶宏、F 父 block 和 U block 已通过。U 153 个目标输出均为 BUF_X8，TT 250 MHz、50 fF 契约下 setup +78.051 ps、hold +3.471 ps，完整原版工艺 DRC 与五类时序/电气违例均为零。源绑定、PG、功能和宏视图检查通过。验收回执见 work/YUZE-LU/289/audit/evidence/U/accepted-parent.json，PR #290。C 详细布线和共享算术优化继续，Issue 保持 in_progress。
<!-- c-actual-baseline -->
C43实际四个不同方案120292已全部完成详细布线，各自setup/hold/电容/slew/fanout均零违例。选用实际setup裕量最大的plan0：TT250MHz、0.1ns uncertainty、153个目标输出50fF条件下setup +6.340040ps、hold +1.990130ps，原约束未放松。最终GDS SHA256为11ed17a55e077a71217667ae6f7e2bb7dbb07d5af22e52450d159d1de4b0bbe9。

该最终源的278701条网络提取前后全层材料一致、153个C驱动BUF_X8、固定信号引脚/宏/外形、无缓存PG双轨、聚焦上层金属与天线、Liberty/LEF及父级cut覆盖均通过。实际ODB导出的最终网表2b74fbc9…与保存文件逐字节一致，120296完成该实际网表的数据/21095状态及clock/reset/control证明；原RTL至综合边界采用机器核验的有限/通用证明和明确列出的人工组合证明，不声称全模块RTL SAT。两方案340/340目标输出已独立逐端口确认唯一BUF_X8（C153/U153/G33/S1；A306/B340）。

C尚未最终后端验收。120303正在对同一个最终GDS执行完整未修改原版FreePDK45规则；原生checker有222个逐项证明为同网连续材料的M2/M3 spacing标记，并非空报告。还须完整原版报告实际零项、root精确native/PG裁定及最终冻结release。PG相对原CTS的230旧记录移除/140新增已追溯至合格v16/C35基线，当前最终边界复核通过。U/G/S/F已验收源保持冻结。

当前证据见work/YUZE-LU/289/audit/C43-ACTUAL-STATUS.md及C43-pending-evidence/，已推送commit80da921f8。PR保持草稿，Issue in_progress；A/B实际顶层RC/STA和多PVT仍在后续范围。
