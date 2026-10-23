# Issue56本机Llama交接

2026-10-23（Asia/Shanghai）。仓库rayggxia-workspace/LLMHardwareDesign、project_id=llm-hardware-design。
Liangruizhi/2663955430@qq.com/182389313已认证；[Issue56](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/56)/
[PR57](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/57)，task/56-llama-cross-model，base PR54。
独立D:/Projects/LLMHardwareDesign-llama；正式源码628c093db2a62a94be30ab22bb4fa176cd081761，交付head/dirty恢复时核PR/git。
临时与正式原始数据D:/Projects/Codex/llama-local-20261023。

用户已提供权重与旁支交接，只读复用D:/Projects/Codex/llama32-1b-download-20261023-565f35c2/，未改原文件/环境。
9模型文件重新核SHA，layer0 GQA4（4Q/1KV）FP32高精度/cached、两次attention/linear/service全部在本机完成。
**没有为本任务增加远端作业、模型下载或数据上传服务器**。此前CPU/RTL作业已结束，分别在Issue53/29交付。
Issue55其他成员底座集成不接管，Issue32数值包仍待用户通知再整合。

完整记录/失败边界见[报告](../experiments/issue-56-llama-cross-model.md)：down静态A约99.8%置零且局部误差70%–83%，
动态改善仍非质量接受；当前W8A8线性/整数GQA不是完整全整数模型。近端RQ最大约0.405%服务收益不足冻结硬边界。
保留同乘积scale完整K INT32；改K组scale时必须重新验证部分和单位/宽归约，不能沿用结论。

精简包index在project/experiments/llama_cross/results/issue-56-run01，含全部编码整数数组与8 witness，
源/输入/输出SHA、校验结果、双来源和旁支smoke边界；原始完整浮点线性capture/重复NPZ仍在上述D盘。
local-data-index.json索引全部本机原始文件，**共享待同步**；当前没有声称其他成员已能访问D盘或完整浮点校准重算。
包核验/解压新D盘目录后review.py可独立重放全部编码整数数学和8 witness，不替代完整浮点线性校准审计。

恢复第一步：核最新AGENTS/Skill、Issue56/PR57及评论/成员进度，核index/包SHA并解压新D盘目录。
运行README中的review命令；本机完整重算另用原始capture和audit.py/audit_linear.py，先核原NPZ SHA，不重下模型。
下一项只围绕FFN激活量化/scale生成成本与固定语义E2b，不盲扩模型；不要把本阶段当划分最终验收。

规则rayggxia-project-collab1.0.0；审查人待指定，未合并未done；登记management-hub PR5 pending。
无board.json/Projects条目工具，已读status-mapping，实际看板unverified、同步pending；管理员待指定，
复用/加入Issue56、Project ID=llm-hardware-design、实际Status、P1、assignee=Liangruizhi，读回条目ID/字段/时间。
原始输入共享处理人待指定，需获准共享位置并核SHA；本机数据保持可用，不能编造远端存储链接。
