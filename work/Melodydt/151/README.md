## 2026-11-02 main同步与当前八主线

当前入口：[同步/重整报告](../../../docs/MAIN_SYNC_AND_RESEARCH_ROADMAP.md)、[main-sync机器索引及验证](main-sync/README.md)。main4b1df2c7的六叶交付已按三方整合；旧七阶段与各轮索引保持历史字节。L4真实A为下一主攻，数值质量并行；无新RTL仿真，R未合格。历史资料如下。

本轮Issue151：[真实数据报告](../../../docs/QWEN_LAYER0_NUMERIC_RTL_REPORT.md)、[qnum辅助源/索引](qnum/evidence-index.json)、[真实A静态候选](../../../docs/QWEN3_SQ2_ATTENTION_PLAN.md)。数据/源/工具SHA与界限分开；PDF仅本地另交付。

本轮Issue151：[F1024实施](../../../docs/W4_F1024_IMPLEMENTATION.md)，源码6a7de2c8、95245/64CASE；[硬件profile](f1024-hardware-profile.json)、[证据索引](f1024-evidence-index.json)、[接续](../../../docs/handoffs/2026-11-02-issue-151-f1024.md)。个人辅助用途为独立数学/源码锁/实验索引，不代表模型质量或物理通过。

# AF16与真实样本准入当前入口（2026-11-02）

Issue151/PR152，Melodydt。[纵向衔接报告](../../../docs/W4_AF16_IMPLEMENTATION.md)、[静态模型准入/下一实际尺寸](../../../docs/AF16_MODEL_ADMISSION.md)、[数值合同](../../../docs/W4_AF16_NUMERIC_CONTRACT.md)。af16-implementation.json为索引；af16-model-admission.json为static ledger，scripts/check_af_model_admission.py核来源与拒绝条件。af16-rtl-evidence为95242真实小型文本，build留本人服务器；af16-package_server等归档脚本按原隔离P目录约定使用，重跑必须新目录/作业。合成静态ALLOW、RTL33CASE与全模型/物理资格分开。

# A16当前入口（2026-11-02）

Issue151/PR152，Melodydt。[实现报告](../../../docs/W4_A16_IMPLEMENTATION.md)、[数值合同](../../../docs/W4_A16_NUMERIC_CONTRACT.md)、[源码/样本边界](../../../docs/A16_SOURCE_MODEL_REVIEW.md)。a16-implementation.json为机器索引；a16-rtl-evidence保存95235真实日志与SHA，archive-helper-first-failure保留归档助手失败而非RTL失败；a16-package_server等是原隔离目录脚本归档，直接重跑须按其P目录约定及新的服务器目录准备。仍L4，未完成真实样本/跨岛/物理。

# F16当前入口（2026-11-02）

Issue151/PR152，Melodydt。[有界FFN报告](../../../docs/W4_F16_IMPLEMENTATION.md)、[数值存储路线](../../../docs/AF_NUMERIC_STORAGE_PLAN.md)，机器索引f16-implementation.json。f16-rtl-evidence保留95206编译失败及95209/30CASE服务器通过的原始文本与SHA；源b77d6b7b；build留本人服务器任务目录。旧F8/A8及W5-IF证据保持原来源与范围。仍L4，下一A16因果候选未实现，非全模型/物理准入。

# 当前W5-IF合同入口（2026-11-02）

Issue151/PR152，Melodydt。docs/W5_IF_INTERFACE_CONTRACT.md为主规格，W5_IF_PROTOCOL_EXAMPLES为通道/候选字段及因果时序，rtl-contracts/W5_IF_PORTS_AND_RESOURCES为真实端口/资源，W5_IF_MODEL_ADMISSION为8样本/6配置需求。w5-if-contract.json链接各机器表，w5-if-checks为静态来源/字段/算术/链接检查，非仿真。逻辑合同待审查，新RTL/母控网络/物理未实现；历史A8/N/F8证据不变。

# 当前三层互联安排（2026-11-02）

Issue151/PR152，Melodydt。正式docs/COARSE_BLOCK_INTERCONNECT_BOUNDARY_PLAN.md及proposed决策将互联边界归入L4合同前置、L5实现、L8最终验收；interconnect-boundary-plan.json为机器索引。仅安排计划，合同尚待编写、L5 RTL未开始；此前A8/N/F8证据和所有历史索引保留。

