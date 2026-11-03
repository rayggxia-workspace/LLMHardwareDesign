# 当前交付入口：23类单块合格，当前453组合仍待最终物理验收

更新：2026-11-04T07:47:49+08:00。单块以[current363规范索引](../work/YUZE-LU/162/block-delivery-r256-current363/index.json)的23类/138个最终文件为准，保留S1350内部驱动和R256；本地接收/版图证据沿各叶的源索引查询。当前453仅重接267个未使用Link8输入，其345个物理宿主、23类固定宏与有效接线保持，见[453状态归属绑定](../work/YUZE-LU/162/state-ownership-candidate453-binding.json)。各块的合格结果不授予整套组合资格。

当前完整路由和所有后继验收进度以[Checkpoint63](../work/YUZE-LU/162/continuation-checkpoint-63.md)与[CONTROL_V1](CONTROL_V1.md)为准；当前仍没有完整零冲突M11/M12路由、最终几何/PG、三档分布RC下300MHz和联合交付通过。[实际发布/在线读回与CPU采样](../work/YUZE-LU/162/publication-runtime-680-682/index.json)绑定提交22b1e110ca9e82147df64d32ea37929ccc18ade0的远程发布，以及Issue680/PR681逐字读回。682只在2秒采样中观察80个指定本人路由进程，共79.56核，不代表所有576核的长期利用率。八父节点、c64 4×16/c96 6×16独立任务动态补位继续，不合并。

以下保留历史阶段记录；其旧图、旧复位版本、旧轨迹或排队状态不得替代上述当前入口。

# Issue162：动态尝试池实测通过，新摆放完整路由与实际程序事件继续

更新时间：2026-11-04T01:21:36+08:00（中国标准时间）。[Checkpoint50](../work/YUZE-LU/162/continuation-checkpoint-50.md)记录252项服务器文件、237项原字节及15项本地辅助/读回证据。source407实际408回归通过：四项真实子进程调度测试、C++有限预算成功及四次全失败拒绝、原默认字节回放、有限资源oracle；默认旧池发射/seed/完成循环AST也逐项核对未改。新池只在16活动槽内有限64尝试动态补位，原内存门不变。4080/4081实际发射，原最终9项物理/RC/程序/预算源码保持。

4140/4141使用已有实际native/pin及exact密度摆放器，各16独立尝试和每项独立原必要检查均完成，low/base/high违例全0。实际面积148.683936/142.668192mm²，对比3690的85.895824mm²更大；high最紧下界占比0.999947902/0.999942741，裕量极小，不能宣布可布通或电气合格。4160/4161自然接替已完成摆放槽，全部七阶段完整路由链已发射/排队。累计22组当前候选链，包括失败、运行及等待，不能说22组完成。417实测区分冲突位置和额外占用：3931/4050首轮至下一轮平均额外占用下降约15%，冲突位置仍约165万；4081位置较少但额外占用更高，不能按单一指标宣布更优或收敛。

source411仅为当前八程序/六错误案例加旁观事件记录；编译/链接成功，三初态仍执行中。复用当前345实例编译模型且重新记录资产SHA，只插入观察语句，移除后完整恢复原test_system.cpp；原测试向量、数值检查和周期计数保持。将独立核对实际AR/R/AW/W/B、主机描述符计划和真实结束/错误返回，不称内部dispatch抓取或逐周期波形；未把未完成轨迹写为通过。当前原三初态完整功能成功仍见48。

规范仍current363的23类/138单块文件及current396的345实例状态宿主，保留块内驱动S1350/R256。仅精确核实后替换本人旧235实例无R的1490/1451/2231/1853四个重复子步骤，原源/规格/输出/父分配及其他/R任务不动。七父节点运行、第八因Resources等待，c64 4×16/c96 6×16；任务/尝试动态补位、原1.2倍+16GiB实测内存门保持。仍无完整M11/M12几何/全PG/low-base-high分布RC/300MHz/当前程序联合通过，继续迭代，不合并。Issue in_progress / PR Draft；登记PR5 pending、看板unverified/同步pending、管理员及审查人待指定。

