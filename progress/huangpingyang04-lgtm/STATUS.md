# huangpingyang04-lgtm 的进度

- 更新时间：2026-10-22 21:02（Asia/Shanghai，UTC+08:00）。
- 当前任务：[Issue #25](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/25)，负责人 huangpingyang04-lgtm；优先级/审查人待指定。
- 已完成：按用户修订重写 [benchmark 调研](../../docs/LLM_BENCHMARKS.md)及 README 入口；围绕线性、门控 FFN、GQA/KV、归约/非线性、MoE 的并列模块实验，列出 MLA/递归状态覆盖缺口。三个模型均为同级结构/尺寸例证，无首选或开发/验证先后。采用 INT8 输入/权重、INT32 累加、整数重定标与位精确参考建议，不沿用旧浮点计算方案；KV/状态/非线性精度单列待冻结。`3219a1d` 中的精度与模型排序建议已被本次修订替代。
- 工作目录：`C:/Users/86188/Documents/ChatGPT/2026DAC/LLMHardwareDesign-benchmark`，独立稀疏克隆；分支 `task/25-llm-benchmark`，基于 main，不带入他人未合并代码。GitHub 插件和本机 GCM 账号均核为 huangpingyang04-lgtm；未接触凭据。
- 验证：`python scripts/check_project.py` 通过（仅管理结构）；27 个来源链接/私有 Git 对象核验通过，Markdown 引用/表列通过。重算三模型的 INT8 矩阵 payload/单列归一化参数、激活/KV/INT32 QK、FFN/专家池/分发字节与累加界；整数合同和模块覆盖两项独立审阅通过。最终空白/暂存范围及线上 CI 以 Issue/PR 回执为准。未执行量化、模型推理、训练、压测、RTL/物理实验或服务器操作。
- 交付：沿用 [PR #26](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/26)，本次修订提交及最终 head 在 Issue/PR 回执更新；审查人待指定，未合并/未验收。
- 下一步：审查本次模块覆盖/INT8合同；由团队冻结模块精度、数据布局及固定资源合同，建立各并列片段的整数输入/尺度/参考摘要，保留真实尺寸与缩小核对应。
- 待确认：量化/校准与非线性/状态精度、Block 容量/端口/时序/物理视图、带宽和定制资源；Llama 获取授权、WikiText 上游许可标注。既有轨迹只提供输入/shape线索，不能作为 INT8 数值结果。
- 接入交接：规则 `rayggxia-project-collab 1.0.0`，project_id=`llm-hardware-design`。已读回管理中心默认分支 registry 尚无项目；[登记 PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5)仍 OPEN，登记 pending，不重复登记。本仓库无 `config/board.json`，本会话无 Projects 工具；在线条目 unverified、同步 pending，不能据此推断本人在线权限。具能力和权限的管理员（待指定）需先确认[候选组织看板 #1](https://github.com/orgs/rayggxia-workspace/projects/1)受众/字段，复用或加入 Issue25，按 `config/status-mapping.json` 同步 `Project ID=llm-hardware-design`、实际 Status 并读回；Priority/日期未确定。恢复先读取最新 Issue/PR；待审查阶段应为 In review。
