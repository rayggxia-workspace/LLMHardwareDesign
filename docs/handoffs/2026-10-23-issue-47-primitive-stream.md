# Issue47 本机整数GQA与KV交接

2026-10-23（Asia/Shanghai）。仓库rayggxia-workspace/LLMHardwareDesign，project_id=llm-hardware-design。
负责人Liangruizhi（2663955430@qq.com，ID182389313）；认证profile已重新核验。规则rayggxia-project-collab1.0.0。
[Issue47](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/47)，[PR49](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/49)。
分支task/47-primitive-stream；base task/41-block-candidate-v1@3fa0b45。
目录D:/Projects/LLMHardwareDesign-primitives。运行源码270568dfcad314f3d16e9bfa68dc378b31bdea9b；
交付commit以PR最新head为准，不自引用未来SHA。仅提交本任务文件，不包含其他成员文件。

## 已执行与证据

[报告](../experiments/issue-47-primitive-stream.md)，[P1–P15映射](../PRIMITIVE_CAPABILITY_MAP.md)，
[源码](../../project/experiments/primitive_stream/README.md)，[索引](../../project/experiments/primitive_stream/results/issue-47-run01/index.json)。
只用已有Qwen3-0.6B、CPU、layer0一个完整GQA组、32独立校准和两个40token评价，无下载或远程运行。
两次整数payload逐字节一致；8边界测试、79,360oracle、81,920独立输入、640Decimal编译值、160发布事件和3审计负例通过。
40,960token/batch及98,304未来扰动输出比较一致。FP32 full/cached仅容差一致，整数代码在本样本逐位一致。
相对RMSE约64.6%/49.3%降至1.80%/1.90%，只局部误差，无事前质量接受阈值、无全模型质量结论。
共享KV逻辑10,240B；130B g/KV exponents及Q/M/r字段另列，完整物理布局/端口尚未实现。

小包evidence.zip SHA e03719d3e21171c380958a2dcbea99e5f3e773babba0ab19bea4d1852c36ff9b，1,026,550B，31成员。
运行及失败/开发资料D:/Projects/Codex/primitive-stream-20261023；capture02、numeric03/04、audit02为正式组。
开发组与本地初次1cfdc8c绑定组保留为历史，不改写producer。源码发布后按线上commit重跑正式组。

## 边界与下一步

norm/RoPE、FP32捕获到codes、校准、Q exponent/M/r编译仍有浮点；没有在线整数前端或全整数模型。
软件cache/epoch不等于DMA、广播、异步队列、无死锁RTL或端口性能；宽算术成本不可按单拍8位算。
下一步本机按E2比较RQ位置/M-A边界及有限资源，保留共享scale和版本约束；不得赠送FIFO/端口或零代价转换。
Issue48资源估算器由huangpingyang04-lgtm推进，本次已读其范围，不接管；Issue42/43、Issue31各自保留。
师兄Issue32/PR36@2ada6cf6的范围/交接已读，未下载整合其数值包，仍等用户通知完成。
[GPU批次文案](2026-10-23-gpu-batch-prompt-v2.md)已记录最新用户要求。
96核CPU只作条件估算，见[决策](../decisions/2026-10-23-causal-gqa-and-cpu-routing.md)，未登录/提交作业。

恢复第一步：核对最新AGENTS/Skill、Issue47/PR49/相关任务和head，运行verify_delivery.py核包，
新D盘目录解压后运行audit.py，见报告命令。不修改现有输出；检查git status并保留无关变更。
若需资源估算器接口，先检查Issue48/PR，不重复实现。E1b额外语言质量不阻塞固定语义EDA配对。

## 协作待办

源码及成果通过PR交付，实际状态以线上读回为准；审查/合并前保持in_review，不done、不自合并。
审查人待指定。登记沿用management-hub PR5 pending，未宣称进入main。
无config/board.json，已读status-mapping；当前工具无Projects条目能力，看板unverified，状态同步pending。
具能力/权限管理员待指定：核对受众/字段，复用或加入Issue47，Project ID=llm-hardware-design、Status=In review、Priority=P1，
核对assignee=Liangruizhi并读回条目ID/状态/时间；不擅自创建看板或扩大权限。
