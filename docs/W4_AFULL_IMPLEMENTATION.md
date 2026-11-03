# L4-A-FULL：单M/N/E/S/T的完整Sq2整数Attention

Issue151 / PR152，Melodydt；2026-11-03 Asia/Shanghai。研究输入cddcdc2d38b588d23ffb082eefabaaf1ad606772，实际仿真源码 **08e674a272a74810e761fadd2d047285e0b1e0ff**。首r01 / **95793 / zenanyan-afull / node1 / c64 / 8CPU / COMPLETED 0:0 / 00:04:32**。32预声明CASE和9份真实握手流长度/SHA全部通过。接收范围为固定H1024/Sq2/KV8/Q16/D128的完整合成整数Attention，不是整模型质量或物理资格。

## 1. 本轮真正完成的计算链

从两行原X出发，真实执行input RMS1024→K/V/Q投影→每Q/K head RMS128→split-half64 RoPE→QK缩放→因果Softmax→PV→全16头8192B context→Wo完整K2048→原X残差，输出两行H1024共4096B。K/V各8头，每头只计算一次供相邻两Q复用；Q共16头，未把H/D或head数缩小。

此前[AH2](W4_AH2_IMPLEMENTATION.md)只验证一个KV供两个Q的context，[ATSP](W4_ATSP_IMPLEMENTATION.md)只验证外部Wo切口下的原残差机制。本轮新增一个[顶层](../project/rtl/block_connection_w4/block_w4_afull_top.sv)和[独立TB](../project/tb/block_connection_w4/block_w4_afull_tb.sv)，将其控制和生命周期整合为一套真实资源；不实例化两个旧验证top。原50份RTL/TB/include及历史source-lock不变。

## 2. 资源、控制与同步原理

实际M1/N1/E1/S1/T1，另复用S helper、N-long和E controller；不实例G/R或私有向量数组，没有新独立bridge硬宏。新局控FSM、head/group/chunk循环、holding/MUX、元数据/计数/错误逻辑属于必须预制的有源逻辑。顶层payload holding448bit（3×128+64），含raw capture及输出装包复用；原生宏/helper/controller内部holding、控制flags另计，448bit不是整岛面积预算。

普通S口在LOCAL/N/E间唯一owner，服务直到目的写ACK及响应退休后才交还；loader阶段从真实S宽口向M供A128/B512。M每组沿完整K累加，最后一次RNE/clip并把结果真实写S后才允许CLEAR复用。N保持全组统计、gamma和exact-U16 EXP回放；E负责真实split-half gather后的RoPE及最终残差。母控不逐条发这些op，当前未实现L5通用网络。

| 阶段 | 实际同步门 |
|---|---|
| 接单/输入 | 捕获generation32/version16；448字逐拍核身份/index/last，真实S写ACK后推进，最后ACK后才允许start |
| 原残差保存 | T BEGIN256，真实读S两行原X，T[2g]=X0[g]、T[2g+1]=X1[g]；全256字COMMIT后才input RMS |
| head计算 | 原T保持read index0不take；真实保活检查owner/generation/wordcount/index/last；8KV轮询，每KV服务2Q |
| context→Wo | 每个有效PV结果写S ACK后计数，512字完整建立才准Wo；不把其余head当zero |
| Wo→原残差 | 每8输出组完成64个K32 chunk，READ两行到S256/257；T逐字capture→写S258并等ACK→E加原X→S0/384写ACK |
| T复用 | 最后残差ACK后实际RELEASE原T，才允许第二BEGIN256；最终Y全部填充/COMMIT，256次host take及实际RELEASE后才DONE |

8个A padding字322/323/326/327/330/331/334/335真实写零并逐ACK，仅初始化一次，随后直到全部loader/Wo结束均保活。新增写保护阻止普通writer覆盖；TB逐ACK及每次实际loader数据核对。相对机械复制AH2每chunk重清零，本轮少197624次S写，不能将新计数套回旧AH2。

## 3. 一S一T的容量与布局

