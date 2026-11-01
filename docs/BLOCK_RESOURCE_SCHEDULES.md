# 大Block宏种类及数量：可审查的串行基线与扩展条件

研究输入`a37e37cad757af5bfc94ed65db3e2e728023c251`，只读本轮integrated及其PR144固定`7078786`叶源。本稿给出**选定资源配置与带前提的构造性执行顺序**，不是算法最小实例数证明、完整映射或吞吐最优推荐。配套`resource-baselines.json`保留逐模型字节、循环算例、完整前提和源SHA，可由`build_resource_baselines.py`复算。

## 1. 主表中的数量可以作为哪一级承诺

顺序为M/N/E/G/R/S/T；每个物理宏实例有自己的原生上下文，profile只是该资源集合执行的有限程序。A_gate可涵盖A_plain模式，因此全芯片示例不再额外加一份A_plain。

| 大Block逻辑类型 | M | N | E | G | R | S | T | 七类叶宏合计 | S+T+双R bank底数 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A_plain 完整无query gate attention | 1 | 1 | 1 | 0 | 0 | 1 | 1 | 5 | 22KiB |
| A_gate 带query gate attention | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 6 | 22KiB |
| F FFN及归属本profile的Norm/residual | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 6 | 22KiB |
| X MoE | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 6 | 22KiB |
| D GDN | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 7 | 38KiB |
| H Falcon完整attention+SSM hybrid | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 7 | 38KiB |

这里1M是串行执行能力，1S/1T分别只给16KiB/6KiB的原生payload分片。N/E/G/R的实例数也以串行使用为准，不承诺原子profile每阶段同时运行。A_plain无G要求确实不包含query gate；F若改变Norm/residual归属，N/E需求可能变化，不能把这张表写成数学下界。

每块还需要局部CTRL/ROM、唯一原生owner、真实MUX/保持/拆拼、布局转换、MEM与NUM等资源；母控、clock/reset/PG和岛间互联另计。当前NUM仍有宽bias/inject、系数、MoE加权累加等缺口，MEM接口/带宽与完整程序也未实现。**七类叶宏合计不是完整硬件BOM**，不能把这些附加能力隐蔽进“一个控制器”。

## 2. 为什么单M可以串行，但必须有真实保存位置

原生M两个输入bank共享一份8×8 S64 merged结果；没有恢复merged的命令。每次EXEC最多K32、N8、rows8。构造顺序以q=1为保守参考，也允许最多8行批处理；N同时只拥有一个统计/回放组。所有中间数据必须在覆盖源之前保存到有容量、有写完成确认的S/MEM版本，不能使用逻辑handle代替真实字节。

### F：先完成mid，再逐8个Down输出重放

1. 对每个I输出tile（最多8列），在同一M上连续执行H方向K≤32的各段Gate，第一段clear，随后append；在该dot完成前不执行其他投影。读出、数值转换并保存Gate，确认写完成。
2. 同一M计算对应Up tile；G按位置与Gate配对。转换/门乘完成后把q×8个mid写到唯一MEM快照并确认，才覆盖对应结果。完成所有I tile，得到完整q×I mid。
3. 对每个H输出tile（最多8列），M只计算该Down dot：从mid快照重放所有I方向K段，首段clear后续append，期间不插入Gate/Up EXEC。
4. 读出并保存完整q×8 Down结果、确认，再复用merged计算下一个H tile。直到全部H输出结束才能释放mid；随后串行处理归属本profile的Norm/residual和输出。

该顺序不偷增M上下文，但需要完整mid的后备保存，且Down对mid重复读。以候选S16、q=1计，Qwen2.5 mid=22016B；q=8为176128B。H2048需256个8列输出tile，所以Down的mid元素payload读取合计5636096B/q1；这只是该种调度的mid读，不包括权重、padding、其他MEM或协议开销。

若把dot分成K32且输出8列，Qwen2.5每个q批次Gate/Up合计176128次EXEC、Down88064次，共264192次EXEC。q可以是1..8，这不是拍数，不含load/read/ACK/NUM；它说明这是一条明确但可能很慢的串行程序，不能据此推荐1M最优。

