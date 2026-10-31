# 样本域片上系统接口、信用与容量合同（步骤3）

基线为研究分支 `39bd7bf66c47e17c18aa39483c1d974a1e079aa2`，叶宏来源643c6012。仅针对仓库现有八样本，不扩展未知模型家族；程序仍为预制有限家族ROM＋M11/M12永久入口/参数绑定，无bootload。本稿与 [onchip-contract.json](../work/Melodydt/151/onchip-contract.json) 是步骤1—3的研究规格输入，不是已实现硬件或RTL验收。本报告由主交付整合为步骤3正式候选；没有改叶宏、运行RTL或使用服务器。

## 1. 禁止隐含外部容量

本轮 **EXT请求credit=0、EXT valid恒0；不设DMA、不自动spill**。合法图放不下时保留semantic_legal，返回GAP_ONCHIP_CAPACITY/GAP_ONCHIP_WEIGHTS等明确诊断，不缩小模型维度、不把源cfg的32768—262144上下文改为256，也不从合法连接集合删掉该边。

需要分别出账：原生S/T/R等payload、新增控制/队列、1024B loader capture、程序/参数ROM、样本权重/状态/KV/activation。地址字段足够宽仅表示描述能力，不表示存在对应RAM。新增片上存储必须单列候选及面积/pin/功耗/布线代价，当前不把它作为可用资源。

## 2. 原生容量和S保守分区

| 资源 | 原生有效payload | 使用限制 |
|---|---:|---|
| S | 1024×128bit=16384B | 四bank共享真实端口，无byte mask；普通读写都要取回应答 |
| T | 384×128bit=6144B | 单批租约，commit后读，末字后release；不能借未释放T放第二批 |
| R active / shadow | 各8192B | length≤256、8lane；shadow还复用作SSM逐元素decay，不是通用RAM |
| R history / next | 各96B | next无通用读口，局部commit后op14才读新history |
| R候选输出 | 32B | op12两包；EXEC覆盖、COMMIT清有效，不能作大向量缓存 |

原生M一个结果context、N一个归约context也不能按空闲寄存器当系统RAM，更不能假定M有结果restore。

默认S按16B整字预留：

| S字地址 | 用途 | 容量 |
|---|---|---:|
| 0..63 | loader完整快照区 | 1024B |
| 64..447 | T整批spool | 6144B |
| 448..1023 | 计算/输入/权重tile/中间量 | **9216B** |

准入先计所有活跃范围、对齐和padding；结果变VALID必须等真实S响应take。两个spool默认同时计入，只有离线生命周期证明和全部响应/ref/lease排空后才能覆盖复用。S→S复制重叠必须有memmove方向或临时区；无byte mask的尾字独占或显式RMW。不允许自动借用T、R inactive bank或未声明的第二S。

### loader快照另有1024B capture的硬件成本

最大loader输出为A `8row×4tile×16B=512B`，B16 `4tile×2half×64B=512B`，共1024B载荷；还需bank/row/tile/wide/half/有效mask等控制元数据。

如果保留首版“loader活动窗口与普通S读写串行”，不能一边让loader输出堵住、一边等往同一个S写快照，再等loader done。主候选新增 **独立1024B片上capture payload**，完整接走此次A/B义务到done，随后经普通口写S0..63。其容量不包括在S16KiB里，也不是原S内两项A队列＋一项B保持寄存器的重复命名。它尚未实现，不能把loader导出到任意宏的路线标为已完成。

T→计算→同T重入先把旧批最多6144B完整读到S64..447，等写ACK和源读完，再release旧租约；此后才能BEGIN新批。一个T不能同时维持旧批读和新批写。该spool不等于整tensor原子发布。

## 3. 固定字段位宽候选

机器文件按字段低位到高位给出完整packing，可直接检查总宽度；本轮没有改变叶宏引脚。