# Issue162：有限线长分支搜索修复，继续当前组合最终物理验收

更新时间：2026-11-04T00:49:21+08:00（中国标准时间）。[Checkpoint49](../work/YUZE-LU/162/continuation-checkpoint-49.md)保存187项服务器记录、184项原字节和7项辅助文件。source400将可选有限预算分支改为(cost,wire)非支配标签和不可变父标签，避免单一代价丢弃短线候选及回溯线长漂移；401实际三个有限预算路由、120组独立完整状态图oracle、三个默认字节回放、11项非法输入拒绝通过。仍是逐分支搜索，4百万标签有内存边界，多接收端贪心树不构成完整性证明；当前部分尝试真实耗尽标签或连接失败，全部保留。九个最终物理/RC/程序/预算验收源逐SHA不变。

实际当前394单轮CUGR快照仍1573232违规，报告仅16809条，覆盖不完整；原棋盘过孔检查也拒绝。不能以详细报告样本当全部违规分布，亦不能把这次快照推成未来3751不可能。当前3740和旧3441完成50轮全局路由仍拥塞失败；自然释放槽补入4050，采用source400+拥塞代价1并保留全部七阶段后继。3931十六个独立尝试均完成首轮，最低1652885冲突，未通过。4010/4011及其余成熟搜索继续；累计18组当前场景完整搜索/后继链，不代表18组已完成。

规范仍current363的23类/138单块文件和current396的345实例状态宿主；S1350块内驱动、R256保留，当前八程序三初态及原生STA见48/47。尚无完整实际M11/M12几何/全PG/low-base-high分布RC/300MHz/当前程序联合通过。继续定位迭代，不合并。八父预算、七运行一排队，c64 4×16/c96 6×16动态补位和原(sum预测×1.2+16GiB)<实际MemAvailable门保持；不动其他任务。登记PR5 pending；看板unverified/同步pending；管理员/审查人待指定；Issue in_progress / PR Draft。

# Issue162：当前reset53真实八程序全通过，继续完整物理组合

更新时间：2026-11-04T00:17:09+08:00（中国标准时间）。Checkpoint48保存129项服务器记录、128项原字节和7项辅助文件。当前场景359的345实例/23类最终PG功能单元，真实八程序三初态全部通过：每次680884检查/217396周期，CPU张量搬运0。392独立逐SHA核对所有23类完整最终功能视图和实际连接顶层；没有拿旧273/reset28程序代替当前reset53证据。此项是零延迟功能成功，仍不是系统物理通过。

source388将测得原生地电容及最低接收pin负载扣入可选有限线长预算，复用原有哈希绑定/跨摆放一致性检查；17项单元测试通过。3890/3891实际1229条关键输出均启用新预算；部分独立尝试在R的rsp_data96跨块网预算处退出，其他尝试继续，不能据此宣布R单块失败或该摆放不可能。原maxcap/300MHz及9个实际物理/RC/程序验收源文件逐SHA保持，未放宽门槛。只精确核实后替换本人旧235实例1430/2230两子step，原证据/父分配/其他/R任务保留。八程序完成后node7自然补3930，node6的3931等待旧完整拥塞诊断3441自然结束；每项后继独立动态补位。

当前仍23类/138个单块交付，规范索引current363，S内部驱动与R256保留；已有11路加389/393共15组完整搜索/七阶段链，各自状态据实区分发射和等待。仍无最终实际M11/M12完整几何/全PG/low-base-high分布RC/300MHz/当前程序联合通过，继续定位迭代，不合并。本人八父预算、七运行一排队，c64 4×16/c96 6×16及(sum预测×1.2+16GiB)<实际MemAvailable原门保持；未动其他人的作业或外部R任务。登记PR5 pending；看板unverified/同步pending；管理员/审查人待指定；Issue in_progress / PR Draft。

# Issue162：新组合必要检查通过，十一条完整路由与最终程序继续

