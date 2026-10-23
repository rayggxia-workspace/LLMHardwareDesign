# ≤4B INT8输入规范与轻量资源估算

[Issue48](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/48)。本工具把模型/场景需求接到六类候选库存，输出容量、线性计算和指定搬运策略下的预算；**不运行模型，不证明完整模型可行或物理收益**。总参数上限是4,000,000,000，包含所有专家、embedding及辅助参数，不能用模型名称中的“4B”或active参数代替。

## 先运行

仅需Python 3.10+标准库，从仓库根目录执行：

```powershell
python -B project/analysis/llm_resources/estimate.py project/analysis/llm_resources/examples/dense_4b.json
python -B project/analysis/llm_resources/estimate.py project/analysis/llm_resources/examples/qwen3_06b.json --output <新的报告文件.json>
python -B -m unittest discover -s project/analysis/llm_resources -v
```

有资源缺口的合法配置仍返回报告，退出码0；非法输入/格式/重复JSON键/已有输出文件返回2。输出JSON固定为UTF-8，拒绝覆盖文件。两次相同源码/输入的报告字节一致，没有时间戳或模型下载。

## 输入合同

机器规范：[schema.json](../project/analysis/llm_resources/schema.json)，版本`llm-resource-input/1`。所有字段显式填写；可空字段用`null`表示未定，未知字段/拼写错误拒绝，0只表示明确的零数量。`compute()`和CLI使用同一严格校验；标准库校验器覆盖本schema使用的子集，不是通用JSON-Schema引擎。

| 配置段 | 内容与约束 |
| --- | --- |
| `model` | 总参数、INT8参数、辅助参数及其存储位宽；三者分区计数必须相等。每组Linear提供唯一名称、总/active实例数、K/N及prefill处理全部行还是末行；或只给聚合`linear_macs_per_token`。两模式互斥；aggregate假设每个active矩阵权重每token使用一次，缺少完整图。多个调用复用同一权重、复杂重计算图须另建版本，不能靠重复条目突破权重计数。 |
| `model.attention` / `recurrent_states` | 每组attention的层数、Q/KV头数、head_dim、可选local window；持久递推状态按每序列元素数/位宽/额外字节声明。KV/递推为独立状态，不能由参数B数推定。 |
| `precision` | 矩阵W8A8、INT32累加固定；KV容量格式可选8/16 bit，aux/state独立格式。量化合同可留空。16位KV、P15、非线性/宽算术的降低与质量并未由本估算器实现，attention逻辑MAC不自动加入INT8阵列时延。 |
| `scenario` | prefill/decode、batch、已有cached长度、新输入长度、输出预留及目标**整个batch合计**token/s。prefill每步处理B×S个输入token；decode每步处理B个token，至少2个输出，因为第1个由prefill产生。目标速度可空。 |
| `hardware` | 候选配置路径、矩阵块数量扫描、频率/有效利用率、RQ II、外存容量/有效带宽、链路有效比例、共享bank保留量。路径相对输入JSON；用`--candidate <文件>`可替换。除候选外，待定时钟/服务率等留空，不使用原候选中的RQ32 II28敏感性值充当RQ33实测。 |
| `placement` / `accounting` | 权重/KV/递推选择shared、external或unknown；scale、padding、workspace、权重读取遍数、KV读取倍率、冷state读写遍数均显式记账。空值保留缺项，不能当免费。shared只使用S bank，不能挪用M/V/A/R私有RAM、ROM或端口FIFO填充容量。 |
| `mapping` / `transfers` | 当前矩阵tile的M/N/K、操作数/累加器副本及保留字节；传输指定shape、logical/storage位宽、元数据、已有有向路径及每步消息数。i33按i64容器传输；每步次数可空，不能凭张量shape自动生成完整通信图。 |
| `model.source` | 假设／配置推导／用户输入三类，保留URI、revision及说明。真实模型配置尺寸不等于已取得INT8 checkpoint或已验证质量。 |

## 计算口径与输出

数值单位是字节、MAC、周期、秒和B/s；GB=10⁹ B、KiB=1024 B。报告的每个下界只在给定配置及调度假设下有效。

- **权重**：INT8 payload＋已知aux位宽＋`ceil(INT8参数/group)×scale字节`＋已知padding。这里scale为flat grouping的容量下界，真实逐行/逐tensor分组和布局还可能增加开销。未知aux格式/padding/scale都列入`unresolved`。
- **状态**：预留容量按`C=cached+input+output`，local KV按window截断；KV scales按每token/每KV头的一行分组。decode单步在`C−1`处评估，这是生成最后一个预留输出时的上下文；prefill注意力使用包含cached前缀的因果三角形。只算所选phase，不估整段生成或端到端延迟。
- **计算**：逐Linear按active实例×处理行数×K×N；LM head可只处理prefill末行。矩阵数量下界为`ceil(线性MAC / (每块native_mul8×频率×利用率×目标单步秒数))`。RQ按显式II另列稳态服务代理；不把281个所有用途的乘法器当256位置矩阵阵列算力，也不把RQ/attention/非线性当免费。
- **外存**：权重流量按active矩阵权重和显式读取遍数，容量仍按总权重。MoE跨行/跨batch选中专家的并集、命中率需另提供，未定便留空。KV读基数假设每query行读其可见KV、组内共享、没有跨query复用；只有给出读取倍率才进入所选DRAM搬运账。倍率可表示多遍读取或跨query缓存复用，不是从KV容量自动推出的实测值。append写入另计。
- **候选内存/链路**：计入每类私有RAM、S bank、ROM和每个端点FIFO。64B header、64B payload对齐、2KiB FIFO时最大payload1984B，大传输分包；指定路径的每一跳分别计费。消息数未知时只给单消息成本，缺完整并发/仲裁/流量表时不判带宽可行。

