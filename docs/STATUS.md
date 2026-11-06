# 当前状态

## R7.3.1–R7.3.2 四类接口与单 F 实测（2026-11-06 CST）

[Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179) / [Draft PR180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)。负责人 Melodydt。PR176 08f2ea20 无新提交。完成 U/C/F/J 试验接口清单和 F 镜像准入。服务器 97751 在 node27 完成。F 的 G 直写和 G→E ADD 两条固定试验路径通过 11/11 个场景，7 笔成功写回读回，24/24 个 P 回归通过。

下一步 R7.3.3 绑定 N 的统计、真实 S 回放和 E 写回。F 跨块传输和独立 300 MHz 时序列在 R7.3.6，正式 Block 端点按 R7.2 单独验收。[验证索引](../work/Melodydt/179/control-f-validation.json)

## R7.2 A2 与 A3 的计算写回和跨块交接联跑（2026-11-06 CST）

[Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179) / [Draft PR180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)。 负责人 Melodydt。复核 PR176 08f2ea20。服务器 97543 在 node27 完成，退出 0:0。10/10 端到端场景、8 笔真实写回和读回、50/50 既有 RTL 回归通过。两个新增局控配置在原 300 MHz 下通过 setup、hold、电气和等价检查。 P0 同一任务写回真实 M/G 结果并从 S 读出，等待 P1 实际写入后的匹配 ACK 才释放。

生产实现端提供同一版本的双 P 顶层、私有 S 选型、块内 M→G 和跨块数据及反向 ACK 端点后，先冻结 A1，再用该镜像流程复验真实 A2/A3、生产复位和组合物理。 PR180 保持 Draft，Issue179 保持 in_progress。

[验证索引](../work/Melodydt/179/control-chain-validation.json)

## R7.2 双局控写确认与复位验证（2026-11-05 CST）

[Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179) / [Draft PR180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)。 负责人 Melodydt。PR176 仍为 08f2ea20。已复核 main 27eaaace 的 16 KiB P4 SRAM 独立资格。作业 97466 在 node27 完成，退出 0:0。A3 16/16，覆盖 6 种非法 ACK 和丢 ACK 隔离。A4 6/6 实际集成及 11/11 协调器场景通过。A5 独立 ACK 校验器在原 300 MHz 下 setup +2.700939 ns、hold +0.115090 ns，电气及网表等价通过。

生产实现端须提供同版双 P 顶层、私有 S 选型、M→G 数据端点及跨块正反向端点。控制端核对绑定和镜像后，用真实路径重跑 A3，继而验证生产复位与组合物理。 PR180 保持 Draft，Issue179 保持 in_progress。

[验证索引](../work/Melodydt/179/control-r72-validation.json)

## A1 生产部署预检与 A3 准入（2026-11-05 CST）

[Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179) / [Draft PR180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)。 负责人 Melodydt。已复核 PR176 08f2ea20、PR178 cdbb3d53、PR163 091af608 和 main 10ea8a73。A1 完成试验绑定核验。12 个源码对象与 5 笔写回轨迹匹配服务器 97317，6 个变体拒绝，R4 静态合同 14/14。生产准入关闭，严格模式退出 2。

由控制端和 Block 实现端核对同一版本双 P 顶层，选定私有 S 容量，绑定 P0.TX→P1.RX 及由目标 S 实际写响应触发的反向 ACK。冻结端点和部署镜像后，再启动 A3 真实双 P 联调。 PR180 保持 Draft，Issue179 保持 in_progress。

[预检清单](../project/control_p_compute_v0_1/deployment_a1.json)

## A2-G 单 P 的真实 SiLU 与私有 S 写回（2026-11-05 CST）

[Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179) / [Draft PR180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)。 负责人 Melodydt。PR176 08f2ea20 已复核。服务器 97317 在 node27 退出 0:0。固定直达 SiLU 路线通过 9/9 个场景，5 笔真实 S 写回与参考一致，4 次描述符拒绝和 1 次真实 G 错误均保持目标 S。既有 RTL 回归 25/25，静态合同 14/14。新增母控、局控和适配器在原 300 MHz 周期通过独立时序、电气和等价检查。