# 当前A8入口（2026-11-02）

Issue151/PR152，负责人Melodydt。a8-index记录当前八主线状态；a8-execution-index绑定服务器95116/r04的80项功能证据、失败尝试、工具/源码/日志SHA；a8-rtl-evidence保留原字节。正式说明见docs/W4_A8_*与COARSE_BLOCK_RESEARCH_PROGRESS.md。不是完整A/L4退出或物理验收。历史W4/W3/W1证据保持各自时间/工具身份。

# 当前W4入口（2026-11-02）

Issue151/PR152，Melodydt。w4-index是当前状态；w4-execution-index为4次真实运行及源/日志SHA，w4-checks/w4-verification为交付复核。W4并未退出整个L4；W0/W1/W3历史索引按原时间保留。旧builder在w4-rtl-evidence/prior-inputs，记录复现修复。

# W3 当前入口（2026-11-01）

Issue151 / PR152 / Melodydt。`w3-index.json`是本轮状态，`w3-execution-index.json`绑定4次实际运行、源SHA和日志；`w3-checks.json`/`w3-verification.json`是交付检查。W0/W1历史索引保留历史时间和范围，不覆盖其原始回执。正式说明见docs/W3_*。

> 当前入口：[W1最小岛壳实现](../../../docs/W1_MINIMAL_ISLAND_IMPLEMENTATION.md)、w1-index.json、w1-execution-index.json。W0/P2历史资料保留；本轮新RTL有限通过不等于通用岛内/跨岛或完整profile通过。

> 当前执行入口：[主线一/W0报告](../../../docs/COARSE_BLOCK_W0_CONTRACT_BASELINE.md)、w0-index.json。八主线逐条推进，当前仅合同/追溯准备；旧阶段回执保持原版本，不提升为全系统验收。

> 最新连接入口：[主报告](../../../docs/COARSE_BLOCK_CONNECTION_IMPLEMENTATION.md)、island-connection-index.json。六配置依赖/共享跳、当前源码证据与W0–W11实施包分别核验；无新RTL/服务器作业。

> 最新数量入口：[大Block宏BOM](../../../docs/COARSE_BLOCK_MACRO_BOM.md)、block-sizing-index.json；五功能类/六整数配置，逻辑调用数和物理实例数分开，NUM/MEM/CTRL另计。

> 当前新增研究入口：[粗粒度执行岛候选](../../../docs/COARSE_BLOCK_HIERARCHY_CANDIDATE.md)及coarse-study-index.json；五profile是逻辑功能，不是物理实例数。P2真实RTL及原验收矩阵保留。

> 当前P2入口：[第二步报告](../../../docs/PHASE2_MST_IMPLEMENTATION.md)、phase2-source-lock.json、phase2-checks.json与phase2-verification-status.json。最新14核心源采用7078786；P1历史固定be10e69/643，旧回执不改写。研究任务仍Issue151/PR152，P3–P7未开始。

# 六类连接方案与bridge归属研究

七阶段当前入口：[P1索引](phase1-index.json)、[正式路线](../../../docs/SEVEN_MACRO_INTERFACE_ROADMAP.md)、[第1步报告](../../../docs/PHASE1_INTERFACE_BASELINE.md)。phase1-native/版本比较/MST参考/验证矩阵是本轮资料；旧静态编译研究与回执保留，不把新旧软件检查写成系统RTL通过。

当前主入口：[静态重研究索引](static-rework-index.json)与[工作报告](../../../docs/STEPS_1_3_WORK_REPORT.md)。family-binding、compile-lowering、static-execution是当前三合同；旧family/edge/96义务为冻结输入，旧onchip/system合同用于比较/回归。工具与实际回执见static-rework-checks/verification，不把37 probe或预算算式当硬件通过。

2026-11-01补充：系统有外存，当前P0暂不接入；旧“无EXT”仅约束该验证profile。当前说明见[外存与N接口澄清](../../../docs/MEMORY_SCOPE_AND_N_INTERFACE_CLARIFICATION.md)，增量检查见memory-scope-checks.json与memory-scope-verification.json。旧steps123检查回执保留历史，不覆盖原运行证据。

