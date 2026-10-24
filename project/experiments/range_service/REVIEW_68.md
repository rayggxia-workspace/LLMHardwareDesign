# Issue68 科学结论与划分边界复核

2026-10-24，Asia/Shanghai。只读审查截点：R双轮、独立接收与checkpoint结果已返回；正式V/R/S全网格尚待执行/接收。本文是该截点的证据与表述审查，不替代最终实验报告。未操作远端、未启动服务器或重跑真实数值。

## 可以使用的R结果

已核本机返回的结构化结果、两轮结果JSON的SHA，以及独立接收回执。每轮是4个native源条件×3种policy共12条件，以及6个真实256步legacy窗口×4种格式×3种policy共72条件。不能把格式组合数量当成模型、独立序列或全生命周期数量。

| 来源与policy | 完整执行的源条件 | 中止的源条件 | 已发布state饱和 | 重编码波次 |
| --- | ---: | ---: | ---: | ---: |
| native32，static_sat/static_guard/guard_rescale各自 | 4 | 0 | 0 | 0 |
| legacy256，static_sat | 24 | 0 | 1508 | 0 |
| legacy256，static_guard | 16 | 8 | 0 | 0 |
| legacy256，guard_rescale | 24 | 0 | 0 | 16 |

native32中三种policy都没有触发guard，输出与状态相同。这证明未触发路径一致，不能把它称为新独立数据对重定标恢复的验证。legacy是已有观察窗口的诊断，不是重新采集的独立质量集合，更不能把不同窗口接成完整8192步整数轨迹。

预先固定的layer0/end8192、S32/D31窗口具有以下可复查结果：

- static_sat完整256步，保留193次state饱和。输出相对RMSE约0.048214%，小输出误差不能掩盖范围失败。
- static_guard已提交3步，在0起始token索引3，即第4个token拒绝；已发布state/scale/epoch/version不变。它是正确执行拒绝协议，不能写成256步范围通过，也不能以已发布饱和为零宣称完成。
- guard_rescale完整256步，两次因果重编码，单位由`[-27,-33]`变为`[-27,-31]`，epoch为2，零已发布饱和。输出局部RMSE约0.047241%，末态对FP64参考RMSE约0.063166%。
- 该S32恢复额外对32768个cell做RNE，产生131072B读和131072B写，即262144B重编码读写。这个数只包含重编码，不包含完整重试、整group trial初始化、旧/新generation、分页、输出二次读取或元数据总成本。

同窗S16/D31也消除了已发布饱和，但输出RMSE由约1.016081%变为1.016631%，略有增加；末态误差仍约2.24844%。因此“消除饱和”“局部精度改善”“应用质量通过”必须分开。所有质量验收标志仍为false，不应事后根据这些数字补设通过阈值。

全部24个legacy源条件的16次重编码合计读写1572864B，RNE262144个cell。原数值记录中initial/operand bridge clip均为0，观测到的I64/shift拒绝次数为0。后者表示该分支未触发，不是所有位宽、最大exponent或8次重试耗尽边界都已由真实数据验证。

独立接收对native evaluation S16/S32 D31完整32步及legacy layer0/end8192 S16/S32 D31完整256步的全部三种policy做Python整数重放，每个suite为6条件；其他数值条件检查双轮SHA。不能把其余条件称作独立完整算术重放。checkpoint的8/16及重编码边界接续通过属于同producer资格，和独立算术验证分列。

## 当前能收敛的划分义务

可以进一步固定R的**状态所有权与发布合同**：同一sequence/position/version拥有唯一已发布state；单位是状态的一部分；越界只根据当前整数proposal判断；失败不发布；只对失败head的旧state逐次RNE重编码并完整重试同token；state、output、units、epoch、version共同提交。只能读取已发布generation或明确定义的未发布trial，不能使用未初始化的其他head。

需要保留并计费的物理选择是：完整旧/新generation的保存位置、坏head重编码与未变head复制路径、scratch tile宽度、backing端口、宽算术服务位置，以及带单位的R输出接口。这些义务不要求所有递推乘法必须制造在独立R宏内；状态owner/controller与算术执行资源可以分开讨论。

S32是当前误差更低的工作参考候选，不是通用范围证明。增加S32位宽和动态扩大单位覆盖范围是不同措施：后者降低物理分辨率，必须继续跟踪误差及下游单位传播。当前整数R输出之后的gated norm、SiLU、Q/K归一化等仍未形成完整全整数消费者链资格。

## V/R/S服务必须守住的公平性

