# huangpingyang04-lgtm 的进度

- 更新时间：2026-10-23 17:11（Asia/Shanghai）。
- 当前任务：[#48 ≤4B INT8输入规范与轻量资源估算](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/48)，负责人本人，审查人/优先级待指定；待PR审查/合并，不done。
- 成果：[输入合同与使用](../../docs/LLM_RESOURCE_INPUT.md)、`project/analysis/llm_resources/`的schema、标准库CLI、PR44固定候选配置快照、四个精选示例及单元/CLI测试；增加专用CI。复用候选格式，不改PR44代码、原始参考或其他成员进度。
- 已完成：总参数≤4,000,000,000（包含全部专家/aux），W8A8/INT32、参数分区/shape/场景校验；未知量保留null；权重/scale、KV/状态、tile、六类库存/FIFO、指定路径打包、线性块数及带宽记账。报告始终是部分解析估算，没有完整模型通过结论。
- 隔离：`C:/Users/86188/Documents/ChatGPT/2026DAC/LLMHardwareDesign-resource-estimator`，`task/48-int8-resource-estimator`，起点main `0cc36f3238c7084d7126d94c314fe7d8bf0f9c5d`；不是PR44派生分支。固定候选来源PR44@3fa0b45，完整commit和字节绑定见文档/报告；PR/最新commit/CI以Issue48交付回执为准。
- 验证：本机Python3.13.5，管理检查通过；31项已知值/负例/容量/带宽/prefill/窗口/打包/CLI/确定性测试通过。源码提交后的冻结重跑、检查命令及摘要见本任务交付记录；准备运行的source_bound=false不冒称冻结结果。
- 冻结记录：[validation.json](../../work/huangpingyang04-lgtm/48/validation.json)，源码commit b21112bb1ce311db4ec22155f4b1ce23ffbcb5b1；四示例各两次逐字节一致，输入/源码/schema/候选全部source_bound=true。全部搬运未知时带宽/时间返回null；已指定传输按参考边及共享TX单独记账，不外推到扩展库存。
- 下一步：Block同学/团队填写真实频率、服务率、RQ通道/II、外存/布局预算和整数合同；算法侧提供生命周期与完整传输/映射，再评估库存。布局、死锁、周期仿真、数值质量及PPA尚未验证。
- 并行任务：[PR26/#25](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/26)为功能benchmark；[PR45/#42](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/45)为控制锥检查；[PR46/#43](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/46)为资源调研。本PR仅增加#48交付；并行个人进度文件合并时保留各任务记录，不覆盖其他分支。
- 协作回执：rayggxia-project-collab1.0.0；project_id=llm-hardware-design，认证身份huangpingyang04-lgtm。登记沿用[management-hub PR5](https://github.com/rayggxia-workspace/management-hub/pull/5) pending；本轮无模型/训练/GPU/远程/EDA作业、无软件安装或权重下载。
- 看板交接：仓库无board.json、当前工具无Projects字段读写，实际条目unverified/同步pending，不推断账号权限。具能力/权限管理员待指定：确认组织看板#1受众/字段，复用或加入Issue48，设置Project ID=llm-hardware-design、提交后Status=In review，核对assignee并读回条目ID/状态/时间；Priority/日期待指定。恢复先读Issue48、PR及本文件。
