> 2026-11-01 P2更新：用户要求同步最新PR144并开始第二步；当前14核心RTL采用707878621b2add4ed218b8c43df2e95c9a56e2ba，仅R相对643变化，七顶层接口不变。新增MST控制原型及实际验证见[第二步报告](PHASE2_MST_IMPLEMENTATION.md)。以下P1/既有研究保留原版本与证据边界，不将旧回执重标为新源通过。

# 第1步：七宏原生接口、阶段与唯一owner合同

本稿复用Issue151 / PR152，研究输入为`343f4d4`，叶源码仍固定`643c6012a11cbf461146ac40fbf61485223fe946`。这是七宏**原生合同候选**，不是共同底座冻结、系统RTL组合通过或全部连接实现。本稿不自动导入PR144后续head，不修改叶RTL或ref-project；整合检查与远端交付状态见[第1步报告](PHASE1_INTERFACE_BASELINE.md)。

完整机器合同为[phase1-native-contract.json](../work/Melodydt/151/phase1-native-contract.json)，149个端口的逐项方向、位宽、源码行与驱动归属见[机械端口附录](../work/Melodydt/151/phase1-port-inventory.md)。每条关键语义可从JSON的`source_traces`及20条易错`source_anchors`回查固定源码；所有14份核心RTL/include记录原始字节SHA-256。

## 1. 七个顶层各自提供什么

方向相对于宏；valid/ready或valid/take相与才表示相应通道的接受事件。时钟与reset另计在完整端口附录内。

| 宏/顶层 | 输入与输出的主要宽度 | 原生同步模型 | 端口数 |
|---|---|---|---:|
| M `block_v2_m` | A128附bank/row/tile/wide；B512附bank/tile/wide/half；命令op4/index6/data64；响应data128/error/saturated | A、B可独立装载；cmd单操作；rsp保持；执行锁定所选输入bank | 27 |
| N `block_v2_n` | 命令op4/count4/param32/data128/aux128；响应data128/error/saturated | 一条命令执行并保持响应；另有跨命令Norm/Softmax与TopK上下文 | 15 |
| E `block_v2_e` | op4/shift5/A128/B128/C128；响应data128/error/saturated | 多周期单引擎；无count/mask；输出保持 | 14 |
| G `block_v2_g` | fn3/gated1/x32/gate32；响应data32/error/saturated | 四级流水；背压使整条流水冻结；无count/mask | 13 |
| R `block_v1_r` | op4/index10/data128；响应data128/error | 单命令、多周期；32bit owner/epoch/position；候选输出与本地提交分离；无saturated | 12 |
| S `block_feed_s_macro` | 普通wr1/addr10/data128与响应128；独立loader描述符/done；A128与B512输出 | 普通读写响应、loader装载、A/B输出是不同通道；共享真实存储bank | 38 |
| T `transaction6k` | BEGIN owner2/gen32/words10；WRITE index10/data128；READ index10/data128/last；独立commit/revoke/release | 单批次、单消费者租约；无cmd_op、通用rsp或commit_error | 30 |

M/E/G/R/T没有因此实例化其他计算宏。N实例化本地`block_v2_n_group`并include EXP表；G include查表函数；S明确实例化storage和feeder。模块、include函数和物理hard macro不是同一种对象；这里核对RTL边界，不重发物理资格。

M/N/R的`cmd_ready`均要求未reset、原生IDLE、旧响应空或本拍被消费；`busy=!cmd_ready`，包含旧响应背压，并非单纯“正在运算”。E相同地使用in/out通道。G没有此IDLE门控，而由`advance=!out_valid||out_ready`统一推进流水。

## 2. 外侧唯一owner与制造边界

| 原生输入或接受信号 | 本次约定的唯一驱动方 | 原生RTL是否已经实例化这个控制器 |
|---|---|---|
| M命令及rsp_ready | M_CTRL | 否 |
| M A/B payload与元数据 | S_LOADER，采用现有loader输出 | loader存在；v2 M组合及外侧调度未实现 |
| N/E/G/R的请求与响应接受 | 对应N_CTRL/E_CTRL/G_CTRL/R_CTRL | 否 |
| S普通请求/take、loader请求/done_take | S_CTRL | 否 |
| S A/B ready | 正常导入M时来自M原生ready | 替代导出sink必须另有预制选择，不能多驱动 |
| T各生命周期与读写接受 | T_CTRL | 否 |
| clk/reset | FABRIC_CLOCK_RESET集成约定 | 共同clock/reset网络未在本稿实现 |