S可只保存一个装载/转换微tile，完整mid保存在真实MEM；不能因mid22016B超S，就随意宣布增加第二个S解决完整模型缓存。Native loader的K32、A/B均S16最坏装载区域为1024B（rows8时A512+B512）；q1因A的4字组padding为A256+B512=768B，而非只按有效元素计A64B。其余存活槽、对齐、响应、NUM状态仍须逐项做working-set账本，不能只看这一个数字便授予S1完整准入。

### A：score、EXP、P和PV均有明确生命周期

1. 先把需要的Q/K/V、gate投影及归一化结果保存；参考取一个query/head组，避免凭空增加N组上下文。
2. 对每8个key，M完成整个D方向dot才读出、scale/mask/转换并保存score。完成长度L的score快照；下一次QK覆盖之前已有分组数据受保护。
3. N STATS全组→FINALIZE；重放原score发N3，保存确切EXP代码并确认；N4得到factor；重放同组EXP发N6，保存P并确认，才能重建N下一组。
4. 对每8个V输出列，M只做该PV的所有L方向K段。P/V必须可反复读取；整个dot完成并保存后才允许其他QK/投影覆盖M merged。
5. 保存所有head的PV输出/concat，再做O投影和A_gate所需门控，以及归属本profile的Norm/residual。

候选16bit下，一个query的score、EXP、P各为2L B。按生命周期复用可选择score+EXP或EXP+P的4L B峰值；若三个区都保留则6L B，均另加Q/K/V、KV cache、PV/O结果及padding。L4096时4L=16KiB，已用满整个S；本基线允许放MEM，未声称能全放S。PV每次≤8列可在M内部累加，完成后要真实保存，不能把下一次QK与尚未保存的PV merged交错。

当前N组长≤65535。以上为L符合原生边界的条件构造，不能把配置131072等更长组简单分段各自Softmax后拼接；若要支持需额外算法/硬件证明。score量化、mask、缩放、RoPE、P/V单位和宽转换仍须NUM/数值合同闭合。

## 3. M2/M3怎样分配才有意义

| 方案 | 明确stage映射 | 必须保留的代价 |
|---|---|---|
| F：M2/S2，完整mid保存 | M0/S0先后算Gate/Up；M1/S1做Down；N/E/G/T以唯一owner共享 | 完整mid快照及每个H tile重放；若重叠下一q批次，还需额外版本buffer |
| F：M2/S2，按H tile重算mid | M0产生完整I方向的Gate/Up/G流，M1始终保留当前8列Down partial；完成后再换H tile | 每个H tile都重新产生mid；用计算/读权重替代完整mid快照，仍需有界K32/配对holding，不是免费免spool |
| F：M3/S3 | M0/S0 Gate、M1/S1 Up、M2/S2 Down；G匹配两个producer的对应位置 | Down仍仅一次覆盖8列；完整mid重放或按H tile重算仍二选一，不能因第三M出现就忘掉H>8 |
| M2/M3但S仍1 | 一个S loader通过预制A/B payload及ready MUX选择目标M，owner串行调度 | S只有一组A128/B512出口和有限私有读；额外M不创造额外feeder、S口或MEM带宽 |
| A可选M2 | M0为后继query/head算QK，M1对前一query的P做PV | N仍一次一组；保护完整P后才能N BEGIN下一组，需有界双版本score/EXP/P与PV保存 |

M2/S2的F七叶向量为M2/N1/E1/G1/R0/S2/T1，合计8；M3/S3为M3/N1/E1/G1/R0/S3/T1，合计10。若保持S1，合计分别7/8，但争用和新MUX都必须计入。S2/S3是所举独立feeder方案，不是必要最小值，MEM/NUM/全局带宽仍可能共享。

Down有`ceil(H/8)`个输出tile。若不保存完整mid而用M2/M3 producer重算，Qwen2.5需256次mid生产遍历；Gate/Up总EXEC从176128变为45088768，Down仍88064次。M3能把Gate/Up分给两台，但不能凭此声称总吞吐三倍；projection、G、feeder、MEM、NUM、输出重放与各stage服务时间需要同一目标下测量。

