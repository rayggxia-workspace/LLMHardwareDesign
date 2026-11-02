# L4-A-H2：完整H1024输入与D128共享KV的双Q头context

Issue151 / PR152，Melodydt；2026-11-03 Asia/Shanghai。输入a0610aff，实际源码 `70611916736ae547f7c25e7acbc100116582ab49`，归档父7436dc0d只整理历史。首轮r01/Slurm **95327 / node1 / c64 / 8CPU / COMPLETED 0:0 / 00:01:16**；Verilator5.042严格顺序32CASE及9份实际数据流SHA通过。此轮接收的是双头context切片，主线四仍未整体退出。

## 1. 相比之前真正补了什么

[ATSP](W4_ATSP_IMPLEMENTATION.md)只计算外部Wo切口与原X的残差；本轮走到Attention前半部，**从真实H1024输入执行input RMS→K/V/Q0/Q1投影→逐头Q/K RMS→split-half RoPE→QK→因果Softmax→PV**。没有缩H为8或D为8；两token、一KV头0供相邻Q头0/1串行复用，输出512个S16元素/64个128bit字/1024B context。

本轮输入和权重仍是独立生成的合成整数。实际流过完整512KiB的四个128×1024 S8投影矩阵，证明这个固定整数profile的真实尺寸/布局/数值/生命周期；不是官方训练checkpoint、整28层模型质量或系统吞吐接收。完整KV8/Q16、Wo、原残差、ATSP集成、cache/decode及其它样本变体尚未实现。

## 2. RTL、资源与控制的归属

新增[block_w4_ah2_top.sv](../project/rtl/block_connection_w4/block_w4_ah2_top.sv)和[独立TB](../project/tb/block_connection_w4/block_w4_ah2_tb.sv)，原48份RTL/TB/include全字节不变。实例为M1/N1/E1/S1，S内部仍含storage+loader；另有既有S helper、N-long controller、E controller。本切片不实例T/G/R，没有新独立bridge硬宏。

新局部FSM负责job/输入/供参身份、S唯一owner、M全K循环、N阶段、RoPE真实搬运、结果保持和错误终态；没有全芯片母控或L5网络。普通S口在local/N/E之间独占切换，LOAD阶段只有实际S feeder宽读供M，不能把普通口当额外RAM端口。M结果写S且ACK后才clear复用；N/E响应退休前不把S owner交给下一阶段。

顶层payload holding为三个128bit寄存器和一个64bit M半字，共448bit，无新的私有X/K/V/context或权重向量数组。原生宏及已有helper/controller内部holding另计；448bit不是整个岛面积预算。新增FSM/捕获/MUX/拆拼/版本逻辑是要在M1–M10冻结前预制的有源RTL，不是M11/M12可以新增的器件。

完整逻辑端口与生命周期见[AH2合同](rtl-contracts/AH2_PORTS_AND_LIFETIME.md)；它尚非物理M10 pin或产品控制ROM冻结。

## 3. 数据布局与实际同步

| 阶段 | 数据路由和完成门 |
|---|---|
| 输入 | job接收32bit generation/16bit权重version；448字含X0/X1各128、H gamma128、Q/K gamma各16、位置0/1系数各16。每字检查generation/index/last，实际S写ACK后推进；最后ACK后才start |
| 完整输入Norm | N0 src0/gamma256/dst384/count1024，然后N1 src128/gamma256/dst0/count1024；三region各次调用互斥，不按8维分段独立归一化 |
| 参数转位 | Norm两行建立后，实际将S512..575的64字参数搬到S128..191；Q gamma128..143、K gamma144..159、coeff160..191；之后才准context覆盖原参数位置 |
| K/V建立 | K投影到S192..223，K逐token完整RMS128到scratch288..319，再RoPE回192..223；V投影224..255，既不head RMS也不RoPE。两份KV只算一次并保持到第二Q结束 |
| Q0/Q1 | 依次把当前Q投影到S256..287，逐token RMS128到288..319；每个RoPE块实际读原前64/后64对应两个S字，448bit有限holding挑选并gather到S374，ACK后E9读取和旋转到当前Q区域 |
| QK | 两query/token的D128完整点积，四个K32命令累加；K0/K1两列真实填B16 staging，其余六列写零。最终读两score到S368/369，未提前把未来score清零 |
| 因果Softmax | token0 count1、token1 count2；N统计/EXP/求和/概率回放，exact U16 EXP真实存S370/371后ACK，再读回生成Q14概率S372/373；未来key不进分母 |
| PV/context | 概率作为两行A；每8个输出channel从原轴V的两个token字真实转置成B列[V0[n],V1[n],0..]。PV结果实际写S并ACK后才下一组；Q0完成后才Q1覆盖Q scratch |
| 输出 | 只读64个实际context字：S512..543和S768..799，token→head→channel-group；通过真实S读ACK捕获128bit并在背压时保持。最后host take才DONE |

