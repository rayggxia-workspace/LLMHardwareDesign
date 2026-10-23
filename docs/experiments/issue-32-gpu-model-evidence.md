# Issue32：16GB GPU 真实权重、整数矩阵与上下文证据

2026-10-23，负责人 YUZE-LU。[任务](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/32)，分支 `task/32-gpu-model-evidence`。这是待审查的阶段结果，不是完整整数模型或硬件验收。主研究线的小模型整数参考、划分搜索和 RTL/端口实验未在本任务重做。

## 结论与合同

- 两模型 FP16 的128-token prefill＋16步固定 teacher-forced decode、完整 prefix／cached／32-token分块检查通过。Qwen3.5 BF16 未通过同一阈值，保留失败，FP16为单独参考组。
- 普通注意力 Qwen2.5 在512/2048/4096的一次与256-token分块延续比较达到预设参考门槛；8192分块可执行，但一次prefill OOM，因此没有同档完整对照。
- Qwen3.5 在512/2048两种策略的 logits 达标，但部分缓存状态相对L2超出0.02；4096只完成分块，8192两策略均OOM。不能称长上下文状态等价通过。
- 实际 CUDA `torch._int_mm` 完成 W8A8→INT32 矩阵计算，抽取真实权重的累加样本由独立INT64求和核对；Qwen3.5候选质量3/4通过、Qwen2.5为0/4。**两个候选均未通过整体验收。**
- 所有状态INT8/INT16对照都是量化后反量化、原生浮点更新。没有验证INT8或INT16整数递推更新，也没有完整无浮点模型。

本轮复查 Issue23/PR24 和 Issue25/[PR26](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/26)@`2cd9ca1513f904d5fd319be11aa23a3e5b9b9646`；PR26仍OPEN。INT8矩阵、INT32累加及INT64整数重定标是主线提案，完整KV／状态／非线性／scale合同未冻结。本目录方法和门槛仅为提前冻结的本地诊断，不替代全项目方案。没有修改旧Qwen3-0.6B脚本或移除其保护。

## 硬件、版本、来源与隔离

RTX4060Ti 16GB，SM8.9；驱动610.88、WDDM、驱动CUDA13.3。实测FP16、BF16矩阵以及INT8→INT32内核可用。隔离Python3.12.4、torch2.10.0+cu128、transformers5.17.0，完整依赖／RAM／磁盘在结果包 `environment-and-audits.zip`。

最初SMI约空闲10.7GiB、RAM空闲8.3GiB，D盘空闲约104GiB；CUDA自身报告空闲显存约14.9GiB，二者不同。早期不设上限的长运行观察到本任务进程Shared GPU约5GiB，停止本人进程，保存历史；不当作驻留独显基准。正式 `bounded` 组固定9728MiB分配上限，保留512MiB物理余量策略。分配上限限制PyTorch，不构成WDDM驻留证明，没有PCIe/显存流量实测。

权重、隔离环境与原始大trace位于 `D:/Data/llm-gpu32/`，未修改全局驱动/环境，不终止他人进程。正式运行所有参数均检查在CUDA，不使用CPU卸载；CPU仅存放离线比较快照。

| 模型／执行路径 | 固定官方版本 | 校验与范围 |
|---|---|---|
| Qwen/Qwen3.5-4B，纯文本 `Qwen3_5ForCausalLM` | HF `851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a` | 两权重分片9,319,828,096B，SHA256见manifest；官方ModelScope只传输与HF元数据相同字节；非LFS核验Git blob ID。未执行视觉/MTP |
| Qwen/Qwen2.5-3B，普通GQA | Qwen官方ModelScope commit `5defd2796acd3cb2051bb4c787eddc7f8f35e113` | 两分片6,171,926,992B，逐文件官方SHA256，固定commit元数据再次核验；此版本不冒称HF revision。qwen-research许可 |

HF和PyTorch官方站点的下载途中发生TLS EOF；保留分段，通过官方元数据与完整SHA匹配后使用镜像传输。PyTorch wheel最终SHA为 `fbde8f6a9ec8c76979a0d14df21c10b9e5cab6f0d106a73ca73e2179bc597cae`。不更改全局代理/驱动。GitHub正常git传输失败后，通过当前本人 `gh` 认证的Git对象API上传，逐commit核对SHA相同，不重写作者或借用凭据。

