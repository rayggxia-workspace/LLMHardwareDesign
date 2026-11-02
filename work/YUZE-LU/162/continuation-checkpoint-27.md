# Issue162 checkpoint27：S适配器单块全通过，1391实际原生组合STA通过，四路M11/M12继续

当前分支task/162-programmable-control，Issue #162 / PR #163，负责人YUZE-LU，in_progress / Draft，不合并。本检查点不结束任务。

[proof27](continuation-proof-27/index.json)实际捕获 326 项远程源绑定记录，287 项按原字节复制，逐项核对大小/SHA；辅助脚本及精确Git发布回执另索引。所有原始快照以-text保存，提交后还核对Git blob与实际捕获字节。

source139精确commit c2ca8b00b3c701d196d8307aee6c45e9d43eb0c3，943文件，archive a59f5bbbba63b5dedb915d3cbbb9cae7429d442f22a3cc9721ec990072f9e010；新增两个预测ready状态位属于S适配器M1–M10，不增加包槽/协议拍；S1350本体及其他20类全部保留。三初态RTL各21070检查/4569周期/1450包通过，独立生产/消费占用oracle逐周期检验ready。1390/1391各自完成实际P&R、原生全部四门、固定PG完整deck、实际PG物理、新鲜RC/300MHz和六文件交付；仅1391作为当前所选实现。实际单块索引 [block-delivery-ready140](block-delivery-ready140/index.json)，实际PNG已打开检查。其S适配器1740×1740µm、活动面积27024.802µm²，原生单块setup/hold +1.444169/+0.019669ns，不能拿来替代组合路径。

source140精确commit 0f6c47b9bba177dbf2ac1f223a02dd22a7f6b33f，943文件，archive d0bee6bd0aae0f1f0614e52c7094d207e2c8ad08496f0de3c4a1a62abd9a1176，已发布/冻结。新拓扑生成器在真实完成所有抽取/归属验证后输出生成回执，不授予物理资格。上次proof26的12份Git自动换行转换已由a857b4620272d37687f3b4e9b05b13255c1a043f恢复原始捕获字节，全部Git blob重新核验；远程原始数据/门槛未改，详见proof26-line-ending-correction.json。

1391同一实际235实例图、209个Link8的完整原生拼接STA正式通过：最坏setup +0.023951065ns（汇总按6位小数），setup/hold计数均0，电气、所有实际计时端点和注释覆盖通过。1390仍有−0.000684786ns setup，按失败保留，不放宽阈值。实际M11/M12仍未通过，23.95ps原生裕量很小，不能宣布系统通过。两个实际场景的代表程序仍在编译/执行，旧S1350组合程序也保留正常收尾，不继承旧结果。

1391第一次原生地电容合并检查在passed审计已写出、最终大文件哈希回执尚未完成的短窗口启动，因receipt.json未存在而失败；是任务先后错误，未获得任何电容资格。确认实际完整receipt已完成、execution及typed timing真实通过并精确绑定审计SHA后，仅追加native-cap-residual-02新任务，原失败/规格不改。重试完全复用原计算及门，两个摆放1404/1405的原生地电容+上层线电容必要条件均low/base/high0违例；仍省略耦合/全部pin负载/绕路/过孔，只用于筛选失败，不是最终RC证明。

实际严格发射器选定1391及1404摆放，追加28条不可变任务：1410/1411/1412/1413四个独立M11/M12全网路由，及各自真实几何/原生mask XOR/全PG/三角点完整分布RC与300MHz/实际程序和联合六文件验收。路由参数只改变搜索，不放宽任何门；源算法与已过source114回归逐文件相同。1410到node2、1411到node4，1412/1413到c96 node25，节点内动态补位；native STA与真实程序在node3/5/6/7并行，仍共八自有节点。

为给新组合补位，仅逐一核对UID、完整命令、原335实例/100个S外置Link8图及新适配器正式PG通过，精确停止旧外置S路由steps95155.72、95101.50、95102.48，每个占满节点仅一条；原规格/部分输出、其他旧实验、父分配、R及其他任务均保留。这些是方案淘汰的未完成搜索，不冒充硬件失败。原6×16(c96)/4×16(c64)上限和sum预测×1.2+16GiB保护不改；实际补位已核验。

check_project通过，相关Python语法、重放模型属性/连接/类型/参数拒绝测试已通过；代码/文档差异检查与原工具快照空白分开。下一步持续处理四路搜索、实际几何/PG/三角点RC/300MHz及最终单元三初态代表程序，失败继续定位迭代，全部最终六文件/版图/源索引须实际齐全。

协作回执：rayggxia-project-collab1.0.0；llm-hardware-design；登记management-hub PR5 pending；看板unverified/同步pending（缺config/board.json，处理人待指定），审查人待指定。R保留并由并行任务修改，本声明组合不宣称其已接入。研究RC未制造校准/EM-IR签核。不自行合并，不标done。
