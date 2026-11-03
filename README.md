> 主线五G1首切片最终：源码7a656a3fe4a86342d24b72ebecdc524052bf86d7，96208/n03/node1/c64/8CPU自然COMPLETED0:0/3分1秒；12终态定向+18实际AF及10actualSHA通过。另unit96170的DMA29/SEQ30通过，共89项不同预声明检查，非全图证明。n01/96183原18项成功、n02/96192失败及12项组件成功均保留，不把失败整合当通过。当前无本任务在跑作业、无自动监测。

> 主线五首轮RTL：[实施合同](docs/W5_CONTROL_FIRST_SLICE.md)、[59项单元实测](docs/W5_EDGE_DMA_AND_SEQUENCER_REPORT.md)。共同母顺序器与真实SACK DMA已实跑；实际G1 A→两F整合96183正在服务器验证，未预报通过。主线四质量门保留。

> 2026-11-03 H1 v0.1：[工作报告](docs/H1_WORK_REPORT.md)、[图/控制表规格](docs/H1_GRAPH_CONTROL_SPEC.md)。三图4路径、28定向拒绝+11独立审查通过；同候选12叶含新增edge S16KiB，产品表1184/2016/1808B。仅离线协议/预算，母控/端点/物理仍GAP；下一H2，L4质量并行保留。

> 2026-11-03 总方案更新：[混合控制总方案 v0.6](docs/HYBRID_METAL_CONTROL_PLAN.md)。目标为共同有源底座冻结后，仍能以M11/M12永久定制此前未列出的有界合法执行图；主候选为金属粗任务表＋共同母顺序器＋预制端点/真实ACK及局部令牌握手。当前仅方案交付，控制存储/通用组合RTL与物理待验；已有L4质量、旧54runtime及24GAP不变。

# 当前实现与功能岛研究入口（2026-11-03）

[L4-QUALITY参考/W8](docs/L4_QUALITY_REFERENCE_W8_REPORT.md)完成官方layer0 FP32与独立C++的28stage对照及同Fin10 W8八条真实F回归，95979/r02/56CASE/8actualSHA通过，旧54runtime不变。已实现的[AF1024](docs/W4_AF1024_IMPLEMENTATION.md)仍原baseline；当前旧前缀只作回归，trained完整整数AF质量未接收。

[八主线](docs/COARSE_BLOCK_RESEARCH_PROGRESS.md)仍L4，下一真实整数AF误差/新代表性数据与阈值，旧24GAP保持；通用L5/MEM/物理另门。每步完成后覆盖同一现有本地交流PDF，不推Git。

以下保留按各轮时间形成的研究摘要及项目历史，旧“未开始/已完成”只适用于相应轮次；当前状态以上述入口为准。

---

本轮L4：[真实Qwen layer0 F数值/有限RTL](docs/QWEN_LAYER0_NUMERIC_RTL_REPORT.md)，95247/95248通过但模型质量未接受；[实际A Sq2容量候选](docs/QWEN3_SQ2_ATTENTION_PLAN.md)只静态检查。

本轮研究：[F1024真实尺寸整数FFN及N-long](docs/W4_F1024_IMPLEMENTATION.md)，95245/64CASE通过，训练量化质量仍UNKNOWN，当前L4。

> 主线四新增[AF16纵向衔接](docs/W4_AF16_IMPLEMENTATION.md)：A16两行真实holding→同F16两次，服务器95242/33CASE通过；[八样本静态准入](docs/AF16_MODEL_ADMISSION.md)保留真实形状，24项均GAP，只有合成ABI获静态ALLOW。下一候选Qwen3 F H1024/I3072仍待数值/程序/供参实施，不代表L5或物理已完成。

> 主线四新增[A16有界完整因果Attention](docs/W4_A16_IMPLEMENTATION.md)：H8/Sq2/head1，preNorm/QKV/RoPE/前缀Softmax/PV/Wo/原S16残差，服务器95235/30CASE通过；原F16/A8保留。实际样本数值/规模/供参、跨岛和物理仍待验，L4未整体完成。

> 主线四新增[F16有界完整FFN](docs/W4_F16_IMPLEMENTATION.md)：S16Fin10 hidden/原残差+可变gamma、宽A投影，服务器95209/30CASE通过；[A/F数值存储路线](docs/AF_NUMERIC_STORAGE_PLAN.md)给出下一A16因果候选。仍非全模型/完整L4/跨岛或物理验收。

> 当前研究：[W5-IF三层接口合同v0.1](docs/W5_IF_INTERFACE_CONTRACT.md)、[协议时序](docs/W5_IF_PROTOCOL_EXAMPLES.md)、[模型准入边界](docs/W5_IF_MODEL_ADMISSION.md)。逻辑合同已形成待审查，新端点/母控/跨岛RTL及物理未实现，当前仍L4。