更新时间：2026-11-03T23:54:19+08:00（中国标准时间）。Checkpoint47保存1277项服务器记录、1192项原字节和14项辅助文件。实际reset53场景359的全原生端点/注释/电气检查通过，setup/hold +0.010286/+0.000194ns；这仍是原生诊断，不能替代带真实上层互联的组合验收。四个新摆放3690–3693通过原生地电容、最低输入pin和更强树长下界的low/base/high必要检查，最优3690的high最高占比0.910436；其余0.999215/0.999709/0.999990裕量很小。各自完成即进入独立后继检查，不等最慢摆放。

九条完整搜索（五组C++、两组FastRoute、两组CUGR）及各自六个原验收后继已实际发射/排队。source383增加仅影响搜索的非首选方向代价8/32；9个真实案例、3组默认路由/日志字节回放及9项非法输入拒绝通过，两组当前345实例完整搜索和六后继已动态补位，最终几何/PG/三RC/300MHz门源码保持。仅核实本人旧235实例无R的1480/1501两个重复子step后替换；原源/规格/所有部分输出、父分配和其他/R任务保留。当前八程序已完成实际最终单元编译，三初始化执行中；旧273结果不能替代当前359连接验收。

旧完整337诊断已独立核对16组全部路径，跨簇冲突参与率95.828839%，仍有907903–923066个冲突位置；不是系统通过。旧3250全局50轮仍333729 overflow；两份各20000区域拥塞报告的完整覆盖未经证明，376的“完整”措辞由378明确撤回，错误原件和更正一起保留。375孤立测试误将优先级辅助函数视为全图验证器的失败也保留；真实严格图验证前置后的3项非法输入均拒绝。没有降低任何门槛。

追加局部出口诊断：四个摆放各5335个实际宏pin／总线包围区域均未触发双层边界顶点容量必要条件，最高需求占比0.496441；只说明这些采样区域未获不可能证明，不能推成可布通。原55秒SSH采集超时后实际远程计算完成，已另行读回最终结果；未伪称采集一次成功。

当前规范仍23类/138文件（current363），S内部驱动及R256保留。尚无最终M11/M12完整几何/PG/三RC/300MHz/实际程序联合通过，任务继续、不合并。八父预算：七运行、一排队；c64 4×16/c96 6×16独立任务动态补位，原内存门不变。登记PR5 pending、看板unverified/同步pending、审查人与管理员待指定；Issue in_progress / PR Draft。

# 当前复位分组版本：23类型/138文件，系统仍待独立验收

[实际场景359的规范索引](../work/YUZE-LU/162/block-delivery-r256-current363/index.json)替代298作为当前入口：只把reset28更换为单独完整验收的reset53，其余22类型逐文件复用。reset53六文件/版图及[本地接收回执](../work/YUZE-LU/162/block-local-reception-r256-reset53-361/RECEPTION.json)均逐CRC/SHA验证；全部固定主动逻辑仍归M1–M10，53分支只共用一个复位状态位。实际345实例/316Link8/11147逻辑网的程序/原生/布局布线与三档RC/300MHz继续独立执行。以下旧清单与实验作为历史保留，不能推断新系统通过。

# 当前23类物理块：C8/R256固定PG全门与六文件实收

2026-11-03，中国标准时间。以[规范当前索引](../work/YUZE-LU/162/block-delivery-r256-current298/index.json)为准，23类型/138个最终文件逐项匹配实际合格清单274；原21类保留16类，替换5类控制并新增R256和其适配器。C8/R256在五类新增控制之后完成本轮原生及固定PG全门：[C交付](../work/YUZE-LU/162/block-delivery-r256-c285/index.json)、[C实收](../work/YUZE-LU/162/block-local-reception-r256-c285/RECEPTION.json)、[R交付](../work/YUZE-LU/162/block-delivery-r256-r296/index.json)、[R实收](../work/YUZE-LU/162/block-local-reception-r256-r296/RECEPTION.json)。全部ZIP成员已重新读回CRC/SHA，两张实际PNG已查看。[Checkpoint44](../work/YUZE-LU/162/continuation-checkpoint-44.md)给出新鲜setup/hold和原失败解释。