下一步由控制端和 Block 实现端核对 A1 生产部署清单，冻结实际 M→G 边、跨块数据及反向 ACK 端点，再进入 A3 双 P 交接。A4 生产复位及 A5 组合物理验收待执行。 PR180 保持 Draft，Issue179 保持 in_progress。

[验证索引](../work/Melodydt/179/control-a2g-validation.json)

## 母控与局控 300 MHz 时序整改（2026-11-05 17:24 CST）

[Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179) / [Draft PR180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)。负责人 Melodydt。六个原 setup 违例配置在固定 3.333333333 ns 周期下完成门级整改。独立模块全局布线 RC 估算的 setup 和 hold 均通过，setup TNS 均为 0，电容与转换时间违例均为 0，6/6 网表通过逐周期等价检查。服务器 97316 在 node27 完成，退出 0:0。

后续接入实际 G 和选用的块内数据路线。完整 Block 的 CTS、详细布线、多工况提取与系统验收仍待。控制接入由 Melodydt 负责，组合后端实施责任人待指定。PR180 保持 Draft，Issue179 保持 in_progress。

## A2 单 P 的 M 计算与私有 S 写回（2026-11-05 16:26 CST）

[Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179) / [Draft PR180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)。负责人 Melodydt。单 P 的 M→S 控制切片已通过服务器验收。真实母控、局控、16 KiB 私有 S、feeder 和 M 完成 3 笔写回，3 个非法描述符按预期拒绝，5 个 A2 RTL 场景通过。R6 的 3 个场景复跑通过。作业 97305 与 97307 均退出 0:0。原 LC1 基线复现为 -68.781052 ns。

A2 后续接入实际 G 并验证选用的块内路线。生产部署冻结、双 P 接入、生产复位和组合物理验收待执行。控制端由 Melodydt 负责，生产 Block 与后端的实施责任人待指定。PR180 保持 Draft，Issue179 保持 in_progress。

## R7.2 真实 Block 接入与验收清单（2026-11-05 15:12 CST）

[Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179) / [Draft PR180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)。负责人 Melodydt。R7.2 已交付真实 Block 接入顺序和证据清单。先验证单 P 的实际计算、写回与完成，再验证双 P 的真实数据路径及反向 ACK，之后接生产复位并做组合物理验收。PR176 仍为 08f2ea20。PR163 最新检查点为 103，组合物理门仍待。本轮完成来源、接口、交付差异与文档核验，未执行新的 RTL 仿真或物理实验。

控制接入后续由 Melodydt 负责，真实 P 与组合后端的实施责任人待指定。取得版本化的 M/G/S RTL、端口和数值合同后，先跑单 P 的一笔实际写回，并行复现 LC1 高扇出路径。PR180 保持 Draft，Issue179 保持 in_progress。

## R7.1 控制成本与映射时序（2026-11-05 14:36 CST）

[Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179) / [Draft PR180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)。负责人 Melodydt。两套镜像占用 1152B 和 1168B，每成功任务接受 320B 控制包。97288 在 node27 完成，9 个配置映射通过，面积账为 0.227515 mm²。7 个单时钟配置中 6 个在 3.333ns 下出现 setup 负裕量，LC1 最差为 −68.781ns。10 份源码和 54 份输出已核验。R7.2 待执行。

R7.2 将按实测成本整理真实 Block 接入、时序约束与验收清单。 PR 为 Draft，Issue 保持 in_progress。看板条目待管理员核验。

## 2026-11-05 13:27 CST · R6.3 独立检查与服务器镜像联跑

[Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179) / [Draft PR180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)。负责人 Melodydt。独立二进制核验通过。6 份重新计算 SHA 的变体及 18 份非法 IR 被拒绝。作业 97286 在 node27 完成，退出 0:0。3/3 场景符合预期，4 个任务成功，丢 ACK 场景隔离。162 份源码输入、17 份证据及装载镜像 SHA 已核验。

