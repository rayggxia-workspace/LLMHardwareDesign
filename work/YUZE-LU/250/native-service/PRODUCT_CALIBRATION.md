# 产品M和原生S128服务回校

本轮仍是**部分校准的时间模型**，不表示完整系统、数值、300MHz或互联通过。
旧core12和统一66拍量化的run08--12全部保留。输入图、RNE次序、KV格式、
权重记录数和DDR事务口径保持；两DDR channel各32beat信用继续全局共享。

M产品费用来自102172、source `e1e823b11a53853ca201fb3d3538c66b7f159738`。
其M/guard是真RTL，S provider为RTT2 host，实际local_s_base时序来自控制agent独立实验。

| 边界 | 周期 |
|---|---:|
| core EXEC→INPUT EOP，才释放W bank | 11 |
| core EXEC→CONTINUE RF2flit EOP | 14 |
| core EXEC→FINAL RF4flit EOP | 16 |
| RF EOP→下一core EXEC最早 | 1 |
| RF-only EOP→guard terminal | 2 |
| FINAL RF EOP→两S128真ACK后terminal，RTT2 | 8 |
| BEGIN8flit首LC→ACK EOP | 11 |
| CREATE首LC→RF EOP | 4 |
| SPILL首LC→两S128 ACK后terminal | 14 |
| RESTORE首LC→terminal，另加32B S读 | 13 |

BEGIN以一个N8 output owner为单位。16entry scope cache与16RF owner一一对应；
同N8跨K128复用。spill每K遍历86个N8/P会驱逐16scope，不能当整projection一次BEGIN。
当前先保守串行收BEGIN与下一个accept，未来有界预装可以和W等待重叠，但必须
真实争LC128请求/响应口。当前完整ALLOC、BEGIN重叠、母控PM和外层scope FSM仍未回校。

G保持纯核68、S frontend107 ACK/108 LCtake；观察max的独立wrapper保持107并提供
known shift，由root102159验证，尚不属于原已验收G硬宏的物理面积。

量化使用root102168真local_s_base逐请求回执：两response owners、32B pack、无新SRAM。
known48事务60拍，fallback80事务95拍（均cmd→done）。模型从冻结请求offset回放，
每个真实S端口只能接一个请求/拍，最多两个有序response owner；端口冲突时延后并传播。
X无合法producer max证据，使用fallback；G输出仅在观察max与真实Mid ACK有效时用known。
本目录的数学/程序没有改变，只修改服务绑定与有限调度。

三源copy、P1/P2→P0 scatter、scale两flit metadata和outer-scope FSM仍需完整联接RTL。
scale寄存器目录采用root正式实现，S512B目录保留为替代负对照。E32、N全S32和动态
S32×S32 QK/AV仍未绑定新硬核；不能把模型的旧时间常数作为这三类服务已实现证据。
