# Issue32 Qwen 问题修复与精度边界

关联 [Issue32](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/32) / [PR36](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/36)。旧失败和原报告保留，本报告给出后续修复证据。未合并/未验收，不标done。

用户最新范围：验收给定计算语义下的拆分等价、数据依赖与状态传递、指定整数算术的硬件一致性，以及有依据的容量/端口/通信/实现成本。完整整数模型语言质量不是EDA主线前置条件；已有质量仅作敏感性证据。追加语言质量和8192联合状态质量评估已取消，未执行不记数值失败。

## 显存与高精度参考

Windows Torch未编译FlashAttention；实测可用memory-efficient SDPA。Transformers原生GQA会传enable_gqa=True，该后端不支持；进程内显式repeat_kv并禁用其他后端，避免静默回退。前一OOM异常离开except后再gc，避免traceback保留GPU临时张量。Qwen3.58192独立组上限由9.5GiB调整为11.5GiB，仍受实际物理空闲减512MiB限制，无CPU权重卸载。

| 模型/组 | 8192一次峰值GiB | 8192分块峰值GiB | 状态延续结论 |
| --- | ---: | ---: | --- |
| Qwen2.5 FP16 | 6.671 | 6.114 | 最大cache L2=0.00536987；通过 |
| Qwen3.5 FP16 | 9.985 | 8.287 | 最大cache L2=0.0670345；未通过，保留 |
| Qwen3.5 FP32计算诊断 | 10.642 | 8.680 | cache L2=0.00015652，通过 |

FP32诊断保留大权重FP16驻留，当前矩阵临时转FP32、词表投影分4096输出行转换；激活、卷积、attention和状态用FP32。它证明数值精度/执行顺序影响延续，不证明INT8硬件。FP32缓存容量与FP16组分开。采集/敏感性运行不进入性能表。原生性能组预热1次、同步计时重复3次，全部样本在CSV；WDDM物理驻留只按已有采样说明，不推定整个运行独占或严格驻留。

## 已有量化敏感性（非EDA门槛）

训练校准与测试验证分开；每组16×256=4096预测token，另保留4×128=512回归token。原始WikiText test用于开发；K128使用官方validation分片；K32排除之前16个验证源窗口，再选16个互不重叠窗口。追加FP32辅助语言质量组按用户范围未执行。原门槛未变：每样本KL≤0.05、NLL增量≤0.15、top1一致率≥0.9且有限。

| 模型/候选 | 验证平均KL | NLL增量 | top1一致率 | 验证全样本 | 原回归全样本 |
| --- | ---: | ---: | ---: | --- | --- |
| Qwen3.5 仅W8假量化 | 0.0011094 | +0.000698015 | 98.4863% | True | True |
| Qwen3.5 仅A8假量化 | 0.025515 | +0.013072 | 92.9443% | False | False |
| Qwen3.5 逐行W8A8真矩阵 | 0.025154 | +0.0190526 | 92.1875% | False | False |
| Qwen3.5 校准平滑真矩阵 | 0.0132489 | +0.0164906 | 94.4824% | False | False |
| Qwen3.5 K128真矩阵 | 0.00241376 | +0.0027795 | 97.3877% | True | False |
| Qwen3.5 K32真矩阵 | 0.000972716 | -0.000313714 | 98.5596% | True | True |
| Qwen2.5 仅W8假量化 | 0.00427207 | +0.00412414 | 97.3145% | True | True |
| Qwen2.5 仅A8假量化 | 0.11295 | +0.0865766 | 87.3779% | False | False |
| Qwen2.5 逐行W8A8真矩阵 | 0.117564 | +0.0969909 | 87.5000% | False | False |
| Qwen2.5 校准平滑真矩阵 | 0.0357829 | +0.0245666 | 91.3818% | False | False |
| Qwen2.5 K128真矩阵 | 0.00752991 | +0.00312464 | 95.5811% | True | True |

仅W8通过而A8失败，定位到激活范围为主要损失来源。平滑只在训练校准行选择alpha并先保存factors/selection SHA；仍有失败，未调整门槛。K分组后每组真实INT8×INT8→INT32；有独立INT64核对。embedding、lm_head与卷积未被替换。FP32 scale/dequant/部分和、非线性和状态均明确保留，不能叫完整整数推理。验证集仍是抽样英文诊断加少量自编回归，不能外推所有语言/任务或完整WikiText标准PPL。

## 严格缓存延续与状态精度

FP16辅助的Qwen3.5 K32虽然语言质量通过，128+16缓存/32-token分块严格检查仍失败，最大状态L2约0.02262/0.03391；已停止本人工作进程并保留，未按耗时取消，未在失败后继续宣称长上下文通过。仅提升FP32、仅统一递推顺序也不足。规范辅助后端进一步固定RMS/L2归约树、卷积求和、逐token递推和逐query因果attention，属于明确的FP32诊断后端。

