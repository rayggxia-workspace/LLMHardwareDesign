# A16：H8、两token因果Attention整数合同与独立预期

Issue151/PR152，研究输入`f665230a392cbcf2422594167e1f163d5e5d1c80`；native7078786。固定单head、Sq=Sk=2、D/H8、无bias/cache的有界A_plain计算链：原S16 X→RMS→QKV→真实相邻pair RoPE→QK→因果Softmax→PV→Wo→原X残差。实例化M/N/E/S/T各1，不使用G/R。新路径不是全部真实模型、完整L4或跨岛/MEM/物理验收。

## 1. 输入、数值与源保留

27×128bit共432B：X0/X1各8S16 Fin10，四份8×8权重S8 Fin7，gamma8S16 Fin10，两个位置各8S16 Fin14的RoPE系数。有效336B，六字padding共96B实际canonical零；27个真实ACK后才启动。X0在448、X1在452，原字及其padding不覆盖；权重456..471、gamma472、系数473/474。

RMS逐行执行native整数定义，epsilon_code1（XFin10时对应real epsilon2^-20）：`root=isqrt(floor(sum(x*x)*2^16/8)+2^16)`，`factor=floor(2^38/root)`，`clipS16(RNE30(x*factor*gamma))`输出Fin10；两行结果480/481，482/483为实际零。没有Norm→S8转换，原残差始终是原完整X。

| 阶段 | 精确整数单位/舍入 | 物化位置 |
|---|---|---|
| Q/K/V | A16 Fin10×B8 Fin7，factor1/left0；M op5 0x107，RNE7/clipS16→Fin10 | Q488/489、K490/491、V492/493 |
| RoPE | adjacent-pair `(a*c-b*s,b*c+a*s)`，系数Fin14，全中间一次RNE14/clipS16；native E9 | 完整读A/B后原地址488..491写ACK |
| K布局 | 第0/1列分别K0/K1，其余6列真实零；每列8S16 | 496..503 |
| V布局 | 第h列`[V0[h],V1[h],0..0]`，每列8S16 | 504..511 |
| QK | A16/B16 rawFin20×signedS16 factor11585(Q15)；op5 0x119，RNE25/clip→scoreFin10 | 512/513 |
| Softmax | row0 count1、row1 count2；EXP精确U16、factor floor(2^44/sumEXP)、RNE30→非负S16Q14 | EXP514/515、P516/517，518/519零 |
| PV | PFin14×VFin10 rawFin24，factor1；op5 0x10e，RNE14/clip→Fin10 | context520/521，522/523零 |
| Wo | A16Fin10×B8Fin7，factor1，op5 0x107 RNE7/clip→Fin10 | 524/525 |
| 最终 | E0原X448/452+Wo524/525，S16饱和加，Fin10 | 528/529；T按row0,row1输出 |

两个M格式都是rows2/tiles1/K8/N8，A/B基址4字对齐。A16/B8 EXEC0x11885；QK/PV A16/B16 EXEC0x11887。每投影CLEAR6/SCALE4/EXEC10/READ5 index0,1,8,9，共7命令；每次M结果先保存，再复用同一M。op5的四S32容器各取low16、按行/half拼回，不把EXEC状态当tensor。

## 2. 真正因果mask与真实RoPE

不能用八lane中把未来score置零模拟mask。native N目标count逐行为1、2，STATS、EXP及概率回放全按该count；EXP/P余下7或6个lane实际写零。因此row0概率必为`[16384,0,0,0,0,0,0,0]`，与未来K1的score大小无关。row1接收两项。N命令总数**20**：RMS两服务各4，Softmax两服务各6；masked lane少不代表BEGIN/STATS/FINAL/EXP/FACTOR/PROB少发命令。

常规系数由theta10000、位置0/1独立数学生成：第p对角度`position/10000^(2*p/8)`，cos/sin按Q14 nearest ties-even取整；位置1不是identity。选定测试另有position1各对90度系数`[0,16384]`的合成数值fixture。原生E9使用相邻pair布局，不能声称已经适配实际模型的split-half等其他RoPE布局。

golden0/1只改变X1，权重/gamma/系数/X0相同，要求row0最终字完全相同、row1最终字不同。第一行两组结果均`e07d0fedf8100622fbb00348fee6ffad`。第二行分别`f07e0bfcf87a05fbfbc6029ffeae0005`与`f8560b9cf0761377e85c1b7ce09b2318`。这是选定整数计算链的因果性质检查，不是模型准确率声明。

## 3. 数据历史和逐阶段检查

独立`a16_integer_reference.py`为单文件、标准库、自包含；不import旧task参考、不读取新RTL/DUT输出作期望。EXP由math公式重建1025节点，并以Decimal高精度逐节点交叉后与冻结native表验证；RNE用Fraction、root用独立二分交叉。

`a16-contract-vectors.json`有10组输入与全部Norm、QKV plain/rotated、K/V列、raw M、scores、EXP/P、context、Wo、final及stage saturation。`S_write_history_hex`保存每个地址的每次期望写入；Q/K488..491先plain再RoPE，共两次，不用最终RAM值替代中间态检查。每正常帧恰73次写记录，TB按真实S接受逐次核对，读返回用该时刻已建立的历史版本。

10组覆盖真实RoPE基线、未来token变化、zero gamma原X保真、signed/nonunity gamma、zero rows、正负饱和、quarter-turn稀疏布局、两组固定LCG随机。zero gamma时两行最终输出逐位等于原X，确保没有S8窄化。所有阶段saturation OR到done_saturated，与协议error独立；不承诺全部输入/错误组合已穷举。

## 4. 事务计数、TB与执行边界

普通S103=73写+30读：27入口，6个padding，RMS8事务，6次M投影共12结果写，RoPE12事务，K布局10、V布局10、Softmax10、残差6、最终读2。M42cmd/rsp、6loader、14个native宽读、12个A128 beat、8个B512 beat；N4服务/20native、E6服务、T2字。S448..529包络82字1312B、T32B只作为本切片预约，不把hole当免费共享资源。

`block_w4_a16_tb.sv`自包含全部literal函数；没有TB include。正常计数、A两行/B半矩阵、M四row/half载体、N causal count/原EXP回放、S中间写历史、E阶段、两字输出index/last及末尾T RELEASE均有检查。30预声明CASE包括输入ACK/早start/heldstart、N/M/loader/E返回背压、两个输出之间prefix abort、partial/prestart/running abort/reset、held DONE+abort+ready、N非法opcode、QK/Wo EXEC错误、RoPE/残差E错误、S helper边界error及Softmax第二目的ACK待回abort。S边界注入不是原生S错误检测器；已接受RAM写和已消费第一输出字不回滚。

严格成功行是`PASS_W4_A16 cases=30`，详细全局计数另在`A16_STATS`。contract独立列CASE集合/compile_sources/include_dirs/TB SHA，不从日志反向定义预期。已执行的Python检查仅是数值/文件准备检查，**不是SV编译器**，不能再以其通过担保词法或RTL可执行；实际源码编译/功能只认根任务服务器Verilator回执。

生成器可在正式`work/Melodydt/151/`单独使用：vectors脚本`--root`读取固定native EXP表，reference SHA从脚本同目录读取；`--directory`仅是输出，TB生成器从同目录vectors生成源码及合同。native include仍需`project/rtl/block_v2`。不依赖本机旧draft。所有新RTL执行按用户授权仅服务器、Melodydt目录；本代理没有启动任何RTL/远程任务。
