# Issue 21 资源账本独立只读审查

日期：2026-10-22。审查对象：`D:/Projects/LLMHardwareDesign-partition/project/experiments/operator_partition/{ledger.py,run.py,model-cases.json,experiment.json}`。未改生产目录，未访问或修改 GitHub，未运行真实权重、服务器或 EDA。按协作 Skill 只读审查。

审查时 Git HEAD 为 `cce235975b7be6d77247c9c9c7b09ea15608e2cf`，该实验目录当时尚未跟踪，因此这不是已提交版本的审查回执；以下以实际冻结文件 SHA 为准。冻结副本、输入与校验记录在 `deepseek/ledger-audit/`。

## 当前实质反馈

本审查发现的三项问题均已解决并经只读复核。下文保留初审发现与修复经过；最终复核版本和实际负例结果见文末。当前没有遗留的 P2 待处理项。

### 已解决 P2：将手填模型维度与固定输入配置绑定校验

初审 `run.py` 102–104 行仅校验 `input_file` 的 SHA，随后用 `model-cases.json` 中手填的 `hidden/intermediate/query_heads/kv_heads/head_dim` 建账。该版本中输入文件可以保持正确 SHA，而派生维度填错；事件重放、闭式公式与 clean Git 都不会发现这一层的错误，因为这些检查使用相同的手填参数。

实际反例已执行：仅在内存把 Qwen2.5-0.5B 的 hidden 从 896 改成 897，原输入 SHA 检查仍成立；独立读取 frozen config 的字段检查会拒绝。这个负例没有修改仓库文件，也没有生成正式 run 的假证据。

已落实的修复逐字段检查：JSON 先选 `text_config`（若存在）；dense 用 `intermediate_size`，routed expert 用 `moe_intermediate_size`；head_dim 优先取显式 `head_dim`，缺失才用 hidden/heads；Llama SKU 通过 AST 只读取常量并按已声明 FFN 表达式推导，不执行上游代码。不能统一以 hidden/query_heads 代替显式 head_dim，Qwen3/Qwen3.5 正好提供反例。

初审时 9 个 model-case 的 39 个派生字段已经独立核对，**全部正确**。当时指出的是数据绑定校验缺项，不是本次模型数值错误；该缺项现已修复。初审反例和实际字段值在 `ledger-audit/audit-math-results.json`。

## 审查中发现、已确认修复的两个问题

1. **运行中变源会导致来源不对应。** 初版在结束时才哈希文件，却使用起始读入的配置/已导入代码，并始终标记 `source_status=clean`。冻结副本已改成起始记录源 SHA/HEAD/clean，结束复查所有起始源字节、HEAD 和 status；变化时拒绝 qualified manifest。这一改动解决本次发现的运行期间变化问题。尚未做“修改后又恢复”或 Python 模块载入与第一次哈希之间的竞争测试；不能把当前机制描述成对恶意并发环境的防篡改保证。
2. **materialized softmax 状态访问漏记。** 初版分配 `row_state`，却只计 3S 读与 S 写，没有 max/denominator 状态访问。冻结副本现明确三遍流程：max；写 exp/sum；normalize；合计 `3S+2R` 读、`2S+2R` 写，其中 S 为 score 元素数，R 为 head-row 数。这与行状态驻留 vector bank 的声明相符。online 的行状态读写已计入。

上述修复已包含在本次独立计数实验使用的 SHA 中，不把已修问题继续列为待修阻塞。

## 独立计数检验及证据范围

独立脚本 `ledger-audit/audit_math.py` 不调用生产闭式公式来生成期望值；用自己的标量推导对照生产账本结果。随机 seed `20261022`，80 组 FFN 参数与 80 组 attention 参数，各比较 materialized/streaming 两种调度，包含非整除尾 tile、单 token 和不同 GQA 组。

- 320 个调度案例：2880 项独立流量/MAC 比较全部通过。
- 160 个 FFN 调度案例：480 项独立 matrix/vector/同时活跃峰值比较全部通过。
- 另对 320 份结果调用生产 `audit_events` 重放通过；这部分明确不冒充独立实现。
- 9 个模型配置案例、39 个派生字段与 8 份唯一输入文件的本地来源 SHA 核对通过。
- 初审时 1 个错误派生维度的负例由独立检查拒绝，初审版本输入 SHA 检查不能拒绝；此缺项现已关闭，见文末 39 个实际拒绝结果。

这说明以下关系在所审代码和已声明资源模型下成立：

### FFN

令 T/H/F 为 token/hidden/intermediate，N_t=ceil(T/token_tile)，N_f=ceil(F/feature_tile)，b 为 scalar bytes。

`external_bytes = (2*T*H + 3*N_t*H*F)*b`

`engine_transfer_bytes = 3*T*F*b`

`matrix_read = ((1+3*N_f)*T*H + 3*N_t*H*F + 3*T*F)*b`

`matrix_write = ((2+N_f)*T*H + 3*N_t*H*F + 3*T*F)*b`

