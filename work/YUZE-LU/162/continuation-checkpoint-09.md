# Issue162 继续实现：原生严格组合通过，上层电容与布线仍未闭环

证据采集：2026-11-02 16:45:47 CST。Issue [162](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/162) / [PR163](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/163)，in_progress / Draft，未合并、未授予系统资格。[原始证据索引](continuation-proof-09/index.json)：558项，354项原文件实收；其余大文件保留远程绝对路径、字节数和SHA256。代码截至 source92 commit `57a680bb5939e0b046c49d900b071831fb49bfae`，来源清单及冻结档案SHA均在索引中。

R保留并由并行任务修改；本任务不删除R、不接管其工作树或作业。当前六宏参考组合仍缺R适配及实际接入，不把此事实改写成禁令。main M/N/E/G/S/T原始RTL未改。

## 已经取得的物理及组合证据

| 项目 | 实际结果 | 远程任务目录（共同前缀 `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/`） |
|---|---|---|
| 连续采样6bit写控制的S仲裁器 | 三初态RTL及三条真实RTL组合通过；首次DRC失败、din632不支持形状的修复失败均保留；修复din633后300MHz物理、完整native/GDS DRC、实际最终单元功能、严格LEC全通过，六文件及图齐 | `arbiter-setup-03`、`arbiter-setup-04`（失败）；`arbiter-setup-05/gates-45/deliver`（通过） |
| 最新原生完整组合RC | `native-system-audit.json` passed=true、`typed_native_timing_passed=true`；全部真实端点有限setup/hold、原生电气及完整RC覆盖通过，setup +0.039857ns、hold +0.000583ns | `native-arbiter-sta-19` |
| 全20类固定PG叶交付 | 包括S完整FreePDK45 GDS检查通过、真实供电连通、新鲜RC/300MHz、全部六文件；新S仲裁器同样独立完成。逐层原生掩模及完整信号视图身份核验保留 | `pg-delivery-current-01/<top>/delivery.json`；选择 `composition-pgfinal-05/selected` |
| 固定PG完整组合RC | 最新S仲裁器及20类PG叶的原生组合audit及typed timing通过 | `native-pg-arbiter-sta-20` |
| source79实际最终单元组合 | 三种初态各626539检查、199718周期，三条真实组合，CPU张量搬运0；完整1945.411MB/149模块输入，不以RTL替换最终单元 | `composition-arbiter-04/final-composition` |
| 最新source88实际最终单元组合 | 仍在执行，不能借用source79结果 | `composition-arbiter-07/final-composition` |

两个system_sta入口的顶层receipt.passed按设计保持false，原因是未给实际上层几何、入口不授予整机资格；此处通过的是独立原生audit与typed_native_timing字段。不能据此宣布实际M11/M12或系统时序通过。原生RC并未被零上层线的诊断覆盖或替换。

## 已经证伪的上层方案

- source84/87使用每个实际ODB的输出驱动单元及精确Liberty max_capacitance，按已声明研究RC模型计算真实端点HPWL电容下界；忽略所有原生电容、绕路、via和端点附加电容，只能判失败，不能判通过。原五个候选最低角点已有2661–4991条必然超限网。
- source89加入实际高角点驱动预算、16路独立摆放搜索，以及按真实连接就近分配唯一外围接口位置。4个候选最低角点剩1084–1133条超限；没有被当作可用路由。
- 固定N朝向下的逐对非重叠下界，在高RC角点已有322条网任何平移都必然超限。此前“下界未发现不可避免超限”仅针对low角点；不适用于全部角点，也不是同时满足所有连接的存在性证明。
- source90允许四种刚性旋转，使用独立Python复核能量、非重叠、全部实际引脚网格。8个候选全部失败；最低角点最少仍953条超限。旋转诊断不能运行成正式路由/几何门，实际GDS/ODB旋转支持仍需独立完成后才可授予资格。
- 仅取消5个本任务step，逐项核对UID、Slurm归属、完整命令/源路径、实际placement.json与失败诊断逐字相同；原始日志保留。未改任何父作业或旧队列pending文件，未触及其他任务。

原始失败和实际驱动限制保留于 `wire-cap-current-01`、`wire-cap-preflight-03`、`electrical-placement-01/02`；取消核验见 `dynamic-03/electrical-infeasible-route-replacement/verified-before.json`。自定义M11/M12几何/RC参数及全部电气门槛未放宽。

## 当前有源驱动修复

在新增控制宏内部、最终冻结之前，增加显式BUF_X32输出级，原接口、周期、状态和算术行为不变。新增单元、内部连线、面积、PG和时序均计入该原生物理宏，不隐含在M11/M12中；不增加新的物理宏类别。不覆盖main原六宏或旧合格候选。

- 强驱动复位分发候选 `strong-output-01/reset/gates/deliver` 四门、六文件/图通过；原一位同步复位状态保留。
- 强驱动S仲裁器 `strong-output-01/s_arbiter` 物理、最终功能、严格LEC通过，完整DRC发现din629/din630、din632/din633、dout117/dout118三处M10间距失败，原证据保留。source92只允许这次已观察到的din629、din633、dout117三段预冻结修复，重跑全流程和全部最终门，不沿用失败DRC。
- 强驱动C正在P&R/最终门执行。新增只读最终ODB驱动检查，确认每个实际输出确实由新增BUF_X32/Z驱动，不能凭RTL或综合名称推断强驱动已保留。
- 最新合格仲裁器的实际最终单元组合、新驱动各叶与其后完整组合、实际上层零冲突路由/DEF/ODB/GDS读回、low/base/high真实分布RC和整机300MHz，全部继续执行；当前没有系统通过证据。

## 资源和交付状态

8个本任务节点：node2–7各4×16（64CPU上限），node25/26各6×16，独立任务动态补位。源92修复、单块四门、PG、完整组合及摆放依赖就绪后即补位；未就绪依赖与实际可用内存守卫均保存在队列回执，不能用整批等最慢代替动态补位。运行中的旧工程实验正常保留；已证明电气不可行的5个当前候选按精确核验回收槽位。物理失败继续迭代。

已运行 `python scripts/check_project.py` 通过，仅为管理检查；新Python入口语法检查通过，不当作EDA验收。Git HTTPS传输失败保留；同一分支的精确Git对象通过API逐对象校验、force=false发布，具体当前已发布SHA以PR/读回回执为准，不把本地提交称为已发布。

规则 rayggxia-project-collab1.0.0；登记management-hub PR5 pending；缺board.json，看板条目unverified、同步pending、处理人待指定；审查待指定。不自行合并、不标done。交付继续沿用六文件、版图、组合验证与源绑定索引，不能以本检查点替代最终任务完成。