此处owner表示端口控制权，不是必须随每包传送的通用标签。R的32bit数学上下文身份、T的2bit登记owner与“唯一端口驱动方”也不能混为一谈。母控只能向局部owner下发请求，不能与局部owner并行驱动同一原生输入。

M1–M10必须制成有限家族的算术、MUX、计数/保持、buffer、控制和clock/reset能力并集；M11/M12只永久绑定已存在的路线、程序入口与参数。软件证明两个源错时使用不能让push-pull输出直接短接，必须使用真实预制MUX或一源一线。系统有外存，本阶段不实现或评估接入，保留后续扩展；这不构成产品永久无外存约束。

## 3. M：装载、执行、读取是三类事件

固定源码：`project/rtl/block_v2/block_v2_m.sv`；端口L5–15，ready/锁L38–46，descriptor L48–62，格式化L105–122，命令及状态响应L197–248。

| op | 合法字段/阶段 | 响应及有效性 |
|---:|---|---|
| 3 | 已有merged row有效；`index=(row<<3)|pair`，pair0..3；data0 | 2×S64结果，读不释放 |
| 4 | index0；factor=data[15:0]有符号；left_shift=data[20:16]；高43bit零 | 只设置全局scale，ACK0；不是EXEC |
| 5 | 已有merged row有效；half0/1；shift[5:0]；width[9:8]=0/1/2；保留位零 | RNE右移后钳位S8/S16/S32，**始终四个S32 carrier**；saturated为任一钳位 |
| 6 | index0/data0 | 清A/B/merged/partial有效位，ACK0；**不恢复scale** |
| 10 | bank=index[5]且低5bit零；fmtA/B各1bit，clear bit2，lastK1..8，N1..8，tiles1..4，rows1..8，保留位零；A/B有效/格式匹配 | 执行K≤32的一段；完成响应低8bit为fault_rows，error为OR，saturated0；**不是矩阵结果** |
| 11 | index低1bit选bank，其余零；data0 | 只清该输入bank有效位，保留merged和scale |
| 12 | partial有效、row与owner相符；pair0..3；data0；partial-bank取index[3] | 两个S40 partial分别符号扩展S64，仅诊断，不是已缩放最终结果 |

M A使用8个S8低64或8个S16全128；B按`8*n+k`的n-major布局，S8一次512bit，S16 half0/half1两次。S16 half1必须在相同bank/tile的wide half0之后；S8 half1不被ready接受。执行时仅所选输入bank锁定，另一bank可预装，但两个输入bank**共享一份8×8 S64 merged结果上下文**。

有效EXEC按行原子发布：一行8个S64全部通过才替换；失败行保留此前merged，其他行可能已成功更新。error不表示整条命令回滚，失败追加不能盲目重放。无效描述符是立即error/data0，与有效EXEC最终fault-mask响应分开。未知op或字段guard失败也返回error/data0；外侧必须区分ACK、status、payload，不能见128bit响应就写入S作为张量。

M没有结果release命令。M3/M5只读，后续CLEAR/EXEC可失效或覆盖结果；外侧必须先保存需要的值。已由M5转换成S16且F匹配的四值可以固定取低16拆成两个G32包，不强制增加E/NUM；尚为S32/S64时不能同样裸取。

## 4. N：命令选择功能，count只对部分op有效

固定源码：`project/rtl/block_v2/block_v2_n.sv`；guard L84–100，dispatch L134–164，EXP L168–189，factor L191–201，回放L203–220，TopK L222–232。

