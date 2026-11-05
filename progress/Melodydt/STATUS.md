# Melodydt 的进度

## A2-G 单 P 的真实 SiLU 与私有 S 写回（2026-11-05 CST）

[Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179) / [Draft PR180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)。 负责人 Melodydt。PR176 08f2ea20 已复核。服务器 97317 在 node27 退出 0:0。固定直达 SiLU 路线通过 9/9 个场景，5 笔真实 S 写回与参考一致，4 次描述符拒绝和 1 次真实 G 错误均保持目标 S。既有 RTL 回归 25/25，静态合同 14/14。新增母控、局控和适配器在原 300 MHz 周期通过独立时序、电气和等价检查。

下一步由控制端和 Block 实现端核对 A1 生产部署清单，冻结实际 M→G 边、跨块数据及反向 ACK 端点，再进入 A3 双 P 交接。A4 生产复位及 A5 组合物理验收待执行。 PR180 保持 Draft，Issue179 保持 in_progress。

时区 Asia/Shanghai（UTC+08:00）。控制端由 Melodydt 负责，生产 Block 与组合后端的实施负责人待指定。登记 PR5 待合并，看板配置缺失。[验证索引](../../work/Melodydt/179/control-a2g-validation.json)

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

## 2026-11-05 13:14 CST · R6.2 三端程序镜像生成

[Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179) / [Draft PR180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)。负责人 Melodydt。两套三端镜像通过装载合同检查。联合等待掩码 0x14，分组等待掩码 0x40、0x80。字节级重建一致，证据见 control-r6-build-index.json。

下一步独立解码与服务器 RTL 联跑。 PR 仍为 Draft，Issue 为 in_progress。看板配置缺失，条目未核验，待项目管理员处理。

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

本人分支task/179-local-block-continuation，base task/175-local-block-design；独立部分API目录work/Melodydt/179/control-profiles-2e6d211/delivery，无.git。服务器/public/home/yuzelu/Melodydt/issue179-control-profiles-2e6d211/r003/source，实验commitca954d4294cb320667d35e9741caf90acd0a6513，输入包1aea66096bd4e95786679a658e81e0eda9277ba43198843a88a583c9074729e7。当前任务无未结束作业；恢复下一阶段须先读最新PR176及Issue／PR／交接，未配置自动跟进。

## 2026-11-05 04:09 CST：第14步实际双局控控制门

Issue179／Draft PR180，负责人Melodydt，父dc23b38。实际母控＋2LC取指／全包任务返回，有限16KiB SRAM／ACK网络；10集成／4错误轨迹拒绝，R4有界门满足。97243／node27／debug／4核COMPLETED0:0、27秒，25局控回归通过；26母控回归来自97238且源／checker不变。两次失败与修正记录保留，106输入源／61日志／4编译SHA核验。无reset连续job、两端不同task_sequence再执行、READY传参、背压独立推进及RX不可关闭时隔离均有实际控制证据。存储／链路是有限peer，不是原生S、完整Block或物理。
原方案／同名PDF更新，PR176无变化；下一步R5五类candidate控制profile、分支循环、old-next与取消／协调复位。研究in_progress，PR Draft／未合并；登记pending，看板unverified／同步pending，审查／管理员待指定。全部仿真服务器执行，额度不足保存停止，不使用额外额度，无后台监测。

分支task/179-local-block-continuation，base task/175-local-block-design；本地独立部分API目录work/Melodydt/179/control-rtl-network-dc23b38/delivery；服务器/public/home/yuzelu/Melodydt/issue179-control-network-dc23b38/r003/source，实验commit738720d495eaf5ea53f123bfaacc67c19ef3ff68。MC／LC源码未改，测试实例STALL4096／取消DRAIN128。

## 2026-11-05 03:46 CST：第13步母控协议RTL

