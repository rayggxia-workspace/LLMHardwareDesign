# Liangruizhi 的进度

## 2026-10-23（UTC+08:00）Issue59：Llama down_proj校准/分组与成本

[Issue59](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/59)/[PR60](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/60)，task/59-down-scale，D:/Projects/LLMHardwareDesign-downscale；正式数值/服务源码6d2d6603fde7e2372bd399c1cee511e33e6c2781。全部本机，24候选/144数值与1152服务两轮；13科学文件一致，46080 Fraction输出/1768320 partial独立复核。静态校准扩容/MSE未解决，K128/W128最坏5.39%仍未过探索门；粗35bit与实际W所见scale的32bit安全界分开，guard成本待做。近M模型服务约1.4%/2.3%，未RTL校准，不冻结最终边界。192成员精选包2.63MB已重放24代表case/7680输出/4 witness，全量144编码/浮点原输入本机留SHA共享pending。报告/决策/交接/work59完整保留失败和边界；待审查合并，非done。用户随后授权服务器承接兄方所有安排，另开[Issue61](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/61)先PR36数据接收/逐模型验收/Slurm并行；不混入本轮实际执行。登记PR5 pending；无board.json/Projects能力，看板unverified同步pending，审查人/管理员/完整输入共享处理人待指定。


## 2026-10-23（UTC+08:00）Issue56本机Llama跨模型验证

[Issue56](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/56)/[PR57](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/57)，
task/56-llama-cross-model，D:/Projects/LLMHardwareDesign-llama；正式源码628c093db2a62a94be30ab22bb4fa176cd081761。
复用已有BF16权重/环境、9文件SHA核验，全部本机，无新模型下载或远端作业。
4Q/1KV全组/32+8、GQA两轮117760 oracle与61440源代码；线性16条件43520 INT64/Fraction、2293760独立输入通过。
384服务两轮、18科学文件相同；8 witness/33560节点与48策略包络重算、3合同测试及2真实篡改负例通过。
局部down静态A误差70%–83%、动态6%–17%，不是全模型质量通过；近端RQ最大约0.405%仍不足固定硬边界。
178成员精简包2.47MB已核SHA/安全解包/整数重放；原9.18MB完整capture/全量NPZ本机留存，共享pending，不称远端已可访问。
下一步D1激活量化/scale生成成本与完整E2b，不盲扩模型；K组scale改变后部分和需新验证。
并行Issue53/PR54与Issue29/PR30前阶段作业均已结束；Issue55其他成员集成不接管，兄方数值包仍待通知。
登记PR5 pending；无board.json/Projects工具，看板unverified/同步pending，管理员/审查人待指定；未合并未done。

## 2026-10-23（UTC+08:00）Issue53：CPU服务器小模型迁移

[Issue53](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/53)、[PR54](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/54)，
task/53-cpu-model-pilot，D:/Projects/LLMHardwareDesign-cpupilot，base PR52。
正式推理源码70c0157e348dc4bc1b3792fdb12ee3d78a342a57；现代独立venv/离线依赖、已有固定权重SHA通过。
89943/89945两次32CPU自然完成，各6条件。FP32三线程全过，BF168/16线程各17门失败、32线程全相等，两轮重现。
两个回传包81成员分别核SHA，独立标量/来源/计时审计与3篡改负例通过，不称第二数值内核或全模型质量。
实际结果和可迁移/不可替代GPU边界见docs/experiments/issue-53-cpu-migration.md；失败/原始计时保留。
另在task/29-port-rtl推进原码-defer与factored原型回归/综合，不混同；本机不下载大模型，未整合兄方数值包。
下一步E2b完整attention端口配对；按架构分别pilot，复用兄方已有GPU证据，GPU专属测量不改派CPU。
登记PR5 pending；无board.json/Projects工具，看板unverified/同步pending；审查人/管理员待指定，未合并未done。

## 2026-10-23（UTC+08:00）Issue51：E2a与8核服务器重放

