# 八样本 decoder 子层所需功能类别与宏数量参考

Issue151/PR152，负责人 Melodydt。固定研究输入 `a37e37cad757af5bfc94ed65db3e2e728023c251`，原生叶宏 `707878621b2add4ed218b8c43df2e95c9a56e2ba`。本轮生成文档/机器表和研究一致性检查，不改RTL、不运行仿真/服务器、不接管其他实施任务；正式远端交付状态见PR回执。

结论是**五种子层功能profile、六种主宏配方变体**：A分普通/带输出门，另外F、D、H、X。下表给出明确整数数量。数量是“面积优先、顺序执行、真实MEM/NUM/固定调度与接口能够闭合”的逻辑参考，不是数学最小值、已实现整链、冻结芯片BOM或吞吐保证。S/T各1是本方案采用的scratch/loader和分片发布接口选择，不是所有等价算法都必须各带一个S/T的定理。

## 1. 主数量表

| 变体 | 功能范围 | M | N | E | G | R | S | T | 七类叶实例合计 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A_plain | 完整普通Attention子层，含源Norm/投影/Softmax/输出处理/残差 | 1 | 1 | 1 | **0** | 0 | 1 | 1 | 5 |
| A_gate | A加Qwen3.5全局层PV之后的Sigmoid输出门 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 6 |
| F | Dense FFN完整子层，含pre/post Norm、激活门和残差 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 6 |
| D | Qwen3.5 GDN完整mixer子层 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 7 |
| H | Falcon Attention+SSM完整混合mixer子层 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 7 |
| X | Granite MoE完整子层，router/expert/merge均在本地 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 6 |

五profile不是五个已存在大宏，六配方也不要求芯片同时放六个实例。相同数量向量不等于相同物理实现：A_gate/F/X均为六叶，但程序、局部路线、回放、NUM/gather要求不同；D/H均为七叶，但状态更新式、归一化顺序、bias和系数要求不同。它们可在冻结前合并成具有相应能力并集的通用包装，也可按类型预制异构包装；不能在M11/M12定制时才删G/R或补控制器。

七类之外的本地控制、MUX、格式/布局/尾包、真实缓存、MEM端点、NUM系数/宽归并、完整状态版本服务**未包含在上表合计**，其实例/容量未冻结，不能理解为成本0。机器表把这些额外数量记为null/待定，没有给它们编造零值。

## 2. 为什么 A_plain 不需要 G

当前八样本的普通attention主体是：输入RMS/RMS0→QKV投影及实际bias→可选QK头Norm→RoPE/布局/GQA→QK→scale/mask→Softmax→PV→Wo→可选postNorm/gain→残差。

- N顶层已经有Softmax的score指数函数、exp_sum、factor和概率回放：op0 mode0、op1统计、op2完成统计、op3计算EXP、op4完成EXP因子、op6回放概率。N内部group/divider/sqrt和EXP LUT属于**一个N叶宏内部**，不另计G或外部第二个N。
- RoPE是E的 **op9**，bias/residual是E.op0，支持的数值scale是E.op2等；它们不是G激活。
- Qwen3及Gemma的Q/K Norm都由同一个N顺序完成；Gemma的post-attention RMS0也归A/N。RMS0只改变gamma=1+weight的参数绑定，不需要G。
- Gemma的GELU_tanh在FFN门上，归F；普通attention图没有SiLU/GELU等门。Attention的KV缓存是内存状态，不意味着需要递推R算子。

因此A_plain自然映射为M1/N1/E1/G0/R0/S1/T1。这里“G0成立”是这条既有算子分工的结论，不是声称N/E能替代所有激活。N的op3只是mode0、保存最大值上下文里的有界score EXP，**不能当成任意宽/任意单位的通用Exp**，也不能拿它自动填补D/H动态decay缺口。N单组count<=65535；如果永久接收更长完整Softmax行，仍需额外经验证算法/资源，不能因为本表N1就直接宣称支持131072/262144 context。

