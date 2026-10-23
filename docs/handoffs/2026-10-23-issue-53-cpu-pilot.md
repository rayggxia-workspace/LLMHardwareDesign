# Issue53 CPU迁移交接

2026-10-23（Asia/Shanghai）。rayggxia-workspace/LLMHardwareDesign，project_id=llm-hardware-design。
本人Liangruizhi/2663955430@qq.com/182389313已认证；[Issue53](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/53)、
[PR54](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/54)，task/53-cpu-model-pilot，base PR52。
独立D:/Projects/LLMHardwareDesign-cpupilot；临时D:/Projects/Codex/cpu-pilot-20261023。
正式推理源码70c0157e348dc4bc1b3792fdb12ee3d78a342a57；当前交付head/dirty以git/PR读回为准。

服务器仅/public/home/yuzelu/RuizhiLiang/issue53-cpu-pilot-20261023，独立venv与原模型保留。
现代解释器3.12.7是已安装软件，没有改共享环境；非Python软件未安装。
离线包和每文件SHA、pip安装报告/版本、固定token/源码binding见[报告](../experiments/issue-53-cpu-migration.md)。
不提交权重、wheel、私钥或身份令牌。SSH仅使用本人已有专用密钥，不读取内容。

89940缺hf-xet失败；89941依赖永不满足且未运行，核对只属于本任务后取消；89942修补安装通过。
89943六条件实际跑完；FP32全通过，BF168/16线程数值门失败，BF1632通过，不能因作业退出0称全部通过。
89945是因线程相关BF16疑点触发的同源码重复，只有launcher的run01改run02，原launcher/新launcher SHA及结果分别保存。
89945已COMPLETED0:0，数值门和保存标量重现；两轮12条件及其样本都已归档，不留后台模型作业。
独立摘要审计与3篡改负例通过，未保存全量logits，不称独立内核重算。结果/归档SHA见正式索引。

另有Issue29原码-defer89939前端超时与factored原型89944/89946；代码/证据在task/29-port-rtl与本人port工作树。
不把这些结果混入Issue53数值接受，不把仿真/通用综合称SRAM宏映射/PPA。原码与原测量保持不动。

恢复第一步：重新认证指定GitHub身份、核最新Issue/PR/评论及成员进度，核交付包SHA，解压新D盘目录并重跑audit.py。
先读最新作业回执，不能盲重提交已完成case。模型环境已可复用，不重装、不重下权重。
下一项优先E2b固定语义完整attention端口配对；Qwen2.5/Qwen3.5现有GPU数据等用户完成通知后核SHA整合，避免重复。
扩Gemma/Phi或更长CPU任务前按各自后端/许可/精度/资源先做有界pilot，不能直接推广本例。

规则rayggxia-project-collab1.0.0；登记management-hub PR5本轮读回open/unmerged/pending。
无board.json/Projects条目工具，已读status-mapping；看板unverified、同步pending。
具能力管理员待指定：复用/加入Issue53，Project ID=llm-hardware-design、Status按实际阶段、Priority=P1、assignee=Liangruizhi，
读回条目ID/字段/时间。审查人待指定，不自行合并或done；文件上传/审查/登记/看板分别报告。
