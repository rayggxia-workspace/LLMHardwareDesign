# Liangruizhi 的进度

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

- 当前任务：[Issue23](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/23)，task/23-qwen3-trace，独立D:/Projects/LLMHardwareDesign-inference，base PR22 adf077d04a5f0a3cc2ae13b77f16371bb637591d。源码d63bc2d37a5f1457a4a170b17afba343fb54998d已上传且实际运行两次；54数值正例/4状态负例、35调用13720事件与1365选定边界比较通过，科学payload逐字节重放一致。真实完整Qwen3权重CPU FP32推理已跑通，尚非硬件PPA/模型质量benchmark。成果归档350398bytes、SHA d9f6701fcea9553e557a63a718787ade5da908b44f43f2dae7e2701da7d5de76；结果交付PR待后续实际回执，看板未核验/同步pending。
