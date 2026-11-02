# Issue162 继续实现：新增控制块与固定驱动的最终单块交付

更新时间：2026-11-02 18:14:46 CST。Issue [162](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/162) / [PR163](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/163)，in_progress / Draft，未合并，系统未验收。继续执行实际布局布线，不以本记录作为任务结束。

[证据索引](continuation-proof-10/index.json)记录3479项、2182项原文件实收；重复中间投影和大文件保留远程绝对路径、字节数和SHA256。初始采集18:09:34 CST；[后续摆放候选索引](continuation-proof-10/route-selection-102.json)单独记录18:14:46 CST的32项候选和全部绑定，不能把两次采集混作同一时刻。源93–101冻结清单在索引中，source101为`dd54c55f689a9daf52585cf9eb447463502ef549`；精确发布结果以在线HEAD读回为准。

## 已有最终物理结果

- 14类新增控制块全部完成强输出级的最终P&R、300MHz物理、完整native/GDS DRC、最终单元功能及严格LEC四门，并分别完成固定PG后的完整DRC、原生掩模/信号身份核验、新鲜RC/300MHz与六文件/版图。包括C、D、队列、AXI-Lite、六适配器、固定路由、S仲裁器、状态和复位分发。最终目录`pg-strong-delivery-01/<top>`。
- 独立`control_link8`同样完成上述最终原生及固定PG门、六文件和图，目录`pg-link8-delivery-01/control_link8`。8条组合数据通路、1位同步复位隔离状态；没有载荷寄存器。全输出实际ODB驱动为BUF_X32，未借用旧候选资格。
- 原M/N/E/G/S/T的RTL及原合格文件保留，供电封装另生成并独立验收版本；原六宏固定PG交付与上述15种新控制/驱动类型组成21类物理实现。统一索引`pg-drive-deliveries-01/<top>`，每类V/SDC/DEF/ODB/SPEF/GDS、图、源与门的SHA均有绑定。
- 最新连续写采样S仲裁器的source88完整最终单元组合通过：三种初态各626539检查、199718周期、三条真实外存供数程序、CPU张量搬运0，`composition-arbiter-07/final-composition`。不是继续借用source79结果。
- 全14强驱动控制替换后的20类/26实例，在PG前后均完成严格原生组合audit：`composition-strong-01/native-sta`和`composition-strong-pg-01/native-sta`，setup +0.039857ns、hold +0.000705ns，全真实端点、电气及原生RC覆盖通过。system_sta入口顶层passed仍为false，因为没有实际上层线；不得据此宣布系统通过。

## 固定驱动及真实组合

总线共同位置的下界诊断`joint-wire-feasibility-02`证实：原S自身输出到既有大适配器的被动连接在全部旋转/分离方向、甚至low线RC下不可行。既定RC与验收门未放宽。

保留原六宏的方向下，先给S插入100个固定驱动实例；随后针对实际失败的其他原生输出和多接收端总线，收敛到同一种驱动的309个实例。当前图为21类、335个实际实例；新增309位复位隔离状态分别归相应Link8原生物理块，clk和reset均明确连接，原26个实例不删除。共享总线按实际接收pin分支，每支有独立驱动输出；全部路径收缩后，原数据、控制、扇出及主机端口必须逐项相同。

- 元数据独立oracle通过，涵盖2241条使用中的驱动lane；检测换位与未合格状态模块的阴性对照通过，`boundary-link-oracle-100`。这不是硬件功能或时序验收。
- S-only 126实例和全部驱动335实例的严格原生组合RC均通过，`composition-link8-01/native-sta`、`composition-drive-01/native-sta`。335实例固定PG版本另运行`composition-drive-pg-01/native-sta`，按其实际回执验收；本快照尚未收得该最终回执。
- 强控制、S-only和全驱动的实际最终单元三程序分别运行`composition-strong-01/final-composition`、`composition-link8-01/final-composition`、`composition-drive-01/final-composition`。本次采集仍在编译/执行，不能借前述26实例结果宣称它们已通过。
- 上层优化使用26个明确的摆放簇保留空白驱动区；实际335个原生实例分别计数和检查，未把簇当作新增大宏，也未改原生尺寸。32个候选各16个独立C++搜索，共512次；Python逐项复核代价、网格和非重叠，实际PG接点与唯一外部端口重新核验。其中30个在三种最乐观线电容下界中均无超限，仅取得继续布线的候选资格。原生电容、实际绕路、slew、setup/hold及完整上层几何尚待真实验收。

## 失败、资源与继续执行

旧node25因我漏核新增脚本白名单而退出，四个自有旧布线被中断；原始失败和95096账单已保存，95204恢复后实际六个16CPU槽及旧/新控制器阴性对照通过。未触及其他七个父作业或其他任务。两条新STA配置曾把顺序阶段预算相加填成224GiB，超出控制器单项128GiB规格，在发射前显式拒绝；旧拒绝保留，按实际前次峰值19GiB以内、单项128GiB保守峰值预算重新追加，独立STA入口的224GiB+20%+16GiB可用内存检查未删除。

另外23个旧布线step经Slurm/UID/完整命令、实际S的ODB、pin、尺寸、接收连接与共同位置失败证明逐项一致核验后停止，日志保留，父作业与pending文件不动。证据`dynamic-04/joint-infeasible-routes/verified-before.json`。不以失败的旧布线填充计算资源。

仍使用node2–7各4×16、node25/26各6×16，依赖就绪后动态补位。新的搜索实际每槽16个独立进程；完整最终单元编译保持独立槽。下一步按精确坐标重建并核验候选全部实际接点，完成全网M11/M12零冲突布线、DEF/ODB/GDS读回、PG连续性、low/base/high分布RC和300MHz；失败继续定位迭代。

R保留并由并行任务修改，当前参考组合尚缺其适配/接入；不是永久禁用。新拓扑中R字段按实际实例计算，去掉显式拒绝R的额外断言；现有合格类型/源绑定门继续严格执行，不提前给未验收的R授予资格。

规则rayggxia-project-collab1.0.0；YUZE-LU；管理检查和Python语法检查通过，不替代业务物理门。登记management-hub PR5 pending，缺board.json，看板条目unverified/同步pending、处理人待指定；审查待指定，不自行合并。
