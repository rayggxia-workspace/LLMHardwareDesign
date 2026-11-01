# 六配置的连接角色与共享物理路线候选

Issue151/PR152，负责人Melodydt。研究输入固定`051fddb9a3d2cecd4b76c43d07ec8581db9402ce`，叶源`707878621b2add4ed218b8c43df2e95c9a56e2ba`。本子任务只列所需连接、数据角色和同步规则；实现状态由独立证据审计提供。本轮不改RTL，不运行仿真/服务器，不写远端，也不因端口兼容、角色表或静态检查就标一条路线已完成。

建议用**S中心物化＋有限capture/gather/dispatcher固定网络**作为面积优先串行参照，保留S内loader→M的A128/B512专用路径。M/N/E/G/R之间存在算法数据依赖，并不要求为每个有向宏对各铺一条直接物理总线。这里不提出49对全互联。

## 1. 两层表的口径

机器文件`island-variant-routes.json`将每条依赖拆成：生产/消费角色、格式/布局、等待/释放条件、候选物理hop ID；并另列共享物理路线目录。**逻辑M→N若展开成M→capture→S→gather→N，不能再算为一条已直连的M→N**。E/NUM的算法运算必须单独存在，S搬运/字段选择本身不提供任意数值转换。

每variant的角色表是其所覆盖源模型/层选项的并集，不是一段无条件执行所有行的程序。例如A_plain内Qwen2.5需要bias→RoPE，Qwen3需要QK RMS→RoPE，两者不能同时机械套用。准确层表、Norm/residual归属沿用已提交`block-variant-models.json`；本稿不缩真实H/I/头数/状态，也不改变五profile/六配置及单owner调度前提。

## 2. 候选物理hop：只在端点处适配

| ID | 实际端点路径 | 必须做的工作 |
|---|---|---|
| P_IN | 外部/其他岛/MEM/参数payload→输入holding→S普通写 | X/Y、权重、gamma、bias、cos/sin、state/history、expert数据都有真实来源；等待S写ACK后才可供计算 |
| P_SR | S普通读响应→有限operand gather | 先抓到自己拥有的槽，再take S响应，然后才能发下一S读，避免占响应等第二读 |
| P_ML | S内loader→M A128/B512 | 对齐描述符、A每行128bit容器、B n-major `8*n+k`，S16 B half0后half1；done只说明已装入M |
| P_N | gather/命令formatter→N data128＋aux128 | 原值、gamma或EXP的角色/顺序和count正确；op/param/count保持到握手 |
| P_E | gather→E A/B/C各128 | 最多三路独立operand，支持分拍S读后同时提供；不用的C给明确常量，不误用FMA单位 |
| P_G | gather→32bit pair serializer→G x32＋linear_gate32 | 两来源按同token/head/lane配对；两lane发出/退休计数、尾lane有效性和输出拼包 |
| P_R | gather或CTRL metadata formatter→R cmd_data128 | 按op/index选择state/key/query/x/params/history/taps或OPEN/EXEC/COMMIT元数据；不能把张量当任意命令 |
| P_NUM | gather→真实NUM端点 | 系数Exp/inject、宽bias、宽归并等；128bit只是运输chunk参照，内部算术位宽与协议未冻结 |
| P_IDX | gather→有限layout/index端点 | Split/Transpose/Repeat、动态ID/gather、实际地址计算及范围/身份检查，不是只改软件标签 |
| P_CAP | 各计算结果/NUM/IDX→选中源capture/pack | 真实MUX与holding，不可短接push-pull输出；按当前op分类张量/ACK/ID/统计等 |
| P_SW | capture/pack/layout→S普通写 | 整字写、尾字独占/组装、写ACK、成功后数据可见性 |
| P_TW | capture/pack或gather→T顺序写 | 先BEGIN，正确word_count/index，完整/检查后的chunk最后写自动SEALED |
| P_TO | T读→common egress→外部/MEM或S输入 | 单一选中sink、保持data/index/last，真实stored ACK；末TAKE后RELEASE；回S需实际base+index检查 |
| P_MO | S/gather→common egress→MEM写 | 中间值、privateNext state/history可走MEM staging，不要求把T commit冒充持久根发布 |