单块验收不授予345实例/11,122逻辑网组合资格。完整实际M11/M12、PG、三RC/300MHz、八程序及联合六文件仍继续全门。以下五类/旧21类记录按其原快照保留；涉及“C/R仍执行”的段落是历史阶段，最新单块交付以上方规范23类清单为准。

# R256 组合新增单块交付：五类已实收，C/R 独立验收继续

2026-11-03，中国标准时间。下表五类新配置均完成原生四门、固定 PG 完整 DRC、原几何精确保持、PG 连通、新鲜 RC、300MHz 及六文件交付；[逐块源绑定索引](../work/YUZE-LU/162/block-delivery-r256-five260/index.json)保留实际输入、检查和原始结果 SHA。

| 新物理类型 | die（µm） | 固定PG后 setup/hold（ns） | 实际版图 |
|---|---:|---:|---|
| control_route_r8 | 410×410 | 1.202418/0.003972 | [图](../work/YUZE-LU/162/block-delivery-r256-five260/images/control_route_r8.png) |
| control_status_r8 | 400×400 | 2.115414/0.033135 | [图](../work/YUZE-LU/162/block-delivery-r256-five260/images/control_status_r8.png) |
| control_reset_distribution_r28 | 400×400 | 2.100343/0.156889 | [图](../work/YUZE-LU/162/block-delivery-r256-five260/images/control_reset_distribution_r28.png) |
| control_s_arbiter_r7 | 1470×1470 | 1.237522/0.021788 | [图](../work/YUZE-LU/162/block-delivery-r256-five260/images/control_s_arbiter_r7.png) |
| control_adapter_r | 1490×1490 | 0.757920/0.007943 | [图](../work/YUZE-LU/162/block-delivery-r256-five260/images/control_adapter_r.png) |

本机已实收五个 ZIP／30 个最终文件，原六文件合计 422,207,592 字节，ZIP 合计 69,239,145 字节；每个成员 CRC／SHA 解压回读通过，五张实际 PNG 已查看。[本地回执及源绑定](../work/YUZE-LU/162/block-local-reception-r256-five260/RECEPTION.json)。存储目录 `D:\Data\电路实验\LLMHardwareDesign-deliveries\issue-162\blocks-r256-five260`，大文件不入 Git。

C8 新配置 2371 的原生布局布线、完整 GDS DRC、功能和严格等价均通过；固定 PG 后独立复验继续。R 复用已合格 R256 的原始固定信号几何；新 PG 仍须完成独立全门，不能继承旧六宏组合资格。R 的完整刚体位移为 (+0.095,+0.07)µm，使原生 (0,0) 接点相位接入既定全局相位；未移动单个接点或改动原 M1–M10 图形。345 实例／23 类型／11,122 逻辑网已真实提取，包含 316 个固定 Link8；尚无完整系统通过。

下面保留旧六宏参考组合的 21 类已合格单块基线及其真实交付。该旧表中 C/route/arbiter/status/reset 的参数配置与新增 R256 组合不同，不能直接替代新配置验收。

# Issue162 最终单块交付（S内部驱动及S适配器ready修复）

21类物理块全部原生四门及固定PG/新鲜RC/300MHz验收通过。S1350内部788个BUF_X32无新增状态；S适配器两个预测ready状态位明确归该物理宏，保持原协议拍和有限包槽。其余19类型、S本体均复用精确已合格文件。S/T为标准单元存储。R保留并由并行任务修改，此表不宣称已接入。

**单块通过不代表系统通过。** 全网M11/M12/真实全PG/low-base-high分布RC/300MHz/实际代表程序及联合交付须独立验收。旧失败/基线索引完整保留。

[六文件、SHA和全部源绑定索引](../work/YUZE-LU/162/block-delivery-ready140/index.json)。所有图片均为实际交付PNG。

