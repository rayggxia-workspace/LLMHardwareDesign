# Issue162 checkpoint26：S固定PG与实际235实例图通过单块验收，组合失败继续修复

Issue #162 / PR #163，分支 task/162-programmable-control，负责人 YUZE-LU。当前仍 in_progress / Draft，不合并。

源绑定证据见 [proof26/index.json](continuation-proof-26/index.json)：实际捕获 681 项远程记录，659 项按原字节复制，复制字节逐项核对SHA及大小；原始日志空白和失败原样保留。source138 commit 414dc24a0fd1bdcad6ea5b31bd9e7584aee8ea11，943文件，归档442028ecb33cdbde09661196c2aa609a1cdc5043fd23d3f67cab7115d16a802d；精确Git对象发布/读回，无force。

S1350完整原生四门之外，固定PG完整deck、实际PG连通、新鲜最终提取RC/300MHz及最终交付均正式通过；PG端子2674914，错误PG/未放置/打开输入0，setup/hold +0.017823/+0.005295ns。PG完整信号视图与成功功能/严格LEC视图逐字节相同，所有六文件和真实PNG已校验并打开检查。其他20类型复用精确已合格文件。见 [21类单块索引](block-delivery-s1350/index.json)及正式 docs/CONTROL_V1_BLOCK_DELIVERY.md。当前该索引的旧S适配器是通过单块、但组合失败的基线；新ready候选不能继承其资格。

原topology.py只输出真实图而未生成receipt。source138在独立Slurm任务重放冻结source137原命令，绑定原成功执行/全部输入/新S实际资格，graph、combined.v、leaves.v逐字节相同，完整Yosys逻辑模型相同（只忽略attributes.src源码位置）。实际重放审计通过；没有补造原回执。实际图235实例、21类型、209个Link8；100个原S外置Link8及隔离状态确已不再存在，原335图保留。

组合native STA失败：758 setup违例，WNS−0.106811ns；最坏S适配器s_b_ready到S b_ready，hold/electrical/注释覆盖通过。不得借单块通过声明系统通过。原摆放高RC线电容必要条件172项失败。电气约束候选1404–1407四个均low/base/high必要条件0违例，最好最大比0.87246785，仅为失败筛选诊断，实际RC/走线/PG/时序仍须验收。1400–1403错误请求linked-block旋转被既有防护拒绝；不改原规格，不移除防护，另追加合法新候选。

source139 commit c2ca8b00b3c701d196d8307aee6c45e9d43eb0c3（已精确发布/读回），943文件，archive a59f5bbbba63b5dedb915d3cbbb9cae7429d442f22a3cc9721ec990072f9e010：S适配器内部新增两个预测ready状态位，保持同沿后的原谓词，不加协议拍/包槽。独立生产/消费占用oracle逐周期检查及三初态RTL实际通过；两个物理候选1390/1391正在独立P&R，全部新四门和固定PG及真实组合必须重新验收。S本体不修改。新有状态逻辑明确属于control_adapter_s。后续图生成器完成后输出真实生成回执，仍不授物理资格。

代表程序已在原内存规则内获准执行，未停止旧1183 formal。此前内存停止辅助守卫在预算变化后拒绝动作，未有cancelled记录；已改为无实时拒绝则保留旧任务。仅重复PG95391.4在新PG正式通过后按UID/完整命令验证精确停止，父分配和全部证据保留。八自有节点，c96最多6×16/c64最多4×16独立任务动态补位，原内存规则不变；R及其他任务保留。

验证：check_project、topology重放属性/连接/类型/参数拒绝测试、Python语法通过；相关代码/文档diff --check通过，原工具快照不冒称空白检查通过。继续最终M11/M12/三角点RC/全PG/300MHz/实际代表程序/联合六文件；研究RC未作制造校准/EM-IR签核。

协作回执：rayggxia-project-collab1.0.0；项目llm-hardware-design；登记management-hub PR5 pending，看板unverified/同步pending（未配置config/board.json，处理人待指定），审查人待指定。未完成不记done，不自行合并。本检查点不是结束任务。