| op | 输入及原生阶段guard | 响应/状态 |
|---:|---|---|
| 0 BEGIN | param=0 Softmax/1 RMS/2 L2；Norm epsilon=data低32必须非零 | ACK0；重建Norm/Softmax组并清factor/计数；**不清TopK loading** |
| 1 STATS | context有效、未finalize；count1..8，总数≤65535；S16 data | ACK0；更新count/sum/sumsq/max/min |
| 2 FINALIZE_STATS | context有效、未finalize、总数非零 | Softmax只finalize；RMS/L2计算factor；ACK/error，不输出向量 |
| 3 SCORE_TO_EXP | Softmax统计已finalize、factor尚无；count1..8且不超统计总数；重放同组原score S16 Q10 | 返回U16 EXP代码0..32768并累计exp_sum；**输入不是EXP** |
| 4 FINALIZE_EXP | EXP累计数量等于统计总数、总和非零、factor尚无 | factor=floor(2^44/exp_sum)，须适配U32；ACK/error |
| 5 NORM_REPLAY | mode1/2、factor有效；count1..8，总回放不超组长；data=x、aux=gamma | S16结果；RNE30(x×factor×gamma)，钳位；外侧明确输出F |
| 6 SOFT_REPLAY | mode0、factor有效；count1..8；每个有效U16代码≤32768 | Q14非负S16概率；零扩展EXP再乘factor并RNE30；**无gamma乘法** |
| 7 READ_STATS | context有效 | 混合128bit记录：count/max/min/sum/sumsq，不是同格式向量 |
| 8 BEGIN_TOPK | param=K1..8 | ACK0；开始/重开TopK装载，与Norm组独立 |
| 9 LOAD_TOPK | loading，count1..4，总记录≤40；每32bit为scoreS16+IDU16 | ACK0，保存记录 |
| 10 FINISH_TOPK | loading，非空，K≤记录数 | K个U16 ID；按score降序、同分ID小优先；**不是score或权重** |
| 11 READ_FACTOR | factor有效 | 原始factor低32，高96零；单位取决于上下文 |

N没有mask。有效count外的padding不参与该命令，输出无效lane为零；控制方仍须保留全组shape、顺序、score/EXP/gamma lineage。原生计数不验证“回放的是同一组原值”。`N.exp_score`对应N3，`N.soft_replay`对应N6，不能因为二者都叫回放而共用错误目标op。

RMS使用`a=floor((sumsq<<16)/count)+(epsilon<<16)`，L2使用`a=(sumsq<<16)+(epsilon<<16)`；root=floor(sqrt(a))，factor=floor(2^38/root)，失败/超U32使factor无效。epsilon属于输入raw整数平方单位，需单独转换和取整。gamma标称S16 Q10，N不提供beta、均值中心化或LayerNorm；更改gamma/output_F需重新绑定数值合同。

没有commit/release。组可以跨调用保留；新BEGIN在ready时能覆盖旧组，并不等待外侧保存完毕。未使用的count/param/aux/data字段有些被RTL忽略，机器合同逐op列明；推荐外侧规范置零不能写成RTL原本会拒绝非零。

## 5. E与G：相同端口内有异构结果

E固定源码`block_v2_e.sv`：L26–43负责RNE及打包，L67–83负责运算。合法op0..13依次为ADD、SUB、MUL、FMA、MAX、MIN、SELECT、左移、算术右移、RoPE pair、RNE COPY、ABS、PACK S8、S32→S16。op14/15仍可握手，但只产生error/data0。

- op2/3/9/10/13采用RNE右移，shift0..31；op8为算术右移而非RNE。FMA的C按乘积raw单位解释，不能默认与A/B同F。
- 普通输出为8×S16；op12输出低64的8×S8，shift被忽略；op13把A重新解释为4×S32，输出低64的4×S16，高64为零。
- E没有count/mask，也不输出有效数；外侧按所用op准备全部物理lane与有效尾部。RoPE必须保留真实完整pair。`out_saturated`只是任一lane钳位OR，不指出具体lane。

G固定源码`block_v2_g.sv`及LUT include：L39–67计算，L69–84传递四级valid/error/gated。fn0 SiLU、fn1 Sigmoid、fn2 GELU_tanh、fn3 Softplus；输入x均S16 Q10，每包两lane。fn4..7经过流水后产生error/data0；无独立count/mask。

未门控Sigmoid输出Q14，其他未门控函数Q10；若gated，激活再乘Q10 gate，Sigmoid右移14，其余右移10，最终均Q10。不能只按fn1就把所有输出标Q14。E10可作为已有Q14→Q10 RNE转换，但gated Sigmoid不得重复转换。输出背压时G整条流水冻结；独立gate数据只有gated=1时在数学上消费。