- 任务：https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/151；负责人Melodydt；更新时间2026-10-31T16:22:44+08:00。
- 任务分支：`task/151-six-connection-study`；基线`a103da352b7e431cedc69f54b9f71c05371be1b3`；[PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152)已上传待独立审查，未合并。首份研究commit为796d413458fd267200ab9dbff6d8e1b0b6468cdd，当前head以PR读回为准。
- 正式文档：[六项连接](../../../docs/SIX_CONNECTION_SCHEMES_STUDY.md)、[bridge归属](../../../docs/SIX_CONNECTION_BRIDGE_AUDIT.md)、[协调候选](../../../docs/SIX_CONNECTION_COORDINATION_CANDIDATE.md)。
- `connection-index.json`保存六项功能依赖、来源与改动位置；不是已路由网表或冻结连接矩阵。`source-index.json`保存固定ref/path/Git blob/SHA-256/行数；发布head与历史运行source_commit分别说明。
- 本地目录`D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/`与API交付包`delivery/`隔离。源码快照、草稿和准备脚本只留本地，不作为新正式源码上传；完整来源留在原固定commit。不是完整Git clone，不能从缺失文件推断远端删除。
- 本任务未运行RTL/SystemC或物理实验；没有仿真作业号。原有证据是按范围引用，管理结构检查不能替代业务验证。

核验已提交研究清单（Python3.7+、标准库）：

```text
python -X utf8 work/Melodydt/151/verify_study.py --root .
```

若已用本人认证按source-index重新取得选定原始UTF-8文件，可把它们按snapshot_name放在独立目录，增加`--source-dir <该目录>`逐字节核验Git blob/SHA-256及源码行引用；当前会话的本地来源目录为`work/Melodydt/151/sources/`。无source-dir时只做文档/清单核验，并明确标来源字节核验未执行。

实际结果见`verification.json`；后续提交不因本文件宣称自动监控或测试完成。登记PR5 pending；看板缺配置/工具，unverified/同步pending，处理人待指定；独立审查人待指定。


## 第二阶段：固定产品六连接与分层控制总方案

[总方案](../../../docs/SIX_CONNECTION_SYSTEM_DESIGN.md)、[控制规格](../../../docs/SIX_CONNECTION_CONTROL_SPEC.md)、[六模板](../../../docs/SIX_CONNECTION_TEMPLATE_SPEC.md)与[候选决策](../../../docs/decisions/0006-fixed-product-hierarchical-control-candidate.md)由同一PR152交付。机器合同system-design-contract.json是候选规格实例，不是硬件IR、路由网表或完整模型程序。

本地新包system-delivery与原delivery分开；system-sources仅保存选定相关UTF-8来源，不上传来源快照或草稿。新来源system-source-index.json与原source-index.json分开保留各阶段版本。

verification.json保留第一阶段49a34e75的历史回执；本轮修改后的文件SHA、静态正负例及来源检查以system-verification.json为准，不把旧回执当作当前文件的哈希清单。

```text
python work/Melodydt/151/verify_system_design.py --root .
```

可选加 --source-dir 指向本轮六份来源快照、--prior-source-dir 指向第一阶段36份快照，逐字节核验Git blob与SHA-256；不提供时明确标来源字节检查未执行。校验器包含类型、资源所有者、依赖/事件、数值门槛和容量的拒绝用例，但不执行RTL或模拟真实控制器。实际结果见system-verification.json，包含产物SHA及未执行项。


## PR144实现基线合入

见[当前RTL基线](../../../docs/SEVEN_BLOCK_RESEARCH_BASELINE.md)、rtl-baseline.json与integration-verification.json。原36/7来源及历史回执保留版本身份，本轮重新运行静态检查。当前分支实际包含七宏，不代表系统wrapper/NUM/外部状态管理已实现。

```text
python work/Melodydt/151/verify_rtl_baseline.py --root .
```

## 2026-10-31T20:30:44+08:00：当前RTL推导重写v0.2

