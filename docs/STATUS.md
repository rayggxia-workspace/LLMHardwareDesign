# 当前状态

- 2026-10-23 [Issue59/PR60](experiments/issue-59-llama-down-scale.md)：Llama down_proj校准与K组scale已本机24候选/144数值、1152服务两轮。最佳局部误差5.39%，并非可接受全模型质量；新增对齐归约/元数据/guard边界，未决定必须INT64或固定近端RQ。粗35bit与实际W所见scale的32bit界严格区分。精选证据可重放24代表条件，全量原输入本机留索引共享pending。用户最新将兄方批次交给本会话服务器推进，Issue61先接收PR36已有数据并核剩余缺项；其他成员Issue55集成保持独立。


- 2026-10-23 Llama跨模型：[Issue56/PR57](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/57)
  已有1B权重本机完成一层完整4Q/1KV的FP32/cached、两轮整数GQA/16线性条件/384端口配置。
  重要边界：down静态A约99.8%置零且局部误差70%–83%，动态行scale改善仍非应用质量通过；完整K内留需同乘积scale。
  近端RQ服务最大仅降约0.405%，不冻结不可绕过连接。精简包可重放全部编码整数与8 witness，完整浮点输入本机留SHA/共享pending。
  [报告](experiments/issue-56-llama-cross-model.md)/[决策](decisions/2026-10-23-llama-scale-and-block-boundaries.md)；全模型/RTL/PPA未验收，未done。

- 2026-10-23 CPU迁移：[Issue53/PR54](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/54)
  服务器独立环境已建立，已有Qwen3-0.6B两轮32CPU作业89943/89945完成，各6线程/精度条件。
  FP32完整/cached/chunk及28层KV全通过；BF16的8/16线程分块误差超预设门，32线程相等，两轮重现。
  只证明该小模型短上下文CPU迁移，未测更大模型/长序列、INT8或硬件收益。报告/失败/环境/输入/SHA已归档。
  与Issue29原型回归/分阶段综合并行，分别记录；E2b完整attention与E3公平递推仍是待做主线。

- 2026-10-23 E2a：[Issue51/PR52](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/52)
  完成384组织的无bias整数Linear/RQ8固定资源服务比较，8CPU/8worker服务器89937与本机逐项一致。
  各自优化已有策略后近端RQ最好仅降约0.566%，不足以固定不可绕过边界；矩阵/消费者服务未RTL校准，
  不构成完整E2、LLM端到端或物理收益。正式[报告](experiments/issue-51-rq-port-placement.md)与作业/SHA已留档。
  用户已授权服务器CPU并行；完整模型迁移尚缺现代框架/权重和pilot，师兄GPU专属测量保持分工。

- 2026-10-23本机数值接续：[Issue47/PR49](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/49)
  对已有Qwen3-0.6B一层完整GQA组完成独立校准、冻结KV scale和因果cache局部验证，两次整数payload一致；
  误差改善仅为短切片证据，不是全模型质量或端口/RTL/物理收益。能力清单见[P1–P15](PRIMITIVE_CAPABILITY_MAP.md)，
  [实际报告](experiments/issue-47-primitive-stream.md)。下一步固定语义的RQ/状态端口配对；
  E1b完整模型质量不作EDA额外前置。用户扩展GPU批次由师兄处理，本机未下载新模型或启动其他机器。
  未合并、未done；Issue48资源估算器由其他成员负责，保持范围分离。

- 2026-10-23分析接续：Issue41形成[具体Block候选v1](BLOCK_CANDIDATE_V1.md)，
  六类模板的计算/状态/接口/预连线、声明库存、模型映射和D1–D6均显式；
  [最小实验](BLOCK_MINIMAL_EXPERIMENTS_V1.md)缩为数值门、三类边界判别和冻结后验证。
  本轮只解析复算，不新增模型/RTL/GPU/远程运行；硬件资格/收益未验证，未接管兄方Issue32/31。
  [PR44](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/44)交付待审查合并；
  与其他成员Issue42方法/Issue43资源约束互补，后续只按决策分叉补验证。

