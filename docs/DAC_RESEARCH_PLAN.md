# 面向 DAC 的研究推进与证据要求

更新：2026-10-22，UTC+08:00；用户已确认目标会议为 DAC，具体届次尚未指定。任务[Issue11](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/11)和接续[Issue13](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/13)，负责人Liangruizhi。本文给研究决策和验收依据，不承诺录用，不把计划写成结果。

## 投稿窗口与研究定位

以最近公布的 DAC 2027 官方窗口作暂定规划：摘要北京时间2026-11-12 09:00、正文11-19 09:00（官方为11-11/18 17:00 US Pacific）。正文最多6页，另1页仅参考文献；双盲，按完成稿审阅，需按政策处理AI生成内容。日期与规则于2026-10-22核验，正式投稿前再核对[官方Research Manuscript页面](https://dac.com/2027/program/research-manuscript-submissions)。此处不替团队决定届次、作者或提交论文。

候选定位是通信架构设计工具／加速器设计方法（EDA1.3/1.8）或划分、布局布线与互联规划（EDA7.1—7.3）；按最终有证据的贡献选择，不能用现有开源流程运行成功代替方法贡献。

研究主线候选：**在明确的端点、固定有源资源和可定制连接预算下，如何共同选择局部计算—存储边界与互联组织，让同一底座支持不同LLM数据流，同时量化固定资源闲置与通信代价。**

## 已有工作与本轮分工

- main `1a98e9d` 已合入参考报告、接口分析、逐层资源讨论和远程使用规则。
- YUZE-LU 的 [Issue #7](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7) / [PR #8](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/8)完成VECTOR块及单宏顶层工程尝试；仍有块内／父级时序、电容、宏时钟／功耗模型和完整等价缺口。
- [PR #10](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/10)保存ACT/MXU/GEMM并行结果与电容修复；部分候选通过本次工具门槛，合并块仍未通过。不能据批作业或哈希检查成功称宏资格齐全。
- Issue11新增`project/experiments/frozen_routing/`，Issue13在`project/experiments/endpoint_ablation/`接续严格配对消融，补模型、独立验证与受控基线；未修改上述分支、集群作业、他人记录或参考包。抽象模型不是已有宏的尺寸／端点／时序抽象。

## 需要检验的主张

| 候选主张 | 受控对照 | 最小证据 | 当前缺口 |
|---|---|---|---|
| 端点限制与不可拆导线改变布线可行性 | 同最大合成库存、同映射，overlay逐项放宽白名单／容量并固定路由法与预算；小例精确oracle | 所有成功解全局电气合法；失败保留；区分约束改变与搜索预算影响 | Issue13完成384例反事实配对，9映射有白名单无路径→合法解证据；仍未校准真实引出与via |
| 局部计算—存储簇降低部分跨界负载 | 同计算／存储／适配资源，分离与融合边界 | 相同数值与工作负载的跨界字节、等待、完整面积、时序与活动能量 | 本轮未做物理粒度对比；衔接Issue7，不能由图示推断收益 |
| 后期改线有时比一份固定连接更有适配价值 | 设计集选择固定网络、允许同类映射；冻结后评估不同保留图 | 同资源的多拓扑连接与功能、固定网络同样适用的否定结果 | 本轮固定基线为有限候选池，不是全局最优；无调度／代数重写 |
| 预埋段长度存在端点与可达性折中 | 相同预埋总线长下短段／长段；单独列轨道数预算 | 端点数、合法布通率、定制连接数、预埋利用与失败 | 无RC、拥塞几何、驱动、时钟或制造成本校准 |

不把顺序搜索的改进称新算法。须在完整相关工作比较后，明确新增约束、联合决策或可验证优势在哪里。

## Issue11实验合同

8种预声明底座变体 × 4种拓扑 × 3种合法映射种子 × 2种路由方法，共192例。设计集为普通FFN和门控FFN，保留集为残差FFN与双投影汇合。跨度变体在相同轨道数下保持预埋线长；轨道数／接入选择数变化是设计空间，不能混作同资源收益。

先收缩全部固定导线为不可拆component，后期仅可接白名单端点。输出stub始终是潜在驱动；不同输出不能靠错时发送占用同一被动导线。完整所选连接经独立验证器重建全局电气分量，另核对冻结Block操作能力、映射单射、输入驱动、宽度及端点容量。小例穷举所有连接子集；功能通过连接读取driver后执行软件图，与独立NumPy表达式比较。

16-bit束仅描述同构并行导线，float64功能解释器不模拟其编码或多拍传输；不声称16-bit数值、RTL、周期、RC、PPA或制造H2。权重、时钟、供电、控制分发和缓存调度尚未纳入，必须逐步补齐后再提升证据尺度。

固定互联基线允许所有同类单射映射，但不做代数重写、插入恒等操作或时间复用；逐任务对照每例只试一个固定映射，搜索自由度不同。结果分开呈现，不据覆盖数计算优越倍数，不把“候选中未覆盖”写成“固定互联本质不支持”。

## Issue13接续证据与下一步

384例将master库存和constraint overlay分开，固定每例mapping与14次路由预算：restricted44/96，access71/96，capacity44/96，joint71/96；230成功解及248份cut均读回验证。仅9个固定映射具备原白名单无路径、access条件合法解的因果证据，不把所有成功变化归因于原配置全局不可行。容量放宽未观察到额外成功，但微例证明容量约束实现有效；不概括为容量无关。真实记录见[Issue13实验](experiments/issue-13-endpoint-ablation.md)。

这轮复用了已经观察过的四图；restricted96例与Issue11对应方法逐项相同，不称新盲测。接续[Issue16/PR18](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/18)按[宏端点合同](MACRO_ENDPOINT_CONTRACT.md)冻结三份普通LEF原字节/SHA，完整导出6791PIN/6956PIN RECT/30OBS RECT并逐字节重放；见[实际记录](experiments/issue-16-macro-endpoints.md)。上游逐文件预期SHA、RTL/tool/image精确版本仍未知，不能将新捕获哈希当上游认证。下一步先补逐bit接口匹配与DEF/技术访问规则，再做固定K个mapping、总预算相同的端点感知对照。端点矩形可读不代表工艺访问、时序、PG或等价已合格。YUZE-LU的Issue15推进同资源ACT/MXU分离/融合物理对照，避免重复认领。

## 进入下一阶段的门槛

1. **模型基础**：本轮源码／输入冻结，独立负例和oracle通过，原始结果读回并确定性重放；承认启发式未找到解的未知状态。
2. **宏资格与F0/H1**：沿Issue7补齐等价、minimum_period/内部时钟模型、arc、边界驱动负载、PG和电气门槛；同资源flat/hierarchy条件一致。处理人由后续Issue指定，不在这里给其他成员派活。
3. **物理受限定制**：用通过资格的宏替换抽象库，冻结全部有源单元、位置、端点、时钟和供电；只允许声明金属／通孔变化，至少两个真正不同计算图。不得靠为每图新增buffer、改变宏或移动位置修好后仍称同底座。
4. **任务级校准**：增加握手、背压、存储冲突、时钟传播和数值边界；软件→RTL→局部物理参数对照，外部输入／权重供给口径一致。没有活动与功耗模型则能量记未测。
5. **论文决策**：只有关键主张、受控基线、保留集和失败边界形成证据链才决定投稿；若当前窗口前未通过，保留可复现结果并调整主张或届次，不以更多无关扫描填充篇幅。

## 相关工作入口与阅读状态

以下优先核对原文中的可定制资源、运行时选择器／三态、工作负载、映射算法、工艺和基线自由度。它们已覆盖大量先例，“少量掩模＋多任务DNN”本身不足以作为新颖性。

| 一手来源 | 用途与目前阅读状态 |
|---|---|
| Shin/Hamada/Kosuge, *A Connectivity-Aware Via-Programmable DNN Processor Using a Single Photomask*, OJCAS 2026, DOI 10.1109/OJCAS.2026.3656510 | [作者官方目录](https://klab.t.u-tokyo.ac.jp/en/international-journal-papers/y-2026/)、[公开作者接收稿](https://www.researchgate.net/publication/400045017_A_Connectivity-Aware_Via-Programmable_DNN_Processor_Using_a_Single_Photomask)。本轮已读作者稿I—VI及实验表，尚未取得出版社排版全文或复现工程 |
| Agile-Chip 的ASIC/FPGA/单层与双层平台比较，IEICE 2026 | [出版商摘要](https://www.jstage.jst.go.jp/article/transinf/E109.D/10/E109.D_2025EDP7273/_article/-char/en)。本轮已读摘要，未完成全文核对，不引用其未核实数值 |
| VPEX3，IEICE 2012 | [出版商摘要](https://www.jstage.jst.go.jp/article/transfun/E95.A/12/E95.A_2182/_article/-char/en)。via-programmable与专用布线先例；本轮只核对摘要 |
| Ahmed/Lemieux/Wilton，MPSA性能与成本权衡，TVLSI | [作者原稿](https://people.ece.ubc.ca/~lemieux/publications/ahmed-tvlsi2010.pdf)。作为可定制层数与成本口径入口，待精读，不据此声称本项目优势 |

VPNA作者稿已有面向1D CNN的单VIA、多任务底座、规则端口、映射与后布局评估。特别是其串行总线具有预制三态驱动与使能，允许有电路支持的分时共享。我们的静态被动单驱动模型覆盖面更窄，不能把其合法共享判为错误，也不据两种模型宣称优劣。

后续差异验证应聚焦运行时加载权重、矩阵／向量／存储反馈、真实宏端点与固定轨道共同约束，以及保留数据流的适配范围。加入时间复用时须新增明确的预制选择能力、控制、缓存和成本模型；目前均待验证。正式引用和参数校准仍需团队审阅，所有本项目测量以实际运行manifest和实验记录为准。

## Issue19 接口证据与输入问题

[Issue19/PR20](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/20)补齐旧wave206 ACT/MXU逻辑端口—Liberty—普通LEF关联：3032信号位、原合同685连接、2346边界网；10项生产SHA对照、148项业务检查、205390项独立比较、6个篡改负例及离线重放通过。与Issue16当时未知状态相比，本轮补齐选定两宏的上游生产索引对照；并未补齐全部工具版本或功能等价。

真实发现两份Liberty cell.area缺分号及4处VDD/VSS方向差异。显式窄兼容profile仅用于接口审计，严格模式仍拒绝，原始输入未改；PG与时序/宏资格仍未闭合。详情与版本见[实验记录](experiments/issue-19-interface-contract.md)。PR17已推进新M9物理视图，本结果只绑定旧数据，不能代替新视图验收。下一步须刷新协作状态、重新绑定新版本并核对DEF/工艺访问，固定预算mapping对照的前置条件仍保留。

## 用户明确的首要研究问题（2026-10-22）

以[共同问题](RESEARCH_QUESTION.md)和[划分方法v0](OPERATOR_BLOCK_PARTITION.md)为当前主线。允许少量有结构差异的代表模型，首轮推理prefill/decode，训练作为结构约束。Issue21给出630个调度账本及数值核，证明调度省存储不能直接推出物理合并收益；仍欠真实权重trace、具体bank/端口模板、布线/时序校准与端到端收益。此前宏资格与互联实验作为前置证据，不能替代模型驱动划分。
