# Issue126：排障复盘独立交付

- 仓库：rayggxia-workspace/LLMHardwareDesign；project_id：llm-hardware-design。
- Issue：[#126](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/126)；原工程Draft PR：[#129](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/129)，不修改、不合并。
- 本文档分支：`task/126-blocker-summary`，从main创建，PR目标也是main；`172ce35d2fd625a2c592145ddd18c036eb0149b4`仅为原工程已发布的证据来源；新PR号在发布后补入回执。
- 独立工作树：`LLMHardwareDesign-blocker-review-126`。原`LLMHardwareDesign-full-pin-126`的未提交内容与驱动保持完整。
- 正文：[60条逐次记录](../experiments/issue-126-blocker-review/README.md)；[中文HTML](../experiments/issue-126-blocker-review/report.html)。
- 数据：[逐次台账](../experiments/issue-126-blocker-review/data/incidents.json)、[证据SHA](../experiments/issue-126-blocker-review/data/evidence_manifest.json)。

所有记录包含用户要求的8项、原因假设、尝试与结果；57条原生/本地试验闭合时间与3条流程观察时间分开。driver commit为实际执行版本，有些此前只在本地存在；本PR保存原生执行Tcl/失败日志/原回执及输出SHA，不把文档提交当CAD执行版本。

继承未完成：LL100处补线后仍6处M5间距失败；VECTOR和SYSTEM原负时序/电气未闭合；共同底座不能冻结；两模式完整上层与公平系统对照未完成；ACT/MXU缺匹配SRAM GDS。硬截止未按时交付、后半程小时报告缺失如实保留，没有原因证据的空档不归咎外部工具。

恢复工程的第一步：读取逐次台账和现有远程`execution.json`核对最新终态；不能根据旧静态日志或本次历史观察重复提交作业。具体剩余动作/可否估时见每项记录。本轮复盘没有新增物理试验，也没有取消历史作业。

rayggxia-project-collab1.0.0；登记沿用PR5 pending；缺Projects配置/已验证能力，看板unverified、同步pending；有权限管理员与审查人待指定。Issue126整体仍未验收，不标done。
