> 本轮L4：[F16 H8/I8](W4_F16_IMPLEMENTATION.md)已有S16输入/原残差+可变gamma RTL及服务器95209/30CASE证据；W5-IF合同不变，完整A仍待补preNorm/QKV/RoPE/Wo/残差，实际模型数值/规模/供参未接收。下一步见[A/F路线](AF_NUMERIC_STORAGE_PLAN.md)，L5 RTL尚未开始。下文旧阶段记录保留当时状态。

# 功能岛研究八条主线与当前进度

Issue151 / PR152，负责人Melodydt；2026-11-02。沿用w0-index的八主线/W包映射，历史索引保留原时间。A8实现的历史输入为1d722477564e14f7dc93e39ce8e28b8e2d150cb0，业务交付为714cab4fda64c8e5cdd74c57ae8bc704e4902981；三层互联计划以714cab4为输入；本轮W5-IF合同输入为f9a90c845504b198cc3265106e03c67902382ebb，新交付commit由PR152最新回执核验。工程进展与外部审查/合并分开。

目标是在共同预制底座内准备功能岛及全部必要有源适配和本地控制，M11/M12只连接已存在的岛端点、永久绑定有限模型产品；母控管子层任务/依赖，本地控制管宏op、流水与真实存储ACK。外存存在并保留接口灵活性，当前算子切片暂不实现真实外存。固定控制流程允许每次更换tensor/weight内容，不等于运行时装入新程序。

| 主线 | 工作包 | 要实现什么 | 当前证据与未完成项 |
| --- | --- | --- | --- |
| L1 合同与证据固定 | W0 | 固定七宏源、每op格式/握手、角色路径、owner/生存期/ACK与测试门；明确六配置适用的样本层型 | 合同和14核心锁、172角色路径及P2缺口已形成可审查资料；不是172条硬件通过，外部审查待完成 |
| L2 共同岛壳 | W1 | 真实输入数据→S存储ACK→启动；输出/完成保持、错误/reset/abort、资源归属；逐步推广参数/形状 | 已有固定S8 DOT8、8输入拍、硬件清padding的可变数据岛壳；完整通用shape、跨岛存储确认与无reset排空未完成 |
| L3 E/G与FFN核 | W3 | E按op收齐A/B/C；G双路配对、128↔32拆拼/在途退休；gate/up→SiLU×up→down→残差 | E/G适配器和有限FFN8已实现测试，未改原生宏。本次F8服务器25项还覆盖其组合；不是任意模型完整F |
| L4 N及完整A/F纵向集成 | W4/W5 | N统计/FINAL/原码回放/归一化/Softmax，结合M/E/G组成完整Attention/FFN子层 | 正在推进：N/preNorm F8/A8已验证，完整A/F及真实shape未验收；W5-IF有界逻辑合同v0.1已形成待审查，接口/母控/岛间RTL未实现 |
| L5 双岛与一般拓扑 | W2/W6 | 岛间fragment、目的stored ACK、源CLOSE/release、母控事件；同岛复用、fork/join、条件分支和合法反馈 | 尚未开始RTL。已安排W2实现拟定固定母控控制网与双岛stored ACK，W6扩一般拓扑；先依赖L4/W5-IF有界接口合同 |
| L6 NUM/R与D/H岛 | W7/W8 | 按需求补宽数值服务；R候选保存、history/state两pass、old/next版本、多tile提交/错误；组成GDN/SSM岛 | 尚未开始RTL；R原生最终资格仍为上游独立依赖。有限单tile不能代替完整状态/模型验证 |
| L7 动态MoE岛 | W9 | router→TopK ID/rank→选分数Softmax→专家数据/计算→宽加权归并→残差 | 尚未开始RTL；不能把ID当score，或仅测专家FFN就宣称完整X。依赖所需NUM与容量映射，不必等待R通过 |
| L8 真实MEM、完整产品与物理 | W10/W11 | 真实容量/地址/搬运/带宽/故障，完整产品程序/层表、母子控制与ROM预算；共同底座和定制金属/PPA验证 | 尚未开始系统RTL/物理验证；接口、容量和后端约束应前置研究，最终验收依赖前面真实成果。不能把大模型缩到8维后称真实尺寸通过 |

六配置是A_plain（普通Attention）、A_gate（带输出门Attention）、F（FFN）、D/H（两类GDN/SSM状态流程）和X（MoE）。它们是资源/流程配置，完整硬岛尚未制成；当前F8/A8是验证岛内机制的固定小切片，并不要求每岛装齐七类宏。

## 三层互联问题已纳入主线（2026-11-02修订）

