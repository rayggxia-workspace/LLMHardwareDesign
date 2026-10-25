# LLMHardwareDesign：预制计算底座研究

本项目研究面向多个计算图的预制计算底座：预先确定计算 Block 和部分物理资源，再通过有限的金属／通孔层定制跨 Block 互联。当前处于**架构定义与研究方案整理阶段**；具体工艺、Block 库、定制层集合和实现工具链仍待确定。性能、能耗和成本优势是待验证目标，不是已有结论。

[完整MoE与分组边界验证](docs/experiments/issue-74-moe-grouped.md)已完成服务器8整数MoE条件和12同资源分组服务；宽算术/元数据/端口计价后仍保留M/V物理映射选择。原失败及整模型/物理验证限制保留，详见[Block v2第13节](docs/BLOCK_PARTITION_V2.md)。

[最新有限Granite端口与宽成本实验](docs/experiments/issue-76-granite-ports.md)24配置全部独立通过：完整merge可在V16KiB内，近M仅省约0.00084%条件slots。保留M/V物理选择，优先校准宽算术局部暂存与预连线；见[Block v2第14节](docs/BLOCK_PARTITION_V2.md)，完整FSM/STA/PPA与整模型质量仍未验收。

[首轮 Block 电路验证](docs/experiments/issue-80-block-circuit.md)已补齐实际宽控制器、有限 frame 和单 ROM 服务。895×4 个命令独立通过；同库存局部连接使本批执行周期减少 42.5%—44.0%，研究库逻辑面积增加约 0.16%（不含共同 memory wrapper）。纯 byte norm 仍代价高，完整 M/A/R、SRAM/ROM 宏和 STA/PPA 未验；见[电路规格](docs/BLOCK_CIRCUIT_SPEC_V1.md)与[Block v2 第15节](docs/BLOCK_PARTITION_V2.md)。

[归一化专用化与真实 M 消费者](docs/experiments/issue-82-norm-circuit.md)已在服务器完成174条正式RTL命令独立核验。H1536 norm从258244降至61492 cycles，但完整M消费者仅降2.17%，logic-only面积增26.44%；下一步优先减少重复喂数和算术共享，4步SFU尚待时序资格。见[Blockv2第16节](docs/BLOCK_PARTITION_V2.md)，非整模型或最终制造PPA。

## 从哪里开始

1. [项目说明 v1.0](预制计算底座项目说明_v1.0.md)：研究问题、已确认边界、候选方案和待决策清单。
2. [研究资料导读](研究资料导读.md)：依据原 README 完整要点整理的阅读顺序、架构问题和 EDA 研究路线。
3. [项目简介](docs/PROJECT_BRIEF.md)、[架构与目录](docs/ARCHITECTURE.md)、[当前状态](docs/STATUS.md)：持续更新的项目入口。
4. [不同 LLM 架构下的 Block 研究](docs/面向不同%20LLM%20架构的预制计算底座.md)、[Gemmini 学习笔记](docs/Gemmini学习笔记.md)、[工艺互连资料](docs/常见开源工艺金属互连线.md)：研究背景与候选方向。
5. [布线总报告](ref-project/llm-routing/总报告.html)、[线长报告](ref-project/llm-routing/线长报告.html)、[模块与接口报告](ref-project/llm-routing/模块与接口报告.html)与[结果包阅读说明](ref-project/llm-routing/阅读说明.txt)：参考项目的布线分析、模块接口及其证据边界。

`sources/` 保存手写笔记和讨论资料；`ref-project/llm-routing/` 保存参考项目结果包，**不纳入 Agent 的主动或例行维护范围**；用户更新后可按要求提交，无需逐项审查或做哈希检查。该包不包含源代码、完整物理数据库、工具环境或运行日志，不能单靠仓库内容重新运行物理实现。详情见[来源与复现边界](docs/DATA_PROVENANCE.md)。

## 最新关键边界证据（2026-10-24）

[Issue72关键闭环](docs/experiments/issue-72-numeric-closure.md)已在本人CPU服务器完成：Granite高精度条件参考和768整数路由、Falcon完整整数R分支/续接及3种out_proj粒度、20完整compute服务均独立接收。因果重标在当前72步零发布sat；分组A8降低局部L2但增partial成本。10对标签零差、实际部署差<0.02%，不支持冻结独立R或V/R合宏。详见[Block v2第12节](docs/BLOCK_PARTITION_V2.md)和[索引](project/experiments/closure/results/issue-72/index.json)。完整9.90GB授权服务器/精选2.48MB metadata均SHA验收，PR73待审查合并，非质量/RTL/PPA验收。

[Issue70新增架构最小集](docs/experiments/issue-70-moe-hybrid.md)已在服务器完成Granite小MoE与Falcon并行Attention/SSM的采集、独立数值/路由归因和24配置双轮COPY端口核验。Granite chunk16原FAIL保留、局部仅PARTIAL；Falcon23参考门通过，但两整数状态存储候选均4sat且有FP64更新桥。[Block v2第11节](docs/BLOCK_PARTITION_V2.md)补动态路由/宽merge、参数化状态tile、4096跨head norm及三输入join；未冻结物理宏或E2E。3.14MB精选/966MB服务器完整包有SHA索引，PR71待审查合并。

