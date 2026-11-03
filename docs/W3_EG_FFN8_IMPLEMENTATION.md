# 主线三：E/G公共适配器与FFN8基础核

Issue151 / PR152，负责人Melodydt。输入研究提交99d6df2e094febe4ea8fc9896301adbbfdc803ed；原生叶源707878621b2add4ed218b8c43df2e95c9a56e2ba。本轮从W1的MST骨架扩到真实M/E/G/S/T协作，固定一份可复算的小核数值合同，新增两个公共端点适配器和FFN8本地控制。N归一化、实际完整F/样本尺寸与物理资格不在本轮通过范围。

## 1. 本轮改变与动机

W1能接真实输入，但只输出M的raw S64；G需要双S16窄流，E需要按op同时具备多份操作数。把128bit总线直接相接不能保存单M的gate/up、完成G配对、处理尾部和保证真正存储完成。本轮把这些动作做成可综合的外侧模块，原生七宏及原P2/W1不改。

| 新模块 | 已实现的具体动作 |
|---|---|
| block_w3_e_ctrl | 捕获内部服务参数；按op依次读S并收齐A/B/C；先take/capture一个响应再请求下一份；原生E一次事务；结果mask/保持、写S并等待ACK，最后保留服务应答 |
| block_w3_g_ctrl | 捕获一字或两字S16数据；按两个lane发G；按实际accepted/retired计数收齐多在途结果；odd dummy清零、结果拼回128bit；错误排空/成功写ACK后才应答 |
| block_w3_ffn8_top | 一个固定本地FSM及唯一S helper owner（LOCAL/E/G），16输入ACK、三次M投影/量化读回/保存、G门乘、E残差、T输出/释放、frame/DONE/reset/abort与饱和累计 |

公共表示这些模块可复用或在岛内共享，不是全芯片只有一个集中适配器，也不是新独立bridge物理宏。E/G服务的op/shift/count/address是本地控制的内部端口；FFN8对外只接数据和生命周期信号，不提供运行时程序、opcode、地址、shape或scale加载口。不同op仍按原生合同执行，未删除或改名七宏端口/op。

## 2. 明确的小核数值合同

Fin表示整数码的小数位数，实数=code/2^Fin；它是本小核明确选择，不代表仓库全部样本已接受此量化。

| 阶段 | 格式与实际操作 |
|---|---|
| 输入x、三组W | x8和Wgate/Wup/Wdown各8×8，均S8、Fin7；矩阵按n-major8*n+k存储 |
| gate/up投影 | M S8×S8精确sum，raw Fin14；op5读S16模式、RNE右移4，得到Fin10；每应答仍是四S32槽，取各槽低16，两次应答合为8S16 |
| 门乘mid | G.fn0/gated1，SiLU(gate)查表插值RNE，再乘up、RNE10、clipS16；输出Fin10 |
| down投影 | M A16/B8，mid Fin10与Wdown Fin7形成raw Fin17；op5 RNE7/clipS16得到Fin10 |
| 残差 | 将原x符号扩展为S16 Fin7，用E.op7左移3转成Fin10；E.op0对down+residual做饱和加法 |
| 输出/状态 | 8S16 Fin10共一个128bit字；done_saturated累计各有效退休阶段饱和，独立于done_error |

M三个投影各执行CLEAR、SCALE1/left0、LOAD、EXEC、READ0/READ1，共15命令/应答；gate/up EXEC0x9884，down为0x9885；op5读取参数分别0x104和0x107。每个投影的compact结果先保存到S，才清理并复用唯一M；没有交错保留两个merged上下文或假定原生restore。

G参考由数学函数重建全部2564 LUT节点（SiLU/Sigmoid/GELU_tanh各513、Softplus1025），逐项与固定707表一致。参考计算不取DUT输出或DUT内部结果作为期望；整数RNE、插值、窄化和饱和单独建模。原表生成脚本仅GET作为来源，不运行它改写原生表。

本核未接N，使用同一x执行投影和残差。完整F引入preNorm时须分别保留原始残差X和归一化后的投影输入，不能简单插入N后把残差也换成Norm输出。Gemma postNorm、完整I/H、融合布局、真实模型尺度/质量都没有由FFN8自动闭合。

## 3. 数据布局和固定控制链

| S地址 | 内容 |
|---|---|
| 448..451 | x保留4字：首字低64为8S8，其余56B由硬件canonicalize为0并实际写入 |
| 452..455 / 456..459 / 460..463 | Wgate / Wup / Wdown，各64B |
| 464 / 465 | compact gate/up，各8S16 Fin10 |
| 466 / 467 | x符号扩展S16 Fin7 / E左移后的residual Fin10 |
| 468..471 | mid供A16 loader使用：468为8S16，其余3字实际写零 |
| 472 / 473 | down结果 / 最终残差结果，各8S16 Fin10 |

一帧16×128=256B，其中有效200B、padding56B；只有16次实际写ACK全部完成才置input_stored/允许start。S448..473共416B是本profile预约，不是S宏面积或全部可用工作区；T使用1字16B，实体S16KiB/T6KiB容量不变。

