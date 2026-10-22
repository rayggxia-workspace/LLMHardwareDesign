# huangpingyang04-lgtm 的进度

- 更新时间：2026-10-22 20:31（Asia/Shanghai，UTC+08:00）。
- 当前任务：[Issue #25](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/25)，负责人 huangpingyang04-lgtm；优先级/审查人待指定。
- 已完成：核对 main `1a98e9d7f42885a6bf11dcd5decd0d84da708469`、项目规则、相关 Issue/PR/交接，复用 #21/#23 的研究证据；新增 [benchmark 调研](../../docs/LLM_BENCHMARKS.md)和 README 入口。建议 Qwen3-0.6B 首选、Qwen3-30B-A3B 开发 MoE 子图、Llama-3.2-1B 方法固定后跨实现验证；首片段为真实尺寸 layer0 FFN。
- 工作目录：`C:/Users/86188/Documents/ChatGPT/2026DAC/LLMHardwareDesign-benchmark`，独立稀疏克隆；分支 `task/25-llm-benchmark`，基于 main，不带入他人未合并代码。GitHub 插件和本机 GCM 账号均核为 huangpingyang04-lgtm；未接触凭据。
- 验证：`python scripts/check_project.py` 通过（仅管理结构）；固定 Qwen 配置 SHA 与既有记录一致，MoE 权重索引及 Llama 元数据参数数匹配独立公式；三模型权重/KV/激活、FFN 与 MoE 通信数值复算通过。24 个引用核验通过（公开文本 HTTP、私有文件 Git 对象、权重仅核元数据/头部，未下载张量），归档内 inputs.json 存在，Markdown 引用和表格列数通过；独立内容审阅、`git diff --check`、`git diff --cached --check` 和三文件暂存范围核验通过。线上 CI/最终 head 以 Issue/PR 读回回执为准。Llama HF config 未获访问，已明确替代来源与后续核验要求。未执行模型推理、训练、压测、RTL/物理实验或服务器操作。
- 交付：[PR #26](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/26)已创建；成果 commit `e5787423ce380bed7cd423b14b88dc5884fd4fec`，本次进度链接回写另行提交。当前待审查/in_review，未合并/未验收；最终 commit 在 Issue/PR 回执更新。
- 下一步：审查 PR26（审查人待指定）；后续实验先取得 Block 容量/端口/时序/物理视图及定制资源合同，补导出 layer0 MLP 参考张量。
- 待确认：Llama config/权重获取授权、WikiText 上游许可标注、BF16 误差门槛、正式场景及固定资源预算；本次调研不依赖上述后续实验输入，建议仍待团队审查。
- 接入交接：规则 `rayggxia-project-collab 1.0.0`，project_id=`llm-hardware-design`。已读回管理中心默认分支 registry 尚无项目；[登记 PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5)仍 OPEN，登记 pending，不重复登记。本仓库无 `config/board.json`，本会话无 Projects 工具；在线条目 unverified、同步 pending，不能据此推断本人在线权限。具能力和权限的管理员（待指定）需先确认[候选组织看板 #1](https://github.com/orgs/rayggxia-workspace/projects/1)受众/字段，复用或加入 Issue25，按 `config/status-mapping.json` 同步 `Project ID=llm-hardware-design`、实际 Status 并读回；Priority/日期未确定。恢复先读取最新 Issue/PR；待审查阶段应为 In review。