| 对象 | 位宽/关键字段 | 准入约束 |
|---|---|---|
| handle_ref | 48bit：id8/view8/generation32 | 视图必须受原handle范围约束 |
| typed handle | 256bit：id8、generation32、region4/instance4/role8/type4、base/words/elements/version各32、scale/layout各8、tail8、consumer_count8、owner8等 | 实际只允许64个live handle；唯一表保存有效性/refcount，复制描述符不能改变所有权 |
| task | 512bit：task_id16/epoch32、primitive/resource/phase/flags各8、lease8/gen16、param16、4个48bit源ref、1个目的ref、elements/offset各32、PC16 | 单job≤4源、≤1目的；R多角色/融合QKV通过分阶段和有界描述符列表展开 |
| event | 256bit：task16/epoch32、resource/kind/status/error/flags各8、lease8/gen16、结果id/gen、elements/progress32、failed_rows8、PC16 | context_held、partial_commit、drained与数据完成分开；不能把一个event消费当释放lease |
| phase lease | 256bit：lease8/gen16/resource8、owner16、epoch32、context_key32、native owner/epoch/position各32、phase/计数等 | 同lease RESUME可保留原生context；新context REENTER必须关闭旧context并排空 |
| PARAM_BIND | 256bit：schema/param各16、源kind8/ref48、字段lsb/width各8、scale各8、policy8、range16、目标role8/index16、常量64 | 数据字段先转换/值域检查，再由唯一_CTRL构造native op/index/保留位/身份 |
| ROM微指令 | 128bit：opcode8、条件/flags各4、寄存/资源/phase/lease各8、param16、targetPC16、immediate32 | 预制译码展开为512bit task，微指令并非逐条存完整task |

类型编号覆盖S8/S16/S32/S64/U16/U32/U64/混合记录/有schema的opaque bytes。scale_id指256项静态尺度表（F用有符号32bit记录），layout_id指256项有界布局描述符；未登记/超容量返回控制gap，不默改尺度。

region只包括S、T已提交批、M结果导出、R active/history/output导出、局部capture/FIFO、明确新增但尚不可用的片上存储候选、预制参数ROM/常量。**没有EXT region，没有通用R shadow region**。base_word32/length32不意味着可用64GiB；native S窄化到10bit地址之前，必须先检查真实分区及范围，禁止高位丢弃后再判断。

R owner32与T owner2不是同一个天然事务ID；外层lease显式保存映射。R op0/6/7的身份位域不同。控制索引、身份、长度越界一律REJECT；数值SAT只在相应数值profile允许时使用，不把非法地址夹成合法地址。

上述位宽是逻辑记录，不是每宏新增512根并行控制pin。运输候选为单时钟下独立双向64bit valid/ready控制flit：task8拍，event4拍；完整task/完成槽在首拍前预留，包内不交错、按序组包、beat与字段保持至握手。task直接组入已分配的子控task槽，event使用已有完成槽及母控event FIFO项，不隐含第二份整记录缓存。event按包公平仲裁；两方向各一64bit保持寄存和计数/route锁定计入credit/status预留，更多中继另计。大payload不经母控。串行化、MUX、仲裁、寄存及ready线路均为新增有源候选，物理pin/STA仍待证明。

## 4. 队列、信用与阶段回访

主候选一个graph实例，10个候选服务ID：M/N/E/G/R/S/T、LAYOUT_COPY、NUM_SERVICE、NUM_WACC；后三者并非当前已有硬件。**id8的NUM_SERVICE规划为NUM_CONVERT、NUM_COEFF、CONV_BIAS32/NUM_ADD32子profile的唯一执行所有者，一次只执行其中一个job，串行复用，不能把三个名称当三颗现成算术宏。**id9只承担已定义NUM_WACC。不同子profile的实际算法、范围、数据通路和LUT均须另行实现接收；字段有编号不等于已有硬件。每服务2个task槽、**2个预留完成槽**，执行器一次1个job；全局最多16个已接受未完成task，母控event FIFO16项。每服务通用弹性data FIFO2×128bit；E/G输入收集、G最多8项顺序tag及端点保持另计。

M/N/R原生命令各最多1项；S普通口1项、loader 1项且首版与普通口串行；M结果/N整组/R context/T租约各1份。G一个job内可保持四级原生流水及外部槽，不同job不混流。

task接受时必须同时取得全局任务credit、局部槽/完成credit、有效源引用、兼容lease及目的/必要spool空间。不能先拿不可释放的部分资源再无限等待另一个。已接受响应的捕获空间已预约，不因为母控event FIFO满就停止原生排空。完成事件被接走可回收task/事件槽，但context_held时lease不释放；N/R阶段task结束后可调其他宏，再RESUME同lease。计数/标签耗尽不回绕冒认旧事件，先协调排空/复位或终止。

当前4源/1目的、64 handle、16 lease、fanout8、join4是有限实施候选，不是语义边黑名单。需更多者展开为合法多步，或报告GAP_CONTROL_CAPACITY。动态分支join必须有SKIP/merge语义；反馈必须有初值、版本延迟和有界迭代，不能通过把环删掉提高覆盖率。