主要输出：`storage`（已计入容量下界）、`work`、`external`（已计入流量/带宽下界）、`matrix_instances_linear_lower_bound`、`scans`、`transfers`、`known_constraint_violations_under_input_assumptions`及`unresolved`。**没有违例只说明这些必要检查未排除候选；没有“完整通过”状态。** 空缺项未进入已知下界，不表示实际为0；相关搬运全部未知时，带宽/时间保留null。`listed_policy_traffic_incomplete`标明列出的搬运账是否仍缺项，即使为false也不等于覆盖完整模型通信。每个扫描点均标记topology未映射，扩大M库存不会自动复制连接或带宽。

## 四个精选示例

| 输入 | 用途及可核对的推导值 |
| --- | --- |
| [dense_4b.json](../project/analysis/llm_resources/examples/dense_4b.json) | **合成4B边界**，不是实际模型。假设全部4B权重参与线性计算、250MHz、u=0.5、10 token/s，256位置M块的线性下界为2；每128参数4字节scale使权重已计入4.125GB，每步读取一次需41.25GB/s，超过示例32GB/s。不能因此判2块足够执行完整模型。 |
| [unknowns.json](../project/analysis/llm_resources/examples/unknowns.json) | 同一合成边界，但频率/利用率/目标/放置/带宽等未定；数量及时间保留null。 |
| [qwen3_06b.json](../project/analysis/llm_resources/examples/qwen3_06b.json) | Qwen3-0.6B真实配置尺寸，未运行模型；总596,049,920参数＝595,984,384个INT8矩阵/共享embedding参数＋65,536辅助参数。示例B1、输入128/输出32预留C160，INT8 KV payload为9,175,040B，逐head scale另286,720B。硬件/质量未定。 |
| [moe_2b.json](../project/analysis/llm_resources/examples/moe_2b.json) | **合成**2B总参数／0.5B active矩阵工作量，加一份说明性递推状态；展示总容量、active计算和未知换入流量分开。不是一个已经验证的MoE模型。 |

Qwen配置推导：H1024、I3072、Q16×128、KV8×128、L28、V151936；每层矩阵`2H(Q+KV)+3HI`，共享embedding/head只计一次`VH`。辅助参数为`28×(2×1024+2×128)+1024=65536`。norm32、scale格式等是候选存储假设，不是质量验收。prefill仅末行LM head时，线性工作量为`440401920×S+155582464` MAC/序列。

## 与既有候选及后续流程的接口

固定复用[PR44候选配置](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/3fa0b45070c7ce4587240589d48703d02a1b5246/project/experiments/block_candidate/candidate.json)，Git blob `6ceb6b8b6d4698792a75be782a7278aaab5ee3c5`，在profiles中保留原字节。基线M/V/A/R/D各1、S×8，声明库存464KiB、281个signed8乘法器；M×2/4变为502/578KiB，**只是库存缩放，未完成新连接/调度**。不复制或改写其analyze.py与决策实验。候选仍待审查，无硬件/PPA实现保证；外部自定义配置按本地文件SHA记录，不冒称原版本。

Qwen维度与参数公式沿用[PR26固定调研](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/2cd9ca1513f904d5fd319be11aa23a3e5b9b9646/docs/LLM_BENCHMARKS.md)及[官方配置revision](https://huggingface.co/Qwen/Qwen3-0.6B/blob/c1899de289a04d12100db370d81485cdf75e47ca/config.json)。不读权重、不依赖未合并分支在运行时存在；CLI仅消费本地JSON。

下一步由Block同学/团队填写真实频率、有效服务率、RQ通道/II、格式和存储预算；算法侧补生命周期、逐路径传输与映射，再进入布局/预连线和限定层路由。非线性/attention/递推的整数语义、溢出范围、数值质量，完整调度/争用/死锁、物理引脚/线轨/通孔/RC/STA均不由本工具验证，不能用“无资源下界违例”代签这些环节。

`provenance`记录输入/源码/schema/候选SHA-256、当前Git commit及逐文件字节绑定。未提交源码或外部输入的`source_bound=false`，仍可计算但不能当冻结交付；候选原字节匹配才显示PR44固定来源。业务测试检查已知值、非法/缺参、容量和带宽反例、prefill/窗口、打包/多跳、覆盖输出保护与确定性；管理检查及GitHub CI另列。