| S字地址 | head阶段内容 |
|---|---|
| 0..127、384..511 | 两行完整input Norm，共4096B |
| 128..159 | 共享Q/K head gamma，512B |
| 160..191 | positions0/1的canonical RoPE系数，512B |
| 192..223、224..255 | 当前KV头两行K/V，各512B |
| 256..287、288..319 | 当前Q与head RMS目的scratch，各512B |
| 320..335、336..367 | A容器256B与B staging512B |
| 368..383 | score/exactEXP/P及显式scratch |
| 512..1023 | 两token×16head×128维完整context，8192B |

head阶段S预约4096B Norm+4096B工作区+8192B context=16384B；原X4096B放T，T宏仍6KiB且仅一笔事务。最初参数暂放S512..575，input Norm全部结束后真实搬到128..191，才允许context覆盖。所有context结束后Norm生存期结束，Wo最终输出可写S0..127/384..511。T先原残差、后最终输出两笔串行事务，峰4096B，不能把余下T容量当可并发第二lease或随机RAM。

## 4. 参数流、数值与布局

四语义matrix K0/V1/Q2/Wo3；K/V head0..7、Q head0..15、Wo head0；group7、chunk6分别覆盖投影16×32、Wo128×64；seq16恰0..24575。一个请求在途，每请求16个128bit字/256B，全部6MiB真实传输（K/V各1MiB、Q2MiB、Wo2MiB）。权重tile-major byte offset=64×tile+8×column+k，不能把列连续32K镜像裸接。完整ABI见[端口与生命周期合同](rtl-contracts/AFULL_PORTS_AND_LIFETIME.md)。

S16 Fin10、S8 Fin7，投影/Wo全K最后RNE7；QK factor2896、RNE25；PV RNE14；E RoPE shift14、残差shift0。input/head RMS epsilon_code1对应2^-20，不精确等于源1e-6。Q/K使用同一个split-half64置换保持dot，V始终原轴，context按token→global Qhead→channel供Wo；M rows2载体READ index0/1/8/9，不能用0/1/2/3。EXP按exact U16写回再读取，P Fin14；count1/2实现真正因果前缀。

version0是合法身份；version/generation在admission捕获，不是启动装载控制程序。provider只提供参数，不能修改固定算法顺序；本端点不是实际外存控制器。成品M11/M12永久绑定、程序ROM和八样本能力并集尚未实现。

## 5. 错误与恢复范围

接单即有终态义务，包括部分输入/prestart取消；DONE保持generation/error/sat/partial/words。任一接受的旧/未来/错权重tag、version/index/last或provider error均errorDONE且该坏拍不发S写；非WEIGHT_RX时w_ready0，不承诺无界晚流排空。provider须与局部错误/reset协调，禁止拿此边界当通用MEM恢复。

原生loader/M/N/E错误、helper边界注入、T元数据错误、padding破坏均停止正常推进并协调复位本地参与者；原生S无error pin，helper注入不构成新增硬件检测。已写S或已接受最终输出前缀不回滚，partial记录host前缀；hard reset取消而不补DONE。正常任务消费DONE后无需reset复用。局部同钟域恢复、有限字段和定向注入不等于全系统原子性或任意late事件隔离。

## 6. 实际服务器验证

三fixture为base/future_changed/boundary，done saturation false/false/true从冻结文件读取。未来fixture仅改X1，实际token0全部256个context字和128个最终Y字与base bit一致；boundary真实input RMS及最终原残差正负clip。四个完整正常job（3fixture及最后恢复）核对以下全部计数；其它CASE含早停/取消/输出前缀，不当完整模型帧。

| 每成功完整job | TB实际通过的计数断言 |
|---|---:|
| 普通S请求/ACK | 各806408=205984读+600424写 |
| M命令/响应 | 各30336；EXEC24896、READ3616 |
| loader /S宽读 | 24896 /198144（A宽读98816+B宽读99328） |
| A128 /B512实际拍 | 197632 /99328 |
| N服务/原生命令 | 82 /2340 |
| E服务/原生input/output | 1024 /1024/1024 |
| 权重请求/128bit拍 | 24576 /393216，共6291456B |
| T BEGIN/COMMIT/RELEASE | 各2；write/take各512（raw256+Y256） |
| 最终host输出 | 256字/4096B |