> 当前研究：[八主线与进度](docs/COARSE_BLOCK_RESEARCH_PROGRESS.md)、[A8实现](docs/W4_A8_IMPLEMENTATION.md)、[服务器Verilator验证](docs/W4_A8_VERIFICATION.md)。N29/F825/A826共80项通过；当前仍L4，完整A/F与物理待验，PR待审查。

> 当前研究：[W4 N服务与preNorm F8](docs/W4_N_F8_IMPLEMENTATION.md)、[数值合同](docs/W4_NUMERIC_CONTRACT.md)、[真实验证](docs/W4_N_F8_VERIFICATION.md)。N29/F8 25有限检查和旧114回归通过；基分支冲突已同步解决，PR待审查，完整L4/A/F未验收。

> 当前研究入口：[W3 E/G适配与FFN8实现](docs/W3_EG_FFN8_IMPLEMENTATION.md)、[实际验证](docs/W3_EG_FFN8_VERIFICATION.md)、[数值合同](docs/W3_NUMERIC_CONTRACT.md)。PR152待审查；有限内核通过，不代表完整F/模型/物理验收。

> 主线二首切片已实现：[可变输入的固定DOT8岛壳RTL](docs/W1_MINIMAL_ISLAND_IMPLEMENTATION.md)。新W1最终28项真实RTL检查与原P2回归19项通过；完整W1及六配置未验收，主线三未开始，PR待审查。

> 主线一成果：[六配置合同与证据基线](docs/COARSE_BLOCK_W0_CONTRACT_BASELINE.md)。最新PR144十四核心与707源相同；逐角色合同、原生端口及P2剩余门已准备待审查，主线二未实施。

> 最新连接研究：[六配置大Block的端口同步、已有连接与实现步骤](docs/COARSE_BLOCK_CONNECTION_IMPLEMENTATION.md)。区分当前v2/P2有限组合实测、当前树legacy组件和待实现完整profile；不将逻辑依赖等同直连。

> 当前数量研究：[五类大操作的六张宏BOM](docs/COARSE_BLOCK_MACRO_BOM.md)。同构全七岛保留为对照，本轮按真实算法裁去不需要的整类宏并说明调度/存储前提；未制作裁剪宏或新物理岛。

> 新候选：[七宏执行岛与粗粒度大Block研究](docs/COARSE_BLOCK_HIERARCHY_CANDIDATE.md)。每岛预制七类宏和本地控制，母控调完整子层；M11/M12只连粗端点/永久选择。当前为可行性研究，未形成新岛RTL/物理宏，不替代P2未完成验收。

> 当前研究分支进入P2：14核心RTL已按用户要求更新至PR144固定7078786；新增S普通端口helper、最小MST顶层与固定ROM控制骨架，边界及实测见[第二步报告](docs/PHASE2_MST_IMPLEMENTATION.md)。这不是R最终物理资格或完整模型/共同底座验收；旧记录保持各自时间与版本。

> 当前研究分支已按用户要求整合PR144固定643c6012的七类RTL；M/N/E/G/S/T有上游叶子证据、R仍未合格，系统协调/六链仍为proposed。历史规划/实验按原时间保留，当前源码入口和验证边界见[集成基线](docs/SEVEN_BLOCK_RESEARCH_BASELINE.md)。这不表示PR144或PR152已合入main。

# LLMHardwareDesign：预制计算底座研究

当前正在依据两份审阅建议推进[300MHz吞吐与粗金属接口修订](docs/plans/block-v1-review-300mhz.md)。下述已通过的五宏为`ad3c2b3`的100MHz对照基线；新版须分别重做最终布局布线和完整接口验收，不能沿用旧资格。

当前第一版计算积木为 **M/V/R/S/T五个物理宏，每种一个基础实现**；本轮交付是逐块最终M1–M10布局布线与同源验收。见[五宏规格](docs/BLOCK_LIBRARY_V1.md)、[实施计划](docs/plans/block-v1-library-implementation.md)及[当前交付索引](work/YUZE-LU/121/delivery/README.md)。五块最终原生布局布线、四项独立同源验收及最终文件接收均通过；五块完整原生几何及最终包均齐，项目独立审查待完成。阵列、多实例、跨块预连及产品留下一轮，裕量版本暂不做。下方既有共同边界和历史证据保留各自范围。

本项目研究面向多个计算图的预制计算底座：预先确定计算 Block 和部分物理资源，再通过有限的金属／通孔层定制跨 Block 互联。第一版采用 **Nangate45 原生 M1–M10、via1–via9 预制，自建研究层 M11/M12、via10/via11 后定制**；五块原生单块已有实际实现与验收结果，层次模型和上层互联资格另行验证。性能、能耗和成本优势仍待验证。

