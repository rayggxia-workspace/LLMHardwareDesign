# R3 M 有限供数候选：先行验收合同

2026-11-10，Issue247 / PR243。独立研究/测试目录；不修改正式RTL、R1或R2，不在本机/登录节点运行EDA。具体端口与可接纳的shape以实现代理冻结接口为准，本合同不宣称候选已实装或通过。

## 范围与数值

首轮仅限定static W8、logical row=1、signed S32 activation、signed S8 weight、N≤8、S96全K累加、最后一次RNE至S32并饱和；不是原生产S8/S16/S64 op13。必须保留旧路径/默认关闭，可作为未接LC的独立旁路服务；不得以此自动改变原生产M合同。动态W32、多logical row、W16、非合格shape在旧模型中继续原费用，除非另有明确实际RTL和校准。

独立Python任意精度oracle输入是未拆分S32×W8 Dot，RNE使用floor商/非负余数、正负ties-to-even，最终S32饱和。每列/slot/tag使用不同数据，禁止只用相同常数输出掩盖丢失、重排或覆盖。验证极值INT32_MIN/MAX、B=-128/127、正负ties、零、取消和饱和；K和N的尾部用非零哨兵填充未用位置，保证尾mask实际生效。所有物理packet的累计和/最终输出应可与同一独立oracle对应；内部S96若没有公开读口，可用只读testbench层次观察真实commit后的寄存器，不能添加功能捷径。

完整K上限及累加生命周期必须有硬件/调用合同。对K≤65535，staticW8绝对和小于65535×2^31×128<2^54，S96足够；此边界不能替无界续算担保。数值同值、函数近似、量化质量和完整LLM真实生成分别报告。

## 真实供数与所有权

- 只允许真实4×256×128bit 1RW bank，总16KiB；每bank每拍至多一次物理访问，全体最多64B/拍。实际编译固定SHA的SRAM功能模型；不能同时免费64B读＋64B写，也不能用testbench直接驱动A/B绕过S。
- 输入初始化和最终结果读回可在计时区间外，但计时开始后的每个A/B供数都经真实S请求/响应。数据布局、基址对齐、尾部word/line填充和打包由实际地址序列定义。不得把逻辑字节数的ceil替代实际离散地址访问，或从无限testbench数组补未读取的输入。
- 一/双buffer使用同一控制/算术路径，仅容量参数不同。两配置相同descriptor序列、原始S内容、工具、初始化seed、端口响应和ACK延迟策略。接收/消费后可安全复用时不得故意让单buffer等drain以制造加速。
- 上游leaf在input_accept寄存products，输入buffer可在实际接受后立即复用；数学context的nextK更新仍需实际累加commit。普通非final packet没有leaf输出时，必须有实际commit事件或随真实advance跟踪的有限pipeline，不能固定sleep若干拍或末input_accept就宣称提交。
- buffer空间、inflight reservation、读取命令元数据和返回槽均有限；返回背压不能丢数据或覆盖输入。报告最大占用和全流程push/pop/accept/commit守恒，结束必须排空。
- 当前冻结方向为两个配置共有8项completion reservation、2项read metadata；同context允许多个有序packet在途。`reserved_nextK`仅在合法cmd接受时推进供后继预取，`committed_nextK`仅在真实leaf commit推进。非法命令返回该位置之前的合法reserved前缀，不推进任一数学前缀。final接受即closing，后继非法/重开不得改变会话；最后2次写ACK且final done消费后释放。验收必须覆盖8票满、环绕和同拍pop/push，不能只测不同ctx交错。
- slot必须至少区分FREE/ACTIVE/FINAL_PENDING：FIRST只能新建合格slot；continuation严格匹配tag、nextK、格式、N和round配置；final之后禁止重复first/continuation，直到最后真实输出S写ACK退休。非法命令不发MAC、不写S、不错误推进nextK。错误/取消的slot处理必须明确，不能假称继承原生op13的原子失败语义。

## 背压、复位与服务边界

无人工延迟是headline；另做可重复的每响应/ACK延迟，两个buffer配置使用同策略。实际bank响应必须被保留，延迟代理不得让service消费而bank未消费，或反之；额外代理缓存如有必须有限并计入测试条件，不属于候选硬件。

