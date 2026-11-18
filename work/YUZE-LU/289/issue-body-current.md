用户授权YUZE-LU执行并使用子代理。两套2026-11-17归档方案排除P相关，取C/U接口及C.G-F.S接口端口并集。锁定真实物理版本，逐实际末级驱动升级至X8或保留更强；无逻辑等价型号时单列缓冲ECO。固定外形、端口、M10坐标，重新合法化/布线/提取；原频率、原库、原规则下验收setup/hold、电气/PG/连通、完整GDS DRC和等价/功能。子宏改变先更新视图再验父block。单Slurm节点6–8任务，CPU/内存不超配，保留失败与哈希。只声明宏/block级，不自动宣称A/B顶层长线通过。Refs #287。独立审查人待指定，登记PR5 pending，Projects配置/同步待核验。

## 2026-11-18 已验收里程碑

G/S 叶宏、F 父 block 和 U block 已通过。U 153 个目标输出均为 BUF_X8，TT 250 MHz、50 fF 契约下 setup +78.051 ps、hold +3.471 ps，完整原版工艺 DRC 与五类时序/电气违例均为零。源绑定、PG、功能和宏视图检查通过。验收回执见 work/YUZE-LU/289/audit/evidence/U/accepted-parent.json，PR #290。C 详细布线和共享算术优化继续，Issue 保持 in_progress。
<!-- c-actual-baseline -->
C 最新实际 i8/h50：153 个 BUF_X8、接口/宏位置固定；原生路由报告4项，独立原规则上层24项、天线1项，实际 setup/hold 100/117 项、最差 −116.966/−48.911 ps，电容27项、slew0，尚未验收。59项静态尺寸合并重测 setup97/hold141/电容2，但不是实际重布线通过。局部修复 R/S 边界与 M9/VIA9，唯一残余天线 mem_rd_rsp_data[182] 已定位；单节点6×8CPU中段中继试验120144针对绕 R 宏的毫米级长线做真实重布线/提取。缓存优化523/523通用分区与实际综合→i8/h50 legalized 的21095状态/数据/控制证明120098通过；最终实际网表、完整原deck、时序/电气和视图验收仍待完成。U/F已签收版本保持冻结。中间证据 audit/C-v28-ACTUAL-STATUS.md 和草稿PR290；已上传commit dee67eb6d，Issue保持in_progress。
