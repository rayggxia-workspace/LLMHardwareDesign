# A8服务器Verilator警告逐项审阅：r03失败与r04功能通过

本报告只读root下载的r03/r04源码指纹、完整build log、simulation log及receipt，不运行本地或远程仿真，不修改旧叶、旧controller或旧TB，也不代替外部PR批准。当前A8 top仍为SHA `f6e52569b6a675caf781b7c5a917073127edcabc06cf14d80d539fb787581fc1`，未为消警改源码。

结论：所列全部警告已定位并检查，当前固定源码、合法计数/地址和原生生命周期边界内未发现实质数值或握手bug。r04是保留全部警告的功能测试通过，**不是lint clean**；不将结论扩大为全部参数、四状态等价、完整Attention或物理验收。

## 1. 实际结果与警告数量

| 运行 | 实际结果 | 警告类别及数量 |
| --- | --- | --- |
| r03/job95115 build-n | 默认warnings fatal，exit1；profiles为空，尚无simulation通过 | 33：TIMESCALEMOD18、WIDTHEXPAND13、WIDTHTRUNC2 |
| r04/job95116 build-n及simulate-n | exit0，完整唯一N29 CASE通过 | 同样33条 |
| r04 build-f8及simulate-f8 | exit0，完整唯一F8 25 CASE通过 | 29：TIMESCALEMOD18、WIDTHEXPAND8、WIDTHTRUNC3 |
| r04 build-a8及simulate-a8 | exit0，完整唯一A8 26 CASE通过 | 36：TIMESCALEMOD18、WIDTHEXPAND16、WIDTHTRUNC2 |

r04共98次warning发生，其中54条timescale、37条扩展、7条截断；跨r03/r04为60个唯一“类别/路径/行/列/消息”定点，重复出现不等于多个独立bug。JSON保留每次发生的原文、路径、源SHA、具体理由及run归属，未删消息。

r04实际编译argv只有 `-Wno-fatal` 这一warning开关，没有按类别关闭warning；`--timing --assert`继续启用。该选项只使warning不导致默认非零退出，不关闭断言、CASE、native错误测试或背压检查。三个simulation均exit0，完整预声明case集合分别29/25/26、无缺失/额外/重复，终结数量一致。实际build/sim log SHA与receipt相符；r03仍是失败证据，未被重标PASS。

## 2. 18处生产模块timescale提醒

12个native module和6个已锁controller/top未声明独立timescale，而N/F8/A8 TB有1ns/1ps。逐文件与对应run input SHA核对；去注释检查未发现生产RTL中有 #delay、$time/$realtime/$stime、time/timeunit/timeprecision或specify等依赖本地时间单位的语句。当前行为为时钟事件驱动和整数运算，warning不改变该同步周期关系。

其中N core与旧N controller只报告timescale，没有本次log中的算术位宽warning。其它未展开模块被语法纳入不代表获得新功能资格。未来若加入delay、时间计算、SDF或门级仿真，应重新明确时间单位，不能把本结论作为永久豁免。

新A8 top此次没有单独的算术/握手warning，不能据此声称整个编译lint clean；编译单元的timescale指令继承也不等于A8已具备门级时序资格。

## 3. 两类生产位宽警告的实际安全边界

**旧W3 G控制器total_pairs（F8 build，L71）。** 5-bit `(count+1)>>1` 赋给3-bit total_pairs。合法count1..8得到1..4，全部可表示；F8固定count8得到4。count9..15可能产生更大值，但同一request的非法count guard直接进入error RESPONSE，不进入STREAM或目的写，因此截断值不会被当合法计数使用。没有修改G数学或pipeline retirement，不因warning给非法请求扩权。

**原生T的payload索引（F8/A8 build，L56/L61）。** payload有384项，索引只需9bit，received/cursor使用10bit。合法BEGIN保证word_count1..384；FILL写入时received从0到word_count-1，接受最后字后进入SEALED；READ_REQ的cursor由BEGIN归零；READ_HOLD仅在cursor+1小于word_count时refill，否则进入RELEASE。因此有效访问均在0..383，不会因高索引位被丢弃而alias。当前F8/A8实际只测一字T，不把静态范围推理说成384字穷举或新的原生T物理资格。若内部状态损坏或协议/复位前提被破坏，这个推理不自动成立。