Norm0在384..511、Norm1在0..127一直保活到全部选定投影结束。A staging320..335、B staging336..367、score/EXP/P368..373、gather374各有明确生存期；context使用未来完整A的地址公式512+token×256+qhead×16+group，但本轮只产生64字，其他14个头的context未生成，不能当zero。

## 4. 位宽相同之外还需兑现的数值/布局合同

固定候选Fin10、投影权重Fin7、epsilon_code1。RMS为完整group整数统计/开方/归一化：input count1024、head count128；不能沿用旧A16除8。code1代表2^-20，和源1e-6有差异，训练质量未接受。

投影M factor1，32个K32命令全K1024归约完成后才READ右移7/RNE/S16饱和。QK factor2896，完整D128四chunk累加后READ25，实现选定1/sqrt128整数近似；PV factor1、K2、READ14回Fin10。不能对每个K32块先RNE再求和。M op5两行结果carrier索引为0/1/8/9，四个S32容器各取低16位再拼；QK仅读0/8取前两score并置尾零。

四矩阵ID0=K、1=V、2=Q0、3=Q1，每个16输出group×32个K32 chunk，共2048请求。每请求16个128bit字/256B；**byte offset=64×tile+8×column+k**，t0..3/n0..7/k0..7，不是column×32+k。实际完整权重流每fixture524288B，三fixture同权重但分别核真实接受流SHA。S loader向M供A128和B512、B16两个half，不能凭128bit宽度相同省略布局转换。

RoPE原轴是split-half64，实际gather成[0,64,1,65,...,63,127]，E9/shift14配位置0/1、theta1e6的canonical cos/sin；K/Q同置换保持QK dot，V始终原轴，所以PV context接未来Wo时仍是正确V通道顺序。

## 5. 控制、错误与恢复边界

接单即有独立终态义务，部分输入/prestart取消也held errorDONE。输入448字和权重拍均检查身份/序号/last；只允许一个当前权重请求，坏/旧/未来tag或provider error在接受时直接失败，该坏拍不发S写。非WEIGHT_RX时w_ready0，不承诺无界旧流排空；外部provider须停止/协调后再接新job。version0也是合法tag，version在admission捕获，不是启动装载控制程序。

正常DONE释放后无需reset接下一job。错误协调reset M/N/E/S/helper/loader，清N poison和本地在途；不回滚已写S或host已接受输出前缀。done_words/partial记录实际输出数；硬reset取消任务而不补DONE。这个局部同钟域恢复不能替代L5/MEM任意late返回隔离。原生S无error pin，helper fault force只验证错误传播，不构成新增硬件检测能力。

## 6. 实际验证、计数与证据

[冻结TB](../work/Melodydt/151/ah2/ah2-tb-contract.json)绑定32CASE严格顺序、12 compile源+EXP include/数学依赖和9dump。真实检查包含逐阶段S写/读ACK、原生A128/B512实际排布、M完整归约/READ容器、N replay/count、E原半区gather、KV保活、因果性、权重/输入meta、请求/响应背压、最后权重ACK、真实loader/M/N/E错误、helper错误注入、取消/reset/前缀/正常恢复。

三个独立整数fixture为base/future_changed/boundary；仅改变未来X1时，实际token0两个头的32字/512B输出都bit保持，token1两个头仍可区分。boundary由真实input RMS触发clip，其余stage flags均实际计算。四个正常完整job（3fixture+末尾base恢复）检查全部计数；不声称所有fixture×全部故障穷尽。

