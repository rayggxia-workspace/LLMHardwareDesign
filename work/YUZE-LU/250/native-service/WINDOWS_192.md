# 192列候选：实际S地址、搬运和存活期

以下是待接入LC外层scope FSM的合同。当前SystemC有字节与端口时间模型，
尚没有该scatter地址生成器的独立RTL回归。每个S地址单位为16B/128bit，
合法范围0..1023。所有最终存储都等真实S ACK。

## 实例与列分派

一个8列M结果归属 `p=(col/8)%3`。满192列时每P64列，gate/up各8个
输出context，共16RF。最后一轮first=10944、chunk=64，三P分别24/24/16列。
每个context按K=0,128,...,1920依次更新，不改变每K128的RNE/累加次序。

P0为G服务地点。它保存两个256项S32环形平面（gate/up各1KiB）；
`r=global_col%256`。G每次处理原来的128值，起点只会是r=0或128，
因此每个gate/up输入都是合法连续512B窗口，没有让G跨私有S直接寻址。

第一轮192值后消费0..127、保留128..191；下一轮192..383映射到
ring192..255与0..127。此时恰好256值，依次消费128..255、256..383。
没有超过256值/2KiB的时刻。最后严格累计86个128值G/量化组。

## 一组明确可放进16KiB的地址分配（条带候选）

| S窗口 | P0 word地址 | P1/P2 word地址 | 字节/存活期 |
|---|---|---|---|
| normalized X | 0..255 | 0..255 | 4096B，phase1全程；全部gate/up完成后释放 |
| normalized MidA16条带 | 256..719 | 256..719；P2只用到703 | 7424/7424/7168B，逐组生产ACK后有效，phase2完成最后一次A读取后释放 |
| gate输入/暂存 | 720..783 | 720..735 | P0 1024B环形；P1/2各256B，复制到P0并获ACK后才可覆盖 |
| up输入/暂存 | 784..847 | 736..751 | 同上 |
| G输出Mid32临时 | 848..879 | 不占 | 512B，G最后写ACK后交量化，量化最后读取后释放 |
| 归一化A16临时 | 880..895 | 不占 | 256B，复制到条带所有目的ACK后释放 |
| S中控制预留 | 896..927 | 752..783 | 各512B，保守预留；RF/权重/A/guard寄存器不重复算进S |

正式实现选择寄存器目录，因此P0 phase1峰值14848B，余1536B。P1/P2更小。
两颗256B A tile、4×1152B W bank、512B RF、2×32B结果槽及G的96B
保持槽均为另计的真实寄存器/宏电路，不隐藏到上表余量。

phase2释放X、gate/up和G临时区。每P输出S32最多86×32=2752B；
复制来的A16使用256B临时S窗，再由原A frontend逐S128读到两颗256B寄存器。
shift进入这两颗A lease的12bit寄存器，不占第17个S数据word。
保守phase2最大10944B（Mid7424B、最终输出2752B、A临时256B、控制512B）。输出从P.S送到U.S、
U写ACK后才释放P结果。私有SRAM始终16KiB，没有另加共享池。

spill对照不保留22,016B Mid条带；其2752B Down状态与X、2KiB gate/up
环、G临时512B、A临时256B和控制512B合计10176B。它必须
每K128做真实RESTORE/SPILL及其控制帧、S读写ACK；不能只套M的12拍。

## FINAL写回、scatter gather与ACK

P0的M FINAL直接写canonical ring：gate/up基址加`((col/4)&63)`，
每8值两word。跨256边界需要真实LC地址加法/掩码，不能默认为连续递增。
P1/P2写各自暂存，局部值索引为
`floor((col-first)/24)*8 + ((col-first)%8)`。

P1/P2向P0复制每个128bit word时，目标地址由原全局col和way计算。
源16B保持到P0真实写ACK；P0确认相应epoch/tile/way/col已到齐才发G。
同一时刻只有一个源选择后的copy route；P1、P2按顺序搬运，不能把
两者都当成独占P0端口。source本地S读与destination P0 S写也必须仲裁。

现有linear early-copy无法直接实现packed→interleaved scatter。
合法选择是新增有限的affine/scatter地址发生器，或每8值/每way发一次
32B linear-copy描述符并收费；只改金属不能实现地址置换。满192列时
每P1/P2有16个32B段。新发生器的metadata/加法器、端点及物理时序需计账。

单源无背压连续copy的真实FSM给出32word首请求至末ACK130拍。
故512B gather不能只按32读+32线+32写=96拍验收。P0自身若直接写ring，
无须额外self-gather读；G的真实输入读取已经包含在107/108拍服务里。

## phase2三源Mid分发

Mid tile t归属P[t%3]、本地索引floor(t/3)。一次256B数据+独立scale帧搬运必须先
从真实源S读取，再向三个P的临时S窗写入（同源同目的也收费），各自真ACK
后才能由A frontend再读16word、取对应scale。原生A LOAD独占66拍已经
102140证实；独立两slot预取只允许与旧tile的M重放重叠，不能增加端口。
整个copy/LOAD过程中源S也与本P正常动作共用ordinary S128资源。

root已实做的每个`a_scale_directory32`保存32×6bit shift、32valid和共享key/kk，
约51B控制寄存器；每P为X与Mid放两实例，约102B。X采用stride1，Mid源
采用stride3，索引`(kk-first)/128/3`并检查余数。源各29/29/28项可放下。
接收P不会在目录里保留全部86项，只将当前两A lease的shift与完整object/kk绑定。
COPY携两128bit metadata flit（session/gen/kk/shift/ticket/fullkey），源数据ACK与
接收目录publish或A捕获ACK共同决定释放。约32B有界控制保持槽不属于SRAM。
两flit协议的实际时间线尚待提供；模型4/8拍仅是明确的候选敏感性，不能当实测。

旧S512B宽目录是替代负对照：每P32个16B条目，phase1=15360B，
phase2=11472B，spill=10688B；它还有第17个S word读写。该方案不对应
正式寄存器目录RTL，不能把两者的省面积与省周期交叉选取。

这需要真实三源selector及地址发生器；generic-source与串行guard实验
可作为复用基础，但当前完整192环形scope的程序/RTL/布线仍需联合验收。