## 格式与真实边界

| 路径 | 权重 | 激活／矩阵输出 | 累加 | KV | 递推／卷积状态 | 非线性与scale |
|---|---|---|---|---|---|---|
| FP16参考 | FP16 | FP16外层；内部有FP32 | 原生CUDA后端；不声称全部FP16累加 | FP16 | Qwen3.5递推FP32、卷积FP16 | norm、门控、decay与递推内部含FP32；无整数scale |
| BF16历史参考 | BF16 | BF16外层＋内部FP32 | 原生后端 | BF16 | 递推FP32／卷积BF16 | 浮点；短参考失败 |
| 真实整数矩阵候选 | Linear每输出通道INT8；embedding、tied LM head、卷积保留FP16 | 每token行动态absmax INT8输入；INT32结果反量化到FP16 | `torch._int_mm` INT32 | FP16 | 递推FP32／卷积FP16 | 权重／激活scale为FP32；FP32反量化与bias，norm、SiLU、softmax、RoPE、QK/PV、门控／状态仍浮点；无整数M/r |
| 状态8/16敏感性 | 原生FP16 | 原生 | 原生 | INT8/16候选后反量化 | 同时扰动KV、卷积与递推后原生更新 | FP32 absmax scale、RNE；不是整数状态算术 |

状态scale按最后两轴求absmax：KV为每head，递推矩阵为每value head，卷积`[B,C,K]`为每batch共享scale。它们联合扰动，不能单独归因，更不能说明方法最优。短输入每次decode后舍入，长输入每256-token prefill边界和每decode步舍入，不等于逐token整数prefill。

投影、attention/递推、norm、FFN及decoder边界均有真实hook形状、dtype和调用次数。`operator-events.json`另外覆盖ATen残差加法、功能算子及张量producer依赖；融合SDPA内部和别名完整DAG未暴露。`observed-long.json`提供长条件实际调用聚合和随chunk增长的Q/K/V接口，含OOM前的部分调用，不能将失败条件的次数当完整执行。

## 冻结输入与正确性

固定token IDs全部保存，decode不使用模型生成反馈。独立自编校准4段和验证4段，各128个预测token，中英/代码/硬件文本；动态absmax没有拟合参数，校准只作有限值检查。正式验证前冻结 KL≤0.05、NLL增量≤0.15、top1一致率≥0.9，逐样本同时满足；另须有限值、无累加溢出。该512-token诊断集不代表通用语言基准。

参考门槛预先冻结为logit最大绝对误差≤0.5、相对L2≤0.02，所有实际状态相对L2≤0.02。

| 128＋16 | cached最大logit绝对误差／L2 | chunk32最大绝对误差／L2 | 结果 |
|---|---|---|---|
| Qwen3.5 BF16 | 0.65625／0.042989 | 1.0625／0.033425 | 失败，不扩长；旧cache统计漏dict状态，不能用于容量证明 |
| Qwen3.5 FP16 | 0.195313／0.004973 | 0.0625／0.003421 | 所有64个真实缓存、观察器一致性均通过 |
| Qwen2.5 FP16 | 0.054688／0.002564 | 0.046875／0.003320 | 所有72个KV缓存、观察器一致性均通过 |

Qwen3.5 `fp16-short-01`与后续`fp16-bounded-02`重新执行的四份验证logits逐bit相同，完成代表条件实际复跑。第二次整数运行保存candidate logits，重新读取计算KL/NLL/top1与记录一致。

Qwen3.5 layer0捕获包括128-token chunk与第一次cached单步的真实Q/K/V、log-decay g、sigmoid beta、初态/末态/输出，以及A_log、dt_bias、卷积权重、两次卷积前QKV和128/129时缓存。边界位于函数内部FP32 QK L2Norm及Q/√d之前；g/beta已过相应非线性，不冒充原始gate logits。只保存少量代表状态，不保存每层每步全状态。

独立einsum递推重放：chunk输出L2约7.69e-6、末态4.17e-7；cached输出6.60e-7、末态6.56e-8。初态加0.125负例产生cached末态L2约1.818，能检出错误初态。该证明仍是浮点更新。