```text
16字输入并收ACK → start
→ 保存x16 → E7 residual
→ M gate → op5取字段/compact → S464
→ M up   → op5取字段/compact → S465
→ G gather两源/双lane流水/合包 → S468 ACK
→ 实写mid padding → M down(A16/B8) → S472
→ E0读down/residual并相加 → S473 ACK
→ S回读 → T BEGIN1/FILL/COMMIT/TAKE/RELEASE → DONE保持
```

S普通口只由一个既有block_p2_s_ctrl驱动。top在整次E/G服务（包括目标写ACK和应答消费）保持owner；其他服务不并驱，也不因native完成而提前换owner。loader的wide访问属于真实S内部接口，三个投影装载与普通事务阶段顺序执行，wide读取不计入普通口32笔。

正常完整帧逐次检查32 S请求/32ACK=26写6读：入口16写、x16写1、E7读/写2、三M compact写3、G两读/一写3、mid padding写3、E0两读/一写3、最终T读1。另有3 loader/A/B、2 E服务、1 G服务（4输入pair/4退休pair）、T1字/RELEASE。中断中的已接受写/输出不能回滚，不能把全局计数当无条件守恒。

## 4. 适配器的op、tail、握手与错误边界

E按原生op选操作数：0/1/2/4/5/9用A+B，3/6用A+B+C，7/8/10/11/12/13只用A。多数count1..8，E13按S32输入仅1..4，RoPE9要求偶数count。E12输出compact S8低64，E13输出compact S16低64；尾部清零，数值尺度仍由调用者合同决定。E12是限幅/压位宽，不能自动替代任意scale转换。

G gated时收X/Gate两字，不gated时只收X；count1..8，每拍两S16，按ceil(count/2)真实握手发送/收回。奇数尾lane在原生输入前置零，输出后再mask；不能以固定延迟代替退休计数。原生输出不带fn echo，服务上下文保持到所有已接受数据关闭。遇某拍native error仍排空已接受数据，禁止将该服务结果写回。

内部req在接受时快照，native/memory请求未接受时保持，服务rsp_valid/error/saturated保持到rsp_ready。S读取或native/count错误发生在结果写之前时不发目标写；若已经发写再在WRITE_RSP收到mem_rsp_error，只能报告写应答错误，不能承诺回滚。当前真实S helper普通口没有error能力，此支不是额外存储故障检测资格。

reset需与原生E/G及S helper协调；适配器本身没有无reset取消协议。top的prestart abort丢frame不造done，RUN abort保留一次error完成，已有DONE遇abort保持error/saturated且同拍ready只消费一次；hard reset清有效性不假定RAM已清。输入/输出/DONE背压、输出已被take的前缀不可撤回等沿W1规则。

## 5. 真实验证的范围

实际使用现有本地ModelSim SE-64 2020.4，在获授权的沙箱外独立目录运行；无安装、PATH/license/凭据查看、服务器目录/上传或作业。14锁定核心源保持原字节；E/G本轮获得的是所列服务/小核组合范围的新功能证据，N/R/legacy仍只语法编译。

独立整数参考冻结6输入（normal、zero、正/负极值、mixed、sparse），逐阶段比对S464..473及最终字；正/负极值输出分别全7fff/全8000且饱和，不把clip当执行错误。FFN-r01实际19检查/6609周期通过；FFN-r02补E非法操作和G单拍错误后的21检查/7524周期通过，旧版本按源SHA保留。

最终FFN-r02 summary input452/Sreq823/Sack821/Mcmd353/Mrsp353/Ttake21。正常帧均有独立32/32计数门；全程包含显式pendingACK中断，不宣称全局无条件守恒。21是检查标记数，不是21个独立完整模型任务；恢复流程会执行额外完整帧。

最终adapters-r01编译/仿真均exit0，46检查/2231周期：22个E、14个G基础例及10个握手/ACK/协调复位例。全程Gissued65/Gretired61含协调reset取消4个在途pair，不宣称无条件全局相等。原P2/W1本轮回归47检查通过。全部命令/退出码/日志/源SHA由执行索引统一给出；日志为runner捕获并规范化UTF8LF，原stdout字节SHA另存回执。有限定向测试及TB-only force不等于全参数、随机/形式活性或完整数值质量验收。代理交叉审阅不是外部PR批准。

## 6. 当前边界与接续

本轮是固定FFN8＋一字E/G服务；没有N pre/postNorm、实际模型全H/I、多字张量分配/回放、通用跨岛stored ACK、MEM/NUM、完整产品程序或物理实现。未以小形状替代样本完整尺寸，没有更改角色目录的合法性或为通过检查删掉原P2/W1要求。

新控制逻辑位于wrapper和两个适配模块；不是整片母控，也没有完成M11/M12多模型产品绑定。程序、MUX、寄存、握手和时钟复位资源必须真实预制，不能在上层金属定制时补造。宏内部未用op本轮保留，后续按物理位置跨产品需求并集再决定裁剪。

下一主线为N归约/统计/回放与完整A/F的逐步集成。所有一般W1/P2剩余门、外部设计/PR审查、全模型/物理和协作接入状态按各自证据维护，不能由本次有限功能通过提升。