至少覆盖：read request等待、read response等待、MAC input等待、输出response/写ACK等待、外部done_ready=0。held request的地址/数据/类型和held response的值/错误/tag保持稳定，不能重复发射或重写。最终done及slot释放不得早于全部实际写ACK。reset应清valid/owner/reservation与未完成命令，恢复后不得有幽灵response/写回；SRAM有效旧数据仅按实际reset合同保留，不能把复位当免费擦S。

每次测试记录真实时钟边沿：descriptor accepted、首/末S请求及响应、每个M input accept/commit、首输出、每次S写/ACK、done首次有效、done消费及下一descriptor实际可接受。主服务费用使用**实际start-to-next-ready/next-accept**；单独leaf II=1只作算术能力证据。done后额外人为hold不计入常态性能，延迟压力例单列。

## 最小矩阵与独立计数

- buffer_count=1/2；N至少1/3/8；K至少包含1/7/8/15/16/17/31/32及目标旧模型实际Kchunk/尾K；目标256或其他值需接口冻结后明确。
- 单job、同slot跨多个K chunk、多个slot/tag交错、最后输出全部读回；tag/nextK/first/final/边界/对齐/容量错误及同址输入输出合法性。
- 无背压、若干读响应延迟、若干写ACK延迟；不同slot目的S地址与不同列结果；最后一项ACK和buffer drain明确检查。
- 至少三组原随机初始化1:143、2:143、2:144，源/输入/工具/生成物/日志SHA逐项冻结；脚本不得在缺profile或shape未覆盖时采用任意快倍率。

守恒字段至少含：logical outputs/MAC、descriptor接受/完成/错误数、真实A/B S读的地址/字节/beat、M packet accept/commit、真实S写/ACK、buffer/slot峰值、末尾未退事项。单/双buffer不得改变有用MAC、A/B/输出数据、事务数量和数学结果；预取时机可以变，额外缓存命中若计收益则必须明示实际存储和所有权。

## 面积账本与旧模型接合

固定16KiB S和额外FF分开：列出主乘法器个数/位宽、归约加法器、S96 RF、products/partial/结果快照、每个输入buffer的A/B payload、FIFO/tag/nextK/state。按实际数组和参数推导单/双buffer数据位差并与源声明核对，不能把RF叫SRAM扩容或漏算已有leaf寄存器。没有综合/STA/P&R时只给结构代理，不给mm²、功耗或300MHz资格。

旧模型保留其trace、S32/S96数值合同、2P/1U、每块16KiB、17.1GB/s及既有shared/ideal-port层级。新profile只能替换被**同shape、同工作及清晰边界**校准支持的compute/tail/wrapper；原S/DDR/adapter费用不得无声删除或重复收费。profile必须区分真实S服务总周期和纯M段，给出从实际完整服务到旧收费字段的可审计推导。若实测S路径比旧抽象慢，保留负结果，不能用max裁掉候选开销来保证收益。

当前接口方向：`r3_m_finite #(BUFFERS=1/2)`；packet k1..16、N1..8，ctx3/tag32/ki16/totalK16/shift6/first/last及A/B/out字节地址14位。A64B对齐、out16B对齐；B为K-major×activeN、允许任意字节offset，实际读取1..3条B64B line，另1条A64B。每input槽A64B+B192B=256B。final固定2次16B写及ACK；这不是一条旧K256 tile命令。

主旧体系资格仅static W8/r1、N8、shift16，fullK2048/11008、oldK256=16个K16 packet；需连续同ctx实测16包及延续/末块，不能套8ctx交错的叶II。8ctx旧group顺序为每ctx先16包，A只在DDR层复用而每packet仍实际读A64B。真实event profile须包含每包CMD/S请求/响应/leaf接受/commit/写/ACK/done及每cycle外部ready/valid mask，用同输入先核有限FSM，再替换旧Calendar竞争；每笔S预约仅计一次。

当前状态：验收合同已形成；bench/runner正在按该接口准备，没有仿真/校准结果。