## 6. R：候选输出、提交和身份是独立合同

固定源码`project/rtl/block_library_v1/block_v1_r.sv`。op0..15全部有定义：OPEN、load state、key、query、x/inject、parameters、EXEC、COMMIT、REVOKE、load history、load taps、read active state、read candidate output、read metadata、read active history、load SSM decay。完整逐op index/guard/响应在机器合同中。

| 关键点 | 原生真实边界 |
|---|---|
| 数据 | state/x/inject/output/history为S32共同F；key/query/taps为S16 Q14；decay/beta/逐元素factor为UQ1.31且≤0x80000000；skip固定S32 Q16.16 |
| 容量 | 两个2048×S32银行，active8KiB+shadow8KiB；length1..256，每行8lane；SSM factor复用shadow，不是额外factor RAM |
| OPEN | L112–115；length=data[8:0]，owner[40:9]、epoch[72:41]、position[104:73]，高位零；pending任一存在时拒绝 |
| EXEC身份 | L141–145；mode[1:0]，owner[33:2]、epoch[65:34]、position[97:66]；与当前32bit值逐一比较 |
| COMMIT身份 | L156–160；owner[31:0]、epoch[63:32]、position[95:64]、caller next_position[127:96]；epoch不得0xffffffff |
| 候选可见 | L249–251；成功EXEC设置output_valid及pending_state/history；**提交前已可op12读结果** |
| 本地提交 | L255–261；必要时交换active/shadow并拷贝候选history，epoch+1，清pending/x_valid/output_valid；不代表多tile全模型版本提交 |
| 撤销 | L162；op8清pending/output/decay-valid，保留active/history；**原生不检查身份**，必须由R_CTRL唯一控制 |

R7接受后进入COPY、rsp_valid清零；`cmd_ready`只在IDLE时成立（L46），因此**COPY不能被op8中断**。COPY成功的边沿先更新active/history/epoch，再提出成功ACK；等ACK被消费之后再发op8，也只能处理当时尚存的候选，**不能回滚已完成的这次提交**。可撤销边界位于提交接受之前，reset也不是提交回滚API（L156–162、255–261）。

mode0 GDN与mode1 SSM需要原生loaded/key/query/param/x守卫；SSM另需所有逐元素factor、inject与skip有效。即使标量decay/beta在SSM算式中的使用不同，源码仍要求param_valid。mode2 conv需要x、完整history与taps，不要求active/key/param装载。

pending_history可以保留着继续mode0/1；补key/query/x/参数等部分load只禁止pending_state，这是同一context的RESUME，不是新OPEN。成功conv后又有失败state计算时，旧history候选仍需明确commit/revoke。R无saturated输出，算术溢出以error及无新有效output表达；不能把低32截断值作为成功结果。op11读active，op12读候选输出，op14读active history，三者不可互换。

## 7. S：普通写ACK与loader done分别消费

`block_feed_s_macro.sv` L20–29真实连接storage和feeder，没有实例化M。普通口16KiB=1024个128bit字，addr低2bit选bank、高8bit选行。`block_feed_s16k.sv` L12–36规定：

- 普通`req&&ready`接受读/写；写当拍更新存储，后续`valid/dout`返回din回显ACK。必须take，不能把旧写响应误当下一次读数据。
- 私有wide读一次占4个真实1RW bank，accepted wide_fire那拍普通ready为0；512bit是storage→loader内部通道，不是额外通用外口。
- 普通128和wide512各只有有限响应holding；普通S没有rsp_error、初始化有效位、byte mask或通用事务ID。reset不清存储payload。

loader接受并行描述符，不存在原生packed64bit opcode。rows1..8、tiles1..4；A/B base均4字对齐，即使reuse_b也仍检查B base对齐；A/B范围按原生占用长度验证。A每tile占4或8个128bit容器，S8也按每row一个128bit容器；B为n-major，S8占4字、S16占8字并分half0/1。

内部仅两个512bit A队列和一个512bit B槽，共192B；不是整个描述符1024B快照。`load_ready=!reset&&!busy&&!done_valid`，旧done被take的同拍不会接受新load。合法装载等请求/响应/A/B全部排空才done；非法描述符只产生done_error。**done不是M计算完成**。S.busy仅反映feeder.busy，既不涵盖普通valid，也不涵盖done等待take。

