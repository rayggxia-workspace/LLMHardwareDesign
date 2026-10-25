# Block 库分层验收与剩余缺项（Issue91/93/97/99/102/106）

2026-10-25；负责人 Liangruizhi。依据已保存的80/82/84/85/92/93及[97实际回执](experiments/issue-97-v-consumer.md)。当前已有**原始gate/up→专用SiLU/整512量化→驻留A→实际M→merge/residual→流式norm的Granite整数消费者切片**和选定raw门级重放；仍不能写成M/V/A/R/S/D六Block电路设计均完成。[102完整8头GQA切片](experiments/issue-102-attention-rtl.md)另已形成三遍score整数QK→P15→PV的L2和选定raw gate；非online或KV append。旧84网表的86/88门级/电气结果不继承给93/97/102；93/97新物理由98单独验证，102尚无物理资格。

已有算子与Block逻辑候选可以指导设计。物理边界、宏和制造前固定接口的最终验收需要新的整合与实现证据。

## 验收等级

| 层次 | 需要的可复查证据 | 不能拿来替代它的证据 |
| --- | --- | --- |
| L0 有界合同 | 计算/状态/精度/生命周期/地址/端口/命令/非法条件，有限库存及明确缺项 | 模块名或画框图 |
| L1 整数参考与服务 | 独立参考、真实张量边界、溢出/round/saturation、有限资源逐项记账 | BF16跑通、浮点假量化、仅脚本存在 |
| L2 完整切片RTL | 实际消费者算术由RTL完成；有界存储/端口/ready-valid、错误/恢复、独立receiver；同precision/input/resource比较 | host提供中间结果、无界FIFO、孤立算术单元、只测正常一次 |
| L3 电路/实现候选 | 综合库存、存储宏/ROM/时钟/复位、网表与RTL等价、时序、slew/cap/扇出、布局布线与PVT约束 | 排除memory后的logic-area、理想黑盒STA、cycle数 |
| L4 完整库/产品映射 | M/V/A/R/S/D整合、多代表工作负载、合法容量/端口、端到端数据与数值闭包、设计规则/可制造性、制造前固定与产品后定制边界 | runtime cache开关、单一K/H消费者或一次映射 |

91本身只新增L0及符号地址结构验收。93新增流式gamma及H2560完整norm的有界L2；97新增专用V→实际M完整切片的L2及选定零延迟raw门级证据。102新增同16KiB/8S8/1S32预算的完整GQA A切片L2与选定raw gate，PR105@a62cffb已交付且CI成功。99已合入单head R证据；[106](experiments/issue-106-shared-services.md)已补M/A/Falcon R实际唯一16KiB/8S8/S32/SFU/link银行L2，两等待各7混合/27恢复命令及独立全值通过；选定raw gate两路各4完整命令与RTL逐字段和独立数学通过，物理未验。这些是L3所需的部分证据，未达到含宏/时序/物理的完整L3。

## 逐Block 当前证据与完成门槛