R6 有界控制程序生成验收完成。下一阶段为 R7 控制成本与外部集成交接。 PR 仍为 Draft，Issue 为 in_progress。看板配置缺失，条目未核验，待项目管理员处理。

## 2026-11-05 13:09 CST · R6.1 任务 IR 与目标合同

[Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179) / [Draft PR180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)。负责人 Melodydt。目标表和 RAW16/P IR 解析器已交付。2 份样例准入，18 份非法输入拒绝，声明顺序归一化和 R4 存储合同对照通过。

下一步从 IR 生成三端程序镜像。 PR 仍为 Draft，Issue 为 in_progress。看板配置缺失，条目未核验，待项目管理员处理。

## 2026-11-05 12:53 CST：R4.1～R4.4有界真实provider控制研究交付

Issue179／Draft PR180，负责人Melodydt，最终父5886269a。14/14来源接口静态；10/10真实S、12/12真实DMA＋10/10桥接、6/6实际协调复位＋11/11协调器，共49/49本轮RTL（100%，非覆盖率），20次错误轨迹突变拒绝。最终97281／node27／debug／4核COMPLETED0:0；149源／26证据SHA核验；复核97280与最终RTL不变。真实旧响应flush、4次S payload保留探测、全量三镜像重装、新gen2／epoch2及连续job通过。原Markdown／同名PDF每阶段原位更新；PR176无更新，6份依赖原blob保持。

ACK为可信测试wrapper证书，生产管理传输／物理reset/CDC、活动M/G计算、M11/M12、全ISA／完整Block／数值／综合与物理未验收。R4补强有界门完成，整体Issue仍in_progress（R6／R7待授权），Draft／待指定审查人／未合并；登记pending，看板unverified／同步pending，无自动监测。

## 2026-11-05 12:33 CST：R4.3真实DMA控制门通过

Issue179／Draft PR180，负责人Melodydt，父62148314；实际MC＋2LC＋2私有S＋DMA＋双向CDC FIFO，有限外部native存储。97279／node27／debug／4核COMPLETED0:0：12/12集成＋10/10桥接边界，8错误轨迹拒绝。完整141bit身份与16bit tag分离，LOAD等S写ACK、STORE等外部写ACK，错误与tag耗尽隔离。139源／最终65证据文件及两次失败记录已核。原方案／同名PDF更新，下一步R4.4协调复位／重新装载；整体in_progress，Draft／待审查／未合并，登记pending，看板unverified／同步pending，无后台监测。

## 2026-11-05 12:16 CST：R4.2真实私有S控制门通过

Issue179／Draft PR180，负责人Melodydt，父179c1f79；新增可综合RAW16适配器，实际MC＋2LC＋2私有S，控制核心及原生依赖不改。97276／node27／debug／4核COMPLETED0:0；10/10集成，8轨迹突变拒绝，17写ACK／8读／1268背压边沿，130源／45证据文件SHA核验。原方案／同名PDF更新；下一步R4.3真实DMA，之后R4.4协调复位。整体in_progress，Draft待审查／未合并；登记pending，看板unverified／同步pending，无后台监测。

## 2026-11-05 12:03 CST：R4.1真实provider接口冻结

Issue179／Draft PR180，负责人Melodydt，父ecd6f49；PR176无变化。固定PR178 cdbb3d53和PR182 24e20d13，6份源RTL逐字引入；冻结真实S写ACK／地址单位、DMA完整身份映射与错误／cohort reset边界。来源和静态检查见project/control_r4_v0_1/contract.json及work/Melodydt/179/control-r4-validation.json。仅接口／静态门完成，R4.2～4尚待服务器仿真；既有164 RTL／173软件证据不重复计数。原方案／同名PDF更新，用户已允许额外额度。整体in_progress，Draft／待审查／未合并；登记pending，看板unverified／同步pending，无后台监测。

## 2026-11-05 04:43 CST：第15步R5有界控制研究交付