- 2026-10-23本机接续：[Issue39/PR40](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/40)
  复用真实Qwen3短head完成24组合整数QK/PV及bias边界，89280整数比较和两次科学payload重放通过。
  direct量化局部误差大，离线平衡仅定位，在线scale/GQA共享/正式质量与物理资格尚未闭合，不宣称最终Block。
  [记录](experiments/issue-39-kv-scale-boundary.md)及[师兄Codex可复制文案](handoffs/2026-10-23-gpu-codex-experiment-prompt.md)已交付待审查；
  师兄Issue32 Qwen仍优先，未重复GPU/大模型，等用户完成通知再整合。

- 2026-10-23精度接续：[Issue33](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/33)
  单独实现W8A8候选合同、整数参考与本机量化划分，复用但不接管Issue25/PR26的文档范围。
  [候选精度](INTEGER_PRECISION_CONTRACT.md)及[采集格式](GPU_CAPTURE_CONTRACT.md)已先行发布；
  本机阶段现已完成并交付[PR34](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/34)待审查，未done。
  [报告](experiments/issue-33-integer-precision.md)：20业务测试、1028 RQ RTL用例、实际Qwen3切片和
  4608点量化图搜索。近端RQ减少通信不等于关键路径改善，P7长行全零、短校准裁剪及私有工作区成本均保留。
  尚无INT8端到端/全整数硬件能力结论。大模型/长上下文/GPU交师兄，不启动其他机器；
  [交接](handoffs/2026-10-23-issue-33-integer-precision.md)后等用户通知再整合，旧active文字仅为历史。

