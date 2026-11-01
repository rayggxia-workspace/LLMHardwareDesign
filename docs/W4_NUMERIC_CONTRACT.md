# W4 N与有界preNorm F8独立数值合同

Issue151 / PR152；研究parent `0101cc7e1e6d5718455fb45b61c7428439efc09a`，native `707878621b2add4ed218b8c43df2e95c9a56e2ba`。本子包只写独立Python参考、冻结输入/预期、SV TB及证据读回。ModelSim由根任务实际执行，本代理没有启动RTL仿真、服务器或物理流程。

## 1. N精确整数定义

输入raw均为signed S16，每字8元素；count为整个组有效元素数。RMS/L2的gamma为signed S16，名义Q10；epsilon是非零U32的**raw平方码单位**，不是未经换算的模型浮点epsilon。统计使用原始raw，源与gamma直到组回放结束保持同版本。

令 `Q=sum(x*x)`，整数除法向下取整：RMS的 `radicand=floor(Q*2^16/count)+epsilon*2^16`；L2去掉除以count。`root=floor(sqrt(radicand))`，`factor=floor(2^38/root)`；每个输出 `clipS16(RNE30(x*factor*gamma))`。gamma=1024得到Fin10输出。本参考用整数Newton求根，并以独立二分求根交叉；除法为Python无限精度整数除法。Signed RNE以floor商、非负余数和保留位奇偶处理正负ties，不使用向零截断或普通算术右移替代。

Softmax score为S16 Fin10。数学LUT独立重建 `round(exp(-16+i/64)*32768), i=0..1024`，节点nearest ties-even；对 `score-global_max` 做步长16raw的RNE插值，低于-16384为0、非负为32768。输出EXP是**U16精确码0..32768**；先全部实际写S并ACK，再 `factor=floor(2^44/sumEXP)`，回放同一EXP码得到 `clip[0,16384](RNE30(EXP*factor))`，概率为非负S16 Q14。32768的EXP不能解释成负S16；概率和因整数舍入不承诺恰为16384。

源表只用于版本/逐节点一致性验证，不作为生成预期的输入；没有用DUT输出构造expected。EXP1025节点与native表全部一致；F8沿用的G四函数2564节点也从数学式重建并全部一致。表SHA、脚本SHA及逐阶段预期在两份vectors JSON及运行回执中保存。这证明选定整数合同一致，不证明连续RMS/Softmax误差、模型精度或全参数域质量。

## 2. N首个适配profile

`block_w4_n_ctrl`的首profile是mode0/1/2、count1..257、实际S范围合法且所用区域互不重叠；无in-place。它是当前实现的有界准入限制，不把其他合法连接从长期目录删除。每字count=min(8,remaining)，输入/gamma尾部实际mask零、输出尾部零。

Norm程序：BEGIN → 所有raw STATS → FINALIZE → 每字raw和gamma重读 → op5 → 实际目的写ACK。W=ceil(count/8)时，native命令/应答2+2W，普通S为3W读+W写=4W ACK。

Softmax程序：BEGIN → 所有raw STATS → FINALIZE → 每字raw重读/op3/EXP写ACK → op4 → 每字EXP原码重读/op6/目的写ACK。native为3+3W，S为3W读+2W写=5W ACK。257项有33个输出字，最后字只有lane0有效；末项新max必须先影响整组统计，再重读所有原score生成EXP。

局控保留N组，整个服务独占S helper owner；每次S响应先take/capture再发下一次访问。请求和完成均保持到握手。准入错误在BEGIN前返回error，可直接重试；已经进入native服务后的任何native/helper响应错误置poison，完成消费后仍busy、不接新服务，必须协调reset controller/N/helper后复用。目的写已被RAM接受时，即使后续ACK错误也不能撤销；TB检查第二目的字ACK错误时前两字仍可见，后续字不写。S本身没有error输出，TB通过适配服务的mem_rsp_error输入注入故障，不声称原生S新增了错误功能。

## 3. F8明确scale与数据生存期

16×128入口布局保留W3：x8 S8 Fin7、三个8×8权重S8 Fin7，n-major；有效200B，56B x组padding实际写零。程序/shape/地址/参数固定，仅tensor数据可变，无启动装载程序。

| 阶段 | 固定数值及真实存储 |
|---|---|
| 原X | signextend到S466的8S16 Fin7，直到残差完成保持 |
| RMS | gamma8×1024写S475；src466/dst474，eps1/count8；输出8S16 Fin10 |
| 投影A | 实际新增RNE右3+clipS8 Fin7逻辑；打包低64、高64零并写ACK到S448；449..451仍为零。E12不提供此RNE功能 |
| gate/up | A8 Fin7×B8 Fin7；M op5 S16 RNE4→Fin10，S464/465 |
| mid | G fn0 gated1，SiLU(gate)×up，RNE10/clipS16 Fin10，S468；469..471实际零 |
| down | M A16 Fin10×B8 Fin7，op5 S16 RNE7→Fin10，S472 |
| 原残差/输出 | E7只读原S466，左3→S467 Fin10；E0与down加/clip→S473，T一字输出后release |

N、RNE3窄化、M/G/E已观察到的saturation逐阶段OR到done_saturated，协议error独立。normal输入RMS `[203,-406,608,-811,1014,-1217,1419,-1622]`，窄化投影 `[25,-51,76,-101,127,-128,127,-128]`；最终 `fbfe037bfce80286fdfa0175ff1e0099`，因窄化clip，sat=true。zero的sat=false。常见输入发生clip是此小核显式定义，不授予产品量化质量。

正常帧39个普通S请求/ACK=29写+10读（包括16入口写），N1服务/4native命令0,1,2,5，M15命令/应答、loader3、E2、G1(4pair)、T1字及release。S448..475预留448B，T一字16B；这些不是整个Block全部物理buffer成本。完成必须在T release后；abort/fault协调清叶生命周期但不回滚已被下游消费的T字或RAM内容。已有DONE仍保持两个flag到唯一一次public take。

## 4. 可复核输入及范围

N11组：RMS8混合/零/极值gamma饱和、RMS1、RMS257、L2带负gamma、L2 257、Softmax257末项新max、等值EXP32768、9项cutoff/舍入、Softmax1。F8六组沿用W3 normal/zero/正负极值/mixed/sparse，各有原输入、N root/factor、projection A、S464..475、stage sat和最终预期。

只接受所列有限profile/向量/协议测试证据。未实现/未验完整A、所有完整F的pre/postNorm位置、任意N phase抢占/跨服务回访、TopK控制服务、真实模型形状/质量、MEM、完整ROM产品程序和物理资格。L4仍包含W5后续纵向集成，不能由本次RMS8或Softmax257单项宣布整个主线完成。