Issue179／Draft PR180，负责人Melodydt，父2384c31。母控5指令、2目标／8token、实际PM装载／取指、CALL参数快照、READY／G_WAIT及首错取消／排空；97234／node27／debug／4核COMPLETED0:0，26场景／4突变拒绝。两个子端为有限协议peer，R4实际两个局控接入尚待，非完整Block。94源文件、日志／输出SHA和97230～97234失败／通过记录见control-mother-validation.json；173软件／128局控RTL源未变，复用既有证据。
原方案及同名PDF更新。下一步实际母控＋两个LC／有限SRAM链路，再R5；PR176无变化。研究in_progress，Draft／未合并，审查人待指定；登记pending，看板unverified／同步pending，管理员待指定，无后台监测。所有仿真服务器执行，周额度不足保存停止，不使用额外额度。

本人分支task/179-local-block-continuation，base task/175-local-block-design；本地work/Melodydt/179/control-rtl-mother-2384c31/delivery为独立无.git部分API副本。服务器/public/home/yuzelu/Melodydt/issue179-control-mother-2384c31/r005/source，实验commit3b4ef844df72346271988ce33b5941cc3fa82aba；输入包e215d4a38b9da476c686c0d5f2ded52c7081a5354d27f15262c47ab22cf08015。

## 2026-11-05 02:44 CST：第12步P／RAW16控制门

Issue179／Draft PR180，负责人Melodydt，父76fc765。9类局控指令的受限P／RAW16控制profile已具备进入R4证据：寄存器值读回、有限16KiB SRAM／16B接收槽、RX写后ACK、TX收到ACK后完成、对象valid／DROP、两任务新payload及取消／隔离。存储与链路仍为行为peer，不是原生S、通用控制器或完整Block。
173既有检查＋103原RTL来自97227（后续新TB编译位宽失败）；最终97229／node27／debug／4核COMPLETED0:0，25新场景／4轨迹突变拒绝。DUT与旧回归源SHA一致，三份新测试文件修正，失败日志均保留。原方案／同名PDF补进展；下一步R4母控二进制取指与两个局控，之后R5。研究仍in_progress；登记PR5 pending，看板unverified／同步pending，审查人／管理员待指定，无后台监测。

本人分支task/179-local-block-continuation，base task/175-local-block-design；本地独立部分API目录work/Melodydt/179/control-rtl-transfer-76fc765/delivery，服务器/public/home/yuzelu/Melodydt/issue179-control-transfer-76fc765/r003，实验commit7d8790967e46314a37e27428e5346fd209d956a9。84输入源文件、128当前场景／8编译日志SHA核验，见control-transfer-validation.json。所有仿真在服务器，本机仅静态核验与PDF。周额度不足时保存停止，不启用额外额度。

## 2026-11-05 02:06 CST：第11步对象生命周期

Issue179／Draft PR180，负责人Melodydt，父ddac1c8。单RAW16对象预约／DROP、错误／取消清理及范围互锁通过，执行／对象描述符使用显式loaded位拒绝整记录全零。服务器97225／97226均node27／debug／4核COMPLETED0:0；173既有检查＋76原控制／适配器RTL＋27对象场景通过，3新轨迹突变拒绝。r003只改runner新增全零执行描述符测试，DUT／其他仿真源与r002 SHA一致，因此旧回归有效关联且不重复计数。
现有总方案及PDF继续原位补充；下一步有限RAW16存储／RX/TX／ACK／READY报告，再R4／R5。当前仅逻辑预约；无S数据有效性与寄存器值读回、完整Block／母控／物理证据，R3整体未完成。登记PR5 pending，看板unverified／同步pending，审查人／管理员待指定。研究in_progress，未配置后台监测。

分支task/179-local-block-continuation，base task/175-local-block-design。本地独立部分API工作目录work/Melodydt/179/control-rtl-object-ddac1c8/delivery，服务器/public/home/yuzelu/Melodydt/issue179-control-object-ddac1c8/r003，实验commit6df461bc7b4429fb83975bdae0e3ce8337b834ba；SHA、结果和精确命令见control-object-validation.json。仿真均在服务器，本机仅静态检查／PDF；周额度不足即保存停止，不启用额外额度。

## 2026-11-05 01:45 CST：第10步M服务适配器

