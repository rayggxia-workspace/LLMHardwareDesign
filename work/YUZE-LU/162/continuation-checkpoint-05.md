# 组合失败定位与修复候选（2026-11-02 12:00 CST）

Issue [162](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/162) / PR [163](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/163)，继续实现，未合并、未完成系统验收。main 六宏原始源未改。用户随后澄清R保留且正在修改，撤销“禁止发射”的任务约束；当前已测组合尚未接入R，不删除R或接管并行修改任务。

## 实测失败与修复

- `system-sta-ideal-02`：25个实际最终物理功能视图、原生SPEF、宏间理想连线的乐观诊断，setup −2.095727682ns、hold +0.000582590ns，setup违例131808。复位输入电容159.598983765fF，大于121.154998779fF。关键路径经过复位、M、S、S仲裁、D。诊断从未授予组合物理资格。原始证据见 `continuation-proof-04`，大型报告留在获授权远程任务目录并保存索引。
- S仲裁改为先锁存128bit返回，再向客户提交；ready确认亦寄存。`boundary-fix-01/s_arbiter` 原生布局布线完成；`boundary-gates-03/s_arbiter` 的时序电气、最终网表三初态功能及严格LEC通过，完整原生DRC失败：dout[118]/dout[117]，M10，bbox (995.0500,958.8700)–(995.0950,959.0700)。此候选不合格，保留全部失败；下一步对同RTL做独立密度候选，仍使用完整相同门。
- 复位块先前25相同寄存器被综合合并为1份，该映射只作失败原型。新实现为1个复位状态位及25个显式BUF_X16分支；原生映射有数量断言，未靠RTL外观声称25路驱动。此复位块属于独立固定物理块；系统复位至少保持两个上升沿。
- AXI-Lite桥复位期间禁止AW/W/AR和内部应答握手，避免复位分发一周期延迟期间假接收。
- source47 / commit `116f086e`：`boundary-fix-02` 的reset/axil原生布局布线完成；system三初态各579568检查、184061周期，3个真实组合、CPU张量搬运0。新顶层为20种、26实例，等待最终边界图重提取。
- `boundary-gates-03/reset`、`boundary-gates-03/axil` 全四门通过并生成deliver六文件、版图和源绑定。不得把这些新叶的通过称为组合通过。

## 调度和执行边界

任务仍为8节点：node2–7各c64四项×16，node25/26为c96；全图24候选为旧边界工程基线，后续需用新边界及实际PG重新生成。原Python布线器已保存替换回执，改用源绑定C++路由和独立Python连通/短路检查。旧18类型组合已保存失败/替换记录，不继续授予其当前边界资格。

node26复用本任务Slurm 95041分配，新增步骤每项16核、exclusive，实际执行总和不超过96核；登录进程只负责调度。新守卫在node26读到MemAvailable 524307636224字节；预算为128GiB组合编译＋5×32GiB候选，1.2裕量＋16GiB守卫。所有EDA实际在srun内。不同叶门可独立就绪，formal依赖真实最终功能视图，deliver依赖全部四门，动态补位。

首次复用分配启动门时，子节点PATH找不到singularity，三个门控制器在seal启动即失败，未伪造通过；source48 / commit `5eb0ec19` 改为绝对可执行路径后重跑。dispatch打印回执另遇环境脚本前缀导致JSON解析失败，但控制器已实际启动；保留原始日志与实际Slurm步骤，不重复提交。

## 尚未完成

S仲裁DRC修复；20类型真实拓扑与全部最终网表组合；完整上层几何读回、固定PG接入、时钟复位与真实RC的300MHz验收；组合等价与最终六文件/图/完整源绑定。主线持续迭代，不降频、不对有效复位路径加例外、不放宽门槛。

上传补记：Git连接已恢复，007744510f6ac9fda68c1cdeffd8a558508d75d1已正常push并通过ls-remote和PR head读回；更早“上传失败”为历史事实。服务器不可变source归档不等于GitHub分支已更新，后续提交仍逐次核验。规则rayggxia-project-collab 1.0.0；登记management-hub PR5 pending；看板缺配置及条目能力，unverified/同步pending，处理人待指定。