[Issue51](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/51)，[PR52](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/52)，
task/51-rq-placement，D:/Projects/LLMHardwareDesign-rqports，base PR49@6776470。
指定GitHub登录已核；用户新授权服务器并行，已读REMOTE_RULES，仅本人目录执行89936/89937，均8CPU/8worker并COMPLETED0:0。
正式源码134838c71282f1a823cc99b3d857ebe3331b8d3b；1088 Fraction RQ、8边界测试、384组织服务/资源/credit审计，
981312节点/80832packet，服务器与本机384例逐项相等，原始回传已核SHA。
PE寄存器从单口MC分账并保持总32KiB，复跑数字不变；48对各自最佳策略近端最多降0.5657%、最差增0.0650%，
不固定不可绕过近端RQ；没有完整attention/RTL/物理或模型质量结论。
[报告](../../docs/experiments/issue-51-rq-port-placement.md)、[交接](../../docs/handoffs/2026-10-23-issue-51-rq-ports.md)。
下一步E2b attention/M-A；完整模型CPU迁移先现代框架/已有权重pilot，尚未开始，不与师兄未知进度重复。
登记PR5 pending；看板unverified/同步pending；审查人/管理员待指定，未合并未done。实际交付状态以PR最新读回为准。

## 2026-10-23（UTC+08:00）Issue47：独立校准、GQA共享和因果KV

[Issue47](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/47)，
[PR49](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/49)，task/47-primitive-stream，
目录D:/Projects/LLMHardwareDesign-primitives。认证profile已核为Liangruizhi/182389313/指定邮箱。
源码270568dfcad314f3d16e9bfa68dc378b31bdea9b，已有Qwen3-0.6B CPU，一层一个完整GQA组；
独立校准及两组短评价，两个整数payload逐字节一致。8边界测试、79,360oracle、81,920独立输入、
640Decimal编译值、160发布事件、3篡改负例和31成员归档校验通过。
局部相对RMSE约64.6%/49.3%降至1.80%/1.90%，无全模型质量或硬件加速声明。
P1–P15映射和scale/状态/格式边界已补；当前线上交付/审查状态以PR最新读回为准，未done。
[报告](../../docs/experiments/issue-47-primitive-stream.md)、[交接](../../docs/handoffs/2026-10-23-issue-47-primitive-stream.md)。
下一步E2 RQ/M-A同资源端口配对；不重复其他成员Issue48资源估算器，不整合师兄未通知完成的数据。
GPU批次新文案和96核CPU条件估算已记录；本机不下载较大模型，不启动服务器或其他机器。
登记PR5 pending；看板unverified/同步pending，管理员和审查人待指定。

## 2026-10-23（UTC+08:00）Issue41分析候选与最小决策实验

[Issue41](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/41)，Liangruizhi；
task/41-block-candidate-v1，独立D:/Projects/LLMHardwareDesign-blockv1，base PR40@f2e55e0。
按用户要求给出M/V/A/R/S/D具体候选，计算、状态、接口、预连线/定制范围和D1–D6；
E1数值门、E2/E3/E4三项边界判别、E5冻结验证；不把所有模型/精度/长度盲跑。
正式文档docs/BLOCK_CANDIDATE_V1.md、docs/BLOCK_MINIMAL_EXPERIMENTS_V1.md；解析工具block_candidate。
本轮不新跑模型/RTL/GPU/远程，不整合尚未获用户完成通知的兄方结果。
源码dfb12cddb81f6acdf44a2c1f64600aa37e121a3a，两次解析逐字节一致、三源码绑定、8已知值、
两个容量反例、D1–D6覆盖/文档链接及管理/whitespace通过；这不代表E1–E5已跑。
[PR44](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/44)已上传，待审查合并，未done；
交接docs/handoffs/2026-10-23-issue-41-block-candidate-v1.md，分析/验证/SHA见work/Liangruizhi/41。
本轮后续仅按门槛选择E1缺项；Issue42/43资源/方法调研并行互补，不接管。登记PR5 pending，
看板unverified/同步pending，审查人/管理员待指定。

## 2026-10-23（UTC+08:00）Issue39本机数值接续