## 5. 新增控制32KiB逻辑预算

以下是逻辑字节估算，不是综合面积，也不是已配置RAM。所有项目和公式见JSON。

| 项目 | 公式 | bytes |
|---|---|---:|
| handle/lease表 | 64×32＋16×32 | 2560 |
| task槽/完成保持 | 20×64＋20×32 | 1920 |
| event FIFO/母控在途表 | 16×32＋16×64 | 1536 |
| join/fork上下文 | 16×128＋16×64 | 3072 |
| state/history根元数据 | 256×64 | 16384 |
| 当前region tile mask | 1024bit | 128 |
| scalar参数寄存器 | 256×8 | 2048 |
| credit/status预留 | 1×1024 | 1024 |
| 通用data FIFO | 20×16 | 320 |
| 端点收集/tag预留 | 1×288 | 288 |
| NUM_WACC 8lane累加＋一rank暂存 | 64＋32 | 96 |
| NUM_SERVICE 操作数/结果scratch | 1×128 | 128 |
| 合计/候选上限 | 29504，预留32768 | 裕量3264 |

state根表不是state payload；256项是层/状态子域根及恢复描述符候选，tile地址由有界映射计算，不表示能驻留256份R状态。当前1024tile mask对应至多8192个8lane卷积通道；更大region要使用已证明的顺序计数或扩大元数据，不能隐含扩容。

此32KiB**另于S16KiB、T6KiB和loader capture1KiB**。还没有计NUM算术门、数据MUX/仲裁、时钟/复位和物理路线；数据结构按寄存器还是小RAM实现均待综合比较，不能把bytes直接写成面积。

## 6. 控制ROM暂估2MiB及位宽适配

