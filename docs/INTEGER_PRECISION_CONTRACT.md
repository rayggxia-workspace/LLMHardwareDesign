# 候选整数精度合同 v0.1（Issue33）

2026-10-23，Liangruizhi；[Issue33](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/33)。
这是待验证的数值/实现候选，不是底座已经支持的能力。接续PR26@2cd9ca15，
不改写其作者文档，不把已有FP32/BF16容量、端口周期或放置收益换算为INT8结论。

## 本机与师兄分工

本机只做缩小算子、已有Qwen3-0.6B少量真实张量、策略/端口与适用RTL验证。
Qwen3-0.6B是普通注意力结构参考，不新增其他Qwen3模型必跑项。
不下载3–4B/更大模型，不做长上下文或多模型GPU测量，不启动其他机器任务。
师兄16GB显卡优先Qwen3.5-4B等代表的较长上下文、真实状态与量化质量；
Qwen3-4B不再必跑。结果到达由用户通知后才核验/整合，当前不安排师兄作业。

## 原始规范审读范围与缺口

仅定向读取main@1a98e9d的llaccel gemm_engine/vec_engine/attn_engine与openTPU VPU/DSP，
没有主动维护、重算或完整审计ref-project。来源路径/原字节身份在
`work/Liangruizhi/33/reference-audit.json`。

- llaccel GEMM为8位有符号乘法、INT32累加；bias相加是33位，M<2^31的后处理乘积用64位；
  INT8/INT16输出，向量SiLU/RoPE/乘法涉及16位乘法与更宽临时值。RMS有48位平方和、
  isqrt与udiv；SiLU有两次sigmoid ROM读及插值，不能认为这些都能由单周期INT8 MAC完成。
- 保存的源调用llaccel_pkg、llaccel_luts_pkg及NUMERICS.md，完整定义/表项未随该包提供。
  rshr64负半值/大移位、mulshift64全域、LUT原始表及isqrt/udiv完整边界/延迟均不能据名称推定。
  单独的源码hash回执不是包体或规范；本任务不声称逐位复现llaccel。
- openTPU VPU导入otpu_fp，且MX列末有宽整数计算；其浮点后处理不能充当无浮点目标硬件依据。
  openTPU/llaccel现有物理案例不能验证下述新候选能力。

## 公共整数规则 C1-RNE

二进制补码，零点0。W8/A8接口范围[-128,127]；离线对称量化可仅用[-127,127]子集，
必须记录实际取值范围。`acc=ΣqA*qW`逐步检查INT32，overflow是错误，不隐式wrap或饱和。
无bias时，K*16384<=2^31-1给出保守正界K<=131071；K131072的全(-128)*(-128)
恰为2^31，必须失败。bias/残差另加并重新核界；本轮32位RQ接口不冒充llaccel的33位bias路径。

候选重新量化：`y=Sat_sB(RNE(acc*M / 2^r))`，B∈{8,16}，M∈[0,2^31-1]，r∈[0,63]。
乘积以有符号64位精确保存；先舍入后饱和。RNE按绝对值商/余数实现，严格大于半值进位，
恰好半值仅奇商进位，最后恢复符号；禁止把负数加正半值后算术右移当RNE。
r=0不舍入，M=0输出0；输入溢出/非法M/r必须拒绝。INT16/INT32转换也使用同一规则。

## 分格式与缩放口径