[Issue39](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/39)，Liangruizhi；
task/39-kv-scale-boundary，独立D:/Projects/LLMHardwareDesign-kvscale，base PR38@ec8fa3d。
用户授权筛选后继续本机适合实验，局部开启已有真实短张量的整数QK/PV scale与bias验证；
不改写Issue37的历史架构阶段，不启动其他机器或下载大模型，不接管Issue32/PR36。
正式配置project/experiments/kv_scale/experiment.json，代码/独立Fraction/边界测试；开发探索保留D盘。
给师兄可复制文案docs/handoffs/2026-10-23-gpu-codex-experiment-prompt.md，先续Qwen、后Gemma、最后Phi保留验证。
正式源码a83e624a10ecc3f012eff2f2f770c9f9842c3a76，24组合两次CPU运行；
89280整数比较、296448真实来源值/540指数、11测试/管理/whitespace通过，五科学文件逐字节复现。
direct QK8局部误差大，离线同张量平衡改善仅定位，尚非全模型质量或在线整数硬件通过。
[PR40](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/40)交付待审查/合并，未done；
报告docs/experiments/issue-39-kv-scale-boundary.md，交接docs/handoffs/2026-10-23-issue-39-kv-scale.md，
raw/源/结果SHA在issue-39-run01/index和work/Liangruizhi/39/manifest；恢复先核SHA和最新分工。
后续因果scale/跨GQA变换、独立量化质量/宽算术物理仍缺；等用户通知兄方完成再核验整合。
登记PR5 pending，看板unverified/同步pending，管理员/审查人待指定。

## 2026-10-23（UTC+08:00）Issue37先审查架构与筛选

[Issue37](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/37) / [PR38](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/38)，
task/37-gemma-phi-protocol，独立D:/Projects/LLMHardwareDesign-gemma-phi，base PR34@4a3f5e4。
用户追加“先分析所有已提架构再选型”，本轮只元数据/源码审查与协议/容量公式检查，无新增模型或缩小模型推理。
17变体、12份固定官方config/SHA、5份401缺口；拟主测Qwen2.5-3B/Qwen3.5-4B/条件Gemma4B，
复用已有Qwen3-0.6B，Phi作一个后续保留验证，其他重复规模/原生MoE/MLA按理由暂缓完整实跑。
见[正式审查](../../docs/MODEL_ARCHITECTURE_REVIEW.md)与[交接](../../docs/handoffs/2026-10-23-issue-37-model-selection.md)。
源码946281b9a90dd36b130e691c60667b9f7d1e4d32；8个协议测试/管理/whitespace通过，源码/日志绑定通过，
不称模型验证通过。当前new_numerical_runs_enabled=false；门控接入、整数bias/norm/归约合同、正式质量预算待闭合。
不接管Issue32/PR36的Qwen修复；未整合兄方数据，等用户通知。登记PR5 pending、看板unverified/同步pending。
PR待审查/合并，审查人/管理员待指定，未done；后续在已有授权和分工范围内推进，不新增确认流程。

## 2026-10-23 Issue33精度合同与本机整数验证

负责人Liangruizhi（2663955430@qq.com，182389313），GitHub认证已重新核验。
已读最新Issue25/PR26及原负责人进度、Issue29/PR30与Issue31分工；无重复整数执行任务。
独立D:/Projects/LLMHardwareDesign-integer、task/33-int8-contract，base PR30@cfd63c0；
只在本机开展缩小核/已有Qwen3-0.6B捕获与整数/端口验证，不安排其他机器或大模型下载。
候选精度/数据与采集合同已先行发布；本机整数阶段完成，[PR34](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/34)待审查，未done。
源码03be205018356a36788cb3e5faf01d707cb74a1c；实际捕获与数值/RTL分别绑定db74f40e/60cc1b7/fb94abcc，
见[报告](../../docs/experiments/issue-33-integer-precision.md)与[交接](../../docs/handoffs/2026-10-23-issue-33-integer-precision.md)。
20业务测试、1028 RTL用例通过；实际Qwen3层0少量张量、48精度/36 KV细化、4608点搜索/2214可行；
源与结果SHA、原始失败和工作区漏计修正已记录。近端RQ流量下降不能直接当端到端加速；P7长行全零与短校准裁剪保留。
参考包缺NUMERICS/pkg/LUT/isqrt/udiv完整定义，记录可知边界，不称llaccel逐位复现。
登记PR5 pending；无board.json/当前无Projects工具，看板unverified/同步pending，
管理员与审查人待指定。本机本轮工作已交接；后续等用户通知师兄完成再核验最新仓库/Issue/PR/结果/SHA并整合，
不重复大模型/长上下文/GPU工作，不自动启动其他机器。旧active Goal文字为历史，不能据此推定当前后台续跑。