| 每个成功完整AH2 job | 实际通过的断言 |
|---|---:|
| 普通S请求/ACK | 各85784（18220读/67564写） |
| M命令/响应 | 各2672；EXEC2088、READ388 |
| M/loader | load2088；A128拍16512、B512拍8320、S宽读16576 |
| N | 12服务、744原生命令/响应（2×RMS1024、6×RMS128、4×Softmax） |
| E | 96次RoPE服务/原生输入/输出 |
| 权重 | 2048请求、32768实际128bit拍、512KiB |
| 最终context | 64字/1024B |

S宽读16576中的A宽读8256不能混称A128拍数；两者是不同接口。全局混合统计为 `cycles=3382620 jobs=32 X=11653 Sreq=563555 Sack=563554 M=16671/16671 N=13049/13049 E=577/577 wreq=12814 W=204872 host=257 done=29`，包含早停及三次硬reset：32接单/29DONE、4×64+前缀1=257个host字；S有一个取消在途请求不等ACK，不能拿该混合总数替代成功帧对称断言。测试的10ns时钟及总周期不构成300MHz系统签核或整模型吞吐结论。

独立golden从数学定义计算，3072个完整K1024投影raw dot从实际tile-major字节另行重算；524288编码、327680个S16×S8分解探针、65536个S16重构、1025个EXP数学节点与冻结源、RNE/负例/因果/multihead探针通过。不是读取DUT输出当期望，也不声称所有native内部partial已验证。

每fixture实际接受input7168B、weights524288B、output1024B，9份dump在真实握手时按原序导出，长度/SHA与固定合同和golden全等。17份输入与Git及服务器SHA核对，63份生成fixture文件在运行前后核固定SHA，导出时9actual流再核。已实收14份轻量文本及归档SHA `390643fd368f460a74171d04748d003ecbee74e59fa010502f1e173e05db31a9`；原始数据/二进制/build留本人服务器。[实际回执](../work/Melodydt/151/ah2/evidence/runs/r01/results/run-receipt.json)、[证据索引](../work/Melodydt/151/ah2/evidence/evidence-manifest.json)、[交付检查](../work/Melodydt/151/ah2/final-checks.json)。

首r01即通过，无失败仿真或隐藏重跑。Verilator5.042/g++11.4.0/Python3.10.12，--assert启用、-j8构建/单线程仿真，所有命令exit0。保留28警告（11TIMESCALEMOD、14WIDTHEXPAND、3WIDTHTRUNC），仅-Wno-fatal，未关闭类别；非lint clean。新top只有timescale提示，无本轮算术位宽warning。旧RTL回归、模型推理/训练质量及EDA未执行。

## 7. 归档、位置与下一切片

Issue151原正文64972字符接近GitHub上限，已先提交并逐字读回[原文归档](../work/Melodydt/151/ah2/issue151-history-through-atsp.md)及[SHA](../work/Melodydt/151/ah2/issue-history-archive.json)，再整理在线当前入口；原要求/回执完整保留，不撤销验收门。

服务器yuzelu@10.129.166.172；`/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/ah2-a0610af-20261103`，input-r01/runs/r01，日志runs/r01/logs及slurm/zenanyan-ah2-95327.out/.err，实际submit-r01.sbatch和完整argv已留证。复跑须新input/output/job，不覆盖r01。源归档SHA与17输入清单见evidence/deploy-r01.json和input-r01/source-manifest.json。全部RTL仿真只服务器。

下一 **L4-A-FULL**：扩为KV8/Q16、全部8192B context，再Wo完整K2048和原残差闭环。必须将AH2局控与ATSP机制合并成单S/E/T资源/owner方案，并新验有限供参ABI、ROM/循环和T生存期；**不能直接并排实例化两个验证top，否则会重复S/E，不满足原单S/T条件BOM**。原ATSP和本轮AH2各自通过不等于它们已经整合。随后真实A→F、真实数据/质量与样本变体；仍L4，旧24GAP不放宽，L5通用母控/跨岛、D/H/X、MEM、M11产品绑定和共同底座物理分别待验。
