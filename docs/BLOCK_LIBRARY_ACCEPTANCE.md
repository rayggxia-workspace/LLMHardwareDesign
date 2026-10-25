# Block 库分层验收与剩余缺项（Issue91）

2026-10-25；负责人 Liangruizhi。依据当前实际80/82/84/85源码及其已保存验收；新86/88/92结果必须读对应PR/实际netlist后再更新，本表不预判其通过。当前成果是**一条有实际M的Granite消费者切片及若干算术/协议RTL**，不能写成M/V/A/R/S/D六Block电路设计均完成。

已有算子与Block逻辑候选可以指导设计。物理边界、宏和制造前固定接口的最终验收需要新的整合与实现证据。

## 验收等级

| 层次 | 需要的可复查证据 | 不能拿来替代它的证据 |
| --- | --- | --- |
| L0 有界合同 | 计算/状态/精度/生命周期/地址/端口/命令/非法条件，有限库存及明确缺项 | 模块名或画框图 |
| L1 整数参考与服务 | 独立参考、真实张量边界、溢出/round/saturation、有限资源逐项记账 | BF16跑通、浮点假量化、仅脚本存在 |
| L2 完整切片RTL | 实际消费者算术由RTL完成；有界存储/端口/ready-valid、错误/恢复、独立receiver；同precision/input/resource比较 | host提供中间结果、无界FIFO、孤立算术单元、只测正常一次 |
| L3 电路/实现候选 | 综合库存、存储宏/ROM/时钟/复位、网表与RTL等价、时序、slew/cap/扇出、布局布线与PVT约束 | 排除memory后的logic-area、理想黑盒STA、cycle数 |
| L4 完整库/产品映射 | M/V/A/R/S/D整合、多代表工作负载、合法容量/端口、端到端数据与数值闭包、设计规则/可制造性、制造前固定与产品后定制边界 | runtime cache开关、单一K/H消费者或一次映射 |

本91新增的是L0合同及符号地址结构验收。没有增加L2/L3完成项。

## 逐Block 当前证据与完成门槛

| Block | 当前证据 | 主要未完成项与下一条最小门槛 |
| --- | --- | --- |
| M 矩阵/部分和 | 82/84/85实际8个S8 MAC、INT32 acc；Granite K512、8专家、H1536，RQ/merge/residual/norm完整切片；runtime cache与sharedS32有独立接收 | 不是候选16×16阵列或通用GEMM。通用tile/K/端口吞吐、P/KV宽格式、共享byte-MUL入口、H2560行地址、resident-A输入及owner/scale校验需实现；不可把现有特例的周期线性外推到全M |
| V 向量/宽算术/非线性 | 80独立18typed byte程序RTL、512Bframe、单128KiB数据ROM、外部1.93MB程序；82/85专用精确norm和共享S32 | 两套库存尚未整合。91冻结frame覆盖、程序/LUT部署及新增byte ALU/mux成本；下一步gamma streaming及SiLU→512粒度A8→真实M完整闭包。非线性LUT和SFU必须真实仲裁，C0外置/C1片内ROM不能冒充同库存 |
| A 注意力/KV | 既有Qwen/Llama真实整数参考、状态/端口服务及边界分析 | 没有完整QK→online softmax→PV RTL。概率与KV可宽于S8，S16/S32分解、max/sum/exp/reciprocal/rescale、因果窗口/KV生命周期与统一端口缺少电路闭包；先做一个完整共享GQA组且精度/状态不偷换 |
| R 递推状态 | Qwen3.5/Falcon连续整数、范围/重定标和服务证据 | old/shadow状态原子提交、溢出恢复、有限statebuffer、S16/S32乘法/重对齐/宽累加与控制尚非完整RTL。norm SFU只做当前norm运算，不等于支持R更新；先同一连续序列，错误后不可污染已发布state |
| S 存储/互联 | 82/85实际16KiB 128bit单1RW wrapper和有限响应；cache占4KiB，reset不擦SRAM | 不是8×32KiB多bank库存。需选真实宏、读写语义、跨bank分配/冲突与仲裁、guard/metadata/缓冲、ECC若采用则另计；91仅单bank实用容量。当前SRAM blackbox不代表真实宏时序已合格 |
| D 数据/命令控制 | 85一个命令在途、cmd_ready/accept、epoch与有限响应，有实际恢复测试 | 不是通用DMA/二维stride/gather/scatter/dispatch/图同步。91的64B入口描述符是候选；通用队列/credit/错误传播/epoch终止态须实际整合。92修复验收单列，不能以85常规恢复自动覆盖epoch耗尽 |

上述完成门槛不是要求同时扩大六模块。先闭合对当前Block边界有影响的V/S整合，然后在已冻结硬件库存下逐一添加A/R闭包；不为了凑完整库而追加无关模型或改原精度。

## 必须单独核算的库存边界

- 当前可引用的算术为8×S8、1×S32和128-bit SFU。S16×S16至少4个8-bit片段、S32×S32至少16个，只有乘法数下界；符号、carry、round、读写和仲裁追加成本。A/R的状态更新不能免费加入这张表。
- 16KiB SRAM与512B frame不能相加后继续声称16KiB；128KiB LUT与64-bit外部程序不是同一块ROM。共享M lane用于byte MUL必须增加可实现的输入/输出选择及非乘ALU。
- 85的两路S32响应各64bit属于核心，外部恢复测试2×(128+32)=320bit加control属于未综合环境。整合后每个tag/holder/line寄存必须有来源、生存期或新增计费。
- 91 gamma状态112逻辑bit、两端口路由68bit、命令512bit、8专家delta128bit是显式逻辑义务；不能直接相加当综合FF，也不能因可能复用旧寄存就记0。实际mapped寄存/组合面积留待新netlist。

## 物理边界收敛的判据

制造前固定哪些有源计算、SRAM、SFU/ROM端点和局部连接；产品确定后允许更换哪些金属连接/路由或配置，须与成员Issue55/63的交付协调。当前runtime cache开关只证明运行时访问方式，**没有证明金属定制可制造、跨产品互联可行或端到端PPA获益**。

下一版边界比较须同时固定：数值合同、算术单元及频率约束、容量/端口/物理传输粒度、scale/状态元数据、所有程序与LUT流量、输入输出及重读成本。分别报告数值通过、功能RTL通过、资源映射、STA、电气、布局布线和完整验收状态；任何一个失败不能被其它指标的收益抵消。

当前有界推进顺序：[V/S合同](V_S_INTEGRATION_CONTRACT_V1.md)→同库gamma流式RTL/协议→SiLU完整消费者→新增库存综合/电气→按实际瓶颈推进A/R。Issue88电气试验并行；未收到正式证据前本文件不宣称其完成。项目整体仍为研究与电路实现推进中。