1. placement比较必须固定相同task fingerprint、全部整数步骤、动态单位轨迹、提交/恢复合同和完整输入。相同“S32”标签不等于相同数值合同；static和adaptive分别分组。
2. 同后缀的`shared2_6/shared4_4/shared6_2`与`split2_6/split4_4/split6_2`具有相同lane子分区、端口、路由和上下文时，逐节点资源与周期应相等。标签本身不得产生收益。单组织pilot没有跨组织配对，应报告pairs=0、差值未比较；聚合后才能核对配对。
3. `shared8`改变整池issue粒度与竞争方式。即使它在某种条件下更快，也不是独立R宏或V/R合宏的物理收益证据。
4. V的完整mixed row为25600B，超16KiB。plane→K128布局、finest-unit预扫、后续最大值扫描、重读或spill、gamma流、fresh A8码/指数/描述符均要入图，不能让已送走的tile使用未来才知道的全行最细单位。
5. S32的K128×V32 tile为16KiB，old/new加aux无法同时留在R32KiB。完整旧/新group还需backing；retry只重编码坏head之前，完整trial中其他head也必须有效。不能把软件copy、shadow或rollback当作免费SRAM。
6. 新状态的完整group guard通过之后才能消费其输出；分块输出要在完整K归约后统一RNE，完整V输出barrier后才提交。guard失败路径的饱和shadow只能未发布并丢弃，不能被后续输出读取。
7. SRAM 1RW、bus、TX/RX FIFO、源/目的对象偏移、初态strided打包、scale/epoch/版本元数据及完整宽乘合并都须独立核验。FIFO容量是额外有限库存，不应藏入“通信免费”的假设。

当前服务是两个独立真实流的有界竞争实验：norm32与R32或R256，不是同一连续LLM计算图。背景FFN/attention仅为共同代理负载。特别是norm32与R256的比例是压力配置，不能据此断言真实模型中V/R需求比或所有模型的最优lane配比。

## 为什么目前不能冻结制造级宏边界

本批先确立数值可执行和有限资源服务证据。服务周期、独立资源下界及有限候选最小值，都只对声明的S8多周期lowering、shift/add成本、sqrt/div迭代、store-forward包协议与EXT敏感度参数成立。它们不是实测RTL周期，也不是实际芯片的理论下界、全局最优、PPA或LLM端到端速度。

服务包含一次性captured state的row-major→tile-major迁移以及gamma初始化。生产系统也可从初始化开始使用tile布局，因此短窗总周期须区分cold迁移与稳定运行，不能直接据此选择制造边界。backing服务延迟、银行冲突和端口受压仍需检查真实瓶颈，而不是只看总payload减少。

物理归属最终还受时钟、线长、布线密度、端口实现、SRAM组织、宽算术面积与流水线、布局和共享资源的仲裁影响。本批没有这些完整物理资格，也没有可由局部误差推导出的应用质量门。因此合理结论是收敛到**有限物理候选和必须保留的接口能力**，不直接宣布R独立宏、V/R合宏或固定某种tile宽度已经最优。

## 下一步的最小决策集

- 完成正式服务网格、独立接收和跨label配对，按同数值task/commit合同分别比较tile16本地shadow、tile32+Sshadow、norm reread/spill及backing敏感度，保留所有失败与无收益条件。
- 由实际瓶颈选择一个小RTL/端口资格验证：宽乘合并/shift-RNE吞吐、有限SRAM 1RW、FIFO背压、或owner/epoch提交协议。先校准改变排名的参数，避免扩大模型矩阵。
- 后续数值资格针对真正未闭合的R输出消费者单位传播、受限寿命下的重编码误差预算，以及明确可恢复的guard失败路径。需更长真实输入时另行形成有界采集协议，不循环旧窗口伪造真实连续轨迹。

未发现需暂停全部工作的原则性冲突。应修正的重点是验收口径、服务资格及证据范围；在这些边界内，现有服务器并行工作可继续。

## 本次只读校验索引

返回根：`D:/Projects/Codex/range-service-20261024-1238/returned/`。以下是实际读取的文件SHA，不是尚未返回的服务结果：

| 文件 | SHA-256 |
| --- | --- |
| range-native01/02 的range-results.json（两轮相同，81265B） | `be35ef06944b8fa8e8aece55664ed4cea5c9655114123d5f3b51a39c11eb8866` |
| range-legacy01/02 的range-results.json（两轮相同，481524B） | `fa9023418f297516600d8f5bfbe5b406c1d299b05031d5f022761d5ea3e83392` |
| receive-native01/audit.json | `ef95b9f90e86916f3b043cd417d2e82100e843bdc0f6a790fd8b1cb5637ab6df` |
| receive-legacy01/audit.json | `31f5c3f8df4e49dc431c80f15608bf74a791fbe70c550d97b13a51c81f8da543` |
| chunks01.json | `0438ee159f3f068182932c93d372e01cc7285f675844bc8be74a1e0c95c63a80` |

两轮结果JSON均逐一对照其manifest的字节数/SHA。原始大NPZ未在本机重放；完整独立算术结论来自对应服务器接收回执，不能把本次只读汇总称作另一轮真实算术执行。