2026-11-03 13:10 CST：本机已完整实收21个ZIP，含126个最终文件、21张实际版图及105份验收回执。原六文件共7,633,691,838字节，ZIP合计1,637,695,602字节；每个成员均完成远程原字节SHA及本地ZIP解压读回CRC/SHA核验。文件位于 `D:\Data\电路实验\LLMHardwareDesign-deliveries\issue-162\blocks-ready140`，不将大文件提交Git。[本地实收回执](../work/YUZE-LU/162/block-local-reception-ready140/RECEPTION.json)及[接收器/原索引绑定](../work/YUZE-LU/162/block-local-reception-ready140/SOURCE_BINDING.json)保留各ZIP和全部成员SHA。此次实收只覆盖上述已合格单块，完整组合验收继续。

| 物理块 | 功能 | 实例数 | die（µm） | 活动面积（µm²） | setup/hold（ns） | 版图 |
|---|---|---:|---:|---:|---:|---|
| block_v2_m | M矩阵计算 | 1 | 930×930 | 304,530.90 | 0.039857/0.018500 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/block_v2_m.png) |
| block_v2_n | N归约/归一化/统计 | 1 | 510×510 | 68,015.67 | 0.140712/0.017753 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/block_v2_n.png) |
| block_v2_e | E逐元素/格式 | 1 | 600×600 | 63,751.69 | 0.412125/0.019608 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/block_v2_e.png) |
| block_v2_g | G函数计算 | 1 | 400×400 | 22,831.05 | 0.512034/0.017721 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/block_v2_g.png) |
| block_feed_s_macro | S16KiB标准单元工作存储与feeder | 1 | 1680×1680 | 1,191,739.58 | 0.017823/0.005295 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/block_feed_s_macro.png) |
| transaction6k | T6KiB结果交接 | 1 | 1040×1040 | 431,244.79 | 0.429092/0.007988 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/transaction6k.png) |
| control_c | 可编程C | 1 | 740×740 | 209,902.20 | 0.340552/0.000705 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/control_c.png) |
| control_d | 有限DMA搬运D | 1 | 1170×1170 | 123,455.12 | 0.058717/0.008420 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/control_d.png) |
| control_endpoint_queue | 任务/完成队列 | 7 | 470×470 | 12,159.66 | 1.564079/0.000901 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/control_endpoint_queue.png) |
| control_axil_bridge | AXI-Lite配置桥 | 1 | 400×400 | 3,254.51 | 1.255634/0.008345 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/control_axil_bridge.png) |
| control_adapter_m | M块旁适配器 | 1 | 770×770 | 10,567.91 | 1.357095/0.005789 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/control_adapter_m.png) |
| control_adapter_n | N块旁适配器 | 1 | 1110×1110 | 22,220.58 | 0.365794/0.001216 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/control_adapter_n.png) |
| control_adapter_e | E块旁适配器 | 1 | 1220×1220 | 25,744.01 | 0.268239/0.006154 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/control_adapter_e.png) |
| control_adapter_g | G块旁适配器 | 1 | 790×790 | 15,269.20 | 0.559934/0.004560 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/control_adapter_g.png) |
| control_adapter_s | S块旁适配器 | 1 | 1740×1740 | 27,024.80 | 1.444169/0.019669 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/control_adapter_s.png) |
| control_adapter_t | T块旁适配器 | 1 | 1020×1020 | 13,605.63 | 1.301787/0.007043 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/control_adapter_t.png) |
| control_route | 固定控制派发/完成路由 | 1 | 400×400 | 2,581.00 | 1.284751/0.047432 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/control_route.png) |
| control_s_arbiter | S端口仲裁与交接 | 1 | 1330×1330 | 14,599.41 | 1.331618/0.021265 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/control_s_arbiter.png) |
| control_status | 错误/状态汇总 | 1 | 400×400 | 72.88 | 2.082342/0.015338 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/control_status.png) |
| control_reset_distribution | 固定复位分配 | 1 | 400×400 | 404.32 | 2.110863/0.156328 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/control_reset_distribution.png) |
| control_link8 | 8lane固定驱动与1bit复位隔离 | 209 | 100×100 | 180.08 | 1.458625/0.154350 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/control_link8.png) |

实际图共235实例、209个Link8。原生die面积加总21,516,200.00µm²，活动面积加总2,673,569.99µm²，不含宏间留白。
