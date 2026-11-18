用户授权YUZE-LU执行并使用子代理。两套2026-11-17归档方案排除P相关，取C/U接口及C.G-F.S接口端口并集。锁定真实物理版本，逐实际末级驱动升级至X8或保留更强；无逻辑等价型号时单列缓冲ECO。固定外形、端口、M10坐标，重新合法化/布线/提取；原频率、原库、原规则下验收setup/hold、电气/PG/连通、完整GDS DRC和等价/功能。子宏改变先更新视图再验父block。单Slurm节点6–8任务，CPU/内存不超配，保留失败与哈希。只声明宏/block级，不自动宣称A/B顶层长线通过。Refs #287。独立审查人待指定，登记PR5 pending，Projects配置/同步待核验。

## 2026-11-18 已验收里程碑

G/S 叶宏、F 父 block 和 U block 已通过。U 153 个目标输出均为 BUF_X8，TT 250 MHz、50 fF 契约下 setup +78.051 ps、hold +3.471 ps，完整原版工艺 DRC 与五类时序/电气违例均为零。源绑定、PG、功能和宏视图检查通过。验收回执见 work/YUZE-LU/289/audit/evidence/U/accepted-parent.json，PR #290。C 详细布线和共享算术优化继续，Issue 保持 in_progress。
<!-- c-actual-baseline -->
C40六路实际详细布线120273全部完成，最终原生路由报告0，ODB/DEF/V/SDC逐字节相同，因此只对seed0作独立后续评估。只移植一条已有实际M9时钟线net73798并重新提取RC的120281结果：setup7、WNS−43.646421ps；hold/电容/slew/fanout均0、WHS+1.400824ps，两条PG无缓存连通通过。其余网络、实例、信号/电源引脚及逻辑保持精确一致。C尚未后端验收，不能据此签收250MHz或A/B实际顶层长线。

余下7条均为C内部loader路径：两条pd、五条cached_addr，与排除的P block无关。实际C40 common的21095状态、数据及控制完整等价证明120275通过；实际最终ODB新导出的V与保存V逐字节相同120280，因不同于common V，120282正在单独重证明。120277已完成显式or_k=1的六路实际布线对照；120279继续31条实际冲突信号网的邻域重布。120283/120286仅在完成提取的实际C40 RC上作限定组合尺寸规划，其结果必须实际合法化、重布、重新提取并复验。完整原版最终GDS检查、最终视图和冻结release仍待，不放松原频率、负载、IO/uncertainty或加入时序例外。

PG边界的230旧形状移除/140新增形状已由v16实际PDN谱系、260354条电源材料、实际GDS全覆盖和双轨检查独立核实；这一工程基线批准不替代最终候选PG/GDS检查。当前证据与脚本见 `work/YUZE-LU/289/audit/C40-ACTUAL-STATUS.md`，已推送commit `0f814e89b1a6a105b0f7dd201070548d2bad25ac`。U/F已签收源保持冻结，PR草稿、Issue in_progress。

