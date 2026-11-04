# Issue162 continuation checkpoint78

更新时间：2026-11-04T20:20:31+08:00。YUZE-LU；[Issue162](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/162) / [Draft PR163](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/163)。承接[77](continuation-checkpoint-77.md)。

**完整组合仍未通过，任务继续，不合并。** 保留main六宏M/N/E/G/S/T、R256、S1350内部788驱动、23类型/138份单块六文件与345状态宿主。当前453图SHA `49ba0e348f3583f6facdf60e771fe6f1329b46fe5aac872c3828d4b61ddb1a68`、S5380位置、所有M1–M10及被动M11/M12边界不变；外部R修订及其他任务不动。规范宏交付仍见[current363](block-delivery-r256-current363/index.json)，状态归属见[current396](state-ownership-current396.json)/[453绑定](state-ownership-candidate453-binding.json)。

**1272三个初态的真实内部程序轨迹已实际完成并通过。** 冻结source1270 `46c5820b42bf552d82e4e2d1a0446f7ff2925c6c`（1024源，归档SHA `e34fb39f43595d9f7000c8ba4f739c74c0754076a7f771b75f40b87855d229be`）只重新编译观察bench并链接同一345实例/23类最终单元模型。3226位绑定当前图同一物理网的实际root成员；C_WORD、Q_CMD、Q_TASK、Q_COMPLETE、Q_DONE、C_DONE分别记录C接受的发射字、队列接受/组包后任务、适配器完成及返回/C接受完成。三个初态(1,162)/(2,162)/(2,163)均保留原680884检查、217396周期、8数值程序、14案例、18调用和CPU张量搬运0。逐包核C8指令字、任务载荷、标签/端点完成、返回及所有队列排空。每份完整内部JSONL1517533字节、SHA `3be8f1ff499c3e3f376b62012b7e3f7f040ace8e5ed1c45f4bfd8ad7305514bc`；外部过滤JSONL均与原473逐字一致，原480协议/已知读写payload证据保持。不是逐周期波形，也不是上层物理通过。

1292在接收端独立完整重放三份原始轨迹，并各破坏六种握手中的一项，六份完整破坏均被拒绝。1290接收器错误地要求顶层receipt直接列出dispatcher而停止，1291以冻结manifest/1273源审计另行绑定；随后Windows文本输出把本地一个外部过滤文件LF改为CRLF，SHA拒绝。1292先保存失败字节并从服务器恢复原件，再在自有本地scratch审计函数中仅加 `newline=''`；反向替换精确还原原函数、所有协议/载荷检查不变。服务器原始三态结果、源码、模型均未改动，无重跑仿真。两次接收端失败不解释为功能失败，修复也不掩盖原件。[完整轨迹/负控/来源归档索引](internal-program-events-current1272/index.json)已实收CRC/SHA核验，ZIP885077字节SHA `2d82990cc2dcb235f79ce6166c0c200595ca56fa3d7198bdc13abc88c64b5139`。

12840/12841仅复用已实现且有736/745实际回归的渐进双端窗口4/16，保持source1250、cutoff16/stride16/cost8/加法history/seed4662及9060 trial0真实暖前缀；无新增源/硬件/门变化。1285严格14份完整七阶段规格、六键验收及当前函数/事件绑定通过。1272自然结束后12840自动补位；1286仅核验替换本人6563/source653/95391.98子步骤，原始源/规格/所有失败及部分输出保留，未取消父任务。1287、1293分别实际核验node4/node2各16个路由进程及16对输入体/暖前缀、CLI、四个互不重叠16CPU掩码和内存准入，合计32个。1287控制台误把单节点结果标成two_nodes，执行原件和erratum保留；不能据此声称单份1287覆盖两节点，1293是独立node2证据。当前node2/node4预测256GiB、需323.2GiB可用，实核通过。8父节点36×16=576CPU，c64四槽/c96六槽动态补位不变。

1280对自有node4/95391的12561 trial0执行5秒99Hz用户CPU采样，495样本无丢失，settled函数74.55%、四叉pop22.22%、push3.23%；仅该进程该时间窗，不能推为全局收益。1281前缀符号annotate返回空原件保留，1282完整annotate76943字节；指令采样没有支持“除法为主要瓶颈”，未据此盲加缓存。1294只读35组当前候选实际日志尾：最小仍约613742冲突点，输出均非完整零冲突。11200等到63/64轮，12560/61和窗口4/16均未完成；不能从慢/非零推出全图不可行，也不能从小例或原生通过宣布系统通过。

[远程索引](continuation-proof-78/index.json)/[原字节ZIP](continuation-proof-78/selected-originals.zip)含82项，SHA/CRC逐项验证；运行路由只收不可变读取前缀。[本地索引](continuation-proof-78/local-index.json)/[辅助ZIP](continuation-proof-78/local-helpers.zip)含39项执行/失败原件和只读报告。继续全图零冲突、真实M11/M12接入、最终几何/PG/low-base-high分布RC300MHz setup/hold/电气联合门及最终六文件、版图、源绑定交付；本检查点不结束任务。

规则rayggxia-project-collab1.0.0；project_id llm-hardware-design；本人YUZE-LU。管理结构检查PASS，不替代业务验收；登记management-hub PR5 pending；缺board.json，看板unverified/同步pending，管理员/审查人待指定；Issue in_progress、PR Draft/open/未合并。