- 入口：[总方案](../../../docs/SIX_CONNECTION_SYSTEM_DESIGN.md)、[原生审计](../../../docs/RTL_NATIVE_CONNECTION_AUDIT.md)；原生附录分M/S/T、N/E/G、R。七宏原生接口未统一，本轮统一的是待实现的外侧控制合同。
- 固定faabeda/643c6012；复用Issue151/PR152，PR基分支仍task/143-seven-block-v2。当前真实上传head/CI以PR回执为准，不把输入基线写成输出commit。
- 本地独立目录`D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/rtl-redesign-faabeda/integrated`；与原merge/system包和根管理参考副本隔离，为部分API检查包、非Git clone，无本地暂存区。仅白名单文档/合同/校验/进度上传，不上传RTL、草稿/源码副本、其他会话或ref-project。
- `rtl-derived-contract.json`保存7个实际ANSI接口签名和源码指纹、11项关键边界；`system-design-contract.json`更新完整两遍SSM preload位置和原生命令例子。`verify_rtl_design.py`仅作源码漂移/声明一致性检查。
- 当前回执：`rtl-redesign-verification.json`、`system-verification.json`、`integration-verification.json`及`rtl-redesign-checks.json`；旧verification/integration-checks保留各自历史身份，不描述为当前RTL运行结果。
- 实际静态检查通过后供独立审查；完整产品编译、RTL/SystemC/EDA/整数oracle未执行，无服务器作业。审查/合并待完成，登记PR5 pending，看板条目unverified/同步pending，处理人待指定。

## 2026-10-31T21:15:42+08:00：全合法连接与有限家族范围

用户明确“全部允许组合”，并确认仅M11/M12永久绑定、有限模型类型。[全合法连接规格](../../../docs/ALL_LEGAL_CONNECTION_SPEC.md)与总方案v0.3把六模板降为回归集。all-legal-connection-contract.json列49宏对索引、数据角色、转换/服务与7种自回访；合法性、recipe、实现/验证/物理分开，当前新系统路线全部未完成。

独立目录all-legal-36f9c9d/integrated复制自已交付36f9包，非完整Git clone，无本地HEAD/暂存区；原包和根参考副本不覆盖。新增verify_all_legal_connections.py仅静态覆盖/声明检查，实际命令与报告见all-legal-checks.json、all-legal-verification.json。叶宏RTL、服务器、ref-project未改；完整家族目录/程序、RTL组合/数值/物理验收未完成。

## 2026-10-31T22:10:32+08:00：前三步正式候选交付

- 用户范围：仓库八样本/十层型，规模不明作有据保守估计，暂不考虑外存，M11/M12永久绑定无bootload。入口[工作报告](../../../docs/STEPS_1_3_WORK_REPORT.md)、[FamilySpec](../../../docs/SAMPLE_MODEL_FAMILY_SPEC.md)、[角色账本](../../../docs/SAMPLE_LEGAL_CONNECTION_LEDGER.md)、[片上合同](../../../docs/SAMPLE_ONCHIP_SYSTEM_CONTRACT.md)。
- family-spec/edge-ledger/onchip-contract为当前候选；旧system-design-contract.json标为历史全系统候选，EXTERNAL_MEMORY不参与本阶段准入。全局原语目录保留，但当前无EXT/DMA/spill。
- 19原始源快照只存本地overall-drafts/steps123/family-sources，上传family-source-index记录固定ref/path/Git blob/SHA/字节；不上传原graph或ref-project。sample-memory-demand按真实config推导，sample-connection-obligations绑定96项样本义务到具体槽，均不冒充定点/硬件接受。
- 本地D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/steps123-39bd7bf/integrated为隔离API资料包，非完整Git clone，无HEAD/暂存区；其他包/根参考副本未覆盖。当前分支task/151-six-connection-study，输入39bd7bf，输出commit/CI见PR152回执。
- 实际核验见steps123-checks.json、steps123-verification.json。原生字节/旧合同报告保留各自范围，不能拿旧15owner含EXT的统计当当前片上接口。无RTL/SystemC/推理/服务器/EDA，无新增硬件资格。
- 下一步独立审查前三步规格，决定片上资源规模和实际RTL任务。PR未合并，Issue交付后in_review；审查人待指定。登记PR5 pending，看板unverified/同步pending，管理员待指定。