Issue179／Draft PR180，Melodydt，父af680f3。严格M_CLEAR_ALL_VALID适配器已接现有未改block_v2_m（blob d91ffdf904bc77c19d5d0ecfd4cd11560b44a417）；服务器97224／node27／debug／4核COMPLETED0:0，173既有检查＋61原RTL＋15适配器场景通过。5场景接真实M RTL、5命令／5响应逐次关联，10协议peer场景及3轨迹突变拒绝；clear不含GEMM数值或完整Block资格。源码实验commit944648b45efcf962091b3ca13c0d6dfd35501d5b，输入包SHA7222db6feced886a58f28819a4610551059b0853587fe8fa00aad89ac5248f20。
现有总方案及PDF补进展；下一步对象窗口／寄存器／收发事件，再R4／R5。研究in_progress，R3整体未完成；真实provider协调复位、其他宏服务与物理尚待。登记PR5 pending；看板unverified／同步pending，管理员／独立审查人待指定；未配置后台监测。

本地独立部分API目录work/Melodydt/179/control-rtl-adapter-af680f3/delivery，分支task/179-local-block-continuation，base task/175-local-block-design；原始结果留本人服务器目录/public/home/yuzelu/Melodydt/issue179-control-adapter-af680f3/r002，输入／输出／日志SHA见control-adapter-validation.json。所有仿真在服务器，本机仅静态核验与PDF；额度接近耗尽即保存停止，不启用额外额度。

## 2026-11-05 01:25 CST：第9步故障RTL

Issue179／Draft PR180，Melodydt；父96b8280。当前M clear子集新增CALL身份准入、运行错误、native错误优先、有界无进展隔离；服务器97222／node27／debug／4核COMPLETED0:0，173既有＋10原RTL＋22取消＋29故障通过，两类各6项轨迹突变拒绝。源码实验commit f41158211ef69bb74a9252bd1790e53572e095e0，输入包SHA cac75c8d153b5afac4f04569326901d1e080dfc158eb866d8027cb0e3e71761e。
原TWO_LEVEL_CONTROL_PLAN.md及同名PDF补充进展；下一步服务适配器／对象／收发，再进入R4／R5。研究仍in_progress，未完成R3整体或真实Block；真实provider协调复位、母控、数值／物理未验收。登记PR5 pending；看板unverified／同步pending，管理员／审查人待指定；无后台监测。

本人分支task/179-local-block-continuation；本地独立部分API工作目录work/Melodydt/179/control-rtl-fault-96b8280/delivery，服务器/public/home/yuzelu/Melodydt/issue179-control-fault-96b8280/r005。实际检查及SHA见work/Melodydt/179/control-fault-validation.json；所有仿真在服务器，文档／静态核验在本机。周额度接近耗尽即保存停止，不启用额外额度。

## 2026-11-05 01:00（Asia/Shanghai）：第8步取消RTL

[Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179)／[PR180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)，负责人／认证Melodydt。PR176开始仍08f2ea20，无新增讨论；上传前再核。

局控CANCEL／有界排空RTL已通过服务器173既有检查、10原RTL及22取消场景；6项轨迹破坏均拒绝。最终97218／node27／debug／4核，0:0。真实provider复位、服务适配器、对象／收发和R4/R5仍待，研究in_progress。后续自动推进至R5，受用户周额度约束；每步更新固定总方案和同名PDF。

父a54cbc4；本地独立部分API目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/control-rtl-cancel-a54cbc4/delivery，无.git；服务器独立实验commit6950be60082c1e5320843c2dce144410cfb3633d，不是PR HEAD。源、日志和结果SHA见control-cancel-sources.json／validation.json。登记PR5 pending，看板unverified／同步pending，审查人待指定。


## 2026-11-04 23:47 CST（Asia/Shanghai，UTC+08:00）：第7步最小功能局控RTL

