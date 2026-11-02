# W5-IF合同交接

仓库：https://github.com/rayggxia-workspace/LLMHardwareDesign；project_id llm-hardware-design；[Issue151](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/151) / [PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152)；主要负责人Melodydt；分支task/151-six-connection-study，base task/143-seven-block-v2。

输入commit f9a90c845504b198cc3265106e03c67902382ebb；本轮交付commit按PR152最新证据回执核验。本地独立API包D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/w5if-f9a90c8/integrated，无.git/HEAD/暂存；工作清单及SHA见包外upload-manifest.json。根管理参考副本、旧A8及boundary包未覆盖，他人资料/ref-project未维护。

当前L4/W5-IF有界逻辑合同v0.1已成稿待审查；三层职责、真实native端口/适配缺口、准入/存储ACK/源释放/复用、错误partial及cohort边界、B8候选编码/holding/因果时序、8样本/6profile扩展已列明。入口：[主规格](../W5_IF_INTERFACE_CONTRACT.md)、[协议](../W5_IF_PROTOCOL_EXAMPLES.md)、[模型准入](../W5_IF_MODEL_ADMISSION.md)、[native端口资源](../rtl-contracts/W5_IF_PORTS_AND_RESOURCES.md)。机器索引work/Melodydt/151/w5-if-contract.json，静态结果w5-if-checks.json。

本轮没有新RTL、服务器操作、仿真/EDA或L5实现；全部例子是因果规格，不是测得周期/仿真结果。A8/N/F8旧验证只适用于原源及范围，A8 job95116保持历史证据，不转借给新端点。后续仿真仍用独立SSH+Slurm+服务器Verilator及本人目录；Moba非依赖。运行前重读REMOTE_RULES并按当前AGENTS开工回执，不运行本地ModelSim替代。

实际核验：管理结构、JSON/编码字段覆盖、算例算术、来源SHA、变更白名单及新增链接；命令与结果见w5-if-checks.json及docs/ARCHITECTURE.md。未执行RTL仿真，因为未改RTL；协议安全/活性、面积/时序和完整产品准入未获得验证。

还需：完整A/F数值/残差/layout与参数供给、所选shape的Norm及工作集；A8/F8不能因128bit相同裸接；Nctrl257以上需要计数/地址/存储一起设计。新B8端点/母控/跨岛stored ACK待L5，R/MoE待L6/7，真实MEM/共同M1–M10及两产品M11/M12差分待L8。

在线交付按PR/Issue读回；未合并主干，不自合并/标done。登记management-hub PR5仍待合并（pending）。本轮未发现board.json且工具无Projects条目/字段能力，看板实际状态unverified、同步pending，未证实权限拒绝；有配置和能力的处理人待指定，需要核Issue条目后同步Project ID/Status/Priority并读回。外部审查人待指定。

恢复第一步：重新核Issue151/评论、PR152 head/base/变更、最新个人进度与本交接，确认无并行冲突，读取主规格及w5-if-checks.json，再继续L4完整A/F的数值和容量映射。切勿把合同成稿当完整L4完成、L5已实现或物理冻结。