Issue179／Draft PR180，负责人Melodydt，父2e6d211。五类candidate资源／服务ABI、同一二进制解释器的分支／循环／ARG／PARAM／ADDI、非零old/next实际读值、消费者完成后发布、发布UNKNOWN查询／幂等重试、连续job和条件式cohort reset模型已交付。97246／node27／debug／1核COMPLETED0:0、3秒；34执行、30镜像拒绝、6组114复位／查询检查、4错误轨迹拒绝；113输入源／34轨迹SHA核验。现有164 RTL／173旧软件证据沿用，源码未改；本步是软件模型，不是新增U/C/F/J控制RTL、真实native／provider reset、数值或物理资格。
原方案／同名PDF原位更新，五类静态二进制示例与服务器镜像SHA一致；PR176无变化。按用户“直到R5”停止自动研究，R6／R7未执行；整体Issue仍in_progress、Draft／待审查／未合并。登记pending，看板unverified／同步pending，管理员／审查人待指定。仿真全部服务器执行，本机仅静态编码与PDF；未启用额外额度，无后台监测。


## 2026-11-05 04:09 CST：第14步实际双局控控制门

Issue179／Draft PR180，负责人Melodydt，父dc23b38。实际母控＋2LC取指／全包任务返回，有限16KiB SRAM／ACK网络；10集成／4错误轨迹拒绝，R4有界门满足。97243／node27／debug／4核COMPLETED0:0、27秒，25局控回归通过；26母控回归来自97238且源／checker不变。两次失败与修正记录保留，106输入源／61日志／4编译SHA核验。无reset连续job、两端不同task_sequence再执行、READY传参、背压独立推进及RX不可关闭时隔离均有实际控制证据。存储／链路是有限peer，不是原生S、完整Block或物理。
原方案／同名PDF更新，PR176无变化；下一步R5五类candidate控制profile、分支循环、old-next与取消／协调复位。研究in_progress，PR Draft／未合并；登记pending，看板unverified／同步pending，审查／管理员待指定。全部仿真服务器执行，额度不足保存停止，不使用额外额度，无后台监测。


## 2026-11-05 03:46 CST：第13步母控协议RTL

Issue179／Draft PR180，负责人Melodydt，父2384c31。母控5指令、2目标／8token、实际PM装载／取指、CALL参数快照、READY／G_WAIT及首错取消／排空；97234／node27／debug／4核COMPLETED0:0，26场景／4突变拒绝。两个子端为有限协议peer，R4实际两个局控接入尚待，非完整Block。94源文件、日志／输出SHA和97230～97234失败／通过记录见control-mother-validation.json；173软件／128局控RTL源未变，复用既有证据。
原方案及同名PDF更新。下一步实际母控＋两个LC／有限SRAM链路，再R5；PR176无变化。研究in_progress，Draft／未合并，审查人待指定；登记pending，看板unverified／同步pending，管理员待指定，无后台监测。所有仿真服务器执行，周额度不足保存停止，不使用额外额度。


## 2026-11-05 02:44 CST：第12步P／RAW16控制门

Issue179／Draft PR180，负责人Melodydt，父76fc765。9类局控指令的受限P／RAW16控制profile已具备进入R4证据：寄存器值读回、有限16KiB SRAM／16B接收槽、RX写后ACK、TX收到ACK后完成、对象valid／DROP、两任务新payload及取消／隔离。存储与链路仍为行为peer，不是原生S、通用控制器或完整Block。
173既有检查＋103原RTL来自97227（后续新TB编译位宽失败）；最终97229／node27／debug／4核COMPLETED0:0，25新场景／4轨迹突变拒绝。DUT与旧回归源SHA一致，三份新测试文件修正，失败日志均保留。原方案／同名PDF补进展；下一步R4母控二进制取指与两个局控，之后R5。研究仍in_progress；登记PR5 pending，看板unverified／同步pending，审查人／管理员待指定，无后台监测。


## 2026-11-05 02:06 CST：第11步对象生命周期

