# Issue82 冻结协议 2026-10-25 UTC+08

依赖PR81@7ad23a7；独立task/82-norm-circuit、D:/Projects/LLMHardwareDesign-norm-circuit；真实计算只本人CPU服务器lrz-i82-*。精度保持旧74/80：I32Q12输入、gammaS32Q20、U128 sumsq、floor/H+epsilon17、isqrt(var<<40)、RNE((x*gamma)<<12/den)→I32Q12。无FP或近似倒数；非法H/epsilon、零den、溢出拒绝。

三配置：0为一个unsigned8x8乘法器分16步组成signed32乘法，1步div/sqrt；1为专用32x32乘法器、同1步SFU；2为专用乘法器、每周期4步SFU。保持同16KiB/128bit单1RW，x/output原位、gamma另区，H<=1536；控制/寄存/line buffer、scale metadata/打包/反压全部计费。新增专用单元实际综合计面积，不称同面积。byte基线80的512B frame不同，不跨库存宣传收益。

最小集：两原norm8、H1/非4倍数/零/极值/负gamma边界、旧两层token0/64/71完整1536hidden；三配置×静默/事务编号背压。独立bigint/isqrt/RNE、实际改码重SHA拒绝、忙cfg/完成/复位、generic及原Nangate45非制造研究库logic-only面积；宏/STA不伪填。

接续真实M完整消费者：复用旧74 W8/midA8，完整K512与八专家/H1536，经Q31 RQ、gateQ15完整merge、0.22Q20、真实residual到完整norm。若未闭合，明确M与host边界，不以捕获acc或host中间运算冒充RTL。实际源数据/矩阵接口物理128bit传输、metadata及buffer要记账。

不新增模型、软件、其他机器、Phi或成员55/63范围；旧数据只读，独立source/out，失败原样保留。记录每phase commit/config/input/result SHA、真实命令/日志/独立接收、报告/交接及PR。登记PR5 pending；board/read:project缺失则待同步，不done/不自合并。