固定INT8矩阵+FP32规范辅助后端（源码4806b903147d65a74478cbd0d54c2c3a48cd69cb）的128+16 cached/32-token分块，以及512/2048/4096/8192的256-token分块+32 decode，对照同后端一次prefill，输出logits与所比较全部缓存状态逐位一致（最大误差0）。运行源文件结束时SHA未变。8192一次/分块峰值约7.459/5.777GiB；属于语义诊断，不能列为性能或全整数证据。固定归约、卷积、递推及因果attention运算顺序是本候选语义的一部分；不是将此软件后端指定为主线硬件方案。Qwen2.5原生FP16在8192一次/分块延续通过，并提供实际K128部分和；未追加完整混合模型长质量测试。

状态独立扰动在真实FP32计算轨迹上逐类检查：KV/卷积16-bit在128与2048通过，递推16-bit失败；递推24/32-bit在128与2048通过。所有这些都是量化—反量化后原生浮点更新。8192联合KV16/conv16/recurrent24未执行，按最新用户范围不再追加；不从独立通过推定联合通过，也不作为EDA阻塞。INT24逻辑3-byte和量化器INT32代码实际4-byte分开，scale也是独立开销。

## Block预算与尚未完成的整数合同

Qwen3.5 K32实际矩阵payload3,569,090,560B，权重scale446,136,320B；Qwen2.5 K128为2,774,532,096B和86,704,128B。每组FP32 scale使W/A逻辑开销分别为12.5%/3.125%，K32有K128的4倍scale条目及部分和。原始INT32部分和必须连同scale重定标，或传FP32已缩放部分和；不能只预算INT8激活端口。

Qwen3.5原生固定49.5MiB+32KiB/token，Qwen2.5为36KiB/token；8224词元分别306.5/289.125MiB。递推不能按INT8或INT16自行压缩。INT24真打包与KV16/conv16加动态FP32 scales的示例约297.633MiB，节约仅约2.9%，且当前量化器没有实现3-byte打包。24×16乘积及128项归约可能需要40/47位，继续门控未重定标可能进入63位；这些是条件界，不是已验证的INT64整数状态更新。

矩阵之外，主线应针对所选模块固定整数M/r、scale编码、非线性近似、KV/递推/卷积更新和饱和/舍入规则，然后验证实现一致性。未覆盖部分不阻止其他已指定语义的模块拆分/实现实验；不等待完整整数模型质量。供审查的候选与预算详见[精度候选决策](../decisions/issue-32-qwen-local-precision-candidates.md)。GPU耗时、假量化耗时、逻辑读写字节均不能当目标芯片速度或实测通信收益。

## 复跑与数据

源码与精度协议在各实验目录；模型官方revision/文件SHA和原始大数据位置在结果包索引。原始权重/全logits仍在本人D盘，团队认可共享存储待指定；少量真实更新输入随PR提供：两模型各3个layer0投影、prefill/单步decode的全部K组INT8输入/权重、INT32部分和与FP32 scales；Qwen3.5另有层0/14/30、head0/31在2048/2049/8192/8193的12个真实窗口，附Q/K/V、g、beta、初末态和独立FP64重放。`repair-quality-samples.csv`、`repair-state-sensitivity.csv`、`repair-continuation.csv`和`repair-failures.json`保留可复用字段，完整层/步统计在逐运行ZIP，包SHA在package-index。

完整代表复跑命令（PowerShell，输出目录须不存在，干净源码）：

```powershell
& D:/Data/llm-gpu32/.venv/Scripts/python.exe -B project/experiments/gpu_state_repair/run.py --model-dir D:/Data/llm-gpu32/models/qwen35 --out D:/Data/llm-gpu32/runs/qwen35-fp32-reference-reproduce --compute fp32 --lengths 8192 --perturb-lengths
```

该命令只复跑高精度参考，不把其通过外推到整数路径。固定K32+FP32规范辅助语义的完整复跑命令：

```powershell
& D:/Data/llm-gpu32/.venv/Scripts/python.exe -B project/experiments/gpu_state_repair/run.py --model-dir D:/Data/llm-gpu32/models/qwen35 --out D:/Data/llm-gpu32/runs/qwen35-canonical-reproduce --compute fp32 --integer-group-k 32 --fused-integer --canonical-causal-aux --lengths 512 2048 4096 8192 --perturb-lengths
```

实际完成的12窗口离线代表重放命令见gpu_state_capture/README与交接。用户通知主研究线检查PR并整合；本任务不合并、不标done。
