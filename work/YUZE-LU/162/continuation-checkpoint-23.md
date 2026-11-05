# Issue162 continuation checkpoint23

捕获：2026-11-03T03:18:29.684903+08:00；YUZE-LU；[Issue162](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/162) / [PR163](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/163)，继续in_progress，不合并。[本次源绑定索引](continuation-proof-23/index.json)保存98项远程记录/96项逐字节原文件及10项辅助脚本/精确发布回执。大文件保留获授权路径/大小/SHA；活动日志只代表捕获字节。本检查点不是停止或最终交付。

## 实际新S已经通过的门

S1350原生收尾已通过，见checkpoint22。独立最终ODB/SDC/SPEF物理验收现已正式通过：全部实际端点、RC覆盖、驱动与输入接收器、精确M10接点、PG/放置/连通及约束回读均通过；setup/hold违例端点均0，cap/slew/fanout违例均0，setup WNS +0.017822854ns、hold WNS +0.005294543ns。300MHz、原SDC与电气门不变。

S1350实际最终全部信号单元三初态功能也正式通过，非RTL替代模型。每次124440检查、46581周期、523描述符、9545窄口请求、CPU内部RAM访问0。实际ODB导出保留保护负载，完整物理视图与1181逐字节相同；此次仍重新编译并执行全部三种初态。source136使用--output-groups 0和16路编译，实际编译组织及完整命令/日志SHA见回执。原默认编译作为独立保留实验继续，不凭对象数量推断通过。

完整原生GDS deck和严格全部状态边界formal仍在实际执行，以最终回执为准；不能用物理/功能两门通过代替四门。全部新增驱动归S M1–M10，788个实际BUF_X32，无新增寄存器/协议拍；其他五宏和原S基线保留，原始失败全部保留。

## 固定PG提前计算与严格合流

已在node2空闲槽追加同一S1350的现有pg_fixed_access候选计算。输入来自不可变真实sealed五文件与实际已生成GDS，逐一哈希/大小绑定，candidate-inputs和input-binding明确native_leaf_qualified=false/whole_system_qualified=false。候选已实际完成完整native DRC零违例、PG几何构造、原生加新增PG形状的实际GDS XOR读回，并进入原始完整GDS deck。该计算与原生完整DRC/最终功能/strict formal重叠，未把未验收的叶纳入合格manifest。

source137精确commit2ee4eee17adcd666123c2267c2b5dafe862401d3，941文件，归档SHA0862a85421e6e969f63da7a4fd1505f80d73438f7978f666256dc3dce6178655。Git网络重置后按原始Git对象身份发布并读回，force=false。新增--reuse-computation入口只接收本任务S1350：候选完整native/GDS计算必须实际通过；真正native选择/交付及四门真实回执必须全部通过；候选和合格叶的V/SDC/DEF/ODB/SPEF/GDS全部实际字节、大小及SHA必须一致；候选所有输入/输出也必须仍匹配。然后只复用完全相同的PG几何与完整DRC计算，保留原候选回执，不改写其false资格字段。新回执也不授予native_leaf_qualified，后续实际PG连通、新鲜RC/300MHz及最终交付仍必须完成。该复用合流尚待真正前置，**没有执行成功声明**。

本地六文件完全一致正例及六种文件各自实际字节变化/声明SHA变化共12项拒绝检查通过；语法与check_project通过。源码/文档差异检查通过；原始证据中的工具空白/CRLF按原字节保留和SHA校验，不能把整个原始快照的空白检查写成通过。

## 实际组合与资源

03链必须等待02链真正合格native交付及其实际function/formal；新PG合流/物理/时序/交付4项和新真实组合/精确电容界7项已追加。新S合格PG叶仍须实际选择、真实boundary-graph、完整最终单元三程序、原生STA/PG/电容前置；上层1380–1383及24后继门的严格发射器实际返回ready=false。原01/02链、所有pending/active/completed规格不改写。旧136本地依赖监视器仅停止其已核实的单个python进程，换成137监视同一硬件的新并行PG链；未停止任何Slurm任务。

单块/系统六文件和真实PNG收集器已指向03实际链，仍只在真实成功交付后写出。当前单块表保留旧S/335实例基线；收集后按真实新图更新Link8实例/状态数和S归属，不虚称新S已并入main。系统接收仍要求同一实际M11/M12场景几何、全PG、三初态程序与low/base/high分布RC/300MHz全部通过，不能借单块通过宣布系统通过。

仍为八自有节点2/3/4/5/6/7/25/26；c96最多6×16/c64最多4×16独立任务动态补位。node2实际三个独立16CPU任务重叠；node4功能完成后释放其槽，formal继续。活动规格的内存预测与sum(forecast)×1.2+16GiB保护不改，实际sstat已捕获；缺少ready任务时按真实依赖等待，不造任务宣称满槽。不动其他任务；R保留并由并行任务修改，当前六宏参考尚缺R接入。

负责人YUZE-LU继续全部最终布局布线、实际M11/M12/PG/三角点RC/300MHz及六文件、版图和源索引交付。规则rayggxia-project-collab1.0.0；登记management-hub PR5 pending；缺board.json，看板unverified/同步pending；处理人及审查人待指定，不自行合并。