## 真实整数矩阵质量

Qwen3.5替换248个Linear，校准/验证共1984次整数内核调用；Qwen2.5为252个、2016次。最坏K×127²的INT32界安全；观察最大绝对累加分别1,617,807／642,184，饱和计数0。抽取第一层8／7组真实A/B样本由独立INT64求和逐bit核对通过，不将样本证明夸大为完整模型整数等价。

| 模型 | 样本 | KL | NLL增量 | top1一致率 | 筛查 |
|---|---:|---:|---:|---:|---|
| Qwen3.5 | 0 | .011106 | +.020556 | .976563 | 通过 |
| Qwen3.5 | 1 | .401111 | −.060632 | .906250 | KL失败 |
| Qwen3.5 | 2 | .005958 | −.005319 | .992188 | 通过 |
| Qwen3.5 | 3 | .006309 | +.004220 | .984375 | 通过 |
| Qwen2.5 | 0 | .139270 | −.037546 | .914063 | KL失败 |
| Qwen2.5 | 1 | .173097 | +.221578 | .898438 | 多项失败 |
| Qwen2.5 | 2 | .138997 | +.114277 | .968750 | KL失败 |
| Qwen2.5 | 3 | .205954 | +.063484 | .882813 | KL/top1失败 |

不能用某条NLL改善代替分布质量通过。没有调参后重新挑验收集，也没有将假量化耗时或本GPU速度报告成INT8硬件收益。由于本候选失败且状态合同未冻结，没有扩展其长上下文性能组。

## 长上下文：batch1、decode32

每条件1次预热＋3次测量，所有样本保留；GPU同步墙钟分开计prefill/decode，排除加载/tokenization。正式计时无hook；单独观察器组不进入性能。下表为正式bounded组总时间中位数及测量峰值allocated，**不是目标芯片性能或实测物理流量**。

| 模型 | prefill | 一次：秒／GiB | chunk256：秒／GiB | 实际末端逻辑缓存MiB |
|---|---:|---|---|---:|
| Qwen3.5 | 512 | 3.0944／8.024 | 3.4034／7.972 | 66.5 |
| Qwen3.5 | 2048 | 3.9156／8.733 | 4.1776／8.066 | 114.5 |
| Qwen3.5 | 4096 | OOM | 5.2423／8.382 | 178.5 |
| Qwen3.5 | 8192 | OOM | OOM | 未完成 |
| Qwen2.5 | 512 | 2.2937／5.836 | 2.3219／5.795 | 19.125 |
| Qwen2.5 | 2048 | 3.1260／6.504 | 2.6337／5.920 | 73.125 |
| Qwen2.5 | 4096 | 4.7345／8.408 | 2.9321／6.003 | 145.125 |
| Qwen2.5 | 8192 | OOM | 5.3628／6.350 | 289.125 |

Qwen3.5使用PyTorch参考causal conv和GatedDeltaNet，未装FLA；SDPA内部GQA repeat和临时张量亦消耗空间。实际conv缓存`[1,8192,4]`为紧凑storage，没有把full prefill保存在conv缓存。OOM不等于模型上下文不支持，也不证明换内核后必能运行。

Qwen3.5长512/2048分块相对一次的decode logits L2分别.014884／.006467，但最大逐状态L2为.038785／.074749，超过已有参考门槛；因此只是已执行的高精度状态数据，不是状态等价通过。4096没有同预算一次参考。Qwen2.5在512/2048/4096的最大逐状态L2约.003662／.004384／.005096，logits也达标；8192无一次参考。

状态联合假量化：Qwen3.5短8bit最大logit L2约.911，16bit约.0131；长512/2048/4096的8bit末logit L2约.243/.266/.246，16bit约.0272/.0143/.0186。Qwen2.5相应短8bit约.0217、16bit.00177；长8bit约.0128–.0208，16bit约.00095–.00280。各层误差和FP32 scale字节完整保存；较小的16bit扰动不能证明整数16bit更新可行。

## 给主线的容量、端口和通信输入