主要RTL实施归属**L5/W2、W6**，在**当前L4/W5的前置子任务W5-IF**先定逻辑接口与ACK/资源/层边界，在**L8/W10、W11**接真实MEM并验共同底座和M11/M12物理差分。具体产物、依赖及退出门见[三层互联实施安排](COARSE_BLOCK_INTERCONNECT_BOUNDARY_PLAN.md)。

主候选是岛内固定互联、母控—local CTRL固定控制网、模型数据路线及配套确认由M11/M12定制。母控全局控制网原先未冻结，本次纳入proposed设计安排，不能写成已经预连的物理事实。岛内适配继续随各功能岛实现，不要求等到L5才研究；pin/扇出/路线/中继/缓冲和clock/reset约束从L4/L5前置反馈，最终物理验收归L8。

当前已形成[W5-IF接口合同v0.1](W5_IF_INTERFACE_CONTRACT.md)，含端口/事件/资源表及B8完整因果时序，待审查；下一步L4细化完整A/F数值/残差/布局及Norm/容量映射，再扩大岛顶层；W2可用匹配合同的MST/复制核验证母控和双岛闭环，不把当前A8/F8固定输入帧直接等同通用hidden张量入口。L6/L7复用并补R版本/partial和MoE动态事件。f9a90c8轮次只完成计划；本轮进一步形成有界逻辑合同，没有新RTL/仿真/服务器操作，L5 RTL仍未开始。

## W5-IF本轮合同范围

三层职责、task/fragment/存储ACK/关闭与复用、错误/partial/代际恢复、现MST/A8/F8适配缺口及有限样本要求已经成表。首个W2示例是新SOURCE_COPY_H8→SINK_READ_H8一字传输，尚无RTL；64/128bit编码、536逻辑端点bit/岛及82B显列holding都只是候选，不代表实际M10 pin、完整面积或全模型接口冻结。完整A/F整数格式、参数供给与真实容量仍GAP；原A8/F8相同128bit出口不能裸接通用hidden。

## 当前主线四到了哪里

1. N端点服务已实现单组RMS/L2/Softmax，范围1..257。控制器执行BEGIN→全部STATS→FINAL；Softmax另将EXP U16原码真实写S、ACK后再读回，得到概率并写目的S，最终ACK后才完成。TopK/多组仍未实现。
2. F方向已有RMS-preNorm F8。归一化输入与原始X残差分别保活；M投影/G门控/E残差与明确RNE窄化已组合。这不是所有模型Norm位置都覆盖的完整F。
3. 本次A方向新增A8：单query/head、8key、D8、8输出channel，Q/K/V S8Fin7→score Fin10→概率Q14→PV输出Fin10。M/N/S/T各1，普通数据M→S→N→S→M，不存在新独立bridge硬宏；Nctrl、S helper和原生叶宏不变。
4. 服务器Verilator真实job95116在c64/node1、单task8CPU、1分51秒自然COMPLETED/0:0。N29/F825/A826共80个预声明CASE完整、唯一且PASS，3次compile/sim均0；不是80次完整模型推理。A8为9687周期，逐阶段数据与独立整数预期一致。

主线四仍未整体退出。下一步按样本模型先固定Attention变体及数值/layout合同，再补QKV投影、需要的Q/K Norm/RoPE/GQA、mask/有效长度、输出门/投影/残差。单M每次复用前保存仍需的结果；转置、头映射与缩放转换必须有实际软件布局合同或预制硬件，不靠同位宽假定完成。完整F也需核对各模型pre/post Norm与residual次序。

有界完整A/F流程验证后，才对真实H/head/序列/tile和容量映射给出接收结论；超片上部分与L8真实MEM共同闭合。L5接口/后端反馈可提前设计，但本轮不擅自改为实施L5。

## 结果、限制和交付状态

正式实现/数值/验证见[本次A8报告](W4_A8_IMPLEMENTATION.md)、[数值合同](W4_A8_NUMERIC_CONTRACT.md)、[服务器证据](W4_A8_VERIFICATION.md)。全部新RTL仿真/回归在服务器Verilator，无本地RTL仿真；历史ModelSim证据不改写。

首次环境/编译失败保留，最终功能仿真采用-Wno-fatal保留全部warning，未关闭warning类别、时序、assert或故障CASE；仍有TIMESCALEMOD/位宽警告，不能称lint clean或物理验收。32份继承SV/SVH逐字节不变，R未实例化且未借此获得资格。

PR152待独立审查/合并，不自合并、不标done；负责人Melodydt。登记management-hub PR5仍待最新在线核验；当前config无board.json且工具无Projects item能力，看板unverified/同步pending，处理人待指定。Issue标签、文件上传与在线Projects同步是不同事实。