- [Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179)／[Draft PR180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)，负责人／认证Melodydt，write；PR176开始、恢复和上传前均仍08f2ea20，正文及讨论无变化。
- [功能RTL研究](../../docs/local-blocks/LOCAL_CONTROL_MIN_RTL_V0_1.md)及project/control_rtl_min_v0_1实现配置／单PM口、CALL／任务与执行描述符读取、PC及L_EXEC/WAIT/END；同一DUT执行空任务和M clear程序。每轮进展已直接补总方案。
- Slurm97215在node27、debug分区4核完成，0:0；10场景3926边沿，5份执行轨迹独立检查，13退休／4服务／6终态。173既有软件／合同检查通过；源码、输入／输出SHA和失败／成功作业见control-min-sources.json、control-min-validation.json。
- 服务器实验源码commit d880b56ee06414d6f3e344b20e19ce6badc00feb，为独立快照，不是PR HEAD。最终PR父41777f1d，最终SHA／远端读回／CI见PR180回执。
- 本地部分API目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/control-rtl-min-41777f1/delivery，无.git／HEAD／index；服务器目录/public/home/yuzelu/Melodydt/issue179-control-rtl-41777f1/r005。原包保留；只有实验快照有独立Git历史。
- 下一步取消／异常排空与服务适配器，再扩RAW16／RX/TX；当前M／PM是peer，真实宏／完整Block、母控RTL、四态与物理未验收。无运行中作业／自动监测。
- 研究in_progress，PR Draft／未合并；登记PR5 pending，看板unverified／同步pending，缺board.json／Projects条目工具，管理员／审查人待指定。


## 2026-11-04 21:54（Asia/Shanghai，UTC+08:00）：第6步局控RTL入口合同

- Issue179／Draft PR180，负责人Melodydt；PR176开始仍08f2ea20、正文／讨论未变，上传前再核并记pr176-sync.json。
- [逻辑接口／状态机候选](../../docs/local-blocks/LOCAL_CONTROL_RTL_CONTRACT_V0_1.md)与project/control_rtl_contract_v0_1定义92信号、9生命周期／13顺序机状态、配置／单PM端口互锁、服务／返回信用及RX关闭。8320B程序存储之外至少688B payload寄存器，其他元数据／物理成本未计。
- 新36、累计173组检查；4份人工时序829采样＋1flit示例，不是DUT轨迹。SystemVerilog仅声明，本机PATH未发现iverilog/verilator/yosys，HDL编译／lint／仿真未执行。来源／验证为control-rtl-sources.json／control-rtl-validation.json，进展已补总方案。
- 父e079924c7956c1fddf0994db5ba7cc67fede691a；独立部分API目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/control-rtl-contract-e079924/delivery，无.git／HEAD／index，旧包保留；最终commit／原文核验／CI见PR180。
- 下一步配置／单口仲裁、CALL／FETCH及空任务／M clear EXEC/WAIT/END功能RTL切片；再扩RX/TX和取消。未实现完整控制器、宏或Block，真实provider复位与物理待接收，无服务器作业／自动监测。
- 研究in_progress、PR Draft／未合并；登记PR5 pending，看板unverified／同步pending，管理员／审查人待指定。

## 2026-11-04 20:58（Asia/Shanghai，UTC+08:00）：第5步取消／协同复位与迟到响应

- Issue179／Draft PR180，负责人Melodydt；PR176开始仍08f2ea20、正文／讨论未变，上传前再核并记pr176-sync.json。
- [恢复研究](../../docs/local-blocks/CONTROL_RECOVERY_PLAN_V0_1.md)新增停止新发射、CANCEL/status11、安全排空、poison/status13、7／11参与者模型复位、完整重装／新epoch准入和独立native迟到响应。已锁存包保持，S写入不回滚，native错误status9优先。
- 9组取消／poison及9次恢复共168次退休，2个模型cohort完整复位；新30、累计137组检查通过。旧9次执行报告／镜像／人工参考未改；来源／验证为control-recovery-sources.json／control-recovery-validation.json，进展已补总方案。
- 无tag旧响应在新上下文中不可仅凭相同payload识别；安全依赖真实provider确认与队列清理，observer_origin仅为观察标签。RX关闭／RESET_ACK仍为拟议peer合同，真实Block需补G／feeder／仲裁等复位范围；无控制RTL资格。
- 父c22dde6972e0f86600ecdc4060409e6947b19fb8；独立部分API目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/control-recovery-c22dde6/delivery，无.git／HEAD／index，旧包保留。最终commit／远端原文／CI见PR180回执。
- 下一步局控RTL周期级接口、状态机、配置写口互锁与完整provider确认清单；通用指令／更多服务及真实Block仍待。无服务器作业／自动监测；研究in_progress、PR Draft／未合并，登记PR5 pending，看板unverified／同步pending，管理员／审查人待指定。