## 4. R1、N1等共享资源如何不偷换能力

D/H中的R1按逻辑tile加载、计算、保存并复用。GDN length128、8列使用4KiB active，32heads×16列tile=512个状态任务；SSM length256、8channel使用8KiB，亦512个状态任务。它们不是R实例数、不是整个profile全部任务数（conv另有自己的channel tile），更不是512拍。

完整GDN state2MiB、SSM4MiB，以及old/candidate与history等都在后备存储中。R没有shadow state导出，构造性状态导出顺序需要：保存候选output→本地R7 commit→op11读新active→写candidate MEM并确认→再OPEN下一tile。全job旧版本仍须保留在MEM，不能把不可撤销的本地commit当作全job发布或指望reset恢复旧值。状态版本根、NUM系数/inject、搬运与完整D/H程序均未完成。

N1可以依次承担Norm、Softmax和TopK，但上下文切换前要保存并完成依赖；不能把两个未完成组同时塞进一个原生N。X还要保留原40个router score（候选S16为80B），TopK返回的是ID（8个16B），再gather真实selected score并Softmax，不能把ID当概率。8个expert可逐个执行和merge；若同时保存8个H1536返回，S16也需24576B。顺序NUM宽累加的H维S32候选为6144B，可放MEM按片更新；该NUM功能、精度和存活区必须另行实现证明，不把R0/一个E当作已提供任意宽累加。

E1/G1可通过操作/函数阶段复用，未用op不等于可删掉整套宏；但独立闲置部分真实存在，裁剪须预制前形成变体并验收。当前数量表既不暗中裁剪叶宏，也不将多个owner直接连到一个接口。

## 5. 全芯片复用的两个示例与更小串行参照

| 物理资源安排 | M | N | E | G | R | S | T | 合计 | 显式S/T/R bank底数 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 一套B_state全七类，全部profile时分 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 7 | 38KiB |
| B_nonR六类＋B_state七类，两包时分 | 2 | 2 | 2 | 2 | 1 | 2 | 2 | 13 | 60KiB |
| A_gate/F/D/H/X各一个独立功能实例 | 5 | 5 | 5 | 5 | 2 | 5 | 5 | 32 | 142KiB |
| 五个全七类岛作为对照 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 35 | 190KiB |

13实例方案中，B_nonR可时分A_gate/F/X（也能A_plain），B_state可时分D/H；七类均在B_state，因此它也能串行覆盖其他profile。事实上，一套B_state七类就是更小的功能参考，说明两包13并非功能最低必要。选两包或更多包的理由应是实际并发、流水、带宽、状态局部性与目标时延，而不是五个profile就必须五个物理块。

32相对35只减少3个R，其他七类计数不变；active/shadow数组差为3×16KiB=48KiB。它不是面积节省百分比，也不含局控、MUX、clock/reset、MEM/NUM等成本。13与32的并发能力、服务时间和路由不同，不能按实例总数直接宣称同等吞吐更省。

完整H本身可M1/R1串行。若把H拆成独立plain-attention包和state包，示例计数为M2/N2/E2/G1/R1/S2/T2，共12，而不是通用B_nonR+B_state的13；原因是前者plain attention不含G，后者nonR包要支持A_gate/F/X。若还共享N/S/T等，必须显式增加跨包MUX/owner与调度，不能把两个包的驱动并到一个宏来“免费省”实例。

## 6. 本轮可复查结果与下一步

脚本已核对八模型的H/I与来源，输出1M矩阵循环、mid存储及重放字节、M2/M3重算次数、全芯片7/13/32/35计数与bank底数。实际未修改RTL，未执行仿真、服务器、综合或PPA评估；当前baseline仍有明确MEM/NUM/程序/数值和路线缺口。

```
python -B -X utf8 work/Melodydt/151/build_resource_baselines.py --root . --output-dir work/Melodydt/151
```

下一步应先给出性能/批量/序列目标与MEM条件，保留主表作为串行参照；再选1M、M2/S2、M3/S3等少量候选，在同一数值/生命周期合同和完整存储账本下做真实调度/RTL验证。只有这些证据足够，才决定制造前的宏实例数量和删宏/复制策略。