| 实际边界 | 原生容量／接口证据 | 对预算的约束 |
|---|---|---|
| Qwen3.5递推 | 24层，每层FP32 `[1,32,128,128]`＝2MiB，共48MiB；卷积每层FP16 `[1,8192,4]`＝64KiB，共1.5MiB | 必须独立规划常驻状态及读改写端口；若每token外传读写全部递推矩阵，逻辑上为96MiB/token，非实测且可由片上复用改变 |
| Qwen3.5 full attention KV | 8层，KV4头×256维，K/V均FP16；全模型32KiB/token | 末缓存为49.5MiB固定状态＋C×32KiB。C=8224时理论306.5MiB，未完成运行，不能报实测 |
| Qwen2.5 GQA KV | 36层，KV2头×128维，FP16，36KiB/token | C=8224实际289.125MiB；每decode读旧KV、append新KV，带宽随C增长；chunk不改变最终KV容量 |
| INT8权重候选 | Qwen3.5被替换权重3,569,090,560B＋FP32通道scale4,528,128B；Qwen2.5为2,774,532,096B＋4,128,768B | embedding/head/卷积不在这些INT8字节内；激活行scale另传，INT32输出需4B/元素，不能按INT8输出计端口 |
| Qwen3.5门控与FFN | 真实g/beta为每value-head32路；QKV与g/beta、QK norm及递推依赖已采集 | 门控、指数、归一化、重定标必须有配套单元和精度合同；INT8 MXU通过不覆盖这些路径 |

FP32递推若仅按INT16/INT8存储，理论矩阵payload可为24/12MiB，但这是**未获验证的容量情景**，必须另加scale。当前状态方法每层32个FP32矩阵scale；conv每层1个FP32 scale、KV每head scale，非零开销。整数重定标若采用主线INT64乘移位，还需宽乘法／舍入／饱和资源及跨Block格式接口，不能由GPU浮点反量化代替。归一化和softmax等如果保留FP32，便需要浮点辅助单元或显式回退边界；本轮不证明openTPU的FP32辅助路径能消除，也不证明llaccel整数辅助单元足以实现本模型。

分块使projection/FFN临时激活按chunk缩小，但增加调用、状态交接与KV访问次数；按实际 `observed-long.json` 的shape/calls建通信账本，不把模块logical read/write相加冒充DRAM流量。缓存logical bytes、去重storage bytes、PyTorch allocated/reserved、WDDM Shared和真实测得流量须保持不同字段。这里最后一项为null。

## 产物、失败与复跑

[正式代码与字段说明](../../project/experiments/gpu_model_evidence/README.md)，[JSON/CSV与索引](../../project/experiments/gpu_model_evidence/results/issue-32/)，[完整交接](../handoffs/2026-10-23-issue-32-gpu-evidence.md)。压缩元数据包含源码commit/文件SHA、冻结配置、输入token、模型版本及文件SHA、实际加载信息、全部计时与失败traceback。

代表源码：Qwen3.5正式参考／整数复跑 `82ad35dba0ea7e6d07079e83fe2b781de2ce4c5d`；Qwen2.5 `e6a830ca22977756de3d5bf09bcf71164f8412cc`；观察器Qwen3.5为e6a830c、Qwen2.5为8f73247。运行结束均记录source-at-end；Qwen2.5运行期间仅合入主线其它目录，运行器文件SHA未变。

早期UTF8配置、loading-info set序列化失败，BF16数值失败，未设上限WDDM spill停止，自动上限受显示显存驱逐影响而重新选择固定上限，以及所有正式OOM均保留。`running`历史目录是人工停止的旧组，不能解释为仍有作业运行。没有静默降级或用更低精度覆盖失败。

实际验证：管理结构检查、5项协议测试、四组正式参考/整数产物SHA读回、真实整数样本INT64核对、Qwen3.5递推独立重放及错误初态负例、验证输出重复与质量重新计算、交付包无需模型的重放通过；差异检查通过。原始大trace与权重仍在本机，`local-artifacts.json`给位置/版本/SHA。少量代表layer0原始输入和状态随PR提供，完整团队共享存储尚待项目指定，不声称团队能直接访问本机目录。

未跑Llama3.2：本阶段优先的Qwen3.5与普通注意力代表已完成；未确认访问授权，不为凑列表添加模型。下一步由主线审查并冻结状态/非线性/scale及质量合同，复用本真实输入验证整数状态更新，再决定更大验证集和下一轮校准方法。
