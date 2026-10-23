# Issue32 Qwen 问题修复与精度边界

关联 [Issue32](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/32) / [PR36](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/36)。旧失败和原报告保留，本报告给出后续修复证据。未合并/未验收，不标done。

## 显存与高精度参考

Windows Torch未编译FlashAttention；实测可用memory-efficient SDPA。Transformers原生GQA会传enable_gqa=True，该后端不支持；进程内显式repeat_kv并禁用其他后端，避免静默回退。前一OOM异常离开except后再gc，避免traceback保留GPU临时张量。Qwen3.58192独立组上限由9.5GiB调整为11.5GiB，仍受实际物理空闲减512MiB限制，无CPU权重卸载。

| 模型/组 | 8192一次峰值GiB | 8192分块峰值GiB | 状态延续结论 |
| --- | ---: | ---: | --- |
| Qwen2.5 FP16 | 6.671 | 6.114 | 最大cache L2=0.00536987；通过 |
| Qwen3.5 FP16 | 9.985 | 8.287 | 最大cache L2=0.0670345；未通过，保留 |
| Qwen3.5 FP32计算诊断 | 10.642 | 8.680 | cache L2=0.00015652，通过 |

FP32诊断保留大权重FP16驻留，当前矩阵临时转FP32、词表投影分4096输出行转换；激活、卷积、attention和状态用FP32。它证明数值精度/执行顺序影响延续，不证明INT8硬件。FP32缓存容量与FP16组分开。采集/敏感性运行不进入性能表。原生性能组预热1次、同步计时重复3次，全部样本在CSV；WDDM物理驻留只按已有采样说明，不推定整个运行独占或严格驻留。

## 量化质量

训练校准与测试验证分开；每组16×256=4096预测token，另保留4×128=512回归token。原始WikiText test用于开发；K128使用官方validation分片；K32排除之前16个验证源窗口，再选16个互不重叠窗口。FP32辅助组明确复用K32窗口评估执行后端，不冒称新盲测。原门槛未变：每样本KL≤0.05、NLL增量≤0.15、top1一致率≥0.9且有限。

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

最新整数矩阵延续结果以 `repair-evaluation.json` 和逐运行metadata ZIP为准；128+1只是预检，不能替代正式128+16。FP32显存参考通过不等于此量化路径通过。

状态独立扰动在真实FP32计算轨迹上逐类检查：KV/卷积16-bit在128与2048通过，递推16-bit失败；递推24/32-bit在128与2048通过。所有这些都是量化—反量化后原生浮点更新。8192联合KV16/conv16/recurrent24若执行，见state CSV实际结果，不从独立通过推定联合通过。INT24逻辑3-byte和量化器INT32代码实际4-byte分开，scale也是独立开销。

## Block预算与尚未完成的整数合同

Qwen3.5 K32实际矩阵payload3,569,090,560B，权重scale446,136,320B；Qwen2.5 K128为2,774,532,096B和86,704,128B。每组FP32 scale使W/A逻辑开销分别为12.5%/3.125%，K32有K128的4倍scale条目及部分和。原始INT32部分和必须连同scale重定标，或传FP32已缩放部分和；不能只预算INT8激活端口。

Qwen3.5原生固定49.5MiB+32KiB/token，Qwen2.5为36KiB/token；8224词元分别306.5/289.125MiB。递推不能按INT8或INT16自行压缩。INT24真打包与KV16/conv16加动态FP32 scales的示例约297.633MiB，节约仅约2.9%，且当前量化器没有实现3-byte打包。24×16乘积及128项归约可能需要40/47位，继续门控未重定标可能进入63位；这些是条件界，不是已验证的INT64整数状态更新。

矩阵之外，整数M/r、scale编码、非线性近似、KV/递推/卷积真正整数更新和饱和/舍入合同仍待主线冻结。供审查的候选与预算详见[精度候选决策](../decisions/issue-32-qwen-local-precision-candidates.md)。GPU耗时、假量化耗时、逻辑读写字节均不能当目标芯片速度或实测通信收益。

## 复跑与数据

源码与精度协议在各实验目录；模型官方revision/文件SHA和原始大数据位置在结果包索引。原始权重/全logits仍在本人D盘，团队认可共享存储待指定；少量真实更新输入随PR提供。`repair-quality-samples.csv`、`repair-state-sensitivity.csv`、`repair-continuation.csv`和`repair-failures.json`保留可复用字段，完整层/步统计在逐运行ZIP，包SHA在package-index。

完整代表复跑命令（PowerShell，输出目录须不存在，干净源码）：

```powershell
& D:/Data/llm-gpu32/.venv/Scripts/python.exe -B project/experiments/gpu_state_repair/run.py --model-dir D:/Data/llm-gpu32/models/qwen35 --out D:/Data/llm-gpu32/runs/qwen35-fp32-reference-reproduce --compute fp32 --lengths 8192 --perturb-lengths
```

该命令只复跑高精度参考，不把其通过外推到整数路径。实际完成的代表重放及最新检查见交接和validation回执。用户通知主研究线检查PR并整合；本任务不合并、不标done。
