# Liangruizhi 的进度

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