## 2026-11-04 19:46（Asia/Shanghai，UTC+08:00）：第4步二进制控制执行切片

- Issue179／Draft PR180，负责人／认证Melodydt；PR176开始仍08f2ea20、正文／讨论未变，上传前再核并记pr176-sync.json。
- [执行模型](../../docs/local-blocks/CONTROL_EXECUTION_MODEL_V0_1.md)及project/control_exec_v0_1从7份完整镜像取指；9次实验、100退休、193观察与独立参考通过。有限S字节实际复制，READY／ACK／释放有先后；连续2job不复位，任务序号递增。
- 新26组检查（含8种子×3案例、改变机器码和失败边界），既有81组回归，共107组通过；实际工具／来源／SHA见control-exec-sources.json／control-exec-validation.json；每轮进展已补总方案。
- 父8cb31090ed936906f4cf5a7a9a5ce4fa8ce7f864；新独立部分API目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/control-exec-8cb3109/delivery，无.git／HEAD／index，旧包保留。最终commit／原文核验／CI见PR180在线回执。
- 本轮仅软件二进制执行，RTL／完整Block／宏数值／系统物理未执行；tick非时钟周期。下一步运行取消、排空／poison、provider协同复位及旧响应隔离，再冻结RTL接口，R2整体未完成。
- 无新增服务器作业或自动监测；研究in_progress、PR Draft／未审查未合并，登记PR5 pending，看板unverified／同步pending（缺board.json和Projects工具），管理员／审查人待指定。

## 2026-11-04 19:14（Asia/Shanghai，UTC+08:00）：第3步完整镜像与配置装载

- Issue179／Draft PR180，负责人Melodydt；仅母控／局控研究，完整Block为外部依赖。
- PR176开始核对仍08f2ea20，说明及讨论未变；上传前再核，记录于pr176-sync.json；没有后台监测。
- [装载合同](../../docs/local-blocks/CONTROL_IMAGE_LOADING_V0_1.md)及project/control_image_v0_1交付7镜像2080B、manifest/SHA、单bank全cohort有效互锁、排空／复位的软件模型；配置线编码／硬件尚未冻结，START不执行PC。
- 修正第2步READY经G_EVENT写R0后CALL arg0应为1的轨迹；新增回归。30组新增＋轨迹28＋接口15＋ISA8＝81组通过，管理结构另计；来源与验证见control-image-sources.json／control-image-validation.json。
- 每轮进展已补入[总方案](../../docs/local-blocks/TWO_LEVEL_CONTROL_PLAN.md)。父add63270a2faf707fac035898dd13028ceb1135f，新独立部分API目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/control-images-add6327/delivery，无.git／HEAD／index，旧包保留；最终远端commit／读回／CI见PR180回执。
- 下一步独立二进制PC执行模型，有限寄存器／令牌／对象／队列，实际生成轨迹与人工oracle对照；不得以cases.json驱动运行调度。不改宏RTL／ref-project，没有新服务器作业／自动监测。
- 研究in_progress、PR Draft／未审查／未合并；登记PR5 pending，看板unverified／同步pending（缺board.json及Projects条目／字段工具），管理员／审查人待指定。

## 2026-11-04 18:21（Asia/Shanghai，UTC+08:00）：第2步用例与独立轨迹