| Block | 当前证据 | 主要未完成项与下一条最小门槛 |
| --- | --- | --- |
| M 矩阵/部分和 | 82/84/85及97实际8个S8 MAC/INT32；K512、8专家、H1536；97消费RTL产生的驻留A/δ，owner/version/epoch与旧host δ拒绝、RQ/merge/residual/流式norm完整L2及选定raw gate | 仍非16×16阵列或通用GEMM。通用tile/K/端口吞吐、P/KV宽格式、通用byte ALU入口、M的H2560及多工作负载映射待实现；新网表宏/时序/物理由98，不线性外推周期 |
| V 向量/宽算术/非线性 | 80独立typed byte程序仍独立；93流式gamma全行norm、97专用SiLU/MID/完整512最小δ/A8→实际M已接收；宽RNE/abs/compare/address及缓存寄存计入70,102.970µm²新逻辑图 | 通用80 V ISA/byte ALU/程序与ROM仲裁整合未完成。97选择外部C0 LUT，无片内ROM宏；专用数据通路不能称通用向量库。SFU/ROM真实宏、并行服务与跨算子合法调度待闭合 |
| A 注意力/KV | 102真实Qwen2.5 full/cached输入完整8头、d128、Q8/KV16，实际8S8的3/9limb分解、scoreS32Q12/expQ30/U64sum/SFU除法/P15/PV32；单16KiB、两路79query与同core恢复独立PASS、选定18query raw gate；53,187.764µm²仅逻辑面积 | 三遍score materialized，非online；KV为caller committed前缀快照，无append/淘汰或投影/RoPE/output projection。106已完成与M/Falcon R共享同一bank/算术/link的有界lease，完整8头真实数值接收；在线数值为另合同，宏/时序/整体模型未验 |
| R 递推状态 | Qwen3.5/Falcon连续整数、范围/重定标和服务证据；[Issue99](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/99)独立完整head状态RTL已交付、in_review；PR103@8c51f5d已交付且CI成功，已合入本分支；72连续完整D128×N256单head S32、原子128bit根发布/恢复与selected raw gate独立通过，41,708.534µm²仅逻辑图 | 99是Falcon有界单head，非完整32head/4096norm/conv或GDN。104独立推进Qwen3.5两头GDN，资格以其单独交付为准；106已在相同唯一服务bank接Falcon head0跨lease连续两步与恢复，104 GDN尚未接入；新网表宏/物理仍未验 |
| S 存储/互联 | 93/97/102各自实际16KiB128bit1RW；93 H2560全行统计+256gamma块释放512B候选frame空间；97 MID→M输出生命周期复用、A4KiB保留、有限响应/排空/lease/恢复/canary已验 | 106实际唯一16KiB将M/A/Falcon R按lease复用，结果通过同S口真实导出；不称同时计算或已实现宏。仍为行为wrapper，不是8×32KiB多bank库存或宏资格。真实宏、读写语义、bank/仲裁/guard/metadata/缓冲、ECC若采用则另计；外部320bit+控制FIFO和tag物理布线未含核心面积；M/A导出前缀需成功DONE后提交，环境接收器最大6KiB暂存不在core内，真实下游事务缓冲/撤销消费尚未实现 |
| D 数据/命令控制 | 85/92单命令/有限响应/epoch终止；97实际V→M→norm排空与参数锁存、地址窗/alias校验和错误恢复；102新增单owner/monotonic cache version与scope限定的caller committed prefix、同core恢复；106新增唯一服务lease、结果ACK后释放、已接受事务effect-once排空和不可取消R root提交；92门锥性质属于92源，97有本top真实边界注入 | 尚非通用DMA/二维stride/gather/scatter/dispatch/图同步或91的64B描述符取指。97未作新top普遍形式证明，门级子集未含Q故障注入；通用队列/credit/多context/CDC与制造后路由要另验 |

上述完成门槛不是要求同时扩大六模块。已闭合有界专用V/S消费者；后续在已冻结硬件库存下逐一添加A/R闭包；不为了凑完整库而追加无关模型或改原精度。

## 必须单独核算的库存边界

- 当前可引用的算术为8×S8、1×S32和128-bit SFU。S16×S16至少4个8-bit片段、S32×S32至少16个，只有乘法数下界；符号、carry、round、读写和仲裁追加成本。A/R的状态更新不能免费加入这张表。
- 16KiB SRAM与512B frame不能相加后继续声称16KiB；128KiB LUT与64-bit外部程序不是同一块ROM。共享M lane用于byte MUL必须增加可实现的输入/输出选择及非乘ALU。
- 85的两路S32响应各64bit属于核心，外部恢复测试2×(128+32)=320bit加control属于未综合环境。整合后每个tag/holder/line寄存必须有来源、生存期或新增计费。
- 91 gamma状态112逻辑bit、两端口路由68bit、命令512bit、8专家delta128bit是显式逻辑义务；不能直接相加当综合FF，也不能因可能复用旧寄存就记0。93/97已有各自mapped寄存/组合面积回执；这些逻辑义务不能用简单求和替代真实图，新增模块仍须重新综合。

## 物理边界收敛的判据

制造前固定哪些有源计算、SRAM、SFU/ROM端点和局部连接；产品确定后允许更换哪些金属连接/路由或配置，须与成员Issue55/63的交付协调。当前runtime cache开关只证明运行时访问方式，**没有证明金属定制可制造、跨产品互联可行或端到端PPA获益**。

下一版边界比较须同时固定：数值合同、算术单元及频率约束、容量/端口/物理传输粒度、scale/状态元数据、所有程序与LUT流量、输入输出及重读成本。分别报告数值通过、功能RTL通过、资源映射、STA、电气、布局布线和完整验收状态；任何一个失败不能被其它指标的收益抵消。

当前有界顺序：[V/S合同](V_S_INTEGRATION_CONTRACT_V1.md)→93流式gamma→97专用SiLU完整消费者已形成证据；[Issue98](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/98)对新93/97网表推进受限物理，[Issue99](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/99)并行补R，102完整materialized A已通过；99有界Falcon R已交付，104 GDN与98物理为独立任务，其结果不自动授予106资格。106唯一S/8S8/S32/SFU/link已获L2及严格恢复接收，选定raw gate通过；125,966.694µm²仅logic area，超旧98预算，online/append仍缺。通用V ISA、GDN共享接入、真实下游提交缓冲、宏/PVT和产品定制资格均未完成。项目仍在研究与电路实现推进中。