Issue179／Draft PR180，负责人Melodydt，父ddac1c8。单RAW16对象预约／DROP、错误／取消清理及范围互锁通过，执行／对象描述符使用显式loaded位拒绝整记录全零。服务器97225／97226均node27／debug／4核COMPLETED0:0；173既有检查＋76原控制／适配器RTL＋27对象场景通过，3新轨迹突变拒绝。r003只改runner新增全零执行描述符测试，DUT／其他仿真源与r002 SHA一致，因此旧回归有效关联且不重复计数。
现有总方案及PDF继续原位补充；下一步有限RAW16存储／RX/TX／ACK／READY报告，再R4／R5。当前仅逻辑预约；无S数据有效性与寄存器值读回、完整Block／母控／物理证据，R3整体未完成。登记PR5 pending，看板unverified／同步pending，审查人／管理员待指定。研究in_progress，未配置后台监测。


## 2026-11-05 01:45 CST：第10步M服务适配器

Issue179／Draft PR180，Melodydt，父af680f3。严格M_CLEAR_ALL_VALID适配器已接现有未改block_v2_m（blob d91ffdf904bc77c19d5d0ecfd4cd11560b44a417）；服务器97224／node27／debug／4核COMPLETED0:0，173既有检查＋61原RTL＋15适配器场景通过。5场景接真实M RTL、5命令／5响应逐次关联，10协议peer场景及3轨迹突变拒绝；clear不含GEMM数值或完整Block资格。源码实验commit944648b45efcf962091b3ca13c0d6dfd35501d5b，输入包SHA7222db6feced886a58f28819a4610551059b0853587fe8fa00aad89ac5248f20。
现有总方案及PDF补进展；下一步对象窗口／寄存器／收发事件，再R4／R5。研究in_progress，R3整体未完成；真实provider协调复位、其他宏服务与物理尚待。登记PR5 pending；看板unverified／同步pending，管理员／独立审查人待指定；未配置后台监测。


## 2026-11-05 01:25 CST：第9步故障RTL

Issue179／Draft PR180，Melodydt；父96b8280。当前M clear子集新增CALL身份准入、运行错误、native错误优先、有界无进展隔离；服务器97222／node27／debug／4核COMPLETED0:0，173既有＋10原RTL＋22取消＋29故障通过，两类各6项轨迹突变拒绝。源码实验commit f41158211ef69bb74a9252bd1790e53572e095e0，输入包SHA cac75c8d153b5afac4f04569326901d1e080dfc158eb866d8027cb0e3e71761e。
原TWO_LEVEL_CONTROL_PLAN.md及同名PDF补充进展；下一步服务适配器／对象／收发，再进入R4／R5。研究仍in_progress，未完成R3整体或真实Block；真实provider协调复位、母控、数值／物理未验收。登记PR5 pending；看板unverified／同步pending，管理员／审查人待指定；无后台监测。


## 2026-11-05：局控取消与有界排空RTL通过

局控CANCEL／有界排空RTL已通过服务器173既有检查、10原RTL及22取消场景；6项轨迹破坏均拒绝。最终97218／node27／debug／4核，0:0。真实provider复位、服务适配器、对象／收发和R4/R5仍待，研究in_progress。后续自动推进至R5，受用户周额度约束；每步更新固定总方案和同名PDF。


## 2026-11-04：最小功能局控RTL实际运行

[Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179)／[Draft PR180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)交付[最小功能局控](local-blocks/LOCAL_CONTROL_MIN_RTL_V0_1.md)：配置装载、CALL／PC及EXEC／WAIT／END。服务器作业97215、Verilator5.042、10场景通过，173既有软件／合同检查通过。M和PM为行为peer；R3整体、母控RTL、真实宏／完整Block及物理尚未验收。下一步取消／异常排空和适配器，再扩RAW16／RX/TX。研究in_progress，PR未合并，其他成员任务边界不变。


## 2026-11-04：局控RTL入口合同候选

[Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179)／[Draft PR180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)形成[局控RTL边界／状态机候选](local-blocks/LOCAL_CONTROL_RTL_CONTRACT_V0_1.md)，92逻辑信号、单程序存储端口互锁、返回信用／holding及存储下界；累计173组合同／软件检查。SystemVerilog仅接口／常量声明，HDL编译／功能仿真未执行，下一步功能局控最小切片。其他实现任务与完整Block边界不变，研究in_progress／PR未合并。

## 2026-11-04：两级控制模型补充取消与恢复

[Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179)／[Draft PR180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)新增[取消／poison／协同复位研究](local-blocks/CONTROL_RECOVERY_PLAN_V0_1.md)，9组恢复实验及9次恢复运行、2个模型复位cohort；累计137组软件检查通过。无tag隔离依赖provider复位／静默合同，RX关闭与RESET_ACK仍为拟议peer接口；真实Block复位域、控制RTL与物理尚未验收。下一步冻结局控RTL接口／状态机，其他成员任务边界不变，研究in_progress／PR未合并。

## 2026-11-04：两级控制研究进入首个二进制执行切片

[Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179)／[Draft PR180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)新增[母控／局控二进制解释模型](local-blocks/CONTROL_EXECUTION_MODEL_V0_1.md)：按完整镜像取指，以有限协议peer运行空任务、M清有效位及RAW16交接，9次实验／100次退休与独立参考通过。累计107组软件检查；没有控制RTL、完整Block或物理／数值验收。运行取消／provider协同复位和迟到响应仍待研究；原有宏和其他成员任务边界不变，研究in_progress／PR未合并。

## 2026-11-03：局部 Block 设计宗旨与三模型图册提案