这是14类候选hop/服务端点，不是14条已实现总线，也不是最小线数/缓冲数证明。不同variant只接其实际存在的计算源；A_plain的capture不需要G/R源。MEM真实地址/宽度/仲裁/请求/返回/ACK仍暂缓研究；这些行表示不可缺的供数/完成依赖，不表示已有现成MEM控制器或无限带宽。

最简单串行基线可同一时刻只允许一个计算响应源进入公共capture，但必须仍能独立排空S写ACK、已接收的原生响应、loader/done和将来的MEM返回。若允许多源在途，须增加真实有源仲裁/多槽及证明。S内wide loader与普通口共享bank，不能给S假造独立读口；可先固定不冲突时间窗，再评带宽并发。

## 3. native载体决定的同步/拆拼

- **M**：op3为2×S64；op5即便选S8/S16也为4个S32容器。已授权op5 S16可证明提取低16位；否则按实际单位用E13覆盖的S32窄化或NUM/专用分解，E13不能吃S64。ACK/EXEC故障mask不能写成张量。不同投影间先存结果；M两输入bank不是两结果上下文。
- **N**：data与aux各128，Norm原值和gamma要匹配；Softmax需score统计→原score算EXP→保存EXP→factor→EXP概率回放。op3的UQ1.15 EXP、op6的Q14 probability不是同格式；op7统计混合record、op10 TopK IDs、op11 factor都不能作为同种128bit张量转发。N count4可直接消费E13四S16半包，不必强制合八元素；完整逻辑组、有效数和max/factor上下文必须保留，65535界限不能静默截断。
- **E**：最多A/B/C三份128bit，公共gather可按最大3槽参照，但实际计数/元数据/缓冲预算由实现另定。E9处理相邻pair；源half-vector RoPE要先交织x1/x2及cos/sin，再还原布局，部分RoPE旁路通道不能丢失。op13只低64为四S16、高64清零；目的要求紧凑8S16才合并两半。E3的C是乘积单位S16，不等于任意未缩放残差。
- **G**：x与linear_gate各32bit，不是一个通用128bit输入。先捕获两路来源的word再按pair发，不能占着S第一路响应等第二路S读。原生没有count/mask，wrapper须处理尾lane、pipeline issue/retire、同版本配对及拼包。fn1 ungated输出Q14，fn1 gated乘积右移14后输出Q10；其余gated右移10输出Q10，不能只看fn判格式。
- **R**：op12输出、op11 active、op14 history每包4S32；key/query是8S16 Q14，x/state/history是有声明F的S32，decay/beta是UQ1.31。**R→N/G没有任意合法的裸连**；须证明单位/范围并做合法窄化，E13只覆盖可接受的S32→S16子集，其他需要NUM/已证明分解。JSON给出条件适配hop展开；“经过S”本身不能改变尺度。
- **S/T**：普通S写也返回ACK（dout=din），必须消费；不要把ACK回灌计算链。T是384个不透明128bit字，batch last不等于逻辑tensor末元素；大tensor分片、valid-byte/element计数及全job完成在外层。T不能一字并联给不同延迟消费者后OR多个take。

参数也有线路：op/shift/count、M factor、R owner/epoch/position等可以来自稳定预制ROM/本地控制表；gamma、bias、cos/sin、动态系数、权重和状态payload可由真实MEM/S或已预制可稳定供数ROM提供。动态NUM因子写入命令字段须经过合法范围/单位/版本快照，不是任意tensor可直接驱动控制端。编译期能证明role/layout并不删除这些实际MUX、地址、计数和握手。

## 4. 六配置的必需角色路径

下表的箭头是**算法角色**，统一按前述S/capture/gather、必要E/NUM适配来运输；不意味着箭头两端已有直接物理线。

