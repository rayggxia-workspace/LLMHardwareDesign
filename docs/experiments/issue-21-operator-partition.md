# Issue21：模型驱动划分的首轮证据

2026-10-22，UTC+08:00。负责人Liangruizhi。[Issue21](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/21)。本轮回答前置问题与反例，尚未解决完整物理划分及端到端收益。

## 正式运行与结果

清洁源码commit `680dbbeed9a9189c06b047918ab4ae2ea6eedc28`；本机Python3.13.14、NumPy2.5.0。命令、输入版本、官方配置URL/commit及SHA在manifest/model-cases；临时目录D:/Projects/Codex/operator-partition-20261022/，正式成果project/experiments/operator_partition/results/issue-21-run01/。

9个**配置/算子范围案例**、69组工作负载、630个调度案例（315对物化/流式）；3档bank容量、3档预留、2种边界归属共11340个条件。7050个符合本轮容量条件、4290个失败，全部保留。**这些不是9个完整模型、11340个真实硬件实现或端到端benchmark结果**；相同模型的子图/尺寸是相关样本，不作独立统计泛化。

所有630份事件账本读回、闭式MAC/外部/跨单元公式和315组公平性比较通过。两次清洁源码运行的rows/capacity/pareto/events/numerical/summary/manifest及ZIP逐字节一致；ZIP七成员无需解压读回再验证630例通过。

归档233685bytes，SHA-256：`f85b1f120065f91d13df95cdf343d35eb48640d9a56d2755b46da5c6ed82306d`。结果包括容量失败、事件重数、同一bank同时驻留峰值和来源，非只保存成功。

## 已得到的可解释反例

下表使用Qwen3-0.6B官方尺寸，逻辑FP32字节，bank容量不因joined而增加。单位MiB/KiB为二进制。

| 案例与调度 | matrix bank峰值 | vector bank峰值 | 两引擎之间传输 | 外部传输 |
|---|---:|---:|---:|---:|
| SwiGLU，128 tokens，token tile128/F tile128，物化 | 4 MiB | 3 MiB | 4.5 MiB | 37 MiB |
| 同上，流式 | 1.625 MiB | 128 KiB | 4.5 MiB | 37 MiB |
| 同流式，token tile改16 | 656 KiB | 16 KiB | 4.5 MiB | 289 MiB |
| GQA核，prefill2048，Q tile32/K tile64，物化 | 256.0625 MiB | 256.25 MiB | 512 MiB | 1056 MiB |
| 同上，在线 | 112 KiB | 64.75 KiB | 1024 MiB | 1056 MiB |
| GQA核，decode1/KV2048，K tile64，物化 | 161 KiB | 128.125 KiB | 256 KiB | 16.015625 MiB |
| 同上，在线 | 34.5 KiB | 2.0234375 KiB | 512 KiB | 16.015625 MiB |

由此支持的结论：

1. 流式FFN降低所选调度的中间激活驻留，**没有**减少本模型下的矩阵↔向量总传输。把软件融合/流式的存储收益写成物理Block合并收益会误归因。
2. token tile从128改16进一步降低峰值，却使权重重读次数从1增至8，外部传输37→289MiB。只优化片上容量会遗漏重要代价。
3. 当前在线attention把O的重缩放/累加放在vector侧，每KV tile需传回部分O，因此相同工作和QKV流量下，跨单元字节增加到2倍。这是**所选引擎能力与状态归属**导致的反例；不是所有在线attention都必然增加通信，也不是FlashAttention普遍慢。
4. split/joined仅改变同一通信的跨界/局部归属。joined跨界归零是定义，局部连线、端口、时序和能量仍须实测；本模型不能据此挑选硬件最优Block。

## 正确性、独立检查与修正

- 全仓业务检查164项通过（原148＋新16），管理结构通过。新增核覆盖非整除tile、GQA分组、因果偏移、MLA重排、容量临界、重复/不平衡buffer、错误输入维度等。
- 正式缩小数值核378项（FP64/FP32）和3个故意错误负例通过。FP32最大归一误差：SwiGLU3.03e-7、GQA7.40e-7、MLA7.17e-6；是同已cast输入下与FP64参考比较，不能当真实量化模型精度。
- 独立DeepSeek原版路径数学核72项通过，包括MLA naive/absorb、增量decode/在线softmax、路由选择/组合权重及bias误用负例。独立Qwen/Llama/GDN数学与状态核136项通过，最大绝对误差约4e-15；均为合成缩小数据，未运行官方权重。
- 第一份独立账本公式审查96例通过；另一份320例、2880计数比较、480 FFN峰值比较通过。审查曾发现softmax row-state漏计和运行后才记录source hash的问题，已修复；派生模型维度现与固定config/公开SKU逐字段绑定，错误hidden/head_dim负例拒绝。修复后的独立配置绑定复核9个有效案例接受、39个派生字段篡改全部拒绝，源文件前后SHA一致。
- 开发数值单测曾对理论30.0要求逐bit相等，出现约3.55e-15舍入误报；改为预声明FP64容差后通过。不把这个开发失败描述为正式结果失败或静默改输入。
- 全量diff空白检查识别原始CRLF和上游DeepSeek源码4处行尾空格。原始证据字节/来源SHA保留；自有代码/文档按允许CRLF的空白检查通过，不修改上游原文件来获得形式上的全量通过。

## 研究选择与限制

官方配置确认：Qwen3的head_dim可独立于hidden/Hq；Qwen3.5具有混合递归/全注意力与额外gate；DeepSeek-V3/R1原版的MLA/MoE不同于R1蒸馏学生。Meta HF配置返回401，采用公开官方SKU，未绕过权限。模型/config版本和实现版本分别冻结，不把config中transformers_version当本次实用实现版本。

用户允许少量代表，因此正式benchmark优先dense GQA和MLA+MoE；混合递归作为扩展候选，历史版本作为结构/尺寸敏感性。当前广泛配置调查与廉价账本扫描不代表正式benchmark必须全部覆盖。已观察配置不是盲测，正式比较需另冻结参数集和未用于调参的验证对象。

当前没有真实模型输出质量、设备端到端延迟/吞吐、PE寄存器/端口竞争、真实HBM/NoC、RC/布线、PG/时序或功耗校准；没有最终制造前模板或可定制层集合。后续按共同研究问题推进：可运行代表模型trace→具体bank/端口/状态模板→同资源周期对照→物理回馈→端到端验证。Issue15由YUZE-LU继续，不干预其工程。

交付验证器另经三项独立篡改负例：错误外部SHA、成员/manifest不一致、重封装且更新哈希后的事件计数不一致，均拒绝。验证器边界为给定可信SHA的完整性及事件/闭式账本重放；capacity/pareto仅核哈希，numerical仅核记录状态，不宣称重新运行数值/绑定原源码。