[Issue #175](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/175) 提交[局部可定制 Block 提案](LOCAL_BLOCK_DESIGN.md)：Block 内外主要数据路线后定制、各 S 分管局部、母控/局部程序按模型编译；P/U/C/F/J 为3～4宏候选。同一示例资源给出 Qwen3.5/Falcon-H1/Granite 的七宏及组合两层图。仅文档提案，不启动服务器任务，不修改 #151/#162/#166 的实现或验收。六宏资格不变，R 仍未完成；新容量 S、控制、数值映射及实际 M11/M12 另行接收。

本次核对基线为 `4b1df2c7`（PR161 已合入），下方2026-11-01的“待合并”等表述保留为当时历史记录。当前叶宏结果以 [BLOCK_V2_RESULTS](BLOCK_V2_RESULTS.md) 为准。

面向 main 的六块交付：[PR #161](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/161)；已提交待独立审查，尚未合并。R 仍未完成。

## 2026-11-01：六块成果先交付，R 未完成

按用户决定先提交 M/N/E/G/S/T 六块，不等待 R；六块全部适用最终门及源绑定本地实收通过，R 标为未完成且不在合格清单。Issue #143 保持开放，研究 PR #144 保留；当前 `task/143-six-block-main` 基于 main a103da35，面向 main 的成果整合待独立审查。规格和结果见 docs/BLOCK_V2.md、docs/BLOCK_V2_RESULTS.md；核验命令见 docs/ARCHITECTURE.md。登记 PR5 pending；缺 config/board.json，看板 unverified/同步 pending；审查人待指定。历史记录保留在下方。

- 更新日期：2026-10-30（中国标准时间；本次只更新共同文档规划，不重跑物理实验）
- 当前规划补记：[Issue #139](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/139) 记录 M＋V 三宏（归约与归一化、基础向量算术、激活与门控）＋独立 R＋S＋T，详见[决策 0005](decisions/0005-compute-block-v-split-r.md)。各种先一个实现，逐宏交付最终布局布线；新三宏尚待实现、具体规格仍待验证，原 V 结果不转移资格。现有 #121/#130 实验保留，阵列/多实例/裕量版本/预连后移；本次未改变原实施任务状态或服务器作业。
- 当前阶段：首轮 Block 实现与表征推进；共同底座和任务定制分阶段验证。具体实现状态以 [Issue #121](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/121) / [PR #122](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/122) 为准；历史 H1/H2 证据保留如下。
- 本次共同文档澄清：[Issue #123](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/123) 记录[当前实施边界与分阶段冻结](decisions/0004-block-library-base-freeze.md)：首轮叶块不要求同时确定多实例、不同裕量物理版本组合或预连拓扑；这些在共同底座阶段确定并统一冻结。原实施任务的多阶段范围和验收状态不因此缩减。
- 历史 H1 工程：[Issue #15](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/15) 已完成openTPU ACT/MXU同功能／资源的块内及父层对照。三块和两父层、六类证明共十一份封存来源严格通过；拆分叶面积+0.412%、总信号线+7.142%、通孔+2.974%，完整setup／hold两组均满足2.5ns／0.5ns预算。[中文结果与三类图表](experiments/issue-15-opentpu-results.html)已生成并目视核验，详见[实验记录](experiments/issue-15-opentpu-comparison.md)。独立全量重布线21亦已自然完成并通过十一项来源／证明对照；本次整合不启动、终止或改写既有远程作业。
- 资料接入：[Issue #1：初始化项目并导入初期资料](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/1)；资料已进入 `main`，[PR #2](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/2) 已合并
- 当前资料：项目说明 v1.0（含 2026-10-30 架构规划补记）、专题研究文档、来源笔记，以及五个参考项目七个案例的布线分析包；三份 HTML 报告、llaccel 引擎内部分析及远程服务器规则已通过 [PR #4](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/4) 合入 `main`；工艺互连资料的逐层资源评估补充已一并提交
- 已确认边界：第一版采用 Nangate45 原生 M1–M10、via1–via9 预制，新增研究 M11/M12、via10/via11 后定制；叶块冻结与共同底座冻结分别验收。技术模型、完整宏、共同底座及多产品结果须按实际证据接收，不能将本次文档更新视为实现完成。
- 关键限制：现有布线结果包含少量 RTL 片段，不含完整源工程、物理数据库、工具环境和日志，不能单靠本仓库复跑物理实现
- 历史 H1 工程里程碑（2026-10-23 04:37 CST）：拆分89829自然完成全部严格物理、PG及完整STA，功能89831／RC覆盖89832／五个完整ODB成本复核89833也全部通过。快照f65688a957f13ef70216e923891ef6ff539adfc6f81c3e29a74ba5d10332720d，主对照不随实时采集变化。全量DRT21／89826及功能89827／覆盖89828／完整ODB89835也全部自然通过；补充快照独立保存，不改写主报告。全部作业UNLIMITED，无耗时取消。
- 整合交付：PR #8、#10 已合入 main，H1 完整整合树通过本地核验并由 PR #17 交付，其最终 CI／合并状态以在线记录为准。后续 H2 由[Issue #31](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/31)独立推进，本次不修改其工作树或运行任务。项目登记及看板权限仍待管理员处理，详见[整合回执](handoffs/2026-10-23-h1-html-integration.md)。

- 首轮结果：完整 VECTOR 已完成详细布线并导出最终寄生／宏模型，DRT错误0；3 ns setup及电容检查未通过。修复宏PG接入后，89472完整顶层 `COMPLETED 0:0`，DRT错误0、最终双网PSM和2246位接口检查通过，89475最终只读审计通过；父级仍有3个setup违例。历次失败保留，这些工程结果不构成合格硬核或系统签核
- 任务入口：[本仓库 Issues](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues)
- 项目登记：[管理中心 PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5) 待审查；合并前状态为 pending
- Projects 入口：候选[组织看板 #1](https://github.com/orgs/rayggxia-workspace/projects/1)；本轮查询因缺少 `read:project` 失败，且无 `config/board.json`，实际看板与条目 `unverified`、同步 `pending`。恢复动作见 [Issue #7 看板交接](handoffs/2026-10-21-issue-7-projects.md)

本页只记录全项目阶段和关键限制；具体任务进度以 Issue 和 PR 为准。
