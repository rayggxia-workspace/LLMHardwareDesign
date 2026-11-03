# 粗粒度七宏执行岛候选

日期2026-11-01 Asia/Shanghai，Issue151 / PR152，负责人Melodydt。状态：用户请求研究的候选，未冻结物理类型、实例数、程序或ABI；不替代P2未完成验收。

以每岛包含M/N/E/G/R/S/T全部七类型、必要适配与本地控制作为主参照。基于当前八样本/十层型，母控按A完整Attention、F FFN、D GDN、H Falcon混合、X MoE五种子层profile派发；LINEAR/MST等保留岛内核。profile不同不必对应不同物理大宏，同一岛可按永久产品程序时分服务多个层/profile。异构删宏和整decoder层封装保留公平对照。

选择子层边界可将QK/Softmax/PV、FFN中间值、MoE专家循环与Falcon分支join保持在岛内资源域。此处仅有算法切边/容量推导，未测面积、带宽、时序或走线收益；权重/KV/state仍需真实MEM，单M结果上下文和R多tile发布等缺口保留。M1–M10预制全部有源能力，M11/M12只连接粗端点和选择现成程序/参数，不增加控制、FIFO或buffer。

把完成拆为接单、sealed、传输、stored ACK、释放、状态publish及job完成，防止一任务占岛并等待未启动consumer形成环。粗封装不授予R全子层原子提交，也不把P2固定fixture当通用大Block。用户授权后续服务器仿真按REMOTE_RULES在本人Melodydt目录进行，本轮尚无部署或新作业。

详见[总报告](../COARSE_BLOCK_HIERARCHY_CANDIDATE.md)、[模型映射](../COARSE_BLOCK_MODEL_MAPPING.md)、[控制合同](../COARSE_BLOCK_CONTROL_CONTRACT.md)、[资源研究](../COARSE_BLOCK_RESOURCE_STUDY.md)。下一步先审查边界/程序/容量准入，再细化岛壳、双岛传递和物理对照，不提前宣称所有合法连接或完整模型已经实现。
