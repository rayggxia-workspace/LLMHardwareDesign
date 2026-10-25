# Issue97：原始 SiLU 输入到真实 M 的有界完整电路链

2026-10-25，负责人 Liangruizhi；[Issue97](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/97)，分支 `task/97-v-consumer`。全部实际张量、RTL、综合、门级和数学接收均在本人 CPU 服务器；本机只源码、管理结构和字节接收。交付待 PR 独立审查，不是六类 Block 全部完成。

## 本次闭合的缺口

此前实际 M 的输入 A8 和逐专家 δ 来自主机。本次从既有 Granite-3.1-3B-A800M-Instruct 原74整数参考的 `expert_gate_q12`、`expert_up_q12` 开始，在 RTL 中执行 SiLU、I32×I32→I64、RNE12、完整512元素范围扫描和最小 δ 选择、A8生成，再由真正8路S8矩阵电路消费，完成 RQ、8专家加权 merge、残差和93流式 gamma 归一化。主机不提供 MID、A8 或动态 δ；旧头部 δ 字段改为必须零，任何非零直接拒绝。独立 oracle 从原始 gate/up 与静态权重重算，另核对新输入包的所有静态 mantissa/exponent、W8、路由权重和残差未改变。

这采用**有界专用 V 前端**，没有冒称80通用 byte ISA已接入。真实 M 仍固定 K512、8专家、H1536，不是通用 GEMM，也未包含路由/gate-up投影或完整模型。93的 H2560 norm-only 资格不扩大本次 M 的尺寸。

## 计算、状态和接口

| 阶段 | RTL 计算和精度 | 存储及交接 |
|---|---|---|
| V SiLU/MID | I32 Q12；±32以内原16385字LUT，外侧0/恒等；共享S32×S32→S64，RNE12，I32溢出报错 | 每个专家完整512 MID写S的0–2047B |
| V 动态量化 | unsigned abs(INT_MIN)=2³¹；完整512 absmax选择最小δ∈[0,25]；对全部MID RNE，A8限定[-127,127]，不靠饱和过关 | MID重读；8×512 A8存12288–16383B；最后写应答后才发布该专家δ/valid，全部完成才发布A owner/version/epoch |
| 驻留 M | 8×S8，INT32完整K累加；实际δ进入 Q31/exponent RQ；宽merge、残差沿旧整数规范 | 跳过外部A填充，读取已生成4KiB A；完整1536结果覆盖S的0–6143B |
| Norm93 | 整1536统计、宽和、整数除法/开方、gamma Q20、精确RNE | gamma每256元素流式装入6144–7167B；全行统计barrier后处理，保留4KiB A |

同一16KiB、128bit单1RW；同8个S8、1个共享S32和norm SFU。V/M/norm串行获得S、外部link和S32服务，响应排空后换owner。单命令接口锁存输入地址、owner/version、epsilon和系数；64B程序化描述符尚未实现。512B候选frame留空，不增加一个免费私有存储。新增五个逻辑128bit行寄存、δ接口、比较/abs/桶形移位/RNE/地址/valid与元数据都在实际综合里；δ高常量位可能被综合删除，实际FF以网表为准。

C0 LUT占用外部常量窗 `0x02000000`，预留128KiB。逻辑SiLU65540B，exp2另8196B；本链不使用exp2运算。最后SiLU字与exp2起始字同一物理128bit行，选择仍限定逻辑SiLU索引。程序取指为0；原输入/权重/gamma都在91 DATA窗 `[0x04000000,0x08000000)`，不是此前重叠地址图。16B对齐、跨度和三段不重叠检查在真实top中。

完整K的保守累加界为512×128×127=8,323,072，低于INT32正界；较宽非线性/重定标仍真实使用S32/S64，不以“W8A8目标”当成所有运算只有8位。INT16/INT32能力是此处实际共享单元，非默认免费支持。

## 实际验收