| 配置 | 主要operand/结果路径 | 必须保留的回放、配对与次序 |
|---|---|---|
| A_plain | 外部X→N(input Norm)→M(QKV)；M/E→N(QK Norm如有)→E(RoPE)→M(QK)→E(scale/mask)→N(Softmax)→M(PV)→存储→M(Wo)→N(postNorm如有)/E(residual)→T | Qwen2.5 bias在RoPE前；Qwen3/Gemma头Norm；Phi融合/部分旋转；Gemma Wo→post-attn RMS0→残差；score与EXP分开保存，KV按共享头/正确位置可见 |
| A_gate | A主体，另M(Q_gate Gate)→G.x，M(PV context)→G.linear_gate，G(fn1 gated)→M(Wo) | 每head Q/Gate精确split；Sigmoid门在PV后、Wo前，不在QK前；同token/head/lane到齐 |
| F | N(preNorm)→M(gate/up)；gate→G.x、Up→G.linear_gate；G→M(down)→N(Gemma postNorm)/E(scale/residual)→T | 单M先存gate/up/mid；Phi fused gate_up split；Gemma GELU_tanh及down后RMS0；Falcon gate MuP在SiLU前、down后gain再残差 |
| D | N(input RMS0)→M(qkv等)→R(conv)→G(SiLU)→布局Repeat→N(Q/K L2)→R；另Q经E独有缩放；M(Z)→G.x；R(readout)→N(RMS128)→G.linear_gate→M(Wout)→E残差→T | 实际Repeat16→32再L2，head=floor(vhead/2)，epsilon未知；K不额外Q缩放；**先每value-head RMS，再SiLU(Z)门**；beta/decay真实NUM/格式路径 |
| H | 一次N(input RMS)共享给Attention/SSM两路M；SSM M→E(MuP)→R(conv)→NUM(bias)→G(SiLU)→R(state)；M/E(Z)→G.x，R(readout)→G.linear_gate→N(global RMS4096)→M(Wout)；E两分支join再残差→T | K pre-scale与QK scale不同；conv bias在SiLU前；dt Softplus后源Clip再NUM；**先Z门乘，后跨4096 RMS**；共享输入Norm不重复；单M固定串行物化分支并保存 |
| X | N(preMoE Norm)→M(router40)→N(TopK IDs)→IDX；IDX按ID取原M logits→N(Softmax8)；MEM所选专家weights→M，gate/up→G→M(down)；M return＋N probability→NUM(wide merge/gain)→E residual→T | TopK只ID，必须真实selected-score gather；专家ID/rank/probability/输出关联；8rank到齐；M结果先导出再覆盖；不把E16 FMA当宽WACC |

D/H还需要真实的MEM↔R state/history/coefficients/taps路径，不仅是上表的计算主线：conv op12先保存→op7本地history commit并等COPY→op14导出/ACK；state按old root恢复，SSM op15 decay预载并满足全部原生param_valid/loaded guards，EXEC后保存output→commit→op11导出/ACK。完整next root发布需覆盖全部tile/history和规定下游门；R本地commit、T commit、MEM ACK没有天然联合原子性。

所有配置都包含实际weights入口、参数入口、中间值MEM staging/reload和T输出排空角色。输入不能只写一个“tensor in”而忽略gamma/bias/cos、K/V、专家权重或状态；输出也不只是一个无定义done。大shape/完整state不缩到S/T能装下；MEM未实现时完整映射仍保留gap。

## 5. 逻辑宏对并集与真正的自环

JSON每配置给出`logical_compute_pair_union`（只统计M/N/E/G/R五种计算端点的角色邻接），以及所有172条角色记录，包括NUM/IDX/MEM/PARAM/S/T。六配置的计算宏对并集为21个，**它既不是21条直接物理线，也不是全合法连接覆盖率**。NUM、IDX和MEM数据边另有明确记录，不能因不在“五计算宏对”计数里就忽略。例如X需要E做最终残差，但其输入来自NUM，故只看计算宏对表不能推出E未使用。