混合全局原文为 `cycles=43920722 jobs=35 X=12997 Sreq=7045523 Sack=7045522 M=264773/264773 N=29645/29645 E=8961/8961 wreq=213582 W=3417144 Ttake=3074 Trelease=12 host=1025 done=32`。35次接单减3次hard reset形成32次DONE，32CASE不是32个正常任务；host=4×256+前缀1。Ttake/release中4个正常任务贡献2048/8，其余定向错误、取消、复位贡献1026/4；一个在途S请求被复位取消，故全局S请求比ACK多1。该混合统计不能代替成功帧守恒断言或用于整模型吞吐/300MHz系统结论。

32预声明CASE严格顺序通过：完整stage数值、共享KV/全部head、512context ACK门、padding保活、实际A/B布局、全K Wo、原T保活/逐字capture ACK、两次释放、输入/权重metadata、背压、原生错误、helper边界、T错误metadata不take、取消/reset/输出prefix/heldDONE与正常恢复。raw T元数据注入位于两RMS已覆盖原S后的首投影阶段；不声称每phase穷尽。

独立golden从数学定义计算，完整head投影24576、Wo6144共30720个raw dot从实际tile-major权重另行全K重算，另有QK192/PV12288、6291456编码、S16重构/乘积、1025EXP数学节点及RNE/负例。base Wo2048元素非零、0clip；逐个省略head改变2040–2047个Y元素，交换head改变2047个，错误KV共享改变2048个；不以退化全零样例冒充全head验证。以上数学probe不扩大为任意native内部partial或模型质量资格。

每fixture实际input7168B、weights6291456B、output4096B，共9份握手直接导出流，其长度/SHA与独立golden及固定合同全部一致。18输入与Git blob及服务器SHA核对，75生成文件前后核固定SHA；已实收14文本并逐SHA核对，导出归档SHA `3bea6984aa0efd9e14a31d2e01c3ebb40df35f9e018c1d8f4ee3640538a34e54`，9actual流再次核对。原始参数、binary及build只留本人服务器。[真实回执](../work/Melodydt/151/afull/evidence/runs/r01/results/run-receipt.json)、[证据索引](../work/Melodydt/151/afull/evidence/evidence-manifest.json)、[交付检查](../work/Melodydt/151/afull/final-checks.json)。

Verilator5.042/g++11.4.0/Python3.10.12，固定容器SHA与全部argv见回执；--assert开启，-j8构建、单线程仿真，只-Wno-fatal，不关闭RTL warning类别。保留46warnings（12TIMESCALEMOD、15WIDTHEXPAND、19WIDTHTRUNC），非lintclean。首r01通过，未隐藏失败或覆盖重跑；旧50源回归、完整模型推理/质量和EDA未执行。

## 7. 交付、复现与下一步

服务器yuzelu@10.129.166.172；任务/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/afull-cddcdc2-20261103，工作input-r01，结果runs/r01，日志slurm/zenanyan-afull-95793.out/.err及runs/r01/logs。真实submit和18输入manifest已留证。复跑使用新input/output/job，不覆盖r01；所有RTL编译/仿真仅服务器。

当前主攻仍L4：本轮退出的是固定Sq2完整A整数链。下一 **L4-AF1024** 将完整A的两行Y真实交给F1024，明确独立参数/gamma、存储ACK、父子终态和T释放；固定纵向组合不自动成为L5通用端点。代表性trained质量、官方框架/W8、其它样本变体分别保留门；旧24GAP不放宽。L5母控/一般跨岛、D/H/X、MEM/永久产品程序/共同底座物理尚待各自验收。

研究目录afull-cddcdc2/integrated为隔离API部分包，无.git/HEAD/index/暂存；task151→task143，不改main/旧包/PDF/ref-project。PR152待外部审查，Issue交付回in_review而非done；登记PR5 pending，看板unverified/同步pending，处理人待指定，非已证实权限拒绝。最终资料commit见PR回执。