## 4. 旧N TB的15条位宽提醒

n_words返回8bit、赋给integer32或参与word索引，当前W1..33，扩展不丢值。普通S地址10bit与integer32比较/减法，真实事务位于100..432，完整10bit保留；结果/EXP索引0..32。opcode4、mode2、count16/native_count4扩展成32bit，固定count1/8/9/257及合法native chunk1..8均精确表示。命令顺序、raw-vs-EXP、gamma、tail、总数和存储断言未因此减弱。

store任务address32赋给host_addr10是实际截断，但所有调用为base100/200/300/400加k0..32，最大432，高位零。source1023/count9的越界guard直接使用10bit request字段，不经过store，不能用它的拒绝结果证明任意host地址截断安全。

另一WIDTHTRUNC在 `&& n_count%8`：逻辑操作按非零真值转换，不是仅取余数最低位；当前固定count余数为0或1，用来写脏tail，后续mask断言仍在。更广泛generator输入应显式检查地址/count范围，而不是依赖这份有界审阅。

## 5. F8与新A8 TB的扩展提醒

F8的RNE64在quotient上加逻辑0/1，扩展至64bit后保留当前有界两补码运算；down与residual两个signed16先符号扩展到64bit相加再clip16，避免把测试期望在16bit内先wrap。地址10bit扩成stage lookup的integer32不会丢地址。F8这8条均是TB期望/检查侧，不是新生产数据通路截断。

A8同类RNE0/1扩展以及64-bit结果与signed16冻结lane的比较保留符号和值；有效QK/PV范围可放入S16。S地址/待应答地址扩展到integer32用于stage查表，448..468可表示，unused462/463另有禁止访问断言。read-half布尔 `(m_phase==4)` 扩到6bit cmd_index比较或32bit carrier查表参数，值0/1完全保留；opcode4扩到32bit期望比较仍检查全部opcode。没有将native EXP转signed score或把prob当S8。

## 6. 接受范围与后续纪律

本次没有为消警改native、旧controller/TB或A8 top；新A8只新增外侧组合。已审源码均与相应run指纹匹配，native14/common控制器仍受runner固定锁校验；对“旧32SV整体未变”的完整清单仍以root基线检查为准，不把本次仅被编译/警告涉及的文件冒称完整tree重验。

允许warning非致命是本轮显式编译策略，不能用来自动批准未来warning。出现新类别/位置须另审；真实断言、故障注入、完整CASE、工具/源SHA及退出码仍为接受门。r04支持N/F8/A8所列有限功能和工具组合，不代表四状态/X传播等价、所有ModelSim行为迁移、全模型数值、全部合法连接或PPA通过。

