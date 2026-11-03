# Qwen3 H1024/Q16/KV8/D128：Sq2 Attention片上程序候选

Issue151 / PR152；研究输入71c819c2。只写本轮drafts/attention，未修改旧40+新增4份RTL，未访问服务器、运行RTL仿真或推送。本轮交付的是容量/生命周期/循环候选及可复算静态checker，不是新A岛RTL或L5实现。

**结论：在选定S16数值profile、单token组Sq=Sk=2、无外部KV cache条件下，M1/N1/E1/S1/T1的串行候选可以把全部数据放进一个S16KiB和一个T6KiB。** 关键是把原始两行残差真实spool到T，S内同时保留完整Norm和完整8192B context；并不是只保存一个head就能免费累加Wo。静态checker得到S峰预约16384B、T峰4096B，11个负例拒绝。新local CTRL、T→S捕获/ACK、head布局重排与参数端点仍须实现并验证。

## 1. 真实模型语义与旧小切片的差异

锁定config为H1024、I3072、Q16、KV8、每head128，因此Q宽2048，K/V各宽1024；epsilon1e-6、theta1e6、无attention bias。历史导出config缓存注明transformers5.20.2；本轮另读官方v4.51.0建模源作为明确版本的语义参考，不能据此声称与历史导出软件逐bit相同。文件SHA列在checker结果，官方模型源Gitblob为`5fec83d47888e44a0f3e0ffb2b067ce08e4712d3`。

官方源要点：q/k投影reshape后各按最后128维做RMS（L195–196、217–219）；V不做head RMS；rotate_half把前64维与后64维配对（L98–102），GQA把每KV head相邻复制2次（L132–141），所以`kv_head=q_head//2`；QK缩放为128^-0.5（L179）；Y=X+Wo(Attention(inputNorm(X)))，F再取post_attention_layernorm(Y)并以Y做残差（L284–306）。不能把Q头128缩为8，也不能用H/Q=64推断本模型head_dim。