[Issue68范围/同资源服务](docs/experiments/issue-68-range-service.md)已在服务器完成因果重定标双轮、独立整数接收与两套各56配置的V/R/S双轮有限服务。固定旧S32窗两次重定标消除193次sat，但包含额外clone/retry成本；每套48个共享/拆分同资源轨迹对照为零差。tile16本地shadow作为下一轮工作基线，独立R/合宏、完整质量及RTL/PPA仍未定，详见[新决策](docs/decisions/2026-10-24-r-range-and-finite-service.md)与[Block v2第10节](docs/BLOCK_PARTITION_V2.md)。PR69待审查合并。

[Issue66消费者/连续整数状态报告](docs/experiments/issue-66-scale-state.md)已完成服务器并行双轮及独立接收，补完整hidden消费者和整数input RMSNorm。S32降低短程误差，却未解决长窗同范围饱和；V整行缓冲超限需要重读/spill。因此[Block v2第8/9节](docs/BLOCK_PARTITION_V2.md)收敛数值/状态/资源义务，保留制造边界候选。19.58MB精选可离线验算，5.21GB全量在授权服务器留SHA；PR67待审查合并，非全模型整数或硬件PPA验收。

可转发团队的[算子与Block划分阶段性总结](docs/reports/2026-10-24-operator-block-partition-summary.md)汇总已完成的架构级分区、实验依据和下一阶段验证。

## 当前工作方式

[有证据的Block方案v2](docs/BLOCK_PARTITION_V2.md)已综合Llama/Qwen及服务器主测，并完成[Issue64三组最小服务器实验](docs/experiments/issue-64-block-v2.md)：输出格式、整数attention闭包和同库存完整GQA条件服务。单位/完整归约/共享状态合同可以确定；M+A合宏、R独立、RQ位置和端到端收益仍待验证。10.08MB精选包与独立接收可复查，原失败保留，PR65待审查。

[服务器四模型补齐批次](docs/experiments/issue-61-server-models.md)已完成本轮CPU参考/采集、三主测420线性/56注意力整数探针与独立接收，Phi封存。动态K组scale、概率/KV分离精度及有条件INT32范围证明细化了候选边界；失败保留，尚非整图/硬件/PPA验收。详见[候选决策](docs/decisions/2026-10-23-invariant-preserving-block-boundaries.md)和[两日团队汇报](docs/reports/2026-10-23-two-day-progress.md)。

[Llama down_proj校准与scale粒度](docs/experiments/issue-59-llama-down-scale.md)已完成本机24候选/144数值、1152服务两轮；改K组scale需显式对齐归约/metadata/guard，仍无最终硬件或完整质量结论。

[本机Llama-3.2-1B跨模型验证](docs/experiments/issue-56-llama-cross-model.md)复用完整GQA整数与端口工具，
保留静态FFN激活量化的大误差、容量拒绝和微小RQ服务差异；它是局部候选证据，非全模型/硬件方案验收。

面向DAC的研究主张、相关工作和分阶段验收见[研究推进计划](docs/DAC_RESEARCH_PLAN.md)。本分支新增[冻结连接资源实验](project/experiments/frozen_routing/README.md)，提供可运行的抽象路由、全局电气合法性和软件图检查；其通过不代表物理H2或PPA收益。其他成员已提交的Block物理工程见Issue #7关联PR，尚待审查及质量验收。

[Issue13端点限制消融](project/experiments/endpoint_ablation/README.md)进一步固定库存、映射和搜索预算，区分限制松紧与搜索失败；[真实宏端点接入合同](docs/MACRO_ENDPOINT_CONTRACT.md)说明已有视图与尚未补齐的资格。

[Issue16真实LEF几何库存](docs/experiments/issue-16-macro-endpoints.md)冻结ACT20/MXU20/GEMM20三份普通LEF及SHA，完整导出6791个PIN、6956个PIN矩形和30个OBS矩形，并保存无损原字节及离线重放工具；PR18待审查。几何可读仍不代表工艺访问或硬宏资格已合格。

[Issue19三视图接口记录](docs/experiments/issue-19-interface-contract.md)进一步把3032个信号位与原有685bit连接合同关联，保留两处Liberty语法缺项和四处PG方向差异；原始输入、逐bit表、独立审计及离线重放随[PR20](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/20)交付待审查。旧wave206证据不推广到新M9宏。

远程计算资源与目录权限见[远程服务器使用规则](docs/REMOTE_RULES.md)，使用服务器前请先阅读。

任务、负责人和验收条件以本仓库 [Issues](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues) 为准。每项任务使用独立分支和 PR；开始工作前阅读 [AGENTS.md](AGENTS.md) 与[协作说明](docs/COLLABORATION.md)。管理结构检查命令为：

```powershell
python scripts/check_project.py
```

上面的命令只验证项目管理文件结构，不验证芯片架构或布线分析结论。

业务检查和实际实验命令见[架构与运行](docs/ARCHITECTURE.md)及对应实验README。

## 当前研究主线

接续分析见[具体Block候选v1](docs/BLOCK_CANDIDATE_V1.md)：明确M/V/A/R/S/D的计算、状态、
接口和预连线，并以[最小决策实验](docs/BLOCK_MINIMAL_EXPERIMENTS_V1.md)区分待选边界。
这是分析候选与后续验证计划，尚无最终制造划分或端到端硬件收益结论。

以[共同研究问题](docs/RESEARCH_QUESTION.md)为判据，优先研究算子/Block划分及内部预连线/接口裕量。首轮[方法](docs/OPERATOR_BLOCK_PARTITION.md)与[实际结果](docs/experiments/issue-21-operator-partition.md)区分调度、状态归属和物理边界；630调度案例与缩小数值核已完成，不等同完整模型或端到端硬件收益。