## Exact warning location index (all entries assessed)
The JSON records every occurrence with original message and source SHA. Repeated TIMESCALEMOD messages are not distinct bugs.
| Category | Source:line:column | Seen in | Assessment |
| --- | --- | --- | --- |
| TIMESCALEMOD | `project/rtl/block_v2/block_v2_e.sv:5:8` | r03/n, r04/n, r04/f8, r04/a8 | No timing-dependent production operations found after comment removal; clocked integer behavior is unaffected by missing local timescale in current source. Recheck if delay/time/SDF behavior is added. |
| TIMESCALEMOD | `project/rtl/block_v2/block_v2_g.sv:3:8` | r03/n, r04/n, r04/f8, r04/a8 | No timing-dependent production operations found after comment removal; clocked integer behavior is unaffected by missing local timescale in current source. Recheck if delay/time/SDF behavior is added. |
| TIMESCALEMOD | `project/rtl/block_v2/block_v2_m.sv:5:8` | r03/n, r04/n, r04/f8, r04/a8 | No timing-dependent production operations found after comment removal; clocked integer behavior is unaffected by missing local timescale in current source. Recheck if delay/time/SDF behavior is added. |
| TIMESCALEMOD | `project/rtl/block_v2/block_v2_n.sv:3:8` | r03/n, r04/n, r04/f8, r04/a8 | No timing-dependent production operations found after comment removal; clocked integer behavior is unaffected by missing local timescale in current source. Recheck if delay/time/SDF behavior is added. |
| TIMESCALEMOD | `project/rtl/block_v2/block_v2_n_group.sv:2:8` | r03/n, r04/n, r04/f8, r04/a8 | No timing-dependent production operations found after comment removal; clocked integer behavior is unaffected by missing local timescale in current source. Recheck if delay/time/SDF behavior is added. |
| TIMESCALEMOD | `project/rtl/block_feed_v1/block_feed_loader.sv:6:8` | r03/n, r04/n, r04/f8, r04/a8 | No timing-dependent production operations found after comment removal; clocked integer behavior is unaffected by missing local timescale in current source. Recheck if delay/time/SDF behavior is added. |
| TIMESCALEMOD | `project/rtl/block_feed_v1/block_feed_m.sv:5:8` | r03/n, r04/n, r04/f8, r04/a8 | No timing-dependent production operations found after comment removal; clocked integer behavior is unaffected by missing local timescale in current source. Recheck if delay/time/SDF behavior is added. |
| TIMESCALEMOD | `project/rtl/block_feed_v1/block_feed_s16k.sv:4:8` | r03/n, r04/n, r04/f8, r04/a8 | No timing-dependent production operations found after comment removal; clocked integer behavior is unaffected by missing local timescale in current source. Recheck if delay/time/SDF behavior is added. |
| TIMESCALEMOD | `project/rtl/block_feed_v1/block_feed_s_macro.sv:4:8` | r03/n, r04/n, r04/f8, r04/a8 | No timing-dependent production operations found after comment removal; clocked integer behavior is unaffected by missing local timescale in current source. Recheck if delay/time/SDF behavior is added. |
| TIMESCALEMOD | `project/rtl/block_library_v1/block_v1_r.sv:4:8` | r03/n, r04/n, r04/f8, r04/a8 | No timing-dependent production operations found after comment removal; clocked integer behavior is unaffected by missing local timescale in current source. Recheck if delay/time/SDF behavior is added. |
| TIMESCALEMOD | `project/rtl/block_v1/shared121.sv:3:8` | r03/n, r04/n, r04/f8, r04/a8 | No timing-dependent production operations found after comment removal; clocked integer behavior is unaffected by missing local timescale in current source. Recheck if delay/time/SDF behavior is added. |
| TIMESCALEMOD | `project/rtl/block_v1/transaction6k.sv:4:8` | r03/n, r04/n, r04/f8, r04/a8 | No timing-dependent production operations found after comment removal; clocked integer behavior is unaffected by missing local timescale in current source. Recheck if delay/time/SDF behavior is added. |
| TIMESCALEMOD | `project/rtl/block_connection_p2/block_p2_s_ctrl.sv:6:8` | r03/n, r04/n, r04/f8, r04/a8 | No timing-dependent production operations found after comment removal; clocked integer behavior is unaffected by missing local timescale in current source. Recheck if delay/time/SDF behavior is added. |
| TIMESCALEMOD | `project/rtl/block_connection_w3/block_w3_e_ctrl.sv:4:8` | r03/n, r04/n, r04/f8, r04/a8 | No timing-dependent production operations found after comment removal; clocked integer behavior is unaffected by missing local timescale in current source. Recheck if delay/time/SDF behavior is added. |
| TIMESCALEMOD | `project/rtl/block_connection_w3/block_w3_g_ctrl.sv:4:8` | r03/n, r04/n, r04/f8, r04/a8 | No timing-dependent production operations found after comment removal; clocked integer behavior is unaffected by missing local timescale in current source. Recheck if delay/time/SDF behavior is added. |
| TIMESCALEMOD | `project/rtl/block_connection_w3/block_w3_ffn8_top.sv:5:8` | r03/n, r04/n, r04/f8, r04/a8 | No timing-dependent production operations found after comment removal; clocked integer behavior is unaffected by missing local timescale in current source. Recheck if delay/time/SDF behavior is added. |
| TIMESCALEMOD | `project/rtl/block_connection_w4/block_w4_n_ctrl.sv:5:8` | r03/n, r04/n, r04/f8, r04/a8 | No timing-dependent production operations found after comment removal; clocked integer behavior is unaffected by missing local timescale in current source. Recheck if delay/time/SDF behavior is added. |
| TIMESCALEMOD | `project/rtl/block_connection_w4/block_w4_f8_top.sv:5:8` | r03/n, r04/n, r04/f8, r04/a8 | No timing-dependent production operations found after comment removal; clocked integer behavior is unaffected by missing local timescale in current source. Recheck if delay/time/SDF behavior is added. |
| WIDTHEXPAND | `project/tb/block_connection_w4/block_w4_n_tb.sv:424:81` | r03/n, r04/n | n_words8 expands to integer32; W1..33, no loss. |
| WIDTHEXPAND | `project/tb/block_connection_w4/block_w4_n_tb.sv:460:48` | r03/n, r04/n | Expected phase boundary W1..33 expands to integer32. |
| WIDTHEXPAND | `project/tb/block_connection_w4/block_w4_n_tb.sv:467:44` | r03/n, r04/n | Expected memory sequence W1..33 expands to integer32. |
| WIDTHEXPAND | `project/tb/block_connection_w4/block_w4_n_tb.sv:475:40` | r03/n, r04/n | Expected read/write classifier W1..33 expands to integer32. |
| WIDTHEXPAND | `project/tb/block_connection_w4/block_w4_n_tb.sv:498:16` | r03/n, r04/n | Unsigned S address10 expands for expected address32 comparison; preserves all10bits. |
| WIDTHEXPAND | `project/tb/block_connection_w4/block_w4_n_tb.sv:499:55` | r03/n, r04/n | Address10 expands before subtraction of300/400; checked writes are300..332 or400..432, indices0..32. |
| WIDTHEXPAND | `project/tb/block_connection_w4/block_w4_n_tb.sv:499:80` | r03/n, r04/n | Address10 expands before subtraction of300/400; checked writes are300..332 or400..432, indices0..32. |
| WIDTHEXPAND | `project/tb/block_connection_w4/block_w4_n_tb.sv:511:12` | r03/n, r04/n | Opcode4 expands for integer expected-op comparison; no lost opcode bits. |
| WIDTHEXPAND | `project/tb/block_connection_w4/block_w4_n_tb.sv:512:20` | r03/n, r04/n | Unsigned mode2 expands against param32; unexpected high param bits remain detectable. |
| WIDTHEXPAND | `project/tb/block_connection_w4/block_w4_n_tb.sv:514:30` | r03/n, r04/n | count16 or native chunk4 expands to integer32; fixed count1/8/9/257 and word0..32 give remaining1..257, chunk1..8. |
| WIDTHEXPAND | `project/tb/block_connection_w4/block_w4_n_tb.sv:514:16` | r03/n, r04/n | count16 or native chunk4 expands to integer32; fixed count1/8/9/257 and word0..32 give remaining1..257, chunk1..8. |
| WIDTHEXPAND | `project/tb/block_connection_w4/block_w4_n_tb.sv:514:77` | r03/n, r04/n | count16 or native chunk4 expands to integer32; fixed count1/8/9/257 and word0..32 give remaining1..257, chunk1..8. |
| WIDTHTRUNC | `project/tb/block_connection_w4/block_w4_n_tb.sv:527:41` | r03/n, r04/n | Test host address32 truncates to10; every store call uses100/200/300/400 plus k0..32, max432, so high bits zero. Guard address1023 is a separate direct request field. |
| WIDTHEXPAND | `project/tb/block_connection_w4/block_w4_n_tb.sv:537:22` | r03/n, r04/n | n_words-1 expands within0..32; n_count%8 under logical && means nonzero truth conversion, not LSB-only arithmetic truncation. Fixed remainder0/1; dirty-tail assertions retained. |
| WIDTHTRUNC | `project/tb/block_connection_w4/block_w4_n_tb.sv:537:24` | r03/n, r04/n | n_words-1 expands within0..32; n_count%8 under logical && means nonzero truth conversion, not LSB-only arithmetic truncation. Fixed remainder0/1; dirty-tail assertions retained. |
| WIDTHTRUNC | `project/rtl/block_connection_w3/block_w3_g_ctrl.sv:71:16` | r04/f8 | (count+1)>>1 computed as5bits then stored3bits. Legal count1..8 gives1..4, all fit. Invalid count>8 immediately enters error RESPONSE; truncated total_pairs is never used by STREAM/write. F8 count is fixed8. |
| WIDTHTRUNC | `project/rtl/block_v1/transaction6k.sv:56:13` | r04/f8, r04/a8 | Payload has384entries and requires9-bit indexing, while received/cursor are10bits. Legal BEGIN enforces1..384; FILL accesses received0..word_count-1 then leaves FILL; READ_REQ cursor starts0. READ_HOLD refills only when cursor+1<word_count. Accessed index is0..383. Actual F8/A8 tests use1word; no claim of exhaustive384word test. |
| WIDTHTRUNC | `project/rtl/block_v1/transaction6k.sv:61:36` | r04/f8, r04/a8 | Payload has384entries and requires9-bit indexing, while received/cursor are10bits. Legal BEGIN enforces1..384; FILL accesses received0..word_count-1 then leaves FILL; READ_REQ cursor starts0. READ_HOLD refills only when cursor+1<word_count. Accessed index is0..383. Actual F8/A8 tests use1word; no claim of exhaustive384word test. |
| WIDTHEXPAND | `project/tb/block_connection_w4/block_w4_f8_tb.sv:241:132` | r04/f8 | Logical RNE increment0/1 expands to64bit addition. Two-complement addition preserves signed rounded value for these bounded products; no new arithmetic loss. |
| WIDTHEXPAND | `project/tb/block_connection_w4/block_w4_f8_tb.sv:258:48` | r04/f8 | Signed16 down/residual operands sign-extend to64 before addition passed to clip16; this is intentional widening and preserves overflow for the later clip. |
| WIDTHEXPAND | `project/tb/block_connection_w4/block_w4_f8_tb.sv:258:48` | r04/f8 | Signed16 down/residual operands sign-extend to64 before addition passed to clip16; this is intentional widening and preserves overflow for the later clip. |
| WIDTHEXPAND | `project/tb/block_connection_w4/block_w4_f8_tb.sv:299:31` | r04/f8 | Unsigned10bit address/pending_addr expands to integer32 for address comparison, subtraction or stage lookup. Actual addresses448..475 fit and all10 bits are preserved; invalid stage addresses are separately rejected. |
| WIDTHEXPAND | `project/tb/block_connection_w4/block_w4_f8_tb.sv:299:93` | r04/f8 | Unsigned10bit address/pending_addr expands to integer32 for address comparison, subtraction or stage lookup. Actual addresses448..475 fit and all10 bits are preserved; invalid stage addresses are separately rejected. |
| WIDTHEXPAND | `project/tb/block_connection_w4/block_w4_f8_tb.sv:301:137` | r04/f8 | Unsigned10bit address/pending_addr expands to integer32 for address comparison, subtraction or stage lookup. Actual addresses448..475 fit and all10 bits are preserved; invalid stage addresses are separately rejected. |
| WIDTHEXPAND | `project/tb/block_connection_w4/block_w4_f8_tb.sv:301:34` | r04/f8 | Unsigned10bit address/pending_addr expands to integer32 for address comparison, subtraction or stage lookup. Actual addresses448..475 fit and all10 bits are preserved; invalid stage addresses are separately rejected. |
| WIDTHEXPAND | `project/tb/block_connection_w4/block_w4_f8_tb.sv:308:41` | r04/f8 | Unsigned10bit address/pending_addr expands to integer32 for address comparison, subtraction or stage lookup. Actual addresses448..475 fit and all10 bits are preserved; invalid stage addresses are separately rejected. |
| WIDTHEXPAND | `project/tb/block_connection_w4/block_w4_a8_tb.sv:297:94` | r04/a8 | RNE increment is Boolean0/1 widened for64bit addition; bounded signed QK/PV computations fit64bits. |
| WIDTHEXPAND | `project/tb/block_connection_w4/block_w4_a8_tb.sv:301:36` | r04/a8 | Signed16 frozen score/output lane sign-extends to64 for comparison with integer rounded result; no lost sign or value. Bounded legal inputs fitS16. |
| WIDTHEXPAND | `project/tb/block_connection_w4/block_w4_a8_tb.sv:304:25` | r04/a8 | Signed16 frozen score/output lane sign-extends to64 for comparison with integer rounded result; no lost sign or value. Bounded legal inputs fitS16. |
| WIDTHEXPAND | `project/tb/block_connection_w4/block_w4_a8_tb.sv:333:25` | r04/a8 | Unsigned10bit S address expands to integer32 for input order/stage lookup. Actual448..468 preserved; forbidden unused462/463 are rejected, not aliased. |
| WIDTHEXPAND | `project/tb/block_connection_w4/block_w4_a8_tb.sv:333:81` | r04/a8 | Unsigned10bit S address expands to integer32 for input order/stage lookup. Actual448..468 preserved; forbidden unused462/463 are rejected, not aliased. |
| WIDTHEXPAND | `project/tb/block_connection_w4/block_w4_a8_tb.sv:335:140` | r04/a8 | Unsigned10bit S address expands to integer32 for input order/stage lookup. Actual448..468 preserved; forbidden unused462/463 are rejected, not aliased. |
| WIDTHEXPAND | `project/tb/block_connection_w4/block_w4_a8_tb.sv:335:28` | r04/a8 | Unsigned10bit S address expands to integer32 for input order/stage lookup. Actual448..468 preserved; forbidden unused462/463 are rejected, not aliased. |
| WIDTHEXPAND | `project/tb/block_connection_w4/block_w4_a8_tb.sv:334:18` | r04/a8 | Unsigned10bit S address expands to integer32 for input order/stage lookup. Actual448..468 preserved; forbidden unused462/463 are rejected, not aliased. |
| WIDTHEXPAND | `project/tb/block_connection_w4/block_w4_a8_tb.sv:345:37` | r04/a8 | Unsigned10bit S address expands to integer32 for input order/stage lookup. Actual448..468 preserved; forbidden unused462/463 are rejected, not aliased. |
| WIDTHEXPAND | `project/tb/block_connection_w4/block_w4_a8_tb.sv:347:63` | r04/a8 | Unsigned10bit S address expands to integer32 for input order/stage lookup. Actual448..468 preserved; forbidden unused462/463 are rejected, not aliased. |
| WIDTHEXPAND | `project/tb/block_connection_w4/block_w4_a8_tb.sv:347:101` | r04/a8 | Unsigned10bit S address expands to integer32 for input order/stage lookup. Actual448..468 preserved; forbidden unused462/463 are rejected, not aliased. |
| WIDTHEXPAND | `project/tb/block_connection_w4/block_w4_a8_tb.sv:347:23` | r04/a8 | Unsigned10bit S address expands to integer32 for input order/stage lookup. Actual448..468 preserved; forbidden unused462/463 are rejected, not aliased. |
| WIDTHEXPAND | `project/tb/block_connection_w4/block_w4_a8_tb.sv:369:45` | r04/a8 | Half selector (m_phase==4) is Boolean0/1, widened to cmd_index6 or integer function argument32. Both expected half values remain exact. |
| WIDTHEXPAND | `project/tb/block_connection_w4/block_w4_a8_tb.sv:375:96` | r04/a8 | Half selector (m_phase==4) is Boolean0/1, widened to cmd_index6 or integer function argument32. Both expected half values remain exact. |
| WIDTHEXPAND | `project/tb/block_connection_w4/block_w4_a8_tb.sv:375:128` | r04/a8 | Half selector (m_phase==4) is Boolean0/1, widened to cmd_index6 or integer function argument32. Both expected half values remain exact. |
| WIDTHEXPAND | `project/tb/block_connection_w4/block_w4_a8_tb.sv:381:21` | r04/a8 | Native opcode4 expands to integer32 expected-op comparison; no opcode truncation. |