`vector_read = vector_write = 4*T*F*b`

因此 token tile 变小确实支付全权重重载，feature tile 变小也支付 X 和 output accumulator 的重复 bank 访问。融合没有自动获得免费权重 cache，两个调度没有多拿 bank 容量。

### Attention

令 A=Hq*Q*d，S=Hq*Q*K，R=Hq*Q，C=ceil(Q/Qtile)*Hkv*K*d，N_k=ceil(K/Ktile)。这些是元素数。

两种调度均有 `external_bytes=(2*A+2*C)*b`，计算 `2*S*d` MAC；dense causal 把 masked position 算入，属于明确的工作量基线。

Materialized 的 engine transfer 为 `2*S*b`；online 为 `(2*S+N_k*A)*b`。新增的 `N_k*A*b` 恰是每个 PV tile 输出 O 从 matrix bank 到 vector bank 的传输。online 没有免费行重缩放引擎；vector 中执行 rescale/accumulate/final normalization，其读写均纳入独立比较。

峰值是同时活跃对象的最大值，未把两个 bank 在不同时刻的各自峰值相加冒充同时峰值。split/joined 仅改变跨 Block 与内部传输归属，不能取消内部移动，也不合并 bank 容量。

## 结果可以和不可以支持的结论

当前配置把 bank_access 定义为逻辑张量读写，不是寄存器 tile 或 SRAM 事务模型；没有 latency、端口节拍、链路速率、布局距离或工艺参数。Pareto 仅表示列出的调度指标间不被支配的点，不是物理最优 Block 或可实现吞吐。当前结果没有把这些量伪装成硬件测量。

DeepSeek 只建 initial dense / 单个 routed expert 的 FFN 账本，没有计 router/shared/dispatch；MLA 不被错误塞进 GQA 账本。Qwen3.5 仅覆盖 full-attention core，明确排除线性注意力和输出 gate。上述 scope 与输入元数据相符，不能外推为完整模型成本或真实 token 质量。

后续关于端口/裕量/最优划分的主张，需要增加可证伪的时序/流量模型与物理校准；本轮无需为这些尚未作出的主张新增阻塞。

## 固定版本与复现

| 文件 | SHA-256 |
|---|---|
| ledger.py | `37658c6aca44d7909ce52c1a0f1b559a5249e6304716a5329aac0f617ccb6026` |
| run.py | `033edcedaf50d7bec632d20af4bb3d74b3764cdc6023cad935a63f8693f6d464` |
| model-cases.json | `0428c4a359e6304e62a6775832ba250477f8955f094d8fb5a3a6bfd539890272` |
| experiment.json | `9ee538005ad6062dfaa64f30d102e4a660b7f45889688b7c90673f86403ea13f` |

执行：

```powershell
& 'D:/APP/Python/python.exe' -B 'D:/Projects/Codex/operator-partition-20261022/deepseek/ledger-audit/audit_math.py'
```

依赖：Python 3.13.14；导入生产 run 会加载当前 NumPy，但审查的期望值推导只使用整数算术。结果含脚本 SHA，`snapshot.json` 记录所有冻结输入文件字节/SHA 和观察时间。本审查不替代 method_review 的数值核审查，也不替代根任务的正式运行、提交与远端回执。

## 2026-10-22 修复后复核：全部发现已解决

复核观察到代码 commit `680dbbeed9a9189c06b047918ab4ae2ea6eedc28`。`run.py` SHA-256 为 `9c67cf02568b19f89cea27033b1a6cdf25509a13bf6949afde664faff76462bc`；`ledger.py` 仍为上表 SHA，因此前述 320 案例的账本计数验证继续适用。工作区存在主任务正在更新的文档/结果，不把此观察写成整个工作区 clean。

`run.py` 现新增 `validate_model`，正式 `run()` 在创建输出目录及建立所有实验行之前逐模型调用。已确认 JSON/text_config、显式 head_dim、MoE intermediate 与 Llama AST 常量路径均实际进入校验。

独立执行 `ledger-audit/recheck_bindings.py`，调用当前生产 `validate_model`：

- 9 个实际模型全部接受。
- 将每个已存在的 hidden/intermediate/query_heads/kv_heads/head_dim 分别加 1，39 个单字段负例全部以派生字段不匹配拒绝。
- 执行前后 run.py、ledger.py、model-cases.json、experiment.json、test_ledger.py 的 SHA 全部保持一致。

结果记录：`ledger-audit/binding-recheck-results.json`，SHA-256 `d274f8ab4fac6004891eba544bd5dfdd354b63cbfde19aa708f2673bbee3003f`。复核脚本 SHA-256 `b5f13593014ea8c5bed794d21cddc2cbd68871d37bb6243f8cff02d036cf0dba`。

主任务报告首轮完成 630 个调度案例、11340 个容量组合，并同源重放得到逐字节相同 ZIP。本次补充复核只验证配置绑定，没有重新执行或独立认定该正式运行及 ZIP 对比；这两项由主任务的正式 manifest / replay 回执提供证据。