**当前阶段提示：叶块冻结不等于共同底座冻结。** 首轮先形成可用 Block 与接口；同类实例数量、不同裕量物理版本的组合、排布和固定预连线由共同底座阶段确定。共同底座冻结后，不同产品只改变声明允许的定制图形。详见[当前实施边界与分阶段冻结](docs/decisions/0004-block-library-base-freeze.md)；具体实现范围和验收状态以 [Issue #121](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/121) / [PR #122](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/122) 为准。

**2026-10-30 计算积木规划：** M＋归约与归一化＋基础向量算术＋激活与门控＋R＋S＋T；原 V 拆成三种宏，首版保留独立 R。每种先一个实现，主线须逐宏交付最终布局布线；阵列、多实例、裕量版本及预连拓扑后移。三种新 V 宏及 M/V 缩位宽尚不是已验收实现，现有实验保留。详见[边界与位宽分析](docs/COMPUTE_BLOCK_BOUNDARIES_2026-10-30.md)、[当前规划决策](docs/decisions/0005-compute-block-v-split-r.md)。

## 从哪里开始

1. [项目说明 v1.0](预制计算底座项目说明_v1.0.md)：研究问题、已确认边界、2026-10-30 架构规划补记与待验证清单。
2. [研究资料导读](研究资料导读.md)：依据原 README 完整要点整理的阅读顺序、架构问题和 EDA 研究路线。
3. [项目简介](docs/PROJECT_BRIEF.md)、[架构与目录](docs/ARCHITECTURE.md)、[当前状态](docs/STATUS.md)：持续更新的项目入口。
4. [不同 LLM 架构下的 Block 研究](docs/面向不同%20LLM%20架构的预制计算底座.md)、[Gemmini 学习笔记](docs/Gemmini学习笔记.md)、[工艺互连资料](docs/常见开源工艺金属互连线.md)：研究背景与候选方向。
5. [布线总报告](ref-project/llm-routing/总报告.html)、[线长报告](ref-project/llm-routing/线长报告.html)、[模块与接口报告](ref-project/llm-routing/docs/模块与接口报告.html)、[Block 布局与接口分布报告](ref-project/llm-routing/docs/Block布局与接口分布报告.html)与[结果包阅读说明](ref-project/llm-routing/阅读说明.txt)：参考项目的布线分析、模块接口及其证据边界。
6. [openTPU ACT/MXU 同资源物理对照](docs/experiments/issue-15-opentpu-results.html)、[实验过程与失败证据](docs/experiments/issue-15-opentpu-comparison.md)：本项目实际完成的块内和顶层布局布线，含面积、完整时序及布线成本。H1允许有源修复，尚未实现H2冻结底座／限定制层；单small参数及synthetic SRAM的限制见报告。

`sources/` 保存手写笔记和讨论资料；`ref-project/llm-routing/` 保存参考项目结果包，**不纳入 Agent 的主动或例行维护范围**；用户更新后可按要求提交，无需逐项审查或做哈希检查。该包不包含源代码、完整物理数据库、工具环境或运行日志，不能单靠仓库内容重新运行物理实现。详情见[来源与复现边界](docs/DATA_PROVENANCE.md)。

## 真实模型实验与 Block 分析

[阶段性分析报告](docs/model-analysis/MODEL_EXPERIMENT_ANALYSIS.md)汇总八个具体模型的运行目的、实际范围、关键结果与失败，并将证据对应到 P1–P15 能力和 M/V/A/R/S/D 逻辑域。原实验以固定 commit 链接追溯；本报告集成不等于来源 PR 或整模型硬件验收。

模型资料统一归档在 [docs/model-analysis](docs/model-analysis/README.md)：可阅读[精简字符算子图](docs/model-analysis/COMPUTATION_GRAPHS_SIMPLIFIED.md)，或通过[完整图册说明](docs/model-analysis/COMPUTATION_GRAPHS_FULL.md)查看手工、原始 ONNX 与 onnxsim 图及验证边界。

## 当前工作方式

远程计算资源与目录权限见[远程服务器使用规则](docs/REMOTE_RULES.md)，使用服务器前请先阅读。

任务、负责人和验收条件以本仓库 [Issues](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues) 为准。每项任务使用独立分支和 PR；开始工作前阅读 [AGENTS.md](AGENTS.md) 与[协作说明](docs/COLLABORATION.md)。实际物理实验及冻结结果生成命令见[架构与运行](docs/ARCHITECTURE.md)；管理结构检查为：

```powershell
python scripts/check_project.py
```

上面的命令只验证项目管理文件结构，不验证芯片架构或布线分析结论。