- [Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179) / [PR180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)继续控制研究；每次研究先核PR176并上传前再核；本轮开始08f2ea20／无新讨论，见[同步](../../work/Melodydt/179/pr176-sync.json)。
- [第2步文档](../../docs/local-blocks/CONTROL_REFERENCE_CASES_V0_1.md)与[参考目录](../../project/control_cases_v0_1/README.md)交付3组程序、29指令／464B、11份分离记录／720B，4条人工轨迹共72观察及27组检查；不是PC执行器或RTL结果。
- 结论：源必须等ACK实际接收才完成TX／DROP；接收token此用例等写确认＋ACK发送接受；序号／令牌／对象及错误必须分别退休。M错误为非正常peer注入，正常op6不应报错。
- 按用户要求，本轮目标／上游／产物／实际验证／结论限制／下一步已补入[总方案](../../docs/local-blocks/TWO_LEVEL_CONTROL_PLAN.md)，并新增逐轮记录；以后每轮照此执行。
- 父afd96b359c369c7ea039cca2c642677b0ab5f665；新独立部分API目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/control-traces-afd96b3/delivery，无.git／HEAD／index，旧包保留；最终commit／CI／读回见在线回执。
- [来源](../../work/Melodydt/179/control-case-sources.json)／[验证](../../work/Melodydt/179/control-case-validation.json)记录真实软件检查及SHA；未实施控制／Block RTL、镜像装载、PC执行、模型、服务器或物理任务，无自动监测。
- 下一步完整镜像装配、配置装载／有效互锁与错误恢复合同，再独立二进制控制模型。研究in_progress，PR Draft／未合并；登记PR5 pending，看板unverified／同步pending，管理员／审查人待指定。

## 2026-11-04 17:39（Asia/Shanghai，UTC+08:00）：开始第1步接口研究

- [Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179) / [PR180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)，负责人／认证Melodydt，write核验；只研究母控／局控。
- 每次开始／恢复及上传前核PR176：本轮开始head08f2ea20未变，评论／review空；最终读回见[同步记录](../../work/Melodydt/179/pr176-sync.json)，无后台监测。
- 已形成[接口合同](../../docs/local-blocks/CONTROL_INTERFACE_CONTRACT_V0_1.md)：6模块149原生端口、母局控消息边界、12个P服务、2个16KiB研究profile；[静态检查参考](../../project/control_contract_v0_1/README.md)核字段／对象窗口／路线，始终deployable=false。
- 关键约束：M响应后保留结果上下文；G没有cmd/busy/done；S请求接受不等于写完成，feeder busy=0也可能有待消费done。S32容器／S16值及Q格式须显式适配，不声明M→G裸直通。
- [来源](../../work/Melodydt/179/control-interface-sources.json)与[验证](../../work/Melodydt/179/control-interface-validation.json)记录实际命令／SHA；15组新字段／拒绝测试及既有编码测试按回执核验，无RTL／模型／服务器／物理执行。
- 发布父提交df3e7a2657a96bf0e5031a958d48155010bd7380；本地独立部分API目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/control-interfaces-df3e7a2/delivery，无.git／HEAD／index，旧包保留。最终commit／CI／白名单及远端读回见在线回执。
- 第1步完成P接口基线，R1整体尚未完成；下一步独立预期控制轨迹及镜像／配置装载合同，再R2执行模型。其他类型原生注册和真实接入仍待执行。
- 研究in_progress，PR Draft／未合并；登记PR5 pending，看板unverified／同步pending（缺board.json／Projects工具），管理员／审查人待指定。[恢复交接](../../docs/handoffs/2026-11-04-issue-179-local-block-continuation.md)。

## 2026-11-04 17:05（Asia/Shanghai，UTC+08:00）：限定母控／局控研究范围

