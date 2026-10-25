# Block 库分层验收与剩余缺项（Issue91/93/97）

2026-10-25；负责人 Liangruizhi。依据已保存的80/82/84/85/92/93及[97实际回执](experiments/issue-97-v-consumer.md)。当前已有**原始gate/up→专用SiLU/整512量化→驻留A→实际M→merge/residual→流式norm的Granite整数消费者切片**和选定raw门级重放；仍不能写成M/V/A/R/S/D六Block电路设计均完成。旧84网表的86/88门级/电气结果不继承给93/97；新物理由98单独验证。

已有算子与Block逻辑候选可以指导设计。物理边界、宏和制造前固定接口的最终验收需要新的整合与实现证据。

## 验收等级

| 层次 | 需要的可复查证据 | 不能拿来替代它的证据 |
| --- | --- | --- |
| L0 有界合同 | 计算/状态/精度/生命周期/地址/端口/命令/非法条件，有限库存及明确缺项 | 模块名或画框图 |
| L1 整数参考与服务 | 独立参考、真实张量边界、溢出/round/saturation、有限资源逐项记账 | BF16跑通、浮点假量化、仅脚本存在 |
| L2 完整切片RTL | 实际消费者算术由RTL完成；有界存储/端口/ready-valid、错误/恢复、独立receiver；同precision/input/resource比较 | host提供中间结果、无界FIFO、孤立算术单元、只测正常一次 |
| L3 电路/实现候选 | 综合库存、存储宏/ROM/时钟/复位、网表与RTL等价、时序、slew/cap/扇出、布局布线与PVT约束 | 排除memory后的logic-area、理想黑盒STA、cycle数 |
| L4 完整库/产品映射 | M/V/A/R/S/D整合、多代表工作负载、合法容量/端口、端到端数据与数值闭包、设计规则/可制造性、制造前固定与产品后定制边界 | runtime cache开关、单一K/H消费者或一次映射 |

91本身只新增L0及符号地址结构验收。93新增流式gamma及H2560完整norm的有界L2；97新增专用V→实际M完整切片的L2及选定零延迟raw门级证据。后者是L3所需的部分证据，未达到含宏/时序/物理的完整L3。

## 逐Block 当前证据与完成门槛

| Block | 当前证据 | 主要未完成项与下一条最小门槛 |
| --- | --- | --- |
| M 矩阵/部分和 | 82/84/85及97实际8个S8 MAC/INT32；K512、8专家、H1536；97消费RTL产生的驻留A/δ，owner/version/epoch与旧host δ拒绝、RQ/merge/residual/流式norm完整L2及选定raw gate | 仍非16×16阵列或通用GEMM。通用tile/K/端口吞吐、P/KV宽格式、共享byte-MUL入口、M的H2560及多工作负载映射待实现；新网表宏/时序/物理由98，不线性外推周期 |
| V 向量/宽算术/非线性 | 80独立typed byte程序仍独立；93流式gamma全行norm、97专用SiLU/MID/完整512最小δ/A8→实际M已接收；宽RNE/abs/compare/address及缓存寄存计入70,102.970µm²新逻辑图 | 通用80 V ISA/byte ALU/程序与ROM仲裁整合未完成。97选择外部C0 LUT，无片内ROM宏；专用数据通路不能称通用向量库。SFU/ROM真实宏、并行服务与跨算子合法调度待闭合 |
| A 注意力/KV | 既有Qwen/Llama真实整数参考、状态/端口服务及边界分析 | 没有完整QK→online softmax→PV RTL。概率与KV可宽于S8，S16/S32分解、max/sum/exp/reciprocal/rescale、因果窗口/KV生命周期与统一端口缺少电路闭包；先做一个完整共享GQA组且精度/状态不偷换 |
| R 递推状态 | Qwen3.5/Falcon连续整数、范围/重定标和服务证据；[Issue99](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/99)独立完整head状态RTL已启动、in_progress，当前不计作已通过 | old/shadow状态原子提交、溢出恢复、有限statebuffer、S16/S32宽乘法/重对齐/宽累加须由99实际接收；规范/脚本不代表完成。norm SFU成功不等于支持R更新，连续错误不可污染已发布state |
| S 存储/互联 | 93/97实际16KiB128bit1RW；93 H2560全行统计+256gamma块释放512B候选frame空间；97 MID→M输出生命周期复用、A4KiB保留、有限响应/排空/lease/恢复/canary已验 | 仍为行为wrapper，不是8×32KiB多bank库存或宏资格。真实宏、读写语义、bank/仲裁/guard/metadata/缓冲、ECC若采用则另计；外部320bit+控制FIFO和tag物理布线未含核心面积 |
| D 数据/命令控制 | 85/92单命令/有限响应/epoch终止；97实际V→M→norm排空与参数锁存、地址窗/alias校验和错误恢复；92门锥性质属于92源，97有本top真实边界注入 | 尚非通用DMA/二维stride/gather/scatter/dispatch/图同步或91的64B描述符取指。97未作新top普遍形式证明，门级子集未含Q故障注入；通用队列/credit/多context/CDC与制造后路由要另验 |

上述完成门槛不是要求同时扩大六模块。已闭合有界专用V/S消费者；后续在已冻结硬件库存下逐一添加A/R闭包；不为了凑完整库而追加无关模型或改原精度。

## 必须单独核算的库存边界

- 当前可引用的算术为8×S8、1×S32和128-bit SFU。S16×S16至少4个8-bit片段、S32×S32至少16个，只有乘法数下界；符号、carry、round、读写和仲裁追加成本。A/R的状态更新不能免费加入这张表。
- 16KiB SRAM与512B frame不能相加后继续声称16KiB；128KiB LUT与64-bit外部程序不是同一块ROM。共享M lane用于byte MUL必须增加可实现的输入/输出选择及非乘ALU。
- 85的两路S32响应各64bit属于核心，外部恢复测试2×(128+32)=320bit加control属于未综合环境。整合后每个tag/holder/line寄存必须有来源、生存期或新增计费。
- 91 gamma状态112逻辑bit、两端口路由68bit、命令512bit、8专家delta128bit是显式逻辑义务；不能直接相加当综合FF，也不能因可能复用旧寄存就记0。93/97已有各自mapped寄存/组合面积回执；这些逻辑义务不能用简单求和替代真实图，新增模块仍须重新综合。

## 物理边界收敛的判据

制造前固定哪些有源计算、SRAM、SFU/ROM端点和局部连接；产品确定后允许更换哪些金属连接/路由或配置，须与成员Issue55/63的交付协调。当前runtime cache开关只证明运行时访问方式，**没有证明金属定制可制造、跨产品互联可行或端到端PPA获益**。

下一版边界比较须同时固定：数值合同、算术单元及频率约束、容量/端口/物理传输粒度、scale/状态元数据、所有程序与LUT流量、输入输出及重读成本。分别报告数值通过、功能RTL通过、资源映射、STA、电气、布局布线和完整验收状态；任何一个失败不能被其它指标的收益抵消。

当前有界顺序：[V/S合同](V_S_INTEGRATION_CONTRACT_V1.md)→93流式gamma→97专用SiLU完整消费者已形成证据；[Issue98](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/98)对新93/97网表推进受限物理，[Issue99](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/99)并行补R，实际在线GQA的A RTL仍缺。通用V ISA、A/R整合、宏/PVT和产品定制资格均未完成。项目仍在研究与电路实现推进中。