八样本各预留4096条128bit微指令，共512KiB；共享4096条再64KiB，共 **36864条/576KiB**。PC16可表示65536条，覆盖此预算。每样本预留4096条32B参数记录，共32768条/**1MiB**，param_index16足够。scale/layout/profile字典再64KiB：例如256×16B尺度、256×128B布局、256×64B profile共52KiB，留内部余量。

合计 `576KiB+1024KiB+64KiB=1664KiB=1703936B`，以 **2MiB=2097152B** 为逻辑预算点，裕量384KiB。八样本槽可以共享子程序；预算不是必须物理复制八遍同一逻辑，也不表示每样本已生成4096条。未实际编译完整程序/错误分支前，不能宣称它们都装得下。指令超过预算或描述符表不足返回GAP_PROGRAM_COVERAGE/CAPACITY。

ROM只存控制程序、永久结构/形状/地址映射/数值参数，**不含巨量模型权重，不是动态scratch**。预制ROM、译码、常量/选择端和M11/M12永久绑定仍需实际面积、pin、扇出、时序与路线验证；没有bootload或运行时改图接口。

## 7. 现有八样本的片上需求与明确失败

来源为本目录 `family-sources/*.config.json` 和字符图（精确来源由模型研究稿索引）。导出实际B=1/S=2、FP32，以下改用S16 activation/KV、S32递推状态、S8权重**仅作容量假设**，量化质量尚未接收。源cfg上下文保留原值，不能用微测试长度代替。

| 样本 | H / I（Granite为每专家） | source context | S16 mid | gate＋up | 单FFN矩阵S8 | 每注意力层、每缓存token的KV |
|---|---|---:|---:|---:|---:|---:|
| Qwen2.5 | 2048 / 11008 | 32768 | 22016B | 44032B | 22544384B | 1024B |
| Qwen3 | 1024 / 3072 | 40960 | 6144B | 12288B | 3145728B | 4096B |
| Llama | 2048 / 8192 | 131072 | 16384B | 32768B | 16777216B | 2048B |
| Gemma | 2560 / 10240 | 131072 | 20480B | 40960B | 26214400B | 4096B |
| Phi | 3072 / 8192 | 131072 | 16384B | 32768B | 25165824B | 4096B |
| Qwen3.5 | 2560 / 9216 | 262144 | 18432B | 36864B | 23592960B | 全局层4096B |
| Granite | 1536 / 512 | 131072 | 1024B | 2048B | 786432B/专家/矩阵 | 2048B |
| Falcon | 2560 / 6144 | 131072 | 12288B | 24576B | 15728640B | 注意力层1024B |

公式：mid=`2I`；gate/up=`4I`；单矩阵S8=`HI`；KV/token/layer=`4×KV_heads×D`。单矩阵已全部超过S，更不包含FFN另外两个矩阵、Attention、其他层、embedding、LM head、bias/scale及padding。没有外存时，后续权重tile必须来自实际片上权重存储；目前没有这份大存储，不能把“可按tile计算”当成权重会凭空出现。

按保守完整gate/up/mid物化、保留输入残差的一个FFN调度，活动峰值候选为 `2H+6I`，八样本依次70144、20480、53248、66560、55296、60416、6144（单专家）、41984B；这是具体保守调度的峰值，不是所有实现的数学下界。除Granite单专家activation外均超计算区9216B；Granite完整40选8也不因此可部署：全部8个S32专家输出49152B，完整H的S64累加12288B，NUM还未实现。可另研究tile重算/归并，但必须证明控制和数值并另存权重。

KV按source context计算，每个全局注意力层分别约32、160、256、512、512、1024、256、128MiB；Gemma局部窗口1024时仍约4MiB/局部层。上述不包含其他层、当前Q/score/概率或对齐。若只把KV塞进9216B计算区、忽略所有其他活跃量，最多分别9、2、4、2、2、2、4、9个token；这只是绝对乐观上界，不能据此宣称真实模型可运行这么长。

Softmax一行score＋EXP需约`4C` B，全context32768已需131072B；131072/262144还超过N原生65535统计计数。当前无实现的更长归约方案时记GAP_N_STATS_COUNT，不可把一行分成各自Softmax来冒充同一算法。

GDN一层state为`32×128×128×4=2MiB/版本`，old/next至少4MiB；Falcon一层`32×128×256×4=4MiB/版本`，old/next至少8MiB。history一版本=`12×C_conv` B，另加conv/readout/QK/系数staging。**无外存条件下，旧根/新根所指payload也必须片上真实存在**；只有32KiB元数据和R两个8KiB银行时，这两套完整多tile版本服务均为GAP_ONCHIP_STATE_VERSIONS，不能继续沿用“外部根”一词隐含外存。

Falcon源配置 `mamba_conv_bias=true`、源Conv含第三个bias输入，而R原生conv只有四tap乘加/舍入，没有bias参数端口。这条合法数值边另记 `conv_bias_numeric_path / GAP_CONV_BIAS_NUMERIC_PATH`：需显式共同S32单位的宽偏置加法（例如新增NUM_ADD32及溢出策略），再做下游量化/SiLU；或另行证明提前量化后用E16加法的误差可接受。E普通S16 ADD不是S32加法，不能省略bias或仅改descriptor宣称补齐。

以上大型需求是资源需求表，不是已决定新增几十MiB/GiB片上RAM。若要补齐，只能另评估有成本的片上权重/工作区/state/KV存储、压缩或可证明的重算/新数据流，并重新接收数值/带宽/物理。当前八样本的完整定点部署均未通过片上容量准入，保留全部合法连接需求。

## 8. 当前可容纳的原生容量微实例

- **FFN8候选**：原25字/400B分配整体平移到S448..472，保留四字对齐；加两个S spool的总预留7568B，T一字16B。容量可放下，系统wrapper/整链RTL尚未实现，不能说FFN已通过。
- **Softmax257候选**：score放S448..480，EXP放S512..544；活动1056B，计算区保留跨度1552B；加spool总跨度8720B，T33字528B。N目标总长/尾部守恒由新N_CTRL跟踪，未做RTL组合。
- **仅raw＋EXP且输出全在T的Softmax容量界**：`2×16×ceil(L/8)≤9216`且`16×ceil(L/8)≤6144`，得到L≤2304。没有其他活跃张量/权重/残差的前提不可省略。它不是模型支持上下文上限。
- **R单驻留tile**：L≤256时active最多8192B，输出32B；原生银行放得下并不解决完整GDN/SSM的全部state/history。R最终资格仍由独立实施任务交付，本轮不接管其作业。

## 9. 本轮验收应怎样写

步骤1—3可接收的是：八样本域及来源明确；合法边/profile账本保留gap；字段packing、credit、S分配、零EXT请求和保守容量公式形成可审查规格。母/子控制、spool、NUM、片上版本库、2MiB ROM和32KiB控制存储均未实现，后续RTL/整数oracle/活性/物理仍需独立工作包。

本次实际管理结构检查PASS；字段位宽、S分区及预算算式以本轮脚本核对结果为准。未跑RTL、SystemC、综合、P&R或服务器，不据此改变上游叶宏资格，不把规格完成写成八模型可执行。