- 用户明确本分支不负责完整 Block 实现，仅研究母控／局控。[Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179) / [PR180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)继续复用。
- [综合方案第0、9节](../../docs/local-blocks/TWO_LEVEL_CONTROL_PLAN.md)将 R3／R4 改为控制 RTL＋有限协议 peer、多局控协同；R5／R6 为控制 profile／程序生成；完整 Block、数值／模型质量及系统物理保留为外部依赖门，任务／负责人待指定，不能用 peer 通过替代。
- 当前可以研究：接口／原生 ABI、ISA／装载／取指、对象与上下文、任务／事件／错误、二进制模型及控制 RTL。完整 Block RTL 不是启动前提。
- 下一步 R1 控制接口与 profile、装载准入和有限资源模型，再 R2 二进制控制解释器；未在本轮实施控制 RTL、Block RTL、模型或服务器实验。
- 发布前基线614cdab41cfde66ee31c92fc3e44a9e1733a338a；独立部分 API 目录 D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/control-scope-614cdab/delivery，无 .git／HEAD／index，旧目录保留；最终 commit／核验见在线回执。
- [本轮文档验证](../../work/Melodydt/179/control-scope-validation.json)记录范围与来源。研究 in_progress，PR Draft／未合并；登记 PR5 pending；缺 board.json／Projects 工具，看板 unverified／同步 pending，管理员／审查人待指定。

下方早期研究步骤按其轮次保留；完整 Block 实现目标已由本条和方案范围节修正。

## 2026-11-04 16:25（Asia/Shanghai，UTC+08:00）：综合方案与下一步

- [Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179) / [Draft PR180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)，负责人／认证 Melodydt，已核 write 权限；研究仍 in_progress，未审查未合并。
- 更新[综合方案 v0.2](../../docs/local-blocks/TWO_LEVEL_CONTROL_PLAN.md)：五类 Block／28 宏示例、Block 间／宏间／母控到块／局控到宏的四类连接、24 指令及小端位编码、本地存储／配置装载／任务执行、已有进度及 R0–R7。ISA v0.1 和软件编码不变，宏级断电按用户要求暂缓。
- 明确固定控制归属、建议 M1–M10 控制预连但实际 pin／层未冻结；主要数据通路后制；推荐主机统一装载器，母控运行时发任务／参数，局控从本地 entry_pc 取指。以上是 proposed，不写成已完成 RTL。
- 发布前基线 d6429607d5e0f607c321ab6372e78d5f53ec96ba，tree f7a1826fee23c24ed8d939f2325961e059e44257；任务分支和 PR base 不变。本轮最终 commit／远端核验／CI 见在线回执。
- 新独立 API 目录 D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/control-summary-d642960/delivery；无 .git／HEAD／index，是部分资料快照。旧 179／151 工作包保持；只上传本轮白名单。
- 依赖快照更新：PR178 b9dc77eb，N4／N5 四门通过，P4 完整后续尚未统一验收；PR163 64b7c85 仍无完整系统联合通过；PR167 c97353cf 与 PR152 55243d2c 的独立证据不转移资格。仅核在线／固定文档，没有重验服务器包或实时作业。
- 实际检查及产物 SHA 见[本轮验证](../../work/Melodydt/179/control-summary-validation.json)和[来源](../../work/Melodydt/179/control-summary-sources.json)。未新增 RTL／模型／服务器／EDA 作业或自动监测。
- 下一步：R1 原生 ABI／端口表、固定控制与实际数据端点、镜像／配置装载合同和真实 S 对象布局；R2 有限二进制模型；再 R3 真实 P 局控，同控制 RTL 不同程序。负责人 Melodydt，不接管其他任务。
- 登记 management-hub PR5 pending；缺 board.json／Projects 条目字段工具，看板 unverified／同步 pending，管理员／审查人待指定。[恢复交接](../../docs/handoffs/2026-11-04-issue-179-local-block-continuation.md)已更新。

## 2026-11-04（Asia/Shanghai，UTC+08:00）：母控/局控方案与ISA v0.1

