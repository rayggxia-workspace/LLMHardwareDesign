# Liangruizhi 的进度

- 更新：2026-10-22（UTC+08:00）；GitHub身份Liangruizhi／2663955430@qq.com／ID182389313。
- 当前任务：[Issue19](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/19)／[PR20](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/20)，task/19-interface-contract，D:/Projects/LLMHardwareDesign-interface；base task/16-macro-endpoints，依赖PR18/14/12。capture源码16be20bf，正式run源码c3916f4f；3032信号位三视图关联、685连接与2346边界网核验完成。148项业务检查、205390项独立比较、6个篡改负例及离线重放通过。原始输入另有2处Liberty缺分号、4处PG方向差异，均原样保留并显式报告；未称宏合格/Lib语法全部通过。
- 本轮成果：[实验记录](../../docs/experiments/issue-19-interface-contract.md)／[交接](../../docs/handoffs/2026-10-22-issue-19-interface-contract.md)；原字节归档1585317bytes，SHA与逐文件索引见正式结果目录。交付待审查，未合并／未done；PR最新head与线上状态以读回为准。
- 前一任务：[Issue16/PR18](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/18)在D:/Projects/LLMHardwareDesign-lef，源码23040b0冻结三LEF；6791PIN／6956PIN RECT／30OBS，67项业务检查和原字节重放通过。待审查；没有合法access point或宏资格结论。
- 前序：[Issue13/PR14](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/14)在D:/Projects/LLMHardwareDesign-endpoints，源码dc294114运行384例；restricted44/96、access71/96、capacity44/96、joint71/96，230解、248cut、24精确状态通过。9映射具有白名单无路径→合法解证据；待审查。
- 前序：[Issue11/PR12](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/12)在D:/Projects/LLMHardwareDesign-dac，源码6ab796b运行192例；顺序32/96、多顺序44/96；76成功解、81次数值、24小例及全量重放通过，待审查。
- 协作规则：[Issue5/PR6](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/6)仍待审查，已有规则持续有效，不另开重复PR。
- 下一步：先检查Issue15/PR17最新终态和新M9视图版本；旧wave206接口证据不能推广到新宏。核验输入缺陷、DEF朝向、via/enclosure/OBS合法访问与模型资格；条件闭合后做固定K及总预算的端点感知mapping。YUZE-LU继续其物理对照，保持范围隔离；审查人与后续认领以Issue为准，不自合并。
- 阻塞/待同步：未证明完整RTL等价、时序arc、PG、合法接入或H2/PPA。本机无已验证EDA环境；登记pending（management-hub PR5未合并）；无Projects工具/本地board配置，在线状态unverified、同步pending，管理员待指定。本轮mutation-copy-01清理被自动审批以blocked by policy拒绝，未重试/绕过，具体路径见交接。