- 更新：2026-10-22（UTC+08:00）；GitHub身份Liangruizhi／2663955430@qq.com／ID182389313。
- 前一任务：[Issue19](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/19)／[PR20](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/20)，task/19-interface-contract，D:/Projects/LLMHardwareDesign-interface；base task/16-macro-endpoints，依赖PR18/14/12。capture源码16be20bf，正式run源码c3916f4f；3032信号位三视图关联、685连接与2346边界网核验完成。148项业务检查、205390项独立比较、6个篡改负例及离线重放通过。原始输入另有2处Liberty缺分号、4处PG方向差异，均原样保留并显式报告；未称宏合格/Lib语法全部通过。
- 本轮成果：[实验记录](../../docs/experiments/issue-19-interface-contract.md)／[交接](../../docs/handoffs/2026-10-22-issue-19-interface-contract.md)；原字节归档1585317bytes，SHA与逐文件索引见正式结果目录。交付待审查，未合并／未done；PR最新head与线上状态以读回为准。
- 前一任务：[Issue16/PR18](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/18)在D:/Projects/LLMHardwareDesign-lef，源码23040b0冻结三LEF；6791PIN／6956PIN RECT／30OBS，67项业务检查和原字节重放通过。待审查；没有合法access point或宏资格结论。
- 前序：[Issue13/PR14](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/14)在D:/Projects/LLMHardwareDesign-endpoints，源码dc294114运行384例；restricted44/96、access71/96、capacity44/96、joint71/96，230解、248cut、24精确状态通过。9映射具有白名单无路径→合法解证据；待审查。
- 前序：[Issue11/PR12](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/12)在D:/Projects/LLMHardwareDesign-dac，源码6ab796b运行192例；顺序32/96、多顺序44/96；76成功解、81次数值、24小例及全量重放通过，待审查。
- 协作规则：[Issue5/PR6](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/6)仍待审查，已有规则持续有效，不另开重复PR。
- 前轮下一步（保留历史，当前优先级见下）：先检查Issue15/PR17最新终态和新M9视图版本；旧wave206接口证据不能推广到新宏。核验输入缺陷、DEF朝向、via/enclosure/OBS合法访问与模型资格；条件闭合后做固定K及总预算的端点感知mapping。YUZE-LU继续其物理对照，保持范围隔离；审查人与后续认领以Issue为准，不自合并。
- 阻塞/待同步：未证明完整RTL等价、时序arc、PG、合法接入或H2/PPA。本机无已验证EDA环境；登记pending（management-hub PR5未合并）；无Projects工具/本地board配置，在线状态unverified、同步pending，管理员待指定。本轮mutation-copy-01清理被自动审批以blocked by policy拒绝，未重试/绕过，具体路径见交接。

- 前阶段任务：[Issue21](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/21)／[PR22](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/22)，task/21-operator-partition，D:/Projects/LLMHardwareDesign-partition；base task/19-interface-contract。已固定共同问题、推理范围及代表模型选择原则；正式源码680dbbeed9a9189c06b047918ab4ae2ea6eedc28运行630调度/11340容量边界条件，378数值正例+3负例，164业务检查及逐字节重放通过。成果及归档已上传ddcc2b0032ff8340d94c9a1b7844302cb669ade7，PR22已创建；待审查/合并，未done。
- 当前成果与后续：[实验记录](../../docs/experiments/issue-21-operator-partition.md)／[交接](../../docs/handoffs/2026-10-22-issue-21-operator-partition.md)。研究重点转为代表模型实际trace、存储/端口/状态契约和受控划分；当前微实验不证明端到端/PPA。继续核对Issue15最新结果而不接管。
- 用户授权：常规方案自主决定并记录理由/失败，重要结果汇报；原则性或不能解除的关键阻塞才提问。用户清除旧目标后，新算子/Block划分研究目标已成功登记并核验active；持续推进，阶段交付不虚标整体目标完成。

