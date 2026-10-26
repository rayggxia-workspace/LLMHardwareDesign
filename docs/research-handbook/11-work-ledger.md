# 11｜全项目任务总账：执行成果与协作状态分别看

本表是`2026-10-26T12:30:14.185328+00:00`读取的59个Issue和58个PR快照。
其中包含本次117及成员116正在整理的文档任务，二者不冒称原实验。历史完成项、部分交付、失败和未完成均保留。

执行阶段来自固定报告/任务原文；GitHub标签与PR合并是协作状态。in_review可以包含已执行实验，但没有要求的审查/合并时不写成done。任务可能在快照之后更新，恢复前须在线读回。

| Issue | 负责人（实际assignee） | 执行成果范围 | 快照工作流 | PR快照 |
| --- | --- | --- | --- | --- |
| [1](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/1) 初始化 LLMHardwareDesign 并导入预制计算底座初期资料 | YUZE-LU | 文档接入 | open / status:in_review | [PR2](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/2) 已合并 |
| [3](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/3) 同步两份布线报告并补入 llaccel 引擎分析 | YUZE-LU | 文档交付 | closed / status:done | [PR4](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/4) 已合并 |
| [5](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/5) 完善 AGENTS.md 协作规则并接入 Liangruizhi 本地工作区 | Liangruizhi | 协作交付 | open / status:in_review | [PR6](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/6) open/未合并 |
| [7](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7) 以 openTPU 与 llaccel 验证候选 Block 边界及分层布线流程 | YUZE-LU | 工程已执行，含失败 | open / status:in_review | [PR8](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/8) 已合并；[PR10](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/10) 已合并 |
| [9](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/9) 记录远程服务器使用规则及 sbatch 任务命名要求 | YUZE-LU | 规则文档 | closed / status:done | 本快照无关联PR |
| [11](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/11) 建立面向 DAC 的冻结互联资源模型、合法性验证与多图实验 | Liangruizhi | 抽象实验完成 | open / status:in_review | [PR12](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/12) open/未合并 |
| [13](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/13) 固定库存与映射下验证端点白名单和容量限制的配对消融 | Liangruizhi | 配对消融完成 | open / status:in_review | [PR14](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/14) open/未合并 |
| [15](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/15) openTPU 同资源 ACT/MXU 拆分与合并物理对照及违例收敛 | YUZE-LU | H1工程对照完成 | closed / status:done | [PR17](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/17) 已合并 |
| [16](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/16) 冻结真实宏 LEF 并建立保留 PORT 层次的端点几何库存 | Liangruizhi | 端点冻结完成 | open / status:in_review | [PR18](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/18) open/未合并 |
| [19](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/19) 核验 ACT/MXU 逐 bit 逻辑端口、Liberty 与 LEF 的一致性及既有连接合同 | Liangruizhi | 接口核验完成 | open / status:in_review | [PR20](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/20) open/未合并 |
| [21](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/21) 研究模型驱动的算子与 Block 划分：官方架构证据、流式边界与固定资源微实验 | Liangruizhi | 结构/数学研究完成 | open / status:in_review | [PR22](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/22) open/未合并 |
| [23](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/23) 用固定 Qwen3 权重验证 prefill/decode 状态与算子边界轨迹 | Liangruizhi | 真实模型参考完成 | open / status:in_review | [PR24](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/24) open/未合并 |
| [25](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/25) 面向通用硬件底座的 INT8 LLM 功能模块 benchmark 调研 | huangpingyang04-lgtm | benchmark调研完成 | open / status:in_review | [PR26](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/26) open/未合并 |
| [27](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/27) 固定bank/端口与静态连接约束下的状态归属和划分可辨识实验 | Liangruizhi | 状态服务研究完成 | open / status:in_review | [PR28](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/28) open/未合并 |
| [29](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/29) 以有限缓冲与逐周期RTL验证状态归属和静态存储互联合同 | Liangruizhi | 端口RTL完成，综合受阻 | open / status:in_progress | [PR30](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/30) 草稿/未合并 |
| [31](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/31) 推进 openTPU H2：冻结接口时钟与接入资源并验证限定层布线 | YUZE-LU | 有限H2切片完成 | open / status:in_review | [PR35](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/35) open/未合并 |
| [32](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/32) 16GB GPU真实Qwen3.5与GQA模型参考、量化敏感性和长上下文证据 | YUZE-LU | GPU模型及修订执行 | open / status:in_review | [PR36](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/36) open/未合并 |
| [33](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/33) 建立W8A8候选精度合同、整数参考与本机量化划分验证 | Liangruizhi | 整数合同/小核完成 | open / status:in_review | [PR34](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/34) open/未合并 |
| [37](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/37) 先审查已提LLM架构、筛选最小覆盖模型，再冻结Block划分实验 | Liangruizhi | 模型筛选完成 | open / status:in_review | [PR38](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/38) open/未合并 |
| [39](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/39) 本机验证块级KV scale归约与量化偏置，并交付GPU实验文案 | Liangruizhi | 局部整数诊断完成 | open / status:in_review | [PR40](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/40) open/未合并 |
| [41](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/41) 分析给出算子与Block候选合同及影响划分决策的最小实验集 | Liangruizhi | 分析候选完成 | open / status:in_review | [PR44](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/44) open/未合并 |
| [42](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/42) 提炼固定底座两控制锥物理/功能闭环算法与可复用验证入口 | huangpingyang04-lgtm | 组合锥方法完成 | open / status:in_review | [PR45](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/45) open/未合并 |
| [43](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/43) 调研五个开源加速器的模型规模、硬件资源及Block数量约束 | huangpingyang04-lgtm | 五项目资源调研完成 | open / status:in_review | [PR46](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/46) open/未合并 |
| [47](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/47) 对接P1–P15能力清单，验证固定校准的GQA共享与因果KV状态 | Liangruizhi | 因果GQA合同完成 | open / status:in_review | [PR49](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/49) open/未合并 |
| [48](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/48) 建立≤4B INT8工作负载输入规范与轻量Block资源估算器 | huangpingyang04-lgtm | 估计器交付完成 | open / status:in_review | [PR50](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/50) open/未合并 |
| [51](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/51) 本机E2a：同资源有限端口下比较近端与共享重新量化 | Liangruizhi | RQ服务对照完成 | open / status:in_review | [PR52](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/52) open/未合并 |
| [53](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/53) 验证CPU服务器小模型迁移与线程伸缩，界定GPU批次可迁移范围 | Liangruizhi | CPU迁移完成 | open / status:in_review | [PR54](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/54) open/未合并 |
| [55](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/55) 完整 openTPU small / llaccel_core 资源并集底座集成与 M9/M10 定制验证 | huangpingyang04-lgtm | 完整集成部分完成 | open / status:in_progress | [PR58](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/58) 草稿/未合并 |
| [56](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/56) 本机Llama-3.2-1B跨模型验证完整GQA整数参考与RQ划分 | Liangruizhi | Llama跨模型完成 | open / status:in_review | [PR57](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/57) open/未合并 |
| [59](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/59) 本机Llama down_proj校准与scale粒度：整数宽归约和端口成本 | Liangruizhi | 校准/粒度比较完成 | open / status:in_review | [PR60](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/60) open/未合并 |
| [61](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/61) 补齐服务器模型批次：Qwen证据接收、Gemma窗口/GQA与Phi封存验证 | Liangruizhi | 四模型批次执行完成 | open / status:in_review | [PR62](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/62) open/未合并 |
| [63](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/63) 工作负载通信输入适配器 v1：显式图转换、候选资源检查与资产导入 | huangpingyang04-lgtm | 软件/研究交付完成 | open / status:in_review | [PR79](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/79) open/未合并 |
| [64](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/64) 综合多模型证据细化Block方案v2，验证输出格式与注意力数值闭包 | Liangruizhi | 决策分叉完成 | open / status:in_review | [PR65](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/65) open/未合并 |
| [66](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/66) 关键边界接续：完整消费者链scale传播与Qwen3.5连续状态整数化 | Liangruizhi | 消费者/连续整数研究完成 | open / status:in_review | [PR67](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/67) open/未合并 |
| [68](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/68) R范围与重定标协议、同资源V/R/S有限端口服务验证 | Liangruizhi | 范围及同资源服务完成 | open / status:in_review | [PR69](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/69) open/未合并 |
| [70](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/70) Granite小MoE与Falcon-H1并行混合层：Block决策最小实验 | Liangruizhi | 架构扩展最小集执行 | open / status:in_review | [PR71](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/71) open/未合并 |
| [72](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/72) 定稿关键验证：Granite路由合同、Falcon因果整数链与同资源Block边界 | Liangruizhi | 数值闭环与服务完成 | open / status:in_review | [PR73](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/73) open/未合并 |
| [74](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/74) Granite完整整数MoE与分组量化同资源Block边界验证 | Liangruizhi | 完整MoE切口完成 | open / status:in_review | [PR75](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/75) open/未合并 |
| [76](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/76) Granite有限专家到merge端口缓冲及宽算术SFU-ROM校准 | Liangruizhi | 有限merge服务完成 | open / status:in_review | [PR77](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/77) open/未合并 |
| [80](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/80) Block电路首轮：完整宽控制器、有限frame与局部连接比较 | Liangruizhi | 宽控制RTL完成 | open / status:in_review | [PR81](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/81) open/未合并 |
| [82](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/82) 归一化电路专用化：宽算术/SFU与真实M消费者同精度成本比较 | Liangruizhi | norm/真实M电路完成 | open / status:in_review | [PR83](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/83) open/未合并 |
| [84](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/84) 同容量A缓存与重定标乘法器共享：完整M消费者RTL公平对照 | Liangruizhi | 缓存/共享电路完成 | open / status:in_review | [PR87](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/87) open/未合并 |
| [85](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/85) Block运行时缓存旁路与中止恢复：完整整数消费者接口资格 | Liangruizhi | 运行时/恢复完成 | open / status:in_review | [PR89](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/89) open/未合并 |
| [86](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/86) Block研究库门级等价与受限STA：补足电路资格证据 | Liangruizhi | 选定门级完成，STA失败 | open / status:in_review | [PR90](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/90) open/未合并 |
| [88](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/88) 研究库电气修复：同约束缓冲/驱动调整及代价核验 | Liangruizhi | 受限电气修复完成 | open / status:in_review | [PR95](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/95) open/未合并 |
| [91](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/91) 通用V与共享存储整合合同：Block电路库验收和生命周期闭合 | Liangruizhi | 结构合同完成 | open / status:in_review | [PR94](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/94) open/未合并 |
| [92](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/92) 运行时epoch耗尽边界：终止态排空与实际RTL证明 | Liangruizhi | 边界修复完成 | open / status:in_review | [PR96](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/96) open/未合并 |
| [93](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/93) 流式gamma RTL：16KiB内H1536/H2560全行归一化与消费者回归 | Liangruizhi | 流式gamma RTL完成 | open / status:in_review | [PR100](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/100) open/未合并 |
| [97](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/97) 完整V/M消费者：SiLU与整K动态量化RTL、驻留A及真实scale传播 | Liangruizhi | V到M完整电路完成 | open / status:in_review | [PR101](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/101) open/未合并 |
| [98](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/98) 实际整合核研究库物理资格：固定布局、时钟与线网RC验证 | Liangruizhi | 物理阶段部分完成 | open / status:in_progress | [PR111](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/111) 草稿/未合并 |
| [99](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/99) R状态RTL：完整head连续递推、因果重标与原子发布 | Liangruizhi | Falcon单head RTL完成 | open / status:in_review | [PR103](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/103) open/未合并 |
| [102](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/102) 完整GQA注意力RTL：固定整数函数、有限存储及真实cached输入 | Liangruizhi | 完整GQA切片完成 | open / status:in_review | [PR105](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/105) open/未合并 |
| [104](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/104) 完整GDN状态RTL：Qwen3.5双head连续重标与宽乘法lowering | Liangruizhi | GDN双head RTL完成 | open / status:in_review | [PR107](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/107) open/未合并 |
| [106](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/106) 真实共享Block服务：M/A/R单存储与算术仲裁、跨owner恢复及全链验收 | Liangruizhi | 三profile真共享完成 | open / status:in_review | [PR108](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/108) open/未合并 |
| [109](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/109) GDN接入真实共享服务：四profile连续切换与完整双头发布 | Liangruizhi | 四profile真共享完成 | open / status:in_review | [PR113](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/113) open/未合并 |
| [110](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/110) A固定limb路径精化：同整数函数与库存的宽度、移位和面积对照 | Liangruizhi | 等价面积精化完成 | open / status:in_review | [PR112](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/112) open/未合并 |
| [114](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/114) 汇总真实模型实验：能力需求、Block边界与证据限制分析报告 | YUZE-LU | 分析文档已合并 | closed / status:done | [PR115](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/115) 已合并 |
| [116](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/116) 归档模型分析文档与计算图至 docs/model-analysis | YUZE-LU | 其他成员归档任务 | open / status:in_progress | 本快照无关联PR |
| [117](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/117) 全项目研究教程：逐模型实验、算子与Block划分、电路及物理证据总汇 | Liangruizhi | 本次完整教程交付 | open / status:in_progress | 本快照无关联PR |