正式 RTL 源为 `40491d1` 的phase8，硬件字节与最早映射源 `064995e` 相同；原 norm93 SHA `a42bb0f74a097eb14297820eaca6fe14350f233139d47153eb20dd47218aea5d`。最终已合入93交付 `f660e353`，没有借文档合并声称新RTL执行。最终严格接收来自phase9，汇总/归档phase10。

- 六个真实输入：层0/13，token0/64/71；每个8×512原gate/up。两种确定的端口/乘法等待方式，各自同一个core连续运行，真实最小δ为8–12。
- 每路50条accepted命令、29个成功输出：27条完整消费者、2条V数值边界。逐项核4096MID、4096A8、8δ、12288INT32 acc、12288down、1536join和1536norm；原74全部对应整数码不变。
- 两个合成原始输入分别覆盖LUT端点及外侧、索引与数值RNE正负tie、INT_MIN和全行δ跳变；实际δ分别为 `[25,25,25,25,25,25,25,25]` 与 `[0,0,0,1,6,7,15,15]`。
- 每路11错误：6地址/配置拒绝且外部读为0、MID溢出、非零旧host δ、3种A元数据不匹配。后者明确检查实际Q经边沿保持且M不启动、packet/MAC不变。20条完整恢复、7阶段abort、4配置/reset冲突、done/abort冲突、终止epoch拒绝；实际计数12次soft_abort、3次stale response、外部响应FIFO峰2。
- 5次暴露Q注入仅用于RTL验证：3次元数据、2次max附近epoch，检查真实边沿后值，非生产写入口、非任意状态形式证明。终止态不回卷，必须协调core/fabric硬复位。
- 原始字段类型/键集/命令序列严格接收；每路11个**真实文件篡改后重算SHA**负例被拒绝，覆盖MID、A8、δ、acc、down、join、norm及协议字段。
- 实际映射门级另跑层0/token0和层13/token71，quiet/heldreply各一组，每组V-only后完整链，共8输出。每一字段与同driver RTL完全相同，且再次经原74独立oracle；4个实际门级文件篡改重SHA被拒绝。该driver没有Q注入；50命令错误/abort资格只在RTL，不包装成门级已测。门级是零延迟逻辑+行为store82，非全等价证明或SRAM宏签核。

正式回执：`receipt-s0.json` SHA `ef38f84d876a939aff7eab2d77eeffdd1943b61295b695a89a7883fae532f7fc`，`receipt-s1.json` SHA `cde42cefb892cc8e8d0d83c08c2ef678e2d4fc61868ef798efa0f597d6c4b1e7`，`gate-receipt.json` SHA `932a267391e62d8a23bda0e214b67daea187082fa52bb4c6004866818d024ebd`，均在 [结果目录](../../project/experiments/v_consumer/results/issue-97/)。

## 周期、通信和资源

| 条件（六真输入范围） | top active cycles | V active cycles | norm active cycles |
|---|---:|---:|---:|
| quiet | 6,003,222–6,003,235 | 82,506–82,519 | 213,700 |
| 确定端口/响应等待 | 7,258,386–7,258,399 | 101,191–101,204 | 219,460 |

这些是实际有界链的active计数，包含V输入/LUT、M权重和gamma取数及运算；不含测试canary配置、完成保持/ack、A/结果debug读回，不能叫整模型端到端延迟或频率测量。未以更短输出选择有利样本。

每个真实完整命令：V原gate/up各1024行读，LUT4096行读，S读1024/写1280；M外部405504事务，A读393216/写0，6,291,456 MAC、384行结果写；norm外部gamma384行、S读1152/写768。共享S32端口0共26112次、端口1共7168次（V4096+norm3072）。总外部412032事务，line payload 6,592,512B；按每事务5×128bit桥，总2,060,160beats/32,962,560B。scale不由host运送，内部128bit逻辑接口及相关MUX/存储计入逻辑面积。