- 当前任务：[Issue23](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/23)／[PR24](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/24)，task/23-qwen3-trace，独立D:/Projects/LLMHardwareDesign-inference，base PR22 adf077d04a5f0a3cc2ae13b77f16371bb637591d。源码d63bc2d37a5f1457a4a170b17afba343fb54998d已上传且实际运行两次；54数值正例/4状态负例、35调用13720事件与1365选定边界比较通过，科学payload逐字节重放一致。真实完整Qwen3权重CPU FP32推理已跑通，尚非硬件PPA/模型质量benchmark。成果归档350398bytes、SHA d9f6701fcea9553e557a63a718787ade5da908b44f43f2dae7e2701da7d5de76；结果交付5c6da01360fbd165c84a790147c4b5d4dfde8e77已上传，PR24已创建，待审查/合并，未done；看板未核验/同步pending。

- 最新接续：[Issue27](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/27)，task/27-state-port-model，独立D:/Projects/LLMHardwareDesign-stateport；base PR24的7e0e82b7。源码6ffb9417f0f01f614b733ce6c3ca9837906b3203已远端上传，干净源码完成两次资源扫参与两次实际head捕获；3456条件/4896调度、6数值正例/10适用负例、8科学payload逐字节重放通过。25业务测试、96图独立审计及399项实际输入审计通过。归档491436B，SHA f760dec66344c11fe9c7f04f55d91f610157d7ad624f6d66faa6a9bbdb1f1588。见[报告](../../docs/experiments/issue-27-state-port-model.md)；[PR28](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/28)已创建，本提交包含完整结果；待审查/合并，未done。
- 研究判断：状态归属须结合不可隐藏的端口争用、逐bank容量及物理边界余量；当前模型没有校准时序/面积/能量，不能称最终Block或全模型加速。接下来推进可执行端口微架构与独立精度合同，再覆盖完整/差异模型；持续Goal仍active。
- 协作同步：PR24的head与CI延迟已解除，7e0e82b7线上Project structure检查通过（run39775448318）；PR17固定0f58e74首个合并父层通过物理/分层STA，但配对与父层证书未闭合；PR26固定2cd9ca15独立负责benchmark调研，不重复其范围。登记PR5 pending，Projects工具/本地board配置缺失，在线状态unverified/同步pending，处理人待指定。

- 2026-10-23接续：[Issue29](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/29)，task/29-port-rtl，独立D:/Projects/LLMHardwareDesign-portrtl，base PR28@a3f8335。两bank三端点可执行RTL、有限响应FIFO、逐拍仲裁/反压、实际数据与版本检查已实现；ModelSim九组定向smoke、服务器Verilator开发阶段2程序/2压力测试通过，独立轨迹审计及正式全量扫参待完成。编译工具路径/参数宽度失败保留，不称正式结果。PR待创建；整体Goal active。

- 2026-10-23正式运行更新：源码916dcf9e、[PR30](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/30)；Slurm89836／89837均COMPLETED0，两次1872程序＋54压力测试完整PASS，27份results逐字节一致。独立全量结果1698897检查、33witness逐拍2482636检查与2191来源绑定通过，8类真实变异检出。报告docs/experiments/issue-29-port-rtl.md，原始20MB证据已放共同服务器project-circuit/LLMHardwareDesign/issue-29并SHA读回，未仅留本机。通用综合89838已TIMEOUT，未完成检查，尚未证明宏映射/PPA，PR draft、Issue in_progress。整体Goal持续active，下一步扩差异结构与完整权重/KV/算术/物理成本；源码交付与验收区分。

## 平台目标状态核验

2026-10-23重新调用get_goal核验：平台目标实际为blocked，工具未返回该状态的历史原因；此前沿用active的文字不代表当前平台状态。研究目标尚未完成，本轮依既有授权继续执行并完成实验交付；平台自动续跑尚未恢复，恢复由用户/系统控制，不能以Issue进度或本地文档代替。

## 89838最终状态

通用Yosys作业89838于2026-10-23 09:55:54 CST达到20分钟时限，Slurm最终TIMEOUT（elapsed20:28，batch0:15）。日志确认已进入PROC_MUX，未完成后续memory_collect/check/stat/JSON；未证明综合通过，也不能把工具超时解释为RTL功能错误。原始日志和SHA索引已保存work/Liangruizhi/29/audits/synth-timeout01/。 下一步保留同一源码，使用单配置-defer与RTLIL检查点分开前端和proc成本；该后续检查尚未执行。先前运行中快照仅代表其采集时刻。
