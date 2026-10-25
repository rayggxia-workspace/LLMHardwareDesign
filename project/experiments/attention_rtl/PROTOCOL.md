# Issue102：有界完整GQA注意力RTL合同（预注册）

负责人Liangruizhi；Issue102，base PR101@5820c223c41327e154869616339dded900609007。只本人CPU服务器新issue102-attention-rtl-20261025/Slurm lrz-i102-*，不下载或重跑模型；98物理/99 R及成员55/63独立。所有actual数组/RTL/map/接收在服务器，本机源码、元数据与字节校验。最终root上传/PR，非done。

## 冻结输入与采样

Qwen/Qwen2.5-3B revision5defd2796acd3cb2051bb4c787eddc7f8f35e113，layer0、KVhead0对应完整8Q heads，d128、B1。61 capture a96eef6175d15173496d674caee7b0078971f2f5，manifest SHA165e8109f8025c8bfafc9079d5a9e40e688897162cf6e9ca48d337efd5c3b5e5，selected-raw.npz SHAe7b8162bae2e8e85962de5e46a32b656ff3e51095149810ea81a779820cf0d10。

64 full回归：prefix128 positions0..3,124..159共40，全部8头；prefix1024 positions1023,1055共2作容量/尾部代表，不重复整矩阵。61真正cached：prefix128 positions128..159共32；prefix1024 positions1024,1055共2。共76真实query×完整8头。先小pilot，再全量两路无等待/确定性等待；独立接收全部有效QK/score/exp/P/PV。不同执行模式分列，不能把full后32行当cached。cached使用真实query与最终cache前缀快照，非逐token写入采集/RTL append。calibration来源和静态KV单位不变，禁止用评价数据调整scale。

原64 full prefix128实际keys160、prefix1024 keys1056；本RTL每query仅访问committed prefix pos+1，不读未来。原64未来QK不在本次执行域，接收明确只裁合法prefix，其他数据一律逐位比较。原捕获FP32→S32Q20、离线KV指数/Q8编码/scale/LUT仍是声明的offline float桥，运行链无浮点。模型质量、native INT8、RoPE/projection未验。

合成边界与真实样本分列：length1和1056零score；P32768→32767；score差16/48 RNE ties、-16 LUT端点和略小于端点；完整8头。非法长度/scale/address、数值溢出、只读LUT故障导致Psum guard拒绝；失败保留，不用有利输入替换真实失败。

## 数值与资源

保持64函数：Q8[-127,127]×K16[-32767,32767]三平衡radix128 S8；I32QK，常数94906266 Q30×I32经S64产品和RNE shift=18-Qe-Ke→S32Q12。其他倍率首版拒绝。max仅合法前缀；exp[-16,0]grid128查U32Q30，差<-65536输出0，RNE索引。U64sum，每row至少一个exp=2^30；U128 SFU除法实际128迭代，加余数RNE与P15上饱和。先验证Psum<=32769+ceil(active/2)，再三非负P limbs×三平衡V limbs，9S8产品+shift/add得PV32。V scale固定，输出单位2^(Ve-15)。maxT1056对应budget33297、保守PV limb前缀界1365976128；非online O证明。

三遍score：QK写score+max；读score/exp求sum；再次读score/exp求P；之后独立PV阶段。不能称online。8S8+一个S32服务+现有SFU、一个16KiB128bit1RW；同预算A切片不等于M/A已物理共享。独立controller/service边界保留；额外8路累加、宽shift/RNE/compare、lineholder/metadata/FSM/mux均综合计费。

S字节布局：Q[0,1024)，metadata保留[1024,1280)，score[1280,5504)，P[5504,7616)，K/V共用16key tile[7616,11712)，8头PV[11712,15808)，scratch保留[15808,16320)，64B canary[16320,16384)。只一条query，8头顺序执行，KV按头重复读取如实计入。一个tile先完整装载/应答再消费；PV tile读写八路输出累加，全输出归约完整后才能发布。不凭空增加SRAM端口或buffer。

C0 LUT128KiB：保留97原SiLU/exp2字节，新增expQ30对象offset0x12010，8196逻辑B/8208物理B、2049字合法；SHA659e0c81ddb592f49e27443dcfe89b9cf88439512cfba613dcd161950e5b6f80。旧91padding只对这一个新对象版本升级，不能混用旧exp2Q24。每次lookup一次有限外部128bit事务，无免费ROM/cache。K/V分别在DATA窗独立、对齐、无alias。ROM/SRAM宏面积、外部控制/320bit测试FIFO和epoch布线另列，不混入logic-only。

## 协议与验收

单命令，锁存owner/version/epoch、位置/长度、KVscale/Qscale、地址/格式；同owner/version的K/V单位和base不可变；新version明确新cache。window必须0。S写也等应答，response保持直到take。外部request/take显式mask reset/abort；softabort取消发布、增加不回卷epoch，旧响应只discard不写S；max终止须协调fabric硬reset。所有服务排空后发布，done保持至ack；无隐式无限队列。配置仅idle，reset/abort同拍无假握手。

每case不硬reset；连续不同token、参数pin突变、busy冲突、阶段abort/恢复、迟到旧响应、错误后恢复、terminal边界、canary均实际核验。无等待/确定性等待两路；大epoch后门边界若采用必须声明RTL-only且读真实边沿，不推到gate。门级只选正常完整8头，独立数学oracle与对应RTL记录逐项比较。

独立receiver不import本输入producer，参考64独立receiver与bigint/Fraction；重新从捕获检查编码，重算有效QK/score/exp/P/PV，严格键/类型/源SHA/输入域。真实写盘修改JSONL并重SHA必须拒绝，不以纯SHA失败替代语义负例。实际库存/逻辑面积、cycles、S操作、LUT、payload/5×128bit packet/header、等待、元数据分别报告。无宏/STA/RC/CTS/PVT资格，非完整六Block设计完成。

## 审阅修订：单注册缓存与调用者提交边界

2026-10-25根审查发现只记最近owner/version不能防A→B→A旧版本重用。正式版冻结一个owner，首次合法命令后到协调hardreset前不得改变；input_version必须非零、单调不回卷，旧版本拒绝。同版本K/V地址与scale不可变、committed length不倒退；softabort保留该注册记录。更大version显式替换缓存，旧版本失效，不能恢复旧标签。合成三例version修订为1000/1001/1002，原input01中100+length会逆序；仅标签改变，所有张量/编码/LUT字节保持并留input01失败/旧运行证据。

length是调用者承诺已完成写入的有效KV前缀；RTL核范围、position+1、同版本单调及访问域，**不**自主验证外部写应答或append完成。没有KV写接口；不宣称硬件append/淘汰或全cache coherence。

库存接收首版发现动态索引vacc造成generic memory对象；正式版使用8个显式固定下标I32累加寄存器，避免将256bit寄存误称第二SRAM。radix shift用固定case0/7/14/21/28译码，新增mux/宽移位仍计入实际映射，不靠generic乘法器数量宽松判定。