| 对象 | 候选格式与粒度 | scale/运行时边界 |
| --- | --- | --- |
| 线性权重 | s8，每输出通道，静态 | 真实权重校准；描述性FP32 scale留离线证据，硬件边界传整数M/r或dyadic exponent |
| 输入激活 | s8，静态张量或动态每token/行分别试验 | 动态max/scale若由浮点产生，明确是离线探索；全整数动态scale路径未凭此成立 |
| 部分和 | s32，输入与权重scale的乘积 | 完整K累加后才RQ；每K tile提前RQ是不同函数，不作等效划分 |
| RQ参数 | M:u32（最高位0）＋r:u8（0..63） | 静态每输出通道N组；逐行动态是M×N组，未经证明不能免费因子分解 |
| 向量/SiLU/RMS输入输出 | s16，fraction_bits=12 | 实数=q*2^-12；范围[-8,8)，转换/饱和节点显式，gamma另为s16/f14 |
| KV | s8或s16，独立profile；每head静态或每token-block | scale粒度、有效长度、追加元数据与转换单列；不能从W8A8推定KV格式 |
| softmax score | s16/f8；max差值用更宽无符号数 | 输入来自INT32 score的明确RQ，mask在求max/exp之前处理 |
| probability | P7:s8非负0..127/127；P15:s16非负0..32767/32767 | P7可用原生signed8乘法；P15×V8需要额外实现，质量/成本分别比较 |
| 递推状态 | s32/f20；q/k s16/f14，v s16/f12 | beta/decay:u16/f15；每次宽乘/归约后的RNE和Sat32单列，不宣称完整GDN已整数化 |
| norm/softmax中间值 | 平方和u48、归约/宽乘i64、概率和u64 | 全程范围检查；除0拒绝，isqrt取floor；LUT与常量为版本化输入 |

分格式是本轮可执行候选，不是最终KV/状态/非线性精度决定。除非数据包声明相同q/scale/参数，
不同候选的精度变化不能归因于Block划分。

## 非线性候选与能力成本

- SiLU：独立生成的257项sigmoid表，输入网格[-8,8]、间隔1/16、输出u16/f16，
  高精度Decimal生成后固定原字节SHA。两点线性插值的fraction为8位，插值右移取floor，
  最后x*sigmoid按C1-RNE右移16、Sat16。这不是缺失的llaccel LUT逐位复现。
- RMS候选：u48 `sum(x²)+eps_total`，floor isqrt；u32 gain numerator与root作整数除法，
  inverse用u32，最后`x*gamma*inverse`在i64中RQ。eps/gain常量离线生成并固定，
  gamma/f14、输出/f12；不默认支持浮点sqrt/除法，也不默认与llaccel u16 inverse一致。
- Softmax：独立exp(-i/256)表，i=0..4096、u32/f24，超范围置0；再整数分数除法、RNE，
  P7/P15分开。sum用u64；mask全空拒绝。固定P7可能随长度丢失概率质量，必须保留失败。
- 递推核仅核验已量化、已规范化q/k和beta/decay输入之后的状态更新；这些输入的产生若
  尚为浮点，记作边界外回退/缺口，不能称全整数GDN或模型。

硬件成本候选：一个signed8×signed8乘法器可用radix128非负7位digits实现宽乘；
16×16最坏9个部分积，32×31最坏25个部分积，32×16最坏15个部分积，
16×8可保留原生有符号8位操作数、最坏3个部分积。另需宽累加、移位、取负、舍入/饱和。
Python实现不是硬件速度；串行RQ RTL将单独测握手/延迟，其他wide/非线性仅列算法成本。
恢复除法u32为32迭代、u64为64迭代；u48 isqrt为24迭代，还需相应比较/减法/状态资源。
这些是明确微架构候选，面积/Fmax/能耗未知；ROM至少514B sigmoid、16388B exp，
读端口、lane并行副本、查表延迟和广播不能免费。未实现部分禁止标为硬件已支持。

## 图与物理记账

计算图显式包含quantize/scale、INT32 partial、RQ、round、sat、pack/unpack、状态转换节点。
比较矩阵附近/共享向量RQ时，只有一个相同RQ资源可用，不给近端方案额外算力或存储；
比较相同q/scale/结果与相同调度自由度。物理传输按实际连续span、起始地址、64B beat
和元数据分别计数，不能把FP32字节统一除四；特别保留K tile部分和驻留/搬运、s32状态、
尾拍/缓存深度/静态可达失败。服务周期是假设与本机RTL实测分列，不外推芯片收益。

交接数据见[采集合同](GPU_CAPTURE_CONTRACT.md)；实现/验证进度见Issue33及后续实验报告。
