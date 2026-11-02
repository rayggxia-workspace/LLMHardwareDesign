# Issue162 组合修复检查点06（2026-11-02 12:55 CST）

Issue [162](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/162) / PR [163](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/163)。继续实现，in_progress / Draft；未完成整个系统物理验收，未合并。

用户澄清：R保留，正在由另一任务修改。不删除R，不接管其修改；当前已测六宏组合尚无R适配器，不能把缺项写成永久禁用或已完成接入。main 4b1df2c7 的M/N/E/G/S/T RTL diff仍为空。

## 已实际修复

S仲裁已用固定M10逃逸修复，通过全部四门，六文件位于 `s-arbiter-escape-01/escape-45-gates/deliver`，失败密度候选仍保留。新复位分发及AXI-Lite桥也已四门通过。

新S适配器含A135bit/B517bit两项寄存交接，S ready不再组合依赖M ready；任务完成等待原生done及真实M消费全部包。source54首轮CTS因hold缓冲预算失败，保留失败。source55仅增加该适配器CTS实现的缓冲数量预算到100%，不修改约束或验收门槛。

该新适配器最终四门全部通过：setup **+1.415061831ns**、hold **+0.017014446ns**；原生及完整GDS DRC零违规，最终网表三初态功能、严格LEC通过。六文件及版图位于 `feed-handoff-02/gates/deliver`。die1740×1740um，活动单元面积18173.652um²，明确计入物理代价。查看了其实际最终GDS渲染图。

替换后的真实图为20种、26实例、**7534条信号/时钟/复位网络**，无未归属活动逻辑。source54 RTL三真实组合三初态各579592检查/184069周期，CPU张量搬运0。

## 组合时序仍须最终验收

`composition-repair-02/ideal-sta` 使用全部真实最终物理功能视图及原生SPEF。此前−2.095727682ns、后续−0.700330496ns的宏间路径已消除；当前最差setup +0.039856ns、hold +0.000583ns，原生setup/hold和电气违例计数全零。

**这仍是零上层RC诊断，receipt.passed=false。** 7534个边界驱动尚部分注释；285219项未注释驱动须按真实连接审计（报告开头是未使用DFF/QN），输入保护单元亦须按实际ODB/Liberty分类。正裕量不能替代完整上层RC、时钟负载及全部功能端点验收。

## 固定PG与资源

原生PG最高可为M7。各叶候选实际增加M7→M8→M9→M10固定供电接入，保持已验收原件不可变并保留原供电端口；完整原版GDS子树加声明固定几何，逐层XOR及实际形状读回，完整native/GDS DRC。M10接入中心为4um网格的(8.095/16.095,12.07)um。

`pg-fixed-04`逐叶执行，供电全连通和fresh RC/STA独立验证；不能从单项DRC授予资格。G的实际供电连续性、所有PG ITerm及实际物理检查已通过，其余逐项排队。旧PG原型和失败保留。

node25的95001验证修改前的边界，独占96CPU却只有16CPU单任务；保留命令、日志及SHA后仅替换本任务该作业。新95086实际96CPU，6项×16CPU动态补位，初始38项PG/RC任务并持续追加真实组合检查；记录forecast、MemAvailable、1.2裕量+16GiB守卫及依赖。node2–7各4×16受64核硬件限制，node26保留本任务分配，总8节点，不动其他任务。

旧24个全信号候选仍为工程基线，路由拥塞未收敛。新候选按真实连接权重搜索紧凑摆放，不改宏尺寸/方向/内部线。最终网表编译尝试按实际物理宏分区，唯一输入差异是编译器注释，保留可逆检查；首轮误将角色M作模块名，失败保留，source59已按实际模块声明修复。编译分区本身不算功能通过。

## 证据与继续工作

[proof06索引](continuation-proof-06/index.json)：185项逐文件SHA，151项原始复制共1860963字节；大文件留在授权项目目录，既有证据不覆盖。源快照54–59绑定到相应真实commit和归档SHA。

继续完成全部固定PG资格、新最终网表三组合、新边界含PG全图布线及实际几何独立读回、完整组合RC/300MHz/电气/时钟/复位、严格组合等价、最终六文件和源绑定。失败持续定位迭代，不以单块通过宣布系统通过。

规则rayggxia-project-collab1.0.0；身份YUZE-LU。登记management-hub PR5 pending；无board.json/Projects条目能力，条目unverified、同步pending，处理人待指定。管理结构检查通过不替代业务验收。