A_gate的区别是源Qwen3.5全局层多了一条 `Sigmoid(Gate)×PV_context`，位置在PV后/Wo前。本参考复用G.fn1/gated来做，所以增G1。若另行研究用N/NUM等重构Sigmoid，必须另证明舍入、范围、误差和资源，不是本表已经证明G1不可替代。

证据：[N内部EXP及命令guard](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/707878621b2add4ed218b8c43df2e95c9a56e2ba/project/rtl/block_v2/block_v2_n.sv#L57)、[N Softmax factor与回放](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/707878621b2add4ed218b8c43df2e95c9a56e2ba/project/rtl/block_v2/block_v2_n.sv#L138)、[E.op9 RoPE](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/707878621b2add4ed218b8c43df2e95c9a56e2ba/project/rtl/block_v2/block_v2_e.sv#L72)、[Qwen3.5输出门位置](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/a37e37cad757af5bfc94ed65db3e2e728023c251/docs/model-analysis/COMPUTATION_GRAPHS_SIMPLIFIED.md#L276)。

## 3. 每种宏做什么：计算与数据生命周期分开

| 宏 | 本方案用途/关键原生op | 为什么串行基线只计1 | 不能因此假定 |
|---|---|---|---|
| M | op4 signed factor/left-shift；op10 S8/S16分段dot与S64合并；op3原始S64或op5 RNE/clamp读出；op6/11有效性生命周期 | QKV、QK/PV、gate/up/down、专家各次投影按固定顺序复用 | 两输入bank不是两个结果上下文；没有merged结果restore，不能免费交错QK/PV partial或gate/up/down partial |
| N | mode0 Softmax；mode1 RMS；mode2 L2；op8/9/10 TopK（X） | 每个统计/因子/回放组完成后才改上下文，再处理下一head/token/用途 | busy不是lease空；不能在未回放完一组时BEGIN另一组并丢掉旧factor |
| E | op0 add、op2 mul、op9 RoPE、op10 S16 RNE右移、op13四S32→四S16子集及必要选择 | 相邻阶段按packet串行 | 不是通用S32/S64 bias/加权累加器；M.op5若已提供可接受S16可证明提取，不强制每条边再E13 |
| G | fn0 SiLU、fn1 Sigmoid、fn2 GELU_tanh、fn3 Softplus；可紧邻门乘 | 同一两lane流水线遍历通道/heads/专家和不同非线性阶段 | 它没有通用Exp/宽系数；ungated Sigmoid Q14，gated Sigmoid经>>14返回Q10，其余gated经>>10返回Q10，不能只按fn推输出格式 |
| R | op6 mode2 conv、mode0 GDN、mode1 SSM；OPEN/load/EXEC/output/commit/export | 卷积与状态更新、不同层/head/tile依次复用，完整状态从真实存储恢复/导出 | 单R的active/shadow各8KiB不是完整2/4MiB状态；单tile commit不是完整token根发布 |
| S | 普通128bit字读写和**写ACK**、回放/scratch、内置A128/B512 loader | 选定单S的串行scratch/装载服务，较大数据必须有真实分片/存储方案 | 总16KiB不等于全部可自由分配计算区；普通口/宽loader共享真实bank；loader done只是已供数而非M计算完成 |
| T | BEGIN→顺序WRITE→SEALED→COMMIT→READ/TAKE→RELEASE | 选定单租约6KiB输出chunk接口，所有tensor按真实容量分片 | 一次fragment_last不是完整子层done；复用前必须release，同T再入和保留旧批需真实spool/存储 |

M/E/G是主要计算资源；N、R同时拥有跨多条命令保留的上下文；S/T是数据生命周期/接口资源而非额外算法计算要求。每个大Block仍需一个明确本地owner域，它可以包含多个局部FSM/helper；本轮没有用“控制器一个”估造门数或ROM容量。每个原生端口在任一时刻只能有一个owner。

## 4. 各变体的宏用途与顺序约束

### A_plain / A_gate

M顺序做QKV或fused QKV、QK、PV、Wo；N做input Norm、实际存在的QK头Norm、Softmax及Gemma post-attention Norm；E做bias、RoPE、score/gain与残差，S/T负责真实存储和chunk发布。A_gate多出的G只做Qwen3.5 context输出门。普通A中的N.op3已经供Softmax EXP，因此不把“有Exp”机械映射为G。

Qwen2.5有三路QKV bias；Qwen3 Q宽2048而H1024；Gemma A内input/Q/K/post-attention四个RMS0 site，window1024与global配置分别绑定；Phi fused QKV5120拆3072/1024/1024，RoPE96/128；Qwen3.5 Q_gate8192按16head各512再拆Q256/Gate256，RoPE64/256；Granite score scale0.015625、Wo后gain0.22。上述差异是程序/参数/布局，不要求另复制一个G给普通A，也不能为了共用A_plain而删除Norm/bias或改scale。

### F

M做gate/up（或fused gate_up）及完整I down；G.fn0/2 gated分别实现SiLU或Gemma GELU_tanh门；E做支持范围内的缩放/格式/残差；**N1是因为这里F包含pre-FFN Norm，Gemma还包含down后/post-FFN Norm**。若只切一个无Norm的FFN内部核可以讨论N0，但那不是本表完整F。

Phi gate_up输出16384再拆8192/8192；Falcon gate在SiLU前有0.353553...、down后0.078125；Gemma两处FFN Norm都是RMS0。单M结果必须先导出再算下一投影，不能一边保留down partial一边任意重算gate/up。Qwen2.5单token中间S16向量22016B已大于S16KiB，故M1/S1不是现有片上完整映射证明。

### D

M做qkv8192/z4096/beta32/a32及Wout；R同一实例先conv4、再GDN状态；G顺序做卷积SiLU、beta Sigmoid、dt Softplus以及SiLU(Z)输出门；N做input RMS0、实际Repeat16→32后的Q/K L2和每value-head128 RMS；E做Q独有1/sqrt128、支持的格式/残差。

R主要使用OPEN/op1 state load、op2/3 key/query、op4 x、op5 decay/beta、op9/10 history/taps、op6 mode2/0、op12 output、op7 local commit、op11/14 export。op8只撤未提交候选，不能回滚已接受op7 COPY。完整L2 epsilon、decay Exp和单位仍未接收；G Sigmoid结果到R所需系数单位还需真实适配/数值证明。输出顺序必须是R读出→每head RMS128→乘SiLU(Z)→Wout→residual，不能改成H的顺序。完整state为[B,32,128,128]，不是24个GDN层各独占一R，也不是R1本地就装得下。

### H

完整H用一个M串行完成Attention/SSM投影和矩阵；一个R先conv4再mode1 SSM；一个G复用卷积SiLU、Z门和Softplus；一个N先共享input RMS2560，再按调度完成Attention Softmax、SSM门后global RMS4096；一个E处理K/MuP/gain/残差及支持的格式子集。R mode1还要求op15预装逐元素UQ1.31 decay和实际loaded/param_valid/skip/inject guards，不得因为“算法上似乎不用某参数”就删掉原生命令前提。

SSM投影8736=Z4096+XBC4608+dt32，XBC卷积有bias且在SiLU前；R没有该bias口，需要真实数值路径。状态[B,32,128,256]，读出先乘SiLU(Z)，再跨4096做一次RMS，Wout和ssm_out之后与attention_scaled相加，再与X相加。一个R可顺序服务32层的tile，前提是全状态/history在真实MEM和old/next根下恢复/导出；缺这些服务时完整H仍未映射。

### X

N1先做一次pre-MoE RMS1536，然后TopK40→8（op8/9/10）以及**selected8 logits**的Softmax；M1做router及所选8专家fused gate_up/down；G1做每专家SiLU门；E1负责可支持的格式/最终残差，S/T负责ID/rank/probability/输出等实际存储与发布。TopK只ID，selected logits必须从已保存40 logits真实gather；ID不能当概率或score。每专家I512，fused gate_up1024，不在专家内部新增Norm。

8个1536维专家返回必须在共同单位下宽加权归并，gain0.22后再残差。E的S16 FMA并不直接提供该S32/S64 NUM；统计数量没有把NUM或专家数据访问变成已实现。40专家不是只永久保留某8个专家，完整权重/身份域仍在范围内。

详细每宏op/mode用途、0实例理由、生命周期类别和限制见`block-variant-models.json/variant_rows[*].macro_rows`。这是已有op的**候选可达用途目录**，不是完整native程序已经编译或执行。

## 5. 每模型/层的分配与全局复用

| 模型 | 源层序列对应变体 | 每种所需变体各放1实例的说明性池 | 该池七宏总数 |
|---|---|---|---:|
| Qwen2.5×36 | 每层A_plain→F | A_plain1、F1，所有36层依次复用 | 11 |
| Qwen3×28 | 每层A_plain→F | A_plain1、F1 | 11 |
| Llama×16 | 每层A_plain→F | A_plain1、F1 | 11 |
| Gemma×34 | 局部29/全局5都A_plain→F，保留各自窗口/RoPE/Norm参数 | A_plain1、F1 | 11 |
| Phi×32 | 每层A_plain→F，保留融合投影/部分RoPE | A_plain1、F1 | 11 |
| Qwen3.5×32 | [D→F,D→F,D→F,A_gate→F]×8 | D1、A_gate1、F1 | 19 |
| Granite×32 | 每层A_plain→X | A_plain1、X1 | 11 |
| Falcon×32 | 每层H→F | H1、F1 | 13 |

上表是帮助理解重复利用的池例子，不是每产品最优BOM或必须制造这么多岛。特别是24GDN层不等于24R，32SSM层不等于32R。若同一包装预制了D+A_gate的全部能力，可以让一个mixer实例按固定程序复用；若一个包装预制全部五profile能力并配齐MEM/NUM/控制，可讨论全域串行资源并集M1N1E1G1R1S1T1。后者只是条件化参考，并没有证明当前七叶加在一起就能跑完整模型、满足吞吐或构成数学最小值。

反过来，若为六个变体各摆一份，数量向量为M6/N6/E6/G5/R2/S6/T6，共37叶；这只是**配方目录一份各1**的求和，不是支持八模型的必选芯片。A_gate与F/X或D/H的宏向量相同，也不自动说明它们无需新增任何本地程序/路由/NUM就能合并。物理实例配置要由完整调度、容量、吞吐目标与实际后端共同选择，当前未测PPA。

按源242层展开：A_plain178、A_gate8、F210、D24、H32、X32，共484个逻辑子层调用。机器表保留完整242层的零基层号和准确变体序列，以上数字不是instance count、native任务数或ROM字数。

## 6. H整体与两分支拆分备选

面积优先主基线是完整H七类各1。若确有并行吞吐需求，可以讨论两个**不同于普通A的**包装：

| 拆分部分 | M | N | E | G | R | S | T | 责任 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| H_Attn_owner_wrapper | 1 | 1 | 1 | 0 | 0 | 1 | 1 | 保存X；唯一shared input RMS2560；将同一N fork到两路；Attention分支；接收scaled SSM返回；join后residual1 |
| H_SSM_branch | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 只消费归一化N；SSM投影/conv+bias/dt/state/门后global RMS/Wout/ssm_out；不重复input RMS或残差 |
| 拆分合计 | 2 | 2 | 2 | 1 | 1 | 2 | 2 | 共12叶 |

相对完整H增加M/N/E/S/T各1，G/R不增加。inputNorm与join留在Attention owner包装，因此不必再额外设第三个NormJoin大Block。若选择另一种外置NormJoin结构，必须重新计数，不能只列两分支却漏掉共用工作。

H_Attn_owner_wrapper不是完整A_plain：它等SSM同token返回再做混合残差；H_SSM_branch也不是完整H。新的回传接收、分支holding、版本/任务保留、真实MEM与无等待环控制必须预制，不能把另一大Block的data直接接到原A接口就声称闭合。两颗M只提供潜在分支重叠条件，实际加速/面积代价未测；单M完整H仍可按固定合法顺序串行，源共享Norm和Add顺序不变。

## 7. 这不是完整LLM的BOM

本表覆盖对象严格是仓库**8样本/10种decoder层型**的子层需求类别。原图验证为代表层B1/S2/FP32/no-cache，并未导出完整网络、带历史decode、embedding、RoPE频率/mask生成、最终Norm、LM head、采样/停止。Llama源图还是配置重建/随机参数；Granite别名需绑定真实权重。不能将五profile写成已覆盖整LLM。

| 外围共享服务 | 可讨论的复用方向 | 仍未证明/设计 |
|---|---|---|
| Embedding | MEM索引/gather、S/T；lookup不天然需要M矩阵乘 | token ID/词表/权重格式、地址/容量、输入工作流 |
| 位置频率与mask供给 | 固定表/位置索引和已接收算术/布局 | LongRoPE/Llama3/MRoPE实际规则、范围与数据服务 |
| 最终Norm | 已有N/E/S/T按预制程序时分服务 | 真正最终层权重/epsilon/格式/输出协议；不推导必须独占新增N Block |
| LM head | 复用M/E/S/T投影服务 | 全词表形状/格式/完整K累加、logits存储/吞吐，不推导必须独占新增M |
| Sampling/logit transform/stop | 按真正greedy/TopK/TopP/temperature/penalty策略设计共享程序/算术 | N TopK<=40条且ID16bit不能直接等同大词表采样；N group<=65535；R是递推算子，不是sampling RNG；是否需要G/NUM由真实算法细化 |

这些外围可与已有资源时分，或冻结前预制共享服务，但本轮没有给未经验证的独占物理Block数量。相关数量在JSON中为null，而不是0或强制再造一组MNE/S/T。系统有外存，本轮暂不研究其接口与调度，仍须在有源底座冻结前闭合供数/完成/容量/故障依赖。

## 8. 机器表与实际检查

`build_block_variant_models.py --root <checkout> --output-dir <独立目录>`只依赖已提交的FamilySpec、coarse-model-map、phase2-source-lock及锁定14核心源码。`--check`逐字节重算，不修改目标文件。它生成：

- `block-variant-models.json`：六变体×七宏的明确整数count、每宏用途/op与compute/lifecycle类别、8模型/10层型完整分配、复用池/资源并集例、H拆分比较、外围未覆盖与限制。
- `block-variant-model-checks.json`：实际研究一致性断言、源指纹数量及产物SHA；不是RTL或最小硬件证明。

当前313项研究检查通过，保留真实H/I/头维度和所有Norm源字段、242层序列、484逻辑调用；14核心源码SHA与7078786 source-lock匹配。管理结构检查通过，单独不提供业务资格。没有运行本轮RTL/SystemC/推理/服务器/EDA；P2的一段MST有限RTL证据不转移成这些完整profile通过。[FamilySpec](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/a37e37cad757af5bfc94ed65db3e2e728023c251/work/Melodydt/151/family-spec.json)、[既有粗映射](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/a37e37cad757af5bfc94ed65db3e2e728023c251/work/Melodydt/151/coarse-model-map.json)、[源锁](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/a37e37cad757af5bfc94ed65db3e2e728023c251/work/Melodydt/151/phase2-source-lock.json)。

```powershell
python -B -X utf8 work/Melodydt/151/build_block_variant_models.py --root . --output-dir work/Melodydt/151
python -B -X utf8 work/Melodydt/151/build_block_variant_models.py --root . --output-dir work/Melodydt/151 --check
```

所有推荐数量仍依赖真实数值lowering、单owner串行调度与MEM/NUM/状态/布局服务；完整LLM程序和物理接收未完成。源真实尺寸没有缩到S/T能放下，也没有用缺实现缩小语义合法集合。