[官方建模源v4.51.0](https://github.com/huggingface/transformers/blob/v4.51.0/src/transformers/models/qwen3/modeling_qwen3.py)，[官方固定config revision](https://huggingface.co/Qwen/Qwen3-0.6B/blob/c1899de289a04d12100db370d81485cdf75e47ca/config.json)。本轮实际checker读取根任务提供的本地缓存，不执行或vendor整份建模源。

## 2. 物理资源候选及控制边界

| 类型 | 此构造选择实例数 | 用法 |
| --- | ---: | --- |
| M | 1 | rows2、最多4个K8 tile；顺序Q/K/V、QK、PV、Wo；全K最后才RNE |
| N | 1 | 复用N-long：2组RMS1024、48组head RMS128、32组prefix Softmax1/2 |
| E | 1 | 768次RoPE8和256次原残差add8 |
| S | 1 | 16KiB；全部阶段均不越界 |
| T | 1 | 先持原始X4096B，实际释放后再用于最终输出4096B |
| G / R | 0 /0 | 此Attention构造不使用；不能借它们当免费payload RAM |

这是可构造串行baseline，不是数学最小值、吞吐最优或已证明PPA。若共同底座已选择全七类岛，物理G/R仍在且本profile闲置，M11不能按产品删除它们。新local CTRL拥有head/group/chunk、N/E服务与S/T生命周期；未来母控只发粗任务/entry及预约依赖，不逐条调度三万条M命令。L5尚未开始。

另显式预留256bit新layout holding（两S字的split-half/V转置捕获）和64bit M半行holding，及真实控制/MUX/计数/参数身份逻辑；不假定能从现E/N controller内部免费引出私有holding，也不把320bit视作完整CTRL成本。所有有源布局/解析/保持须预制，不能留给M11金属创造。

## 3. 一S一T的阶段布局与生存期

初始输入448个S16字、7168B：X0在0..127、X1在128..255、H gamma在256..383；Q/K gamma与两位置系数先在512..575暂存，共64字。Q/K gamma各128项，RoPE canonical系数两位置各128项。这个固定输入/参数映射是新候选，不是现F1024/A16的host帧ABI。

1. **保存原残差**：真实T BEGIN256，按组g=0..127写`T[2g]=X0[g]`、`T[2g+1]=X1[g]`，每字来自实际S读取/捕获；完整写完COMMIT。T进入READ_HOLD，整个head计算期间read_take=0。256字4096B小于384字容量，但剩余空间不能再开第二事务或并发写结果。
2. **完整输入Norm**：N0 src0/gamma256/dst384，各128字；N0完成且原X已spool后，N1 src128/gamma256/dst0。三region互斥，N1覆盖的是已无S消费者的原X0。最终Norm0在384..511、Norm1在0..127，无需全Norm复制。
3. **参数转位**：N1写ACK完毕后，X1/H gamma都结束S生存期。真实读写64字，把暂存512..575搬到128..191；然后才允许context覆盖原暂存区。Q gamma128..143、K gamma144..159、coeff160..191。
4. **逐head计算并完整保存context**：下表整阶段恰预约1024字，没有再借一片S。

| S字地址 | head阶段内容 | 字节 |
| --- | --- | ---: |
| 0..127 /384..511 | Norm1 /Norm0完整1024维 | 4096 |
| 128..159 | Q/K gamma各128维 | 512 |
| 160..191 | 位置0/1 canonical cos/sin | 512 |
| 192..223 | 一个KV head的两token Kraw→旋后K | 512 |
| 224..255 | 同KV head两token V | 512 |
| 256..287 | 当前Q head两token Qraw→旋后Q | 512 |
| 288..319 | Q/K head RMS目的scratch，和src/gamma分离 | 512 |
| 320..335 | 4tile、rows2 A512容器 | 256 |
| 336..367 | B16 staging512B；B8仅用前16字 | 512 |
| 368..373 | score2字、exact EXP2字、P2字 | 96 |
| 374..383 | 明列备用scratch | 160 |
| 512..1023 | 两token×16heads×128维完整context | 8192 |

work128..383共4096B，Norm4096B+context8192B+work4096B=16384B。context地址为`512+token*256+q_head*16+channel_group`，512个字全部实际产生一次后才准许Wo；不能把未写的其他head当zero。

5. **Wo与原残差**：完整context建立后才能释放Norm。Wo每8个H输出采用rows2、64个K32 chunk，全部2048维归约完才读出，分别保存到工作字256/257。然后消费T当前两字，先X0[g]再X1[g]，每字必须捕获并真实写S258后才发E0；最终写token0的S[g]、token1的S[384+g]。下一Wo组只能在这两次E服务ACK闭合后复用。T单向顺序恰与初始交错spool一致，不需要随机读或S64 context restore。
6. **重新封装输出**：最后原X字已消费且最后残差写ACK闭合后，实际T RELEASE；然后BEGIN256，从S0..127/384..511按token-major写最终Y，COMMIT/DRAIN/RELEASE。总共两次串行T事务，始终只有一个T实例。前缀输出被host接受后错误/abort不回滚。

## 4. GQA/head循环与实际权重流

依kv_head0..7：先投影该K/V head的两token各128维，K分别head RMS128及RoPE；保留K/V512B+512B。随后执行q_head=2kv_head和2kv_head+1，每个Q投影→两组RMS128→RoPE→rows2 QK→prefix Softmax count1/2→16组PV输出context。两个query heads完成后才能覆盖该KV缓冲。V轴保持原通道顺序，不对V做split-half重排。

这用循环复用KV，并非物理复制成16份。两token无cache prefill的K/V来自本次X投影，不需要外部KV历史输入；真实decode/更长context必须另有KV容量、版本、读写与故障合同，不在此证书。

| 实际参数 | 形状/所选容量 | 供给要求 |
| --- | --- | --- |
| Wq | [2048,1024] S8，2MiB | 每head128个输出；rows2复用同chunk权重 |
| Wk/Wv | 各[1024,1024] S8，各1MiB | 每KV head只投影一次，供相邻两个Q head使用 |
| Wo | [1024,2048] S8，2MiB | 完整16head context后2048维归约 |
| input_layernorm gamma | [1024] S16，2048B | 完整输入RMS，和F的postAttention gamma不同 |
| q_norm/k_norm gamma | 各[128] S16，各256B | 官方共享head维权重，跨各自heads复用 |
| RoPE位置参数 | positions[0,1]、theta1e6及canonical512B系数 | 必须由真实规则供给，不能套旧theta10000/相邻原轴 |

projection权重共6MiB，24576个256B chunk、393216个128bit拍，不能把训练tensor或整个权重镜像默认放进16KiB。可复用F1024的有序chunk/版本/ACK思想及原生M/Sloader端口，但需新的四矩阵Q/K/V/Wo端点语义/有限控制表和真实参数镜像，不是现F1024程序已经支持Attention。系统有外存，实际MEM/地址/带宽控制器仍未实现或评估。

## 5. 数值和layout必须补齐的内容

- Q/K每head128做完整RMS，不能一次按2048维，也不能拆RMS8。复用N-long范围即可，src/dst/gamma互斥。A rows2每tile后两字共8字须真实初始化zero。所选Fin10下epsilon_code1=2^-20，和source1e-6有约-4.6326%参数相对差，输出质量未知。
- 源RoPE为每head128维、half64，**不是256维旋转**。先把Norm输出索引`[0,64,1,65,...,63,127]`真实gather成相邻pair，再E9/shift14，每8值一个服务。源cos/sin各128项由`emb=concat(freqs,freqs)`重复半区，故canonical每token64对cos/sin=128项，两个token共512B；这种去重复须保留源码证明。只接受位置0/1的候选；任意position、dynamic/partial RoPE未支持。
- K/Q使用相同维度置换，因此QK dot不变；V不置换，PV的128通道context仍按原V轴拼head后接Wo。需要真实K/V宽B布局：QK每K32 chunk中两key列有效、其余六列写zero；PV每8输出通道列为`[V0[n],V1[n],0,...]`，不是裸接S compact向量到B512。
- QK使用D128的1/sqrt128：候选nativeM factor2896（Fin15）、最终RNE25，score S16Fin10，scale相对误差约-0.0106817%。不能沿用D8因子11585。QK rows2/tiles4/N2第一EXEC0x14287、后续0x14283，四chunk完成才读index0/8，明确只取前两score并置尾零。
- Softmax两row真实count1/2排除未来key，不把未来score0加入分母；exact EXP为U16，P为非负S16 Fin14。PV rows2/tiles1/K2/N8可用0x11827，最终RNE14回Fin10。QKV/Wo rows2/tiles4/B8第一0x14885、后0x14881；默认Fin7权重时最后RNE7。

选定S16能装入不等于训练量化质量已接受。若真实诊断要求S32/FP32、更长seq或额外持久scratch，本证书会失效，必须重算，而非自动借R/MEM/其他岛。

## 6. F1024 per-matrix power2尺度源审结论

原生M已有signed16 factor、左移0..31（SCALE cmd_data[20:16]）和READ右移0..63（[5:0]）、S16输出宽度码1；先raw全K累加、最后RNE/clip。设A码Fin=Fa、W实值=Bcode×2^-Fw、目标输出Fin=Fo，factor1时需要`R-L=Fa+Fw-Fo`。Fa=Fo=10时，Fw8→READ0x108，Fw6→0x106，Fw=-4→SCALE left4及READ0x100；这些不需新增M算术datapath。

但**当前不改的F1024顶层不能选择这些新尺度**：源码L234–236固定SCALE1、READ0x107，所有matrix相同；weights_version仅身份tag，无指数配置/ROM选择。只换provider内容/版本不能修改实际执行shift。下一新top可以预制按matrix选择的有限常量/ROM与路径，并复用现有M能力，仍属于新控制RTL与再验收；M11不能凭空增加该译码/MUX。若保持每次M输出Fin10，则G的SiLU及gated RNE10、E原残差单位可保持现数值合同。

字段合法还须S64范围合法：K3072、|A|≤32768、|B|≤128时left30最坏和超过S64，checker拒绝；更高Fw导致READ超过63也不能由该native字段免费表示。per-channel八个不同scale不是单一M scale lane的per-matrix方案，不在此结论中。真实trained矩阵应先给出量化尺度/饱和与误差门，再冻结有限profile。

## 7. 可复算检查与当前结果

本轮实际执行（仅Python3.7标准库）：

```powershell
python -B work/Melodydt/151/qwen-numeric-71c819c/drafts/attention/check_qwen3_attention_plan.py --root work/Melodydt/151/qwen-numeric-71c819c/integrated --config work/Melodydt/151/overall-drafts/steps123/family-sources/qwen3.config.json --model-source work/Melodydt/151/qwen-numeric-71c819c/drafts/data/upstream-modeling-qwen3.py --output-dir <新的独立目录>
```

config/model-source是明确读到的缓存；未vendor全建模源码，复跑者需取得相同固定源或提供其路径。默认结果保留布局、计数、实例配方与例子；`--emit-trace`可另存912个静态M组、82个N组、1024个E组、768个真实重排块定义，不是RTL周期trace或硬件实例数量。

当前结果 `qwen3-attention-plan-checks.json`（由checker-output-final4生成）：M EXEC24896、cmd30336，N2340命令，E1024服务，loader24896、宽读198144，S512个context字唯一覆盖，256个原残差按T顺序正确关联，最终256字token-major。按每RoPE块重新gather两S字的明确保守recipe，普通S期望806408=600424W+205984R；换用holding复用优化时必须重新给出生存期及计数，不能把该数写成已测。静态负例11个全部拒绝：活数据S重叠、Sq3、FP32、原X也留S、T未释放再开、随机跳读T、缺context、错GQA、错RoPE配对、提前M量化、字段合法但S64溢出尺度。

这只证明所列资源/程序合同自洽。下一步须结合真实tensor/FP32切口完成尺度和误差门，再冻结输入/供参/position ABI并实现新的本地CTRL、Tspool与布局路径，随后服务器验证完整realshape数据与错误/背压/恢复；不将checker通过写成A1024已实现、L5已开始或完整模型推理通过。