- [Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179) / [Draft PR180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)，负责人/认证Melodydt，write权限核验；研究主线按用户要求聚焦两级控制。
- 已形成[架构方案与R0–R7研究门](../../docs/local-blocks/TWO_LEVEL_CONTROL_PLAN.md)、[明确指令/编码](../../docs/local-blocks/CONTROL_ISA_V0_1.md)，24个操作码、9类记录、小端布局、描述符/端序和错误语义；规范JSON及标准库参考codec/独立向量进入本任务。
- 基线commit `1f3e916ed5c40fc54a0e7af90c675017c87317e4`、tree `0beb612ccc0dacc350e1ab5765b583efdf1fe324`；仍在task/179-local-block-continuation，PR base为task/175-local-block-design。最终发布SHA以PR/Issue在线回执读回。
- 新独立API目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/control-plan-1f3e916/delivery，无.git/HEAD/index；旧179和151资料包保持。只上传显式白名单，继承固定远端父树。
- 实际验证入口/结果见[本轮回执](../../work/Melodydt/179/control-plan-validation.json)；编码检查不等于完整镜像装配/语义编译或硬件执行。未启动新RTL/服务器/模型/EDA，无作业或自动监测。
- 下一步：R1固定真实端口与native参数字布局、能力/拓扑profile和部署检查器；R2二进制执行模型；再R3真实P局控及同控制硬件不同程序。私有S/新R/原控制物理继续由原任务负责，不接管。
- 方案proposed，整体研究in_progress、PR Draft/未审查未合并；登记PR5 pending；缺board.json/Projects条目字段工具，看板unverified、同步pending，管理员/审查人待指定。
- [交接](../../docs/handoffs/2026-11-04-issue-179-local-block-continuation.md)。此前容量/接入/原研究记录全部保留在下方。

## 2026-11-04 11:09（Asia/Shanghai，UTC+08:00）：PR176接续研究

- 当前任务：[Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179) / [Draft PR180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)，负责人/实际认证Melodydt，仓库write权限已核验；优先级和独立审查人待指定。
- 远端分支：`task/179-local-block-continuation`；设计父提交`08f2ea20a11dfdd09892a67599163e32b7237edb`；PR base=`task/175-local-block-design`。首交付commit `8513c23d70ac6156a9735f04da271cf6764a1f7c`；最终HEAD以PR180在线读回为准。
- 已完成：核对PR176/Issue175及评论、相关任务与交接；建立独立接续任务/分支；整理[已有进展和研究方案](../../docs/local-blocks/CONTINUATION_RESEARCH.md)，交付8项可重复payload容量分析。
- 关键发现：Qwen全gate/up/input共41KiB；32KiB驻留gate或Mid/input共23KiB；16KiB需不同分片/重放方案；F0两对象恰好满16KiB、Falcon J0余1KiB。仅payload下界，调度/RTL/物理未验。
- 本地：`D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/delivery`独立API资料目录，无.git/HEAD/index，不是完整clone；根参考副本、151既有工作包不改。远端以固定base tree继承未改内容，仅提交本任务白名单。
- 验证：管理结构检查通过；容量生成/重算及提交范围/来源核验以[任务回执](../../work/Melodydt/179/README.md)和验证索引为准。未执行新RTL/模型/服务器/EDA，无新增作业或自动监测。
- 下一步：先向用户介绍进度和方案，再在179中明确Qwen dense FFN对象/bank/真实打包/回放合同及16/32KiB两种有代价的候选轨迹；依赖PR178、PR167按其固定资格接收，保持其他任务范围。
- 状态：研究in_progress，Draft PR未审查/未合并，不标done；登记PR5 pending；无board.json/Projects item字段工具，看板unverified/同步pending，管理员待指定。
- [恢复交接](../../docs/handoffs/2026-11-04-issue-179-local-block-continuation.md)。

## 已有任务的记录入口

本分支设计基线没有Melodydt个人进度文件，新增此摘要，不覆盖其他未合并分支的实际记录。Issue151/PR152最新进度继续保留在[55243d2c固定版](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/55243d2c58626547d0d452bfb25fa79b7499b486/progress/Melodydt/STATUS.md)，G1切片已交付、整体未完成；接入/仿真记录由其引用的PR148/PR150维护。合并发生同路径冲突时保留两侧进展，不用本任务摘要覆盖历史。原PDF/服务器/作业/实施要求归各原任务，不在179中复制执行。