## 逐项说明

每项保留原负责人和来源，不因为本教程汇总就接管其后续工作。

### Issue1 · 初始化 LLMHardwareDesign 并导入预制计算底座初期资料

**实际成果：** 导入项目定义、初期资料、来源和目录，建立可维护的项目入口。

**限制与接续：** 材料接入不能证明完整物理流程可复现。

**证据入口：** [T1原任务快照](10-evidence-index.md#t1)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/1)。

### Issue3 · 同步两份布线报告并补入 llaccel 引擎分析

**实际成果：** 同步布线/线长/模块与接口报告及llaccel分析，保留参考资料边界。

**限制与接续：** 不把已有结果包当完整源工程或新实验。

**证据入口：** [T3原任务快照](10-evidence-index.md#t3)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/3)。

### Issue5 · 完善 AGENTS.md 协作规则并接入 Liangruizhi 本地工作区

**实际成果：** 明确Issue、独立分支/目录、身份、个人进度、SHA和交接规则。

**限制与接续：** PR上传与审查合并、登记和看板分别核验。

**证据入口：** [T5原任务快照](10-evidence-index.md#t5)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/5)。

### Issue7 · 以 openTPU 与 llaccel 验证候选 Block 边界及分层布线流程

**实际成果：** 完成VECTOR及并行块分层试验、宏视图、PG接入和接口检查。

**限制与接续：** VECTOR setup/cap及父层失败保留；多个报告各有版本，非最终底座。

**证据入口：** [S7-PARALLEL-BLOCKS-ACCEPTANCE](10-evidence-index.md#s7-parallel-blocks-acceptance)、[S7-PARALLEL-BLOCKS-REPAIR](10-evidence-index.md#s7-parallel-blocks-repair)、[S7-PARALLEL-BLOCKS-WAVE2](10-evidence-index.md#s7-parallel-blocks-wave2)、[S7-PARALLEL-BLOCKS](10-evidence-index.md#s7-parallel-blocks)、[S7](10-evidence-index.md#s7)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7)。

### Issue9 · 记录远程服务器使用规则及 sbatch 任务命名要求

**实际成果：** 记录服务器目录、资源和作业命名规则并提供入口。

**限制与接续：** 规则存在不表示本次整理启动或检查服务器作业。

**证据入口：** [T9原任务快照](10-evidence-index.md#t9)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/9)。

### Issue11 · 建立面向 DAC 的冻结互联资源模型、合法性验证与多图实验

**实际成果：** 192例冻结互联搜索，32/96与44/96成功；小例穷举和电气/数值复核。

**限制与接续：** 搜索预算不同；合成连通不等于真实H2/时序。

**证据入口：** [S11](10-evidence-index.md#s11)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/11)。

### Issue13 · 固定库存与映射下验证端点白名单和容量限制的配对消融

**实际成果：** 同master库存384例，扩接点44→71/96；保留cut证书和未知失败。

**限制与接续：** 不是工艺访问或芯片PPA；capacity无变化不等于永远无用。

**证据入口：** [S13](10-evidence-index.md#s13)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/13)。

### Issue15 · openTPU 同资源 ACT/MXU 拆分与合并物理对照及违例收敛

**实际成果：** ACT/MXU拆分与合并完整物理/功能/RC证据；叶面积+0.412%、线+7.142%、via+2.974%。

**限制与接续：** 单small/typical且允许有源修复，不是普遍制造后改线证明。

**证据入口：** [S15](10-evidence-index.md#s15)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/15)。

### Issue16 · 冻结真实宏 LEF 并建立保留 PORT 层次的端点几何库存

**实际成果：** 三普通LEF、6785信号位与原始PORT/RECT/OBS完整库存、独立解析。

**限制与接续：** 几何矩形和中心不是合法via/access；底层版本缺项保留。

**证据入口：** [S16](10-evidence-index.md#s16)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/16)。

### Issue19 · 核验 ACT/MXU 逐 bit 逻辑端口、Liberty 与 LEF 的一致性及既有连接合同

**实际成果：** ACT/MXU共3032信号位三视图及685bit既有连接合同。

**限制与接续：** 两处Liberty缺分号、四处PG方向差异；无完整arc/物理资格。

**证据入口：** [S19](10-evidence-index.md#s19)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/19)。

### Issue21 · 研究模型驱动的算子与 Block 划分：官方架构证据、流式边界与固定资源微实验

**实际成果：** 9配置案例、11340容量条件及流式/物化反例；MLA/MoE缩小数学核。

**限制与接续：** 不是9个真实权重模型，不把FP32账本缩放为INT8。

**证据入口：** [S21](10-evidence-index.md#s21)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/21)。

### Issue23 · 用固定 Qwen3 权重验证 prefill/decode 状态与算子边界轨迹

**实际成果：** Qwen3-0.6B固定权重，54调用、完整KV/fresh-prefix及错误状态负例。

**限制与接续：** FP32短上下文与局部边界；无语言质量/目标性能结论。

**证据入口：** [S23](10-evidence-index.md#s23)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/23)。

### Issue25 · 面向通用硬件底座的 INT8 LLM 功能模块 benchmark 调研

**实际成果：** 通用INT8功能、真实尺寸、容量/通信公式和模型/模块/数据集分层。

**限制与接续：** 不含新权重运行、质量、RTL或物理实测。

**证据入口：** [S25](10-evidence-index.md#s25)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/25)。

### Issue27 · 固定bank/端口与静态连接约束下的状态归属和划分可辨识实验

**实际成果：** 3456固定bank/端口/连接配置、真实Qwen头参考、独立调度审计。

**限制与接续：** 假设服务；1RW位置收益4.51%/3.92%，不能继承到整数电路。

**证据入口：** [S27](10-evidence-index.md#s27)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/27)。

### Issue29 · 以有限缓冲与逐周期RTL验证状态归属和静态存储互联合同

**实际成果：** 27配置、1872程序及54压力测试；有限FIFO/反压/逐拍witness。

**限制与接续：** 算术为延迟代理；原型综合超时，不称完整attention或SRAM宏实现。

**证据入口：** [S29F](10-evidence-index.md#s29f)、[S29](10-evidence-index.md#s29)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/29)。

### Issue31 · 推进 openTPU H2：冻结接口时钟与接入资源并验证限定层布线

**实际成果：** 同功能冻结资源，仅M8–M10/V8/V9重布；DRC/PG/RC/完整分层STA通过。

**限制与接续：** 约92.5%父层线已预埋，无第二计算图，不是通用共同底座。

**证据入口：** [S31](10-evidence-index.md#s31)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/31)。

### Issue32 · 16GB GPU真实Qwen3.5与GQA模型参考、量化敏感性和长上下文证据

**实际成果：** Qwen2.5/Qwen3.5 FP16参考、真实INT8矩阵、分组敏感性和规范辅助长连续对照。

**限制与接续：** 早期OOM/状态失败保留；FP32辅助存在，非全整数模型。

**证据入口：** [S32](10-evidence-index.md#s32)、[S32R](10-evidence-index.md#s32r)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/32)。

### Issue33 · 建立W8A8候选精度合同、整数参考与本机量化划分验证

**实际成果：** W8A8/INT32、RQ RTL1028例、LUT/小norm/小递推、真实切片与4608划分点。

**限制与接续：** 原参考RTL规范不完整；质量和全模型硬件未通过。

**证据入口：** [S33](10-evidence-index.md#s33)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/33)。

### Issue37 · 先审查已提LLM架构、筛选最小覆盖模型，再冻结Block划分实验

**实际成果：** 先比较GQA/窗口/递推/MLA/MoE和训练/权重差异，再冻结最小协议。

**限制与接续：** 历史配置访问缺项以后续实际采集补齐，不倒改成早期已跑。

**证据入口：** [S37](10-evidence-index.md#s37)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/37)。

### Issue39 · 本机验证块级KV scale归约与量化偏置，并交付GPU实验文案

**实际成果：** Qwen真实head的24块scale/概率候选、89280 oracle值、bias与错误scale反例。

**限制与接续：** 当前张量拟合含前视，尚非因果全GQA/质量结论。

**证据入口：** [S39](10-evidence-index.md#s39)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/39)。

### Issue41 · 分析给出算子与Block候选合同及影响划分决策的最小实验集

**实际成果：** 给出M/V/A/R/S/D计算/状态/接口/预连线和决策型最小实验。

**限制与接续：** 候选不是目标电路或制造边界验收。

**证据入口：** [S41](10-evidence-index.md#s41)、[SDAC](10-evidence-index.md#sdac)、[SGPU](10-evidence-index.md#sgpu)、[SOP](10-evidence-index.md#sop)、[SRQ](10-evidence-index.md#srq)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/41)。

### Issue42 · 提炼固定底座两控制锥物理/功能闭环算法与可复用验证入口

**实际成果：** 同两门底座两目标、冻结/连通/逻辑参数化重放，15测试与原证据绑定。

**限制与接续：** 小组合片段，无完整状态核心/DRC/LVS/STA。

**证据入口：** [S42](10-evidence-index.md#s42)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/42)。

### Issue43 · 调研五个开源加速器的模型规模、硬件资源及Block数量约束

**实际成果：** 区分板上/仿真/规划与INT8/FP32/W4/BF16，形成数量/容量/带宽约束。

**限制与接续：** B数及PE数不能直接定完整模型Block数。

**证据入口：** [S43](10-evidence-index.md#s43)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/43)。

### Issue47 · 对接P1–P15能力清单，验证固定校准的GQA共享与因果KV状态

**实际成果：** 独立校准、全2Q/1KV共享变换、静态KV和未来扰动/版本测试。

**限制与接续：** 当前scale编译有浮点；局部约1.8%误差不是质量验收。

**证据入口：** [S47](10-evidence-index.md#s47)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/47)。

### Issue48 · 建立≤4B INT8工作负载输入规范与轻量Block资源估算器

**实际成果：** 严格≤4B W8A8/INT32输入、31测试、四例双轮，unknown和通信/容量分开。

**限制与接续：** 仅下界/显式假设，不自动证明模型可部署或时延。

**证据入口：** [S48](10-evidence-index.md#s48)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/48)。

### Issue51 · 本机E2a：同资源有限端口下比较近端与共享重新量化

**实际成果：** 384组织/192位置对，同库存双策略包络；decode物理包节省为0。

**限制与接续：** 近M最优包络约0.5657%，未校准完整算术/物理。

**证据入口：** [S51](10-evidence-index.md#s51)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/51)。

### Issue53 · 验证CPU服务器小模型迁移与线程伸缩，界定GPU批次可迁移范围

**实际成果：** Qwen3 FP32/BF16×8/16/32线程、双轮参考及计时。

**限制与接续：** BF16部分线程失败，CPU时间不替代GPU/目标Block。

**证据入口：** [S53](10-evidence-index.md#s53)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/53)。

### Issue55 · 完整 openTPU small / llaccel_core 资源并集底座集成与 M9/M10 定制验证

**实际成果：** 原完整顶层、四宏/状态归属、open观察器及llaccel补测已有证据。

**限制与接续：** 迁线异网接触失败；共同底座/M8/两案例定制未完成。

**证据入口：** [S55M](10-evidence-index.md#s55m)、[S55](10-evidence-index.md#s55)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/55)。

### Issue56 · 本机Llama-3.2-1B跨模型验证完整GQA整数参考与RQ划分

**实际成果：** 完整4Q/1KV和K8192/16输出，独立整数、早RQ反例、有限端口。

**限制与接续：** 静态down近全零；不是全FFN或全模型质量。

**证据入口：** [S56](10-evidence-index.md#s56)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/56)。

### Issue59 · 本机Llama down_proj校准与scale粒度：整数宽归约和端口成本

**实际成果：** Llama24候选/144数值条件、宽归约、元数据与1152服务配置。

**限制与接续：** 最佳5.39%仍未过原5%探索门；权重相关界不覆盖全层。

**证据入口：** [S59](10-evidence-index.md#s59)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/59)。

### Issue61 · 补齐服务器模型批次：Qwen证据接收、Gemma窗口/GQA与Phi封存验证

**实际成果：** Qwen2.5/Qwen3.5/Gemma主测及Phi封存；420线性/56注意力条件。

**限制与接续：** 部分格式/饱和失败保留；CPU FP32参考、非全整数/新GPU测量。

**证据入口：** [S61](10-evidence-index.md#s61)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/61)。

### Issue63 · 工作负载通信输入适配器 v1：显式图转换、候选资源检查与资产导入

**实际成果：** 适配、生命周期、真实pin导入；223测试、10重放和通信搜索强基线。

**限制与接续：** 合成资源研究，真实M8/冻结底座C层blocked。

**证据入口：** [S63](10-evidence-index.md#s63)、[S63R](10-evidence-index.md#s63r)、[S63N](10-evidence-index.md#s63n)、[S63T](10-evidence-index.md#s63t)、[S63C](10-evidence-index.md#s63c)、[S63G](10-evidence-index.md#s63g)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/63)。

### Issue64 · 综合多模型证据细化Block方案v2，验证输出格式与注意力数值闭包

**实际成果：** 输出格式1080条件、整数注意力56条件、576服务图及Block v2。

**限制与接续：** 局部改善不升级旧质量；M+A合宏仍未物理证明。

**证据入口：** [S64](10-evidence-index.md#s64)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/64)。

### Issue66 · 关键边界接续：完整消费者链scale传播与Qwen3.5连续状态整数化

**实际成果：** 完整H2560 down-residual-norm-next切口及Qwen双head连续R/conv。

**限制与接续：** 旧长窗饱和保留，部分生产链FP桥仍在；范围策略由68补。

**证据入口：** [S66](10-evidence-index.md#s66)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/66)。

### Issue68 · R范围与重定标协议、同资源V/R/S有限端口服务验证

**实际成果：** static/guard/adaptive对照、完整checkpoint、448服务日历及独立接收。

**限制与接续：** 重标改变函数；宽算术假设瓶颈不等于物理宏最优。

**证据入口：** [S68](10-evidence-index.md#s68)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/68)。

### Issue70 · Granite小MoE与Falcon-H1并行混合层：Block决策最小实验

**实际成果：** 新增Granite/Falcon参考、真实切口和COPY/端口对照。

**限制与接续：** Granite chunk失败，Falcon早期浮点更新/sat不升级整数。

**证据入口：** [S70](10-evidence-index.md#s70)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/70)。

### Issue72 · 定稿关键验证：Granite路由合同、Falcon因果整数链与同资源Block边界

**实际成果：** Granite路由精度/证书；Falcon32head完整整数分支/恢复/输出分组。

**限制与接续：** Attention/MLP切口外；物理归属微小条件差不定稿。

**证据入口：** [S72](10-evidence-index.md#s72)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/72)。

### Issue74 · Granite完整整数MoE与分组量化同资源Block边界验证

**实际成果：** 两层8条件全部专家/merge/残差/nextnorm；Falcon分组同函数M/V比较。

**限制与接续：** Granite质量局部误差仍在，offline末8行不冒充新cached调度。

**证据入口：** [S74](10-evidence-index.md#s74)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/74)。

### Issue76 · Granite有限专家到merge端口缓冲及宽算术SFU-ROM校准

**实际成果：** 24配置及byte/ROM微核校准；fullH merge峰14224B可驻V。

**限制与接续：** 公共microframe过慢，尚非完整wide FSM或PPA。

**证据入口：** [S76](10-evidence-index.md#s76)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/76)。

### Issue80 · Block电路首轮：完整宽控制器、有限frame与局部连接比较

**实际成果：** 895命令×四条件、实际取指/CALL/RMW/ROM，LOCAL周期少约44%。

**限制与接续：** 任务分布非模型频率，512B框架与后续norm不是同库存。

**证据入口：** [S80](10-evidence-index.md#s80)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/80)。

### Issue82 · 归一化电路专用化：宽算术/SFU与真实M消费者同精度成本比较

**实际成果：** 三硬件profile、174命令，完整K512/H1536消费者逐码。

**限制与接续：** 最快norm完整链只少2.166%，面积增加，未物理定稿。

**证据入口：** [S82](10-evidence-index.md#s82)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/82)。

### Issue84 · 同容量A缓存与重定标乘法器共享：完整M消费者RTL公平对照

**实际成果：** 同16KiB/端口A缓存与一个S32，84命令及端口反转反例。

**限制与接续：** 静态编译变体，零竞争不代表并发零成本。

**证据入口：** [S84](10-evidence-index.md#s84)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/84)。

### Issue85 · Block运行时缓存旁路与中止恢复：完整整数消费者接口资格

**实际成果：** 单核cache_mode锁存、显式cmd握手、60完整输出及中止恢复。

**限制与接续：** epoch终止缺陷后来由92修复；独立fabric/CDC未验。

**证据入口：** [S85](10-evidence-index.md#s85)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/85)。

### Issue86 · Block研究库门级等价与受限STA：补足电路资格证据

**实际成果：** 四84网表双等待完整门级通过；全DFF/IO受限STA暴露大量违例。

**限制与接续：** 零延迟门级非形式等价，诊断周期不是合格Fmax。

**证据入口：** [S86](10-evidence-index.md#s86)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/86)。

### Issue88 · 研究库电气修复：同约束缓冲/驱动调整及代价核验

**实际成果：** 四变体缓冲/tie/驱动/hold成本及精确8条门级通过。

**限制与接续：** 无真实线RC/CTS；历史native电气摘要需按98完整表提升口径。

**证据入口：** [S88](10-evidence-index.md#s88)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/88)。

### Issue91 · 通用V与共享存储整合合同：Block电路库验收和生命周期闭合

**实际成果：** H2560 X驻留/gamma流式、frame/A容量与符号行证明。

**限制与接续：** 当轮无张量/RTL，实际实现由93完成。

**证据入口：** [S91](10-evidence-index.md#s91)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/91)。

### Issue92 · 运行时epoch耗尽边界：终止态排空与实际RTL证明

**实际成果：** 复现并修max generation排空与cfg/done假握手，10条门锥性质。

**限制与接续：** 一周期安全非完整活性/任意重排/门级注入证明。

**证据入口：** [S92](10-evidence-index.md#s92)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/92)。

### Issue93 · 流式gamma RTL：16KiB内H1536/H2560全行归一化与消费者回归

**实际成果：** 双等待各51完成记录，六Granite链及两Gemma完整H2560 norm。

**限制与接续：** cost02修正beat字节；最终物理网表的完整门级另见98。

**证据入口：** [S93](10-evidence-index.md#s93)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/93)。

### Issue97 · 完整V/M消费者：SiLU与整K动态量化RTL、驻留A及真实scale传播

**实际成果：** 真实gate/up→SiLU/MID→整K量化→M/merge/residual/norm，selected gate通过。

**限制与接续：** router/gate-up投影和通用V/整模型不在切口。

**证据入口：** [S97](10-evidence-index.md#s97)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/97)。

### Issue98 · 实际整合核研究库物理资格：固定布局、时钟与线网RC验证

**实际成果：** 97精确研究物理及4×2正常门级accepted；93最终物理表通过。

**限制与接续：** 93完整门级接收在来源快照未完成，本次未查服务器新终态。

**证据入口：** [S98R](10-evidence-index.md#s98r)、[S98](10-evidence-index.md#s98)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/98)。

### Issue99 · R状态RTL：完整head连续递推、因果重标与原子发布

**实际成果：** 72连续、全head重标、readout/root发布及两checkpoint门级。

**限制与接续：** 不是32head完整分支或4096消费者RTL，不继承98物理。

**证据入口：** [S99](10-evidence-index.md#s99)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/99)。

### Issue102 · 完整GQA注意力RTL：固定整数函数、有限存储及真实cached输入

**实际成果：** 79query双等待、完整8头QK到PV和版本恢复，selected gate通过。

**限制与接续：** 非online，无KV append/投影/RoPE/全模型。

**证据入口：** [S102](10-evidence-index.md#s102)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/102)。

### Issue104 · 完整GDN状态RTL：Qwen3.5双head连续重标与宽乘法lowering

**实际成果：** native32/portable12、S32宽lowering、共同root、恢复/边界及selected gate。

**限制与接续：** 输入生产/输出gatednorm切口外；引用参考优先级补丁须一并接收。

**证据入口：** [S104](10-evidence-index.md#s104)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/104)。

### Issue106 · 真实共享Block服务：M/A/R单存储与算术仲裁、跨owner恢复及全链验收

**实际成果：** M/A/Falcon共用同S/8S8/S32/SFU/link，7混合/27恢复双等待。

**限制与接续：** 最大6KiB环境sink未实现为下游硬件buffer，新top未物理。

**证据入口：** [S106](10-evidence-index.md#s106)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/106)。

### Issue109 · GDN接入真实共享服务：四profile连续切换与完整双头发布

**实际成果：** 接GDN、完整2048B候选导出，13混合/44恢复及双路8命令gate。

**限制与接续：** 串行owner非模型端到端，新logic-only面积163901.220需独立物理。

**证据入口：** [S109](10-evidence-index.md#s109)、[SV1](10-evidence-index.md#sv1)、[SC2](10-evidence-index.md#sc2)、[SCR](10-evidence-index.md#scr)、[SC1](10-evidence-index.md#sc1)、[SLIB](10-evidence-index.md#slib)、[SMIN](10-evidence-index.md#smin)、[SV2](10-evidence-index.md#sv2)、[SI](10-evidence-index.md#si)、[SARCH](10-evidence-index.md#sarch)、[SP](10-evidence-index.md#sp)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/109)。

### Issue110 · A固定limb路径精化：同整数函数与库存的宽度、移位和面积对照

**实际成果：** 真实组合锥/FF归纳、24套回归/6门级；QK34/PV45少0.80921%面积。

**限制与接续：** 周期不变，无STA，未合入109。

**证据入口：** [S110](10-evidence-index.md#s110)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/110)。

### Issue114 · 汇总真实模型实验：能力需求、Block边界与证据限制分析报告

**实际成果：** YUZE-LU八模型能力/Block边界报告经PR115进入main。

**限制与接续：** 只验文档，不代批原实验PR或升级模型/物理资格。

**证据入口：** [S114](10-evidence-index.md#s114)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/114)。

### Issue116 · 归档模型分析文档与计算图至 docs/model-analysis

**实际成果：** 安排docs/model-analysis图册/分析归档，保留原成果与跳转。

**限制与接续：** 本任务不移动或覆盖其文件，实际本地/远端阶段以该Issue为准。

**证据入口：** [T116原任务快照](10-evidence-index.md#t116)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/116)。

### Issue117 · 全项目研究教程：逐模型实验、算子与Block划分、电路及物理证据总汇

**实际成果：** 逐模型、数值推理、具体划分、电路/物理/映射与完整证据总账。

**限制与接续：** 仅文档/来源核对，原实验未重跑；最终上传回执另见本任务交接。

**证据入口：** [T117原任务快照](10-evidence-index.md#t117)；[当前Issue](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/117)。

## 交付状态如何继续维护

本次教程不更改上表原实验状态，不关闭别人的Issue，不合并原PR，不启动或取消服务器作业。Issue117的最终发布、检查和看板缺项记录在本任务交接。成员116的模型图册归档保持原范围。
