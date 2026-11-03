# W3 E/G S 服务适配器草稿

输入研究 parent：`99d6df2e094febe4ea8fc9896301adbbfdc803ed`；native：`707878621b2add4ed218b8c43df2e95c9a56e2ba`。接口按根 `W3_ABI.md`。本目录只新增 `block_w3_e_ctrl.sv` 和 `block_w3_g_ctrl.sv`，不改 native、P2、W1，不在 adapter 中实例化 E/G。

两模块都是单个 service 在途。req 只在 IDLE 接受，锁存 op/fn、count、地址等内部参数；host 不直接配置这些字段。顶层必须从 request 接受到 response 消费的整个期间，保持一个普通 S owner lease，使用唯一真实 S helper。adapter 在 READ_REQ 保持请求直到 ready，READ_RSP 捕获并消费返回值后才发下一读。成功的结果写入一次，消费真实写 ACK 后才进入 RESPONSE；response 的 error/saturated 一直保持到 rsp_ready。

reset 高有效同步，取消本地有效状态。外层 abort 必须一起 reset adapter、native E/G、S helper 和相关 owner；没有单独的不复位 cancel/drain 承诺。reset 不是 RAM 或已消费外部数据的回滚。

## E：gather → 单 native 请求 → 写回

E service 先 gather 所有所需 128-bit 操作数，然后只发一次 native E input。操作数策略：ops0/1/2/4/5/9 读 A+B，ops3/6 读 A+B+C，ops7/8/10/11/12/13 只读 A。unsupported14/15 仍读 A 并提交给真实 native，让原生 error 返回。

count 为 1..8，E13 为 1..4，RoPE9 要求偶数。违反 count 约束时本地 error response，不读 S、不发 native、不写目标。E13 的输入元素是 32 bit，其它输入元素为 16 bit；inactive 输入实际写零，未使用操作数也为零。E 输出截取有效 tail：E12 是紧凑 8-bit 元素（低64最多8个）；E13 是紧凑16-bit元素（低64最多4个）；其它是16-bit元素。尾部写回零，不能把 E12/E13 共用一个“低64同格式”的约定。

native error 被消费后直接 response，不发 destination write；native saturated 独立保存。正常路径先锁存 masked result，再发 write，等 ACK 后 response。S read error 也不发 native/结果写。若目标写请求已经被存储端接受，后续人为注入 write ACK error 只能报告失败，不能保证已接受写入回滚；真实当前 S helper 没有原生普通 error、固定返回0。

E 状态：IDLE0、READ_REQ1、READ_RSP2、ISSUE3、CAPTURE4、WRITE_REQ5、WRITE_RSP6、RESPONSE7。`operand` 为 A0/B1/C2。所有请求地址/载荷均来自锁存器，在请求背压时稳定。

## G：gather → 多在途 pair 流 → 按序收集

G 总读 A，gated 时另读 B；A 是 `g_in_x`，B 是 `g_in_gate`。输入按 count 先 mask 成零尾部，每拍送2个S16，pair 数为 ceil(count/2)。因此奇数尾部的 dummy lane 在 native 输入即为0，输出再按 count 丢弃。合法 count 为 1..8；非法 count 立即 error，不访问 S/native。fn4..7 仍提交给真实 G，靠其 error 标记处理。

`issued` 只随 native input valid&&ready 增加，`retired` 只随 native output valid&&ready 增加；不按固定延迟推测 response。允许多个 pair 同时在流水内，按序收集到一个128-bit result。最后一个 pair 返回之前，即使前面已 error，也继续发送/排空当前固定 service 的全部 pair；error 累积后不写目标，保证下个 service 不继承上个流水响应。saturated 按所有返回 pair 做 OR，独立于 error。成功只写一次 compact S16 word，并等待真实写 ACK。

G 状态：IDLE0、READ_REQ1、READ_RSP2、STREAM3、WRITE_REQ4、WRITE_RSP5、RESPONSE6。三个计数器 `issued/retired/total_pairs` 均3bit，合法最大4。源字在整个 STREAM 固定，动态选择 pair；in stall 不 advance issued，输出位置由 retired 决定。

## 验证边界

本 agent 未执行 RTL compile/simulation，也不预填通过状态。根 runner 负责 ModelSim；另 agent 的独立 TB 连接真实 S、真实 helper、真实 E/G，验证 operand mask、FMA、E12/E13、odd G、multiple in-flight、响应/写 ACK 背压、错误无目标写、饱和与 reset。native 数值函数本身不在本稿重新实现或修改。

适配器不新增通用 role 标签、跨时钟协议、NUM/MEM、任意长度队列或通用调度器；只实现本次 bounded service 的真实载荷保持、拆分、收集、路由和应答。完整 FFN kernel 的数值准入、端到端地址生命周期与物理资格仍由后续证据说明。
