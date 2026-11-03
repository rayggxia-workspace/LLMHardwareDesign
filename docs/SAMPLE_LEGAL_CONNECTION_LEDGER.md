# 步骤2重做：静态连接动作归并与可执行契约检查

> 用户已采用[七阶段研究路线](SEVEN_MACRO_INTERFACE_ROADMAP.md)，当前执行P1版本/接口合同。最新入口为[源锁与第1步报告](PHASE1_INTERFACE_BASELINE.md)，P2–P7尚未启动；既有静态编译研究继续作为设计输入，不等于新RTL或物理验收。

输入研究版本为 `e44c4f5`，原生 RTL 冻结为 `643c6012a11cbf461146ac40fbf61485223fe946`。本稿为 Issue151 / PR152 步骤2正式候选，原始角色账本与七宏RTL保持不变。本次交付是编译期契约与有限动作规划工具，完整模型编译、互联 RTL 和物理实现均未完成。

## 1. 本次改变的原则

原目录中的 role 表述数学含义、格式、上下文和控制权；它们用于软件静态证明和选择连接方案。运行时不要求每包携带通用 role 标签，也不因此新增通用协议处理器。编译后的产品使用预制端点、固定线路/已制成的 MUX、既有宏命令、永久参数以及必要的本地状态机。若多个 push-pull 输出共享目的端，互斥 valid 不能让它们直接短接；必须有真正的选择器，或产品永久绑定为一个独立驱动源。

M1–M10 必须先制成有限家族需要的能力并集，包括算术、真实路由选择、保持/拆拼寄存器、有限缓冲、命令 owner、状态机和 clock/reset。M11/M12 只能永久选择这些已存在的线路、端点、常量和控制入口，不能增加有源算术器、寄存器或 MUX。共享能力能否只放一份，还取决于同时活跃性、带宽、调度、距离和时序；配方归并本身不能回答版图实例数。

系统有外存。本轮不实现或评估外存接入，不生成 EXT/DMA/自动 spill 动作。这仅约束本轮验证 profile，不能解释成产品永久无外存，也不能因当前 S 放不下就删除语义合法连接。

## 2. 覆盖分母保持不变

机器契约保留原输入 SHA-256，并完整保留每个槽的 ID、源、目的、配方、状态、条件、额外状态守卫和 gap；原 JSON 不覆盖。

| 原始目录 | 数量 | 本轮实际做到的层级 |
|---|---:|---|
| 源 role | 23 | 编译期语义契约 |
| 数据目的 role | 27 | 23×27=621 个枚举槽原样保留 |
| 受控参数目的 | 20 | 23×20=460 个枚举槽原样保留 |
| 配方 | 153 | 全部映射到动作族，保留原语义/状态/映射守卫 |
| 样本连接义务 | 96 | 逐项核对真实 D/P 槽及配方；逐项标出未绑定项 |

153 是 9 类源 schema 与 17 类目的模板的组合，既不是153种算术，也不是153个硬件单元。621+460 是候选槽分母，不是1081条已合法化或已打通的线路。96项只是八样本、十层类型的已知连接需求，不是完整模型图、完整定点准入或驻留证明。此次全部96项仍未完全实例化；新增系统 RTL=0，已编译模型=0，系统 RTL 验证=0，物理资格=0。

契约按不同轴分别记录：枚举/引用检查、动作族分类、具体语义、具体数值、产品实例化、容量/路线、系统 RTL、RTL 验证、物理资格。前两轴通过不意味着后面各轴通过。

## 3. 153配方归并成16类可复用动作

| 动作族 | 落地含义 | 实现边界 |
|---|---|---|
| PROVE_SCHEMA / PROVE_NUMERIC | 静态绑定家族、role、字段、lineage、单位、舍入、饱和和误差 | 软件证明，不需要运行时 role 标签 |
| BIND_PRODUCT | 永久绑定端点、常量、命令字段和控制入口 | M11/M12选择已有能力 |
| SELECT_ROUTE | 独立点对点线路，或真实MUX/demux/phase选择 | 共享线路需要预制有源选择器 |
| HOLD_HANDSHAKE | 源保持或捕获，过滤响应，背压下保持内容 | 可复用宏自身 holding；不能无依据增加每链一份128bit缓冲 |
| PACK_LANES | 取字段、扩展、拆拼、顺序和有效尾部 | 只改布局，不改变数值单位 |
| NATIVE_OP | 精确复用 M5、E10/E13、N3/N6 等既有功能 | 不强制每条转换额外经过E或NUM；要证明公式、布局和时序匹配 |
| ONCHIP_STORE | 有限 S 槽、快照、ACK和credit | 新的分配/互联控制尚未实现；本轮无spill |
| LIFECYCLE | owner、fork保留计数、JOIN、RESUME、REENTER | RESUME保留当前上下文；REENTER必须结束旧生命周期 |
| FIELD_JOIN | 记录选字段并收集独立伴随数据 | 不能凭打包创造score、gamma、inject等缺数据 |
| EXP_REPLAY | EXP lineage及factor上下文，正确发N6 | 复用N算术，新回放/存储/owner控制未实现 |
| CONTROLLED_FIELD | 参数身份、整数域、范围、保留位与更新权限 | ID地址生成需要预制checked地址能力，不能裸转发payload到cmd |
| GATHER_DATA | 用ID查原始score/记录/数据 | 缺数据及索引布局时保持data gap |
| LOADER_CAPTURE | 同S串行重入时完整装载快照 | 候选1024B额外存储/控制；不是现有loader队列 |
| T_BATCH_SPOOL | 同物理T整批重入保存旧批次 | 最大6144B S预留与控制候选；不同T不强制同样spool |
| MISSING_NUMERIC | 既有op与接线无法精确完成的运算 | 保留合法需求与能力缺口；不伪装为新增算术已完成 |