- 更新日期：2026-10-22（中国标准时间）
- 前阶段记录：架构定义、Block物理工程尝试、抽象冻结连接实验、真实普通LEF几何输入冻结与选定接口关联；DAC为研究目标，具体届次未指定
- 资料接入：[Issue #1：初始化项目并导入初期资料](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/1)；资料已进入 `main`，[PR #2](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/2) 已合并，登记／看板缺项继续保留
- 当前资料：项目说明 v1.0、专题研究文档、来源笔记，以及五个参考项目七个案例的布线分析包；三份 HTML 报告、llaccel 引擎内部分析及远程服务器规则已通过 [PR #4](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/4) 合入 `main`；工艺互连资料的逐层资源评估补充已一并提交
- 已确认边界：研究对象和主要问题已写入项目说明；具体工艺、Block 资源、定制层集合和工具链未冻结
- 关键限制：现有布线结果包含少量 RTL 片段，不含完整源工程、物理数据库、工具环境和日志，不能单靠本仓库复跑物理实现
- 最新业务：YUZE-LU的[Issue #7](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7)在[PR #8](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/8)/[PR #10](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/10)保存VECTOR顶层尝试和ACT/MXU/GEMM修复，未合并；时序、电气、模型及等价缺口以最新交接为准。普通分层工程不称物理H2。
- 研究接续：[Issue11/PR12](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/12)的192例实验待审查；[Issue13/PR14](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/14)完成384例配对消融，白名单扩展44→71/96，9映射有原无路径到合法解证据，容量放宽未新增本轮成功。230解与248份cut及全量重放通过，见[实际记录](experiments/issue-13-endpoint-ablation.md)。两PR均未合并，未形成物理H2/PPA结论。
- 真实输入：[Issue16/PR18](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/18)冻结ACT20/MXU20/GEMM20原字节/SHA，6791PIN、6956PIN RECT和30OBS RECT完整保留PORT/PG/OBS；67项业务检查及确定性重导出通过，见[实际记录](experiments/issue-16-macro-endpoints.md)。PR待审查，未形成工艺合法access point或合格宏。
- 并行工作：[Issue15](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/15)由YUZE-LU推进同资源ACT/MXU分离与合并物理对照，不重复开工；普通分层对照不等同物理H2。
- 接口证据：[Issue19/PR20](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/20)完成旧wave206两宏3032信号位、685连接与2346边界网关联，原始两处Lib缺分号及四处PG方向差异明确保留；148项检查、205390独立比较、六个篡改负例和离线重放通过，待审查。见[实际记录](experiments/issue-19-interface-contract.md)，不等同新M9宏或合法接入资格。
- 下一步：刷新Issue15/PR17新M9结果，绑定新视图版本，核对Lib/PG问题、DEF方向及技术via/OBS接入规则。条件满足后固定资源和总预算研究端点感知mapping，继续补齐宏资格。研究路线见[DAC计划](DAC_RESEARCH_PLAN.md)
- 任务入口：[本仓库 Issues](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues)
- 项目登记：[管理中心 PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5) 待审查；合并前状态为 pending
- Projects 入口：[组织总览看板](https://github.com/orgs/rayggxia-workspace/projects/1) 为管理中心配置的候选入口；本仓库无 `config/board.json`，本次Liangruizhi会话无Projects工具，账号在线权限及Issue11/13/16/19条目未核验／同步pending；Issue #3关于缺少 `read:project` 的旧交接属于其他会话，不能据此推断本账号权限。具备工具与权限的管理员待指定

本页只记录全项目阶段和关键限制；具体任务进度以 Issue 和 PR 为准。

- 当前主线（用户2026-10-22明确）：[共同问题](RESEARCH_QUESTION.md)，模型驱动算子/Block划分及块内预连线/接口裕量，耦合块间物理约束。[Issue21/PR22](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/22)已提交待审查，形成官方架构证据、630调度账本、独立数值核与可解释反例；仍无最终划分或端到端硬件收益。正式benchmark允许少量有差异代表，首轮推理。
- 接续优先级：可运行代表模型prefill/decode实际trace→具体bank/端口/状态模板→与Issue15物理证据校准→同资源端到端比较。细节以[划分方法](OPERATOR_BLOCK_PARTITION.md)和Issue为准。

- 真实模型接续：[Issue23/PR24](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/24)已提交待审查，已用固定Qwen3-0.6B权重跑通CPU FP32 prefill/decode；54数值对照、4状态错误负例、13720真实边界事件与两次重放通过。chunking缩小临时张量而同prefix持久KV不变，见[实际记录](experiments/issue-23-qwen3-real-trace.md)。尚无端到端硬件收益，下一步同trace约束bank/端口/带宽并扩差异架构。
- 状态/端口阶段：[Issue27](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/27)正式源码6ffb9417完成3456条件（1224可行/2232拒绝）、4896策略调度及两次重放；真实Qwen单头6在线核正例/10适用错误负例通过。相同流量的placement收益依赖端口与调度，本阶段未物理校准，不能称芯片加速，见[实际报告](experiments/issue-27-state-port-model.md)。下一步可执行微架构端口验证、独立精度合同与差异/完整工作负载耦合。
- 并行更新（核对固定版本）：[PR26@2cd9ca15](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/26)负责benchmark调研，W8A8/INT32矩阵与未冻结KV/非线性格式分开；[PR17@0f58e74](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/17)首个合并父层通过物理/完整分层STA门槛，合格拆分对及父层功能/RC覆盖/总PPA仍未完成，H1不等于H2。

- 2026-10-23：Issue29／PR30完成固定源码916dcf9e的两次bank控制器RTL仿真，每次1872程序／54压力测试／27硬件配置通过，完整结果逐字节复现；独立33witness数据／版本／端口审计通过。1RW状态放置的最佳已找到周期差异缩至prefill1.46%／decode1.71%，2RW本轮八placement等效；仍是合成M/V延迟，不是完整LLM或PPA。通用综合job89838已TIMEOUT，未完成检查，PR draft／Issue in_progress。见[记录](experiments/issue-29-port-rtl.md)。
- 物理并行更新：PR17@ce5896d已形成合格openTPU拆分/合并H1对照，拆分area+0.412%／wire+7.142%／via+2.974%；不是H2或attention校准。独立审计发现3文本Git LF与原生成CRLF的manifest SHA差异，数值复算通过但字节证据缺项仍待处理；不再沿用旧“未配对”状态。

## 89838最终状态

通用Yosys作业89838于2026-10-23 09:55:54 CST达到20分钟时限，Slurm最终TIMEOUT（elapsed20:28，batch0:15）。日志确认已进入PROC_MUX，未完成后续memory_collect/check/stat/JSON；未证明综合通过，也不能把工具超时解释为RTL功能错误。原始日志和SHA索引已保存work/Liangruizhi/29/audits/synth-timeout01/。 下一步保留同一源码，使用单配置-defer与RTLIL检查点分开前端和proc成本；该后续检查尚未执行。先前运行中快照仅代表其采集时刻。
