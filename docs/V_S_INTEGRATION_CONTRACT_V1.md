# Issue91：V/S 有界整合合同 v1（候选，非 RTL 实现）

任务 [#91](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/91)，负责人 Liangruizhi。基于 PR89 的 `d60fac795ba6341df2e48804df564afd3e4e9818`，核对 Issue80/82/84/85 实际 RTL；Issue88 电气修复和 Issue92 epoch 终止态由独立任务负责。本合同只冻结可实现接口、容量与接续实验，不宣称六个 Block 已完成或当前设计可制造。

当前选择：保留一个 16 KiB、128-bit、单 1RW S；先用互斥阶段租约复用计算资源。H2560 保留整行 X/Y、流式读 gamma。通用 V 帧占用 S 的 512 B 地址租约；旧 V 的程序和数据 LUT 分开部署。采用外置 LUT 的 C0 是新候选，不与原片内 ROM 配置宣称同面积、同带宽或同周期。

## 1. 实际库存与需要付费的改动

| 资源 | 当前实际源与边界 | C0 候选：复用、增加或缺项 |
| --- | --- | --- |
| M 乘法 | runtime_cache/mfront85.sv：8 个 S8×S8；固定 K512、8 专家、H1536 | 保留 8 个；V byte MUL 用 lane0，但必须新增操作模式、operand/result mux 和独占所有权，现 Mfront 无可编程 ALU 入口 |
| V byte 非乘运算 | wide_service/byte_alu.sv 有 8 套 byte lane，包括另 8 个 S8 乘法器；当前单命令只选一 lane | **新增一套** byte ADD/SUB/carry、shift、compare、AND/OR/XOR、MUX 和 operand/result 寄存控制；不是免费借用 M。保留 old lane selector 的接口时映射到唯一物理 lane，禁止声称 8-way V SIMD |
| S32 乘法 | mul84.sv SHARE=1：一个 S32×S32→S64；2 个各 64-bit 的响应槽、round-robin；每槽占用时不得覆盖 | 数量不增加。保留两服务端点：M RQ 与 V/NORM phase 互斥端点；SiLU×up 走后者，不附加第三个结果 FIFO。请求含操作阶段与 epoch，由父控制器保证路由 |
| 宽 SFU | norm84 内 sfu84：128-bit 无符号除法/isqrt，profile1 每周期一步算法；并非一般任意宽算术核 | 显式移到共享端点或扩展 norm 服务入口；必须综合比较 mux/控制开销。S16/S32 更新、符号除法、RNE/饱和仍由指定 wrapper 或 byte 程序实现，不能从 SFU 名称推定支持 |
| S | store82：1024×128-bit=16384 B，只有 1RW，写应答也占槽；reset 不擦存储 | 容量不变；V 的 512 B frame 通过租约覆盖。byte store 是读旧 128-bit 行再写，不能假定 byte enable。1RW 在途响应使用现有 dout128；额外 owner/epoch/control 单独计费 |
| V 控制 | wide_engine：64-bit 指令，4 层返回栈，512 B 逻辑 frame，16 B 取指缓存 | 引入程序控制器、栈、取指缓存和地址重定位；即使算术共享，这些逻辑也新增。需要 RTL 实例/寄存生存期及综合核算，不能把原 norm FSM 当通用 V |
| 程序 | Issue80 实际 program.bin 1,928,832 B=241,104 个 64-bit 字；外部 128-bit 取指桥、16 B cache | 外部保留；32 MiB 是编译容量上限，128 MiB 是外部地址预算，均不是免费片内 RAM |
| LUT 数据 | 原 lut32 为 32768×32=131072 B 单 ROM；73736 B 有效，57336 B padding；原 valid 是固定延迟脉冲，无 take | C0 外置只读 LUT，所有读取走有限外部桥，不能套用原 2-cycle ROM 延迟。C1 可保留一个片内 128 KiB ROM，但需宏、端口、控制、面积与功耗证据，单列资源不同的候选 |

上述 8S8+1S32+128-bit SFU 只是已有乘法/SFU库存，**不是整合后逻辑库存不变**。旧完整 byte_alu 整套旁挂会再增加 8 个 S8，不接受这种实现却声称共用原库存。C0 的 byte ALU、控制/栈/cache、mux、标签、守卫、缓冲全须列入综合；本阶段只有明确的逻辑位宽义务，尚无面积测量。

## 2. 程序、LUT 与外部数据地址

地址为字节、末端不含，窗口均在外部预算 128 MiB 内；预算不等于已选定物理外部存储。

| 对象 | 地址范围 | 解释 |
| --- | --- | --- |
| 程序 | `[0x00000000,0x02000000)` | 最多32 MiB；当前 active1928832 B，SHA-256 `37c08d589f73a8ae8c65ef32c5351c5d756af02ea9a8ca7e5b65e5ab7efc1393` 来自 Issue80 已发布 comparison，不在本机重建程序 |
| LUT | `[0x02000000,0x02020000)` | 128 KiB 保留窗口，SiLU offset0，16385×I32Q12=65540 B；exp2 offset65540，2049×U32Q24=8196 B。顺序依据 granite_ports/run_server.py 的 rom_inputs；不能将两者分别向上对齐后仍沿用旧索引 |
| 数据 | `[0x04000000,0x08000000)` | X/gamma/Y、程序输入输出包、权重等由驱动分配且不得越界；其他空洞不可隐式使用 |

C0 LUT 读采用 `lut_base + floor(word_index/4)*16`；返回后按 index低2位选32bit，边界从原32-bit字索引转换。SiLU最后字与 exp2前3字共一条物理行，范围保护以**合法字索引**判定，不能因128-bit行对齐免费访问padding。SiLU合法索引0..16384，exp2逻辑索引0..2048对应物理字16385..18433；word18434..32767为padding且业务请求拒绝。无额外 LUT cache；每个实际 lookup 一次外部行事务，包括重复 index。cache/向量化合并另立付费变体。

程序 PC 和 limit 是64-bit字单位；物理取指 `program_base + floor(PC/2)*16`。程序 base16 B对齐、limit非零、`limit*8<=32MiB`，entry<limit，branch/CALL target/return都受边界检查；只读 host 在命令前核程序/表 SHA。SHA 是软件接收证据，未假定硬件有密码散列核。当前80程序的18种 typed operation 全目录不是一段1.93 MB片内微码 ROM。

## 3. S 地址与生命周期

所有以下地址均为字节；物理存储的地址单位仍是16 B行。X/Y 为同一地址先读后写。V 逻辑 frame0..255 为叶子 scratch，256..511 为调用者数据，重定位后仍保留两半，禁止按8-bit地址截断。

| Profile/阶段 | X/Y | gamma | V frame / MID | A cache | 本阶段活跃字节 |
| --- | --- | --- | --- | --- | --- |
| H1536 原 resident 容量对照 | `[0,6144)` | `[6144,12288)` | 不活跃 | `[12288,16384)` | 16384 |
| H1536 后 M 单独 V | `[0,6144)` | `[6144,12288)` | frame`[12288,12800)`；必须先释放A | 不活跃 | 12800 |
| H1536 gamma256流式 | `[0,6144)` | `[6144,7168)` | frame`[7168,7680)` | `[12288,16384)` | 11776 |
| **H2560 gamma256流式** | **`[0,10240)`** | **`[10240,11264)`** | **frame`[11264,11776)`** | **`[12288,16384)`** | **15872** |
| H2560 X/gamma都分块的成本对照 | `[0,5632)`，tile1408、tail1152 | `[5632,11264)` | frame`[11264,11776)` | `[12288,16384)` | 15872 |
| SiLU前M阶段 | 无最终X；MID512×I32`[0,2048)` | 可保留`[6144,12288)` | frame`[2048,2560)` | `[12288,16384)` | 12800 |

H2560的 `[11776,12288)` 是512 B未分配间隙，**不是**额外免费FIFO、guard SRAM或已计入frame的空间。所有控制/标签/描述符另外计账。V frame在上述norm表中只是保留容量，不代表本轮结构trace已执行它的程序或frame访存。

不合法的两种做法：H1536原fullX+fullgamma+A后再加512 B frame会与A重叠；H2560仅fullX+fullgamma就20480 B，尚未加frame/A已超容量。后M复用A地址必须在M/S/mul/外部应答全部排空、A租约释放后进行。A cache标记 `(owner,input_version,epoch,format,valid)`，不允许跨token/更换输入后凭地址复用。

### 全行统计与流式 gamma 的协议

1. 当前合同仅支持 H1536/H2560、B1、H与tile均为4的倍数；非4倍数尾掩码不在本轮整合验收内，原82小H边界仍保留作独立参考。
2. 先读取整行X的全部H个元素，累计同一个U128 sumsq；只执行**一次** `floor(sum/H)+epsilon` 和 `isqrt(rad<<40)`。计算den之前禁止发布任何Y。H2560不能把norm84(h=256)循环十次，旧核h>1536直接拒绝且gamma基址硬编码384行，必须修改控制。
3. H2560首选X常驻10 KiB，gamma按256元素/64行读取。gamma controller登记 logical_first12、valid_count12、consumed_count12、physical_base10、state2、input_version32、epoch32，共**112逻辑bit**，另有当前请求/响应协议。最简单实现一整tile装满后消费；无双缓冲。
4. 先为整条gamma响应保留一个S写位置和epoch信用，才允许发读；全局外部端口至多一在途，不在已占用holder时继续发请求。每tile输出全部Y写入并按需drain后再释放gamma租约；最后一tile只用有效长度，禁止以旧槽数据当新gamma。
5. output阶段同一条X/G先各读入已有line寄存，再算4个元素并写回Y；全局统计已结束，所以原位覆盖安全。gamma覆盖只能发生于前tile消费/写回应答排空后。错误或abort不发布本命令，S可能已部分写回；重新执行必须重新加载输入/验证cache，不能将其当原子R状态提交。
6. 分块X对照需要第一遍X流式求全行统计，再第二遍重读同版本X并与gamma输出；tail1408+1152只改变地址轮换，不能改变全行den。输入X/Y外部范围必须分离，直到完成前X/gamma只读稳定。

## 4. 有限命令、服务仲裁及恢复

本轮拟定64 B命令描述符，只覆盖 `NORM_STREAM` 和 `V_PROGRAM` 两种入口；M现有打包头仍独立，尚未宣称通用DMA/全图指令集。四条128-bit读取组装到完整私有描述符后，原子验证/接收，不能半条命令开始计算。

| 偏移 | 字段（byte，按列顺序） |
| --- | --- |
| 0 | magic4、version1、opcode1、profile1、flags1 |
| 8 | epoch4、owner4 |
| 16 | H2、K2、experts1、format1、inputQ1、outputQ1 |
| 24 | srcX4、srcGamma4 |
| 32 | dstY4、LUTbase4 |
| 40 | programBase4、entryPC4（字索引） |
| 48 | programLimit4（字数）、epsilon4 |
| 56 | coefficient4、inputVersion4 |

64 B=512bit描述符锁存义务，不自动认为现85已有全部字段。NORM只允许冻结格式、H1536/2560、epsilon17、合法profile；未使用的K/experts/program/coefficient字段为0。V_PROGRAM仅有受限受审wrapper可用，entry/limit/format等必须绑定其profile；尚未设计的命令明确拒绝。flags/reserved值非0拒绝；地址溢出用扩展加法比较后再截断；src与dst不得别名。

- 单命令在途，无隐式命令FIFO。`cmd_accept=cmd_valid&&cmd_ready`；cfg pending、cfg valid、reset/abort、未确认done、epoch终止均使ready为0。未接收请求由上游保持，不静默丢弃。模式/地址/scale/owner/epoch全部锁存，运行中外部pins变化无效。
- 外部端口统一IFETCH/LUT/M/DMA四类，至多一个请求在途/一个128-bit应答holder；轮询仲裁针对有接收信用的请求。单个已接收response保持到take。新外部client2+epoch32=34bit路由标签；S相同2+32=34bit，合计**68bit标签义务**，是否复用旧寄存须RTL证明。原85测试环境双槽320bit+control不是片内免费缓冲。
- S客户M/Norm/V/DMA共单1RW；cfg只在idle，经DMA端口；每次交易含写入也等应答。初版阶段租约互斥，程序取指与LUT仍在外部端口竞争；不得假定双端口、每拍可同时读X/gamma/writeY。后续并行模式若加入round-robin必须实际测试公平性和缓冲上界。
- V byte RMW的S锁从旧行读接收到对应写提交结束；不得持有该锁去等待程序取指、LUT、SFU或外部响应，否则可能环路死锁。先把所需操作数/指令取齐，再进行有界RMW；中止时释放锁且本命令输出无效。
- S32两个响应槽各64bit，V与Norm共享同端点且阶段互斥，不额外叠加结果队列。SFU只有一个在途运算/响应；更改其pulse接口必须加稳定保持或证明现有holder复用，记实际资源。归一化的内部always-take不能直接当通用消费者协议。
- 改profile/owner/framebase前的barrier要求：M/S/乘法/SFU/外部应答均清空；gamma租约结束，RMW锁释放；旧epoch响应只能丢弃不能写S。soft abort撤销publish权限、递增epoch；全局hard reset须与外部协议协调。沿用Issue92修订后的终止态规则，最大epoch不得回绕；本91未执行其终止态RTL验收。
- 错误包括：命令字段/shape/格式非法、地址越界或活跃区重叠、错误owner/epoch/输入版本、LUT域/PC/栈越界、数值溢出/den0、watchdog。error/status/done/epoch稳定保持至ack；异常时已改变的私有frame/X不能冒充有效Y。完整R old/shadow原子提交另立RTL验收。

## 5. 精度与现有算术能做什么

Norm继续旧精确整数合同：X/Y I32Q12；gamma I32Q20；epsilon U32Q24=17；S32乘法产生S64；U128累计、floor/H、整数sqrt、带余数ties-to-even除法；输出超I32范围报错，不偷偷饱和。H2560极值下sumsq<=2560×2^62，rad<2^104、分子<2^75，均需按实际有符号边界独立bigint核验；这些分析上界不替代运行时guard。

| 路径 | 现库存可用部分 | 仍须实现/计费的部分 |
| --- | --- | --- |
| M W8A8 | 8 S8乘、INT32部分和，已有K512完整消费者 | 通用tile/K、其它shape/调度未实现；S8×S8最坏16384，纯正累加保证不溢出需K<=131071，K512上界8388608 |
| 通用V宽运算 | 已80 byte程序证明18typed运算可分解；S32直接乘和U128 SFU可选 | 新增byte非乘ALU、符号扩展、carry/round/saturation、控制/访存逐项收费；不能把byte多周期当1个S32操作 |
| A的概率/KV/PV | QK可能可用8位M；已有整数/服务证据 | P可能U16、KV/S可能S16/S32，8位M不直接支持。分解S16乘至少4个8×8片段且含符号/交叉项/宽累加，需显式程序/端口/周期；在线softmax/max/sum/rescale状态与非线性模块未整合RTL |
| R连续递推 | 已有软件整数/范围/服务证据；S32乘与SFU可作为候选算术 | S16/S32状态乘、宽累加、round/rescale和old/shadow状态提交不能免费借M8，也不能认为Norm核支持R；完整递推RTL、复位/溢出恢复和跨tile存储仍缺 |
| SiLU→mid | 旧74真实gate/up I32Q12、LUT与独立oracle；1×S32乘可做SiLU×up S64 | lookup域处理、RNE12、全512值absmax→动态scale、A8编码/饱和必须有完整实现；外部LUT随机读、frame RMW、程序取指全计费 |

在不接入专用宽单元时，S16乘4个8-bit partial、S32乘16个partial只是分解的**乘法次数下界**，不是完整周期；符号纠正、交叉项相加、读写及控制不可省。现S32×S32乘法可覆盖较窄有符号值，但吞吐/响应槽/scale对齐必须仲裁并测量，未承诺并行免费执行。

## 6. 最小后续 RTL 实验合同

本91只有地址/生命周期/事务枚举和独立接收，以下**未执行**。真实张量/RTL只在本人授权CPU服务器独立Issue/out运行；不新增模型、不在PC重算真实数组。

1. **H1536回归与H2560流式gamma**：同一16KiB/8S8/1S32/SFU库存，使用原85六例H1536完整消费者，新增H2560只取既有合法边界数据或合成整数边界；没有匹配真实H2560 trace时标合成，不能改名为模型测量。对比全局bigint oracle的sum/den/Y每码；错tile den、gamma错位/末tile陈旧值、输入alias为负例。记录descriptor加载、S/外部交易、所有状态等待及面积，分别计norm kernel与input/output开销。
2. **一个实际会争用资源的V非线性消费者**：复用74封存的gate/up/LUT，先完整一个专家512值的SiLU×up→mid。Vframecaller半可放gate16×I32=64B、up64B、mid64B、metadata64B，leaf另256B；中间MID512×I32=2048B写S。必须全512完成后得到一个动态scale，再第二遍量化A8。不能用每16值scale替代原专家512粒度。M/S32争用需真实有限端口压力，不以串行无冲突证明任意并行公平性。
3. **接回真实M的最小闭包**：逐8专家重复上一步，A8写4KiB，保留8个S16 delta共128bit显式元数据。全部完成后drain/release MID与frame，给M新增resident-A入口，核 `(owner,input_version,epoch,format,valid)` 后才消费；旧85只冷加载/运行时cache开关不自动支持这一入口。随后旧全K512/8expert merge→residual→norm，独立oracle从原gate/up开始，不给RTL喂host算好的mid/A8。结果不通过则保留失败，不声称完整消费者完成。
4. **协议最小矩阵**：无背压/确定性held-response两模式；每个阶段reset/abort/restart，跨mode参数突变、busy cfg/重复cmd、LUT/PC越界、frame/A重叠、数值异常、epoch终止、旧响应迟到；按实际DUT事件计数。前后S canary、A owner/version、response最大占用证明有限容量。phase切换必须排空所有在途事务，不只看M busy=0。
5. **库存与电气门槛**：C0外部LUT和C1片内ROM分别给完整库存/带宽，不能当同资源二选一性能图。每个内部布局对比再固定同精度、容量、端口和算术，记录新增ALU/mux/控制/metadata/缓冲/宏。继承Issue88电气修复的方法重新跑实际整合netlist；85、88或80通过不自动覆盖新组合。逻辑面积、cycle数、初步STA均不等于制造就绪。

最小第一步是实现gamma streaming地址/credit controller及只读layout校验器，先闭合H1536回归和H2560整行统计。随后独立加单byte ALU与LUT/取指共桥，不同时改算术精度，以便定位差异。
