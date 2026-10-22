# 固定真实Qwen3轨迹，分离调度、状态与静态连接

Issue23接续Issue21/PR22。选择Qwen3-0.6B固定c1899de2作为第一个实际权重案例：公开无门控、约1.4GiB文件可由本机资源承载，且具有明确GQA、独立head_dim和SwiGLU。此选择为可运行的完整模型验证，不能证明最终benchmark覆盖或模型流行程度。MLA/MoE及混合递归仍属于后续差异化代表候选。

先CPU FP32/eager以明确观察语义，4线程；不预设Intel XPU可用。隔离依赖和权重仅在D盘本任务目录，不改变全局环境。程序和输入先固定commit，实际运行时记录环境、配置、源码/数据和成果SHA。

对相同teacher-forced输入，比较完整prefix、32-token prefill+16步decode、16+16 chunked prefill+相同16步decode；另用96+8验证长度变化。atol=rtol=1e-4预声明，失败保留，不静默放宽。普通CPU运行耗时不是未来芯片速度。

观察所有28层shape、KV实际dtype/长度/字节，对0/13/27层比较末token边界；临时包装已核验4.57.6的eager入口以获取真实post-RoPE Q/K和GQA重复前的KV，避免把q_proj/k_proj当attention输入。每步与无观察缓存路径及独立全prefix对照，恢复hooks/global入口；observer复制不算固有模型驻留。

静态后期定制不能在prefill/decode间自动重接线。运行时选择硬件须另计资源且公平给予基线；固定基线拥有真实可用的chunk/tile/地址调度自由度。若合法固定方案已覆盖所有trace，应接受没有晚期定制优势的结果。单一Qwen的不同长度不等于两个计算拓扑的物理H2。

物理范围继续由Issue15/PR17推进，先读取固定版本终态再引用，不接管其电气/布线/STA收敛。真实trace之后才谈端口/周期模型及与合格物理结果校准；当前不承诺端到端收益。