独立generic inventory严格得到8×S8、1×S32、一块16KiB128bit1RW，无隐藏native div/mod/pow；原Liberty实例表Decimal求和与工具统计一致：**70,102.970µm²、47,499 mapped cells、5,344 DFF_X1**，generic含wrapper寄存共5836bit。全部新增宽算术/地址/FSM/观测寄存已计入。映射lib为Nangate45 typical，SHA（见原map manifest）：`8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1`。

存储宏、外部ROM控制/缓冲、物理布线/时钟和tag sideband不在logic-only面积。外部两响应FIFO最低2×(128+32)=320bit加control另计；32bit epoch旁带没有被桥的128bit beat计数序列化。未对93作无控制的增量面积/速度归因，也没有把空闲512B候选frame算成额外免费库存。新93/97网表物理由98独立验证，不能继承旧84/88电气结果。

## 保留的失败与结论

首轮C++构建与系统`gamma`符号重名失败，修名后新目录重建。早期metadata负例在MSTART同拍写top输出没有触发Verilator缓存的组合重新计算，产生4个失败回归；修为VDRAIN注入、真实边沿Q读回、M不启动后重新执行所有正式条件。这是测试夹具问题，不以失败跑完的部分输出冒充资格。所有日志与仅本任务失效依赖取消都归档。

**可确认的边界：** SiLU/MID的完整512范围决定δ，A及其scale/version必须共同发布；MID不能只按16B传输块各自定标；M可以直接消费同S内驻留A，且切换必须排空共享服务。V/M/norm的生命周期确实可复用16KiB而不叠加私有RAM。这足以作为后续物理实现和A/R电路扩展的基线。

**尚不能确认的边界：** V/M是否制成同宏、ROM片内或片外、最优时钟/分区、通用M/V ISA、多上下文服务、A完整在线GQA、R完整状态原子提交、真实宏/布线/时序和整模型PPA。有限数值/门级成功不等于制造前固定连接已最优。继续依据 [Block库分层验收](../BLOCK_LIBRARY_ACCEPTANCE.md)推进98物理与99 R工作，不扩成“六Block设计完成”。

## 交付与恢复

50个本人Slurm作业全部结束：40 COMPLETED、5 FAILED（构建1、旧metadata夹具回归4）、5仅自有失效/旧版依赖取消。完整包750,458,058B/1085成员留授权服务器 `issue97-v-consumer-20261025/delivery01/full-results.zip`，SHA `ccdda33ea2df686b4ce2493ab3efc241e58f9be570344bea33e52cb41e5be604`；精选220,674B/178成员 SHA `c2d553d09cb6107b230b881c7def1322c8744e6796ef9afc7089eefa4e477c2d` 入仓。两包服务器逐成员、精选PC逐成员、十阶段153条原Git源码字节核验PASS。完整原型和有用临时执行记录保留供98/后续恢复，未清理他人目录。

归档后7个97文本只将末尾CRLF规范为LF，旧Git/SHA与新SHA及非换行字节相等记录在 `work/Liangruizhi/97/line-ending-receipt.json`。原实验包及153源绑定未被改写，不能把规范后的当前HEAD冒充新科学执行版本。93主会话修订通过合并保留原erratum。

[执行索引](../../project/experiments/v_consumer/results/issue-97/index.json)、[交接](../handoffs/2026-10-25-issue-97-v-consumer.md)、[实际命令](../../work/Liangruizhi/97/execution.json)。指定Liangruizhi/182389313认证、origin和分支已复核。此交付本地已整理、主会话负责推送/PR和Issue状态；没有自行合并或标done。登记PR5 pending，看板缺配置/read:project，未核/未同步待管理员，不能写成远端已完成。


发布回执（2026-10-25）：[PR101](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/101)已上传；Issue97为in_review，待独立审查合并，未done。远端读回1ae1dc1d101ec9e8415ab49dfc2979e108c2eba3报告/结果索引/门级接收/库验收表与原Git blob逐字节相同，见work97/remote-readback.json。登记PR5 pending；board配置与read:project缺项，状态unverified/同步pending，管理员/审查人待指定。98/99与A后续继续，不把本任务完成等同Block库完成。