## 8. T：六通道批次生命周期

固定源码`project/rtl/block_v1/transaction6k.sv`，L27–39为ready/状态定义，L46–69为转移。

| 阶段 | 合法接受/可见性 | 下个关键事件 |
|---|---|---|
| EMPTY | BEGIN words1..384，登记owner2/gen32/count | FILL |
| FILL | write_index必须从0连续递增；接受完整128bit字 | 最后一写自动SEALED |
| SEALED | 无revoke时可COMMIT；REVOKE仍可撤销 | COMMIT后READ_REQ |
| READ_REQ | 首读启动拍 | READ_HOLD，出现read_valid |
| READ_HOLD | data/index/last背压保持；take边沿补下一个字 | 连续take稳态II1；末字take后RELEASE |
| RELEASE | release_valid&&release_ready | 回EMPTY；不是末字自动释放 |

T纯透明payload，不执行数值转换。没有cmd_op、通用rsp或commit_error。protocol_error只覆盖若干具体非法BEGIN/WRITE条件且粘滞到reset；不能假设所有提前commit/release都会报错。BEGIN登记owner/gen，后续控制端口不带身份，不验证访问方；T_CTRL负责租约权限。只能一个原生消费者，fork需要外部复制/引用计数，不能OR多个read_take。

同一个T重入新批次必须先保存完整旧批次、确认目的写ACK、读完并release；最大6144B S spool和相应控制仍是待实现方案。不同T可以流水交接，但不因此联合原子。当前合同不能把候选spool当作已存在存储。

## 9. clock/reset/cancel共同规则

七宏逻辑均为posedge clk、高电平同步reset；S的时序逻辑在两个子模块。没有原生CDC合同或跨时钟桥。若实例时钟不同，必须另设计验证CDC。reset期间不统计交易事件，外侧owner/consumer须共同复位或一致地失效上下文，不能保留旧应答/租约身份继续执行。

- M/N/E/G无原生在途abort；停止新请求后排空，或协调reset。M CLEAR命令只能在ready/IDLE执行，不能中断EXEC。
- R8只能在cmd_ready时撤销候选，不能中断算术或已接受R7后的COPY；COPY发布后再R8不能回滚active/history/epoch；不等于清active状态或重建身份。
- S已接受普通写无法回滚，loader无abort；部分装载后单独reset S会与M银行有效性产生一致性问题，须协调处理。
- T REVOKE仅限FILL/SEALED，commit之后应读完release或协调reset；不提供commit后取消。
- M/R/S/T的大块payload存储不会因reset全部清零。消费者只能依据valid、正确阶段和身份使用数据；不能把无效旧字节当零。

## 10. 实际检查与后续门槛

Python3.7标准库，可从仓库根复跑；只写显式指定的独立目录：

```
python -B -X utf8 work/Melodydt/151/build_phase1_native.py --root . --output-dir ../phase1-native-rebuild
python -B -X utf8 work/Melodydt/151/check_phase1_native.py --root . --contract ../phase1-native-rebuild/phase1-native-contract.json --output ../phase1-native-rebuild/phase1-native-independent-checks.json
```

已执行：14核心文件字节一致、7顶层旧签名一致、149端口及24通道完整、M/N/R源码命令case与E合法op表一致、20易错anchor与138处trace引用一致。11个合同错误突变均被拒绝，包括M响应宽度、EXEC当payload、N3当EXP输入、E虚构count、G门控Sigmoid错误Q14、R身份误写2bit/R8伪称可回滚已提交状态、S busy误当全宏空闲、T虚构commit_error、提前freeze声明及丢失trace。全部文本UTF-8 LF；结果和输入SHA见两份checks回执。

这些是源/合同静态一致性检查，不是对源码语义的形式等价证明，也不是RTL仿真。下一步须实现母子控制及有限适配，按合同建立真正RTL testbench，检验背压、错误、重复运行、reset、候选/提交与存储生命周期。MST首个组合、FFN/Softmax和其他允许连接覆盖是随后里程碑，不能因本步骤检查通过而宣称打通。没有执行服务器、综合/P&R或模型误差准入；正式交付和远端状态以PR152回执为准，R最终资格仍须由实施任务独立确认。