- **N→N真payload回放**：Softmax op3 EXP存S，再以完全相同code回到op6；须保留factor/计数/row关联。它不同于N连续服务多个RMS/头。
- **M→M真payload依赖**：A_plain/H的PV context先保存，再作为Wo输入经loader回M。M op10多K段的内部merged累计是native retained context，不凭空多一条外部M反馈线；多次QKV/gate/up只是时间复用，不是自动M→M数据边。
- **R→R状态反馈**：old/next state/history经S/MEM保存、恢复到下一token/tile；单R内active/shadow只覆盖一个有限context，不代表完整状态已驻留。
- **E→E多步数据依赖**：bias再RoPE、score scale再mask、Falcon分支gain/join再加残差等按源顺序物化；并非把几个E组合操作当一个无成本opcode。
- **NUM→NUM accumulator**：X宽归并的rank累加是新增NUM保留context，不是七宏中已有的NUM或R功能。
- **T跨chunk重复BEGIN**是租约复用，不是必须存在T→T payload自环；有同T数据再入需求时必须先完整保存旧批并RELEASE再新BEGIN。S内layout重排可能有S→S复制，但预先正确布局的数据不应被强制多抄一遍。

不要求G/R间任意两种模式都直连。D卷积R→G.x与D输出R→N→G.linear_gate，H输出R→G.linear_gate→N，三种角色/顺序不同，不能只写“R/G/N互联”就算覆盖。G本身复用fn0/1/3不意味着需要一条外部G→G数据回路。

## 6. 同步、错误和实现边界

局部控制要分别记录：command accepted、operand stored、native ACK/result retired、N full-group barrier、G issued/retired、S写可见、loader done、T sealed/transfer/release、目标stored ACK以及state root published。不能用一个busy或done位替代这些条件。M EXEC故障mask、N统计/ID/factor、R状态元数据和S写ACK必须有按当前op保留的response classifier，才能决定进入数据capture还是控制完成通路。

fork/join须保存原残差及每分支stable operand和到达位，不能只把valid相与；不同完成延迟、G流水和背压都需要保持。NUM/IDX动态选择仍是固定程序内的数据，不能改写程序或把ID作为浮点分数。控制/事件与数据排空须有独立进展条件，特别是同岛重入、共享S和跨岛stored ACK/CLOSE不能形成资源等待环。

实现证据由另一份审计标记；本表所有角色/hop均写为`not_assessed_here`，不把源码单宏op、pin兼容、P2四包MST实例或静态配方当完整六配置已实现。六完整配置仍缺完整数值/存储/程序/组合验证，外围embedding/最终Norm/LM head/sampling也不由本表补齐。

## 7. 文件与实际核对

输出为`island-variant-routes.json`、本说明、`build_island_variant_routes.py`及`island-route-checks.json`。生成器只读已提交的`block-variant-models.json`、`family-spec.json`、`phase2-source-lock.json`和锁定14核心源码，支持`--root . --output-dir <独立目录>`与`--check`逐字节重算。542项研究一致性检查通过：六variant/无缺失宏、role ID唯一、所有physical引用、输入weights/params及T输出、D/H次序、X ID/gather/wide角色、未声称direct-wire实现。检查不是RTL或活性证明。

```powershell
python -B -X utf8 work/Melodydt/151/build_island_variant_routes.py --root . --output-dir work/Melodydt/151
python -B -X utf8 work/Melodydt/151/build_island_variant_routes.py --root . --output-dir work/Melodydt/151 --check
```

来源：[六配置和完整模型分配](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/051fddb9a3d2cecd4b76c43d07ec8581db9402ce/work/Melodydt/151/block-variant-models.json)、[FamilySpec](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/051fddb9a3d2cecd4b76c43d07ec8581db9402ce/work/Melodydt/151/family-spec.json)、[MST原生](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/051fddb9a3d2cecd4b76c43d07ec8581db9402ce/docs/rtl-contracts/MST_NATIVE.md)、[NEG原生](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/051fddb9a3d2cecd4b76c43d07ec8581db9402ce/docs/rtl-contracts/NEG_NATIVE.md)、[R更新源码](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/707878621b2add4ed218b8c43df2e95c9a56e2ba/project/rtl/block_library_v1/block_v1_r.sv#L109)。在线交付/状态由根任务统一处理，本子包不声称已上传、合并或验收。