表内首行包含两个动作族，因此共16类。它们是编译器动作类别；一个动作可能无电路、可能复用已有电路，也可能要求多个按距离/带宽复制的实例。条件动作集中定义，不能把每个配方列出的所有条件动作都机械实例化。

两种N replay必须区分：`SCORE_REPLAY_N`的目的为`N.exp_score`，消费STATS对应的原始S16 score，复用N.op3计算EXP并累计exp_sum；它只归入NATIVE_OP，不归入明确要求N6的EXP_REPLAY动作。`EXP_REPLAY_N`的目的为`N.soft_replay`，消费同组的原始U16 EXP代码，在factor就绪后复用N.op6生成概率。机器契约为全部18个相关配方保存显式目标op和输入/输出/上下文约束。

## 4. 五类可执行实例与拒绝条件

### 4.1 M.op5已S16：只需保持和两相拆包

[M源码 L117–121](../project/rtl/block_v2/block_v2_m.sv#L117)说明格式化结果始终放入四个S32 carrier；[L202–204](../project/rtl/block_v2/block_v2_m.sv#L202)的 op5 描述符以 bits[9:8]=1 选择逻辑S16，以 bits[5:0] 选择右移，bits[7:6]和高位须为0。

如果已授权该 M5 RNE/饱和，且结果F=10，四个值 `[-32768,-1,1024,32767]` 已经是S16，则：

```
G包0 = {M[47:32], M[15:0]}     = 0xffff8000
G包1 = {M[111:96], M[79:64]}   = 0x7fff0400
```

可让 M 原生 rsp_data/rsp_valid 保持到两个 G 握手完成，增加两相选择及ready控制；若要提前释放M，才选择预制捕获寄存器。这里没有额外数值算术，也不需要先拼成八个元素。G门控模式另需gate伴随数据。

若M5仍选择S32，即使低16bit看似可取，也必须拒绝这个裸取实例。可另选已授权的原生M5-S16，或E13等明确转换；改用不同舍入/饱和顺序必须重证等价，不能自动删掉样本原有的E13步骤。M.op3的S64也不能默认为S32，宽路径缺口保留。

### 4.2 E12与E13的低64不是同一种载荷

[E L30–41](../project/rtl/block_v2/block_v2_e.sv#L30)仅让 op2/3/9/10/13 执行RNE右移；op12只把八个S16钳位成八个S8，shift不生效。[L80–83](../project/rtl/block_v2/block_v2_e.sv#L80)的 op13把A当四个S32重新组合，再RNE、钳位为四个S16；高64为0。

E12→G在单位相同的前提下，对8个S8作符号扩展并拆成4个G包；E13→G则把4个S16拆成2个G包。扩展/拆包可以用固定线和phase选择，不要为此新增通用算术器。把E12低64当4个S16、把E12 shift误当重标度、把E13 padding当数据，均拒绝这个布局实例。

### 4.3 G未门控Sigmoid Q14→Q10需要数值转换

[G L63](../project/rtl/block_v2/block_v2_g.sv#L63)表明未门控输出保留查表单位；fn1 Sigmoid为Q14，不能直接改标签为Q10。已有 [E.op10 L80](../project/rtl/block_v2/block_v2_e.sv#L80)配合 L30–32 可完成RNE右移4：`8→0`、`24→2`、`16384→1024`。工具规划G两值打到E低两lane，其余置零并外部忽略；复用E10算术，仍缺G/E路由、owner和有效计数控制。

不能把这个数值转换写成纯bitpack。相反，gated Sigmoid 先乘Q10 gate再右移14，输出已经是Q10，不应重复右移4。当前规划仅验证这些整数/单位规则；不等于整个网络的量化误差已通过。

### 4.4 N EXP必须走正确的op6上下文

[N L25–28](../project/rtl/block_v2/block_v2_n.sv#L25)在op6对原始16bit作零扩展；EXP代码32768代表1.0，按S16解释却是−32768，因此不能bitcast概率。[L86–99](../project/rtl/block_v2/block_v2_n.sv#L86)限制有效Softmax上下文、factor、count与重放总数；[L151–153](../project/rtl/block_v2/block_v2_n.sv#L151)选择op4因子，op6随后RNE30并钳位0..16384。

两个EXP代码都为32768时，总和65536，factor=`floor(2^44/65536)=268435456`，op6得到两个8192，即Q14的0.5。工具产生真实N6字段：op6、count2、原EXP U16 data、param/aux规范置零；param/aux在该op不参与公式。

EXP经过S/T或已证明的E10 shift0原样复制后可以继承原schema和上下文，不按“源不是N.op3”永久禁连。执行工具目前只白名单证明这三种copy；其他候选copy需要新增证明规则。组、max、聚合版本或全组count不匹配时拒绝此实例；factor尚未就绪则标STATE_PENDING并等待RESUME；片上快照不足则标MAPPING_PENDING，均不把连接对改成永久非法。group/max/version这些是软件契约，不要求新增通用运行时标签。

### 4.5 TopK ID只提供身份，地址与数据需分别绑定

[N L157–160](../project/rtl/block_v2/block_v2_n.sv#L157)的输入记录同时含score和ID；[L228–231](../project/rtl/block_v2/block_v2_n.sv#L228)只返回ID。工具要求显式ID域、rank顺序、地址单位、base/stride和唯一S_CTRL：`address=base+ID*stride`；ID `[1,3]`、base8、stride2得到S字地址10和14。

动态ID需要在M1–M10前制成checked地址生成/选择能力；M11/M12只能绑定常量和路线。ID32、stride64产生地址2048，超出当前S的1024字窗口时保留MAPPING_PENDING，不将算法需求归为语义非法。若还要score/专家数据，必须给出原始表及ID到记录映射；缺失则DATA_PENDING，不能从ID凭空得到score。工具的score-table示例仅是软件查表契约，不表示当前RTL已经有gather单元。

## 5. 状态/容量边界与96项的处理

96项每项均保留模型、kind、D/P槽、原配方、配置shape、原条件、额外要求和gap。数值、完整命令、companions、owner、route、有限槽、调度仍未实例化。尤其：

- `O0002`等M.read32→E13义务保留原要求，不因存在M5-S16候选而自动换图。
- FFN的E13→G只在F=10已证时归为保持/拆包；F仍未绑定时不声称完成。
- EXP roundtrip复用N6，但完整存储、factor生命周期及计数没有因单个probe通过而完成。
- `O0083`的P0136仍是TopKID→受控S.address；原score/权重数据、专家地址及容量分别待定。
- R宽数值、SSM bias/inject等能力缺口没有被低位抽取或role重命名掩盖。

S ordinary payload、write echo、loader是不同端点。S/T保存的是带编译期schema的快照；使用时继续证明原始lineage。S write ACK须取走并释放响应槽，不能把它当任意独立读端口。S loader原有192B队列不是1024B完整描述符快照；同S串行重入时要先完整排空A和B并收到done，再普通写回。T没有随机读/rewind，同物理T重入要先spool完整旧批次、等待S ACK、最后take/release，再开新批次；仅等待当前T ready不足以解决生命周期。fork不能把多个take直接OR在一起，JOIN不能创建缺失伴随数据。

## 6. 工具、实际验证与限制

所有脚本仅用Python3.7标准库，输入只读，输出显式写入独立目录，UTF-8 LF。下面命令在仓库根运行：

```
python work/Melodydt/151/lower_static_connection.py --root . --output-dir <独立输出目录>
python work/Melodydt/151/verify_lowering.py --root . --output-dir <同一独立输出目录>
```

已执行结果：37/37个明确预期的正/负/状态/容量/缺数据probe通过；1081槽及原守卫、153配方守卫、96真实引用检查通过；独立按原目录目的语义检查18个N replay配方及46个相关槽的N3/N6目标op和动作归属；22561个含负数半整数的RNE结果与独立精确有理数ties-to-even参考一致。37项包括12个候选动作计划、21个当前实例拒绝、1个状态待满足、2个映射缺口、1个缺数据案例。拒绝只针对当前绑定/布局/语义实例，不宣称源目的组合永久非法。

`verification-receipt.json`保存输入、工具、case及生成文件SHA-256；`independent-check-results.json`记录独立检查结果。在输入integrated内运行 `python scripts/check_project.py`：PASS，仅管理结构检查。RTL仿真、模型推理、定点误差评估、服务器实验、P&R与在线状态同步均未执行。

入口也支持 `--case <单实例JSON>` 生成 `single-plan.json`；仅实现五类有限实例规则，其他输入明确报 `UNSUPPORTED_PLANNER_INSTANCE`。此工具不生成RTL，不做完整graph compiler、通用指令集、自动布局布线或外存调度。动作计划必须随后绑定实际资源、实现缺失胶合、验证无死锁与背压，并在制造冻结前完成真实物理预算。
