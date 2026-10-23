# 共享KV数值合同与CPU/GPU分工

2026-10-23（UTC+08:00），Issue47，Liangruizhi。记录用户后续要求及选择理由，均为候选/计划，不宣称任务已执行。

## 局部数值证据如何影响划分

采用独立校准而不是评价时重拟合；完整GQA共享组共同约束g/KV scale，cache payload发布后不可静默重标定。
在本轮一层一个组的两个短文本上，变换降低局部误差且连续cache检查通过，保留此候选，不作为全模型质量接受。
将scale profile、位置和状态版本加入接口；不把P1–P15划为15块，仍按M/V/A/R/S/D及数据依赖比较。
原FP32/BF16实验与Issue39同张量拟合保持历史边界，不改写成新整数或独立校准结果。

## 师兄批次扩展

用户要求尽量一次完成GPU工作。此前“最小集不新增”限制过窄，改为主测、扩展和保留验证分层：
Qwen2.5、Qwen3.5-4B、Gemma3-4B主测；Gemma3-12B4bit、Qwen3-4B、Llama3.1-8B4bit、R1-Distill-Qwen-1.5B有限扩展；
Phi-4-mini保留数据可先采集封存，冻结前不调参。已有合格结果直接复用。
4bit条件单列，不替代W8A8；dense R1蒸馏不代表原版R1 MLA/MoE。取消的额外语言质量矩阵不自动恢复。
详细可转交文案见[批次请求](../handoffs/2026-10-23-gpu-batch-prompt-v2.md)。本机仍不下载或运行上述较大模型。

## 96核超算CPU的条件估算

用户询问可行性，尚未授权改变“仅本机”的执行分工或提交新服务器作业。本轮未登录、未测CPU服务器。
仓库REMOTE_RULES只注明c64/c96和30分钟debug节点，CPU型号、物理核/线程、ISA、RAM和可分配带宽待核实。

CPU可以提供全权重数值参考、结构/张量/状态采集、量化误差和整数oracle；GPU速度、显存及GPU内核验证保留GPU。
已有Qwen3.5原生低精度失败记录也不能通过换CPU静默跳过，须分别声明实现和精度，按自身cached/chunk参考重验。

| 参数量 | BF16/FP16纯权重GB | FP32纯权重GB |
| --- | ---: | ---: |
| 0.6B | 1.2 | 2.4 |
| 4B | 8 | 16 |
| 8B | 16 | 32 |
| 12B | 24 | 48 |

十进制近似，不含scale、模型参数精确差异、双份加载、KV、激活及workspace。4bit纯payload是每参数0.5B，
不表示NF4/GGUF/其他格式的真实文件或运行RAM。若可分配128GB，单模型短/中上下文通常有较大空间，
Gemma12B可探索高精度参考，实际峰值仍须试跑；禁止保存全层完整S×S attention使峰值失控。

密集矩阵估算2PS FLOP：4B、S2048约16.384TFLOP；若有效0.1–1TFLOP/s，该部分约16–164秒。
忽略attention、加载和转存，**这是条件计算量估算，不是运行时间保证**；混合注意力/embedding等需按真实图修正。
decode简化带宽下界t≥W/B：举例有效50GB/s、4B BF16权重8GB，单token至少约0.16秒；12B则约0.48秒。
这是每步读一份权重的理想示例，未计其他流量/计算/NUMA，不能直接承诺6.25或2.08token/s。

先做约10–20分钟有界pilot：只读环境和已授权已有模型，测8/16/32/48/96线程（不超分配），
固定B1、prefill128/512及decode16，性能与插桩分开；核验缓存一致，记录RAM峰值、吞吐和NUMA。
没有现成权重时下载时间另算。根据pilot决定逐模型单进程还是少量独立并行，不能按96倍线性提速。
BF16是否快取决于原生指令/后端，FP16不能凭GPU经验默认最快；旧CPU可优先FP32或已验证量化后端。
正式批次用有合适时限的c96队列并留checkpoint，不把全部任务塞进30分钟debug。须遵守REMOTE_RULES的目录/调度约定。

依据：[PyTorch BF16/oneDNN说明](https://pytorch.org/blog/empowering-pytorch-on-intel-xeon-scalable-processors-with-bfloat16/)、
[PyTorch Xeon生成式推理说明](https://pytorch.org/blog/genai-acceleration-intel-xeon/)、
[Intel推理阶段/带宽说明](https://intel.github.io/intel-npu-acceleration-library/llm_performance.html)。上述实例不是本服务器实测。
