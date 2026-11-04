# Issue179 研究辅助资料

用途：接续[PR176](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/176)；[Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179) / [Draft PR180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)，负责人Melodydt。正式研究见[CONTINUATION_RESEARCH](../../../docs/local-blocks/CONTINUATION_RESEARCH.md)，不是此目录里的临时说明。

- `capacity-input.json`：固定PR176资源/形状及显式同时驻留假设，包含故意超容量的反例；不是已经验证的调度。
- `analyze_capacity.py`：仅Python标准库，生成[容量结果](../../../docs/local-blocks/continuation-capacity.json)；`--check`逐字重算核对。
- `source-index.json`：固定输入Git blob/SHA-256及相关PR的本轮读回版本/状态，来源边界见报告。
- `validation.json`：实际检查/版本/轻量产物SHA，未执行项明确列出；不自引用自身摘要。
- 本地`delivery`是独立API部分资料目录，不上传它的管理快照、来源快照或整个目录；只上传本任务显式白名单。目录无.git/index/HEAD，远端以固定父树继承全部未改内容。

本轮管理结构已运行通过，容量核算/重算及源/白名单核验详见validation.json。没有新RTL、服务器、模型或物理实验，原13图未重渲染。source-index核对的是文件和在线报告版本，不是重新验收服务器大包。

任务分支`task/179-local-block-continuation`，父commit `08f2ea20a11dfdd09892a67599163e32b7237edb`；新Draft PR、最终commit与证据回执由Issue179在线说明提供，避免自引用commit循环。研究保持in_progress；相关审查待指定、未合并、非done。登记PR5 pending；看板unverified/同步pending，见[可执行交接](../../../docs/handoffs/2026-11-04-issue-179-local-block-continuation.md)。

## 母控/局控方案与编译器编码入口

本任务按用户分工以两级控制为主线。正式[方案与研究步骤](../../../docs/local-blocks/TWO_LEVEL_CONTROL_PLAN.md)、[ISA](../../../docs/local-blocks/CONTROL_ISA_V0_1.md)、[规范/codec](../../../project/control_isa_v0_1/README.md)在正式目录；这里保存control-plan-sources.json、control-plan-validation.json和control-example-programs.json。原容量输入/输出与validation.json保留，不改写旧证据。

新独立API目录control-plan-1f3e916/delivery（仅本地，不上传整个目录）从PR180固定HEAD继承；无.git/index/HEAD，旧包保留。编码器输出是机器码/字节序参考，没有执行native描述符、模型或RTL。最新发布commit/白名单/远端原文核验及CI见PR180回执。

## 综合方案 v0.2 与进度快照

[正式综合方案](../../../docs/local-blocks/TWO_LEVEL_CONTROL_PLAN.md)汇总 Block 组成、四类连接、ISA／装载／执行、截至 2026-11-04 16:25 CST 的进度和 R0–R7；ISA 机器版本仍 v0.1，不改 codec。宏级电源开关暂缓。

- control-summary-sources.json：本轮固定父提交／文件版本、GitHub PR 元数据和说明快照；只读核验，不是服务器原包重验。
- control-summary-validation.json：本轮实际管理、容量、编码及文档／来源／白名单检查，工具版本和产物 SHA；不自引用自身 SHA。
- 本地工作目录 control-summary-d642960/delivery 为独立部分 API 快照，无 .git／HEAD／index；原目录不覆盖，配置装载器／完整编译和新 RTL 均待实现。本地辅助脚本／快照不整体上传。

## 17:05 CST 控制研究范围修正

本分支只研究母控／局控。完整 Block 实现、S 扩容、计算数据通路、系统物理／模型质量为外部依赖；真实验收门保留，任务／负责人待指定。当前可用已知接口与有限协议 peer 推进控制合同、装载／执行模型和控制 RTL 验证。[综合方案第0、9节](../../../docs/local-blocks/TWO_LEVEL_CONTROL_PLAN.md)和[control-scope-validation.json](control-scope-validation.json)记录本轮修订／检查。旧综合方案与容量记录仍为历史输入，不表示已完成硬件。

## 第1步：控制接口、原生服务及PR176同步

正式[接口合同](../../../docs/local-blocks/CONTROL_INTERFACE_CONTRACT_V0_1.md)和[机器可读参考](../../../project/control_contract_v0_1/README.md)登记M/G/S范围原生端口、接受／完成、12服务和2个16KiB控制profile。control-interface-sources.json绑定10份固定输入；control-interface-validation.json记录实际检查／产物SHA；pr176-sync.json保存开始与上传前的最新上游核对。

每次开始／恢复研究和上传前读取PR176最新head、状态／说明、评论／review／逐行评论，比较并同步受影响合同；未配置定时监测。新本地目录control-interfaces-df3e7a2/delivery为部分API快照，无.git／HEAD／index，旧目录保持。工具只验证静态字段，始终deployable=false；指令执行／真实数据／RTL／物理均未执行。

## 第2步：控制用例与独立预期轨迹

[正式文档](../../../docs/local-blocks/CONTROL_REFERENCE_CASES_V0_1.md)与[参考目录](../../../project/control_cases_v0_1/README.md)包含3组程序／分离记录、4条人工参考和27组属性／拒绝检查。control-case-sources.json、control-case-validation.json记录来源和实际验证；pr176-sync.json持续保存上游核对历史。没有PC执行／控制RTL／完整镜像或服务器任务。

用户要求每轮进展直接补到总方案，本轮已补当前摘要与逐轮记录；以后每次交付包括目标、上游差异、产物、实际验证、限制和下一步。新的本地control-traces-afd96b3/delivery为独立部分API快照，无.git／HEAD／index，旧包保留。

## 第3步：完整镜像、配置准入及失败恢复

[正式合同](../../../docs/local-blocks/CONTROL_IMAGE_LOADING_V0_1.md)与[参考目录](../../../project/control_image_v0_1/README.md)交付7镜像2080B、manifest／SHA与单bank配置状态模型。control-image-sources.json／control-image-validation.json记录代码父版本、来源、实际命令及SHA；旧回执保留。上一轮CALL arg0快照已纠正并补回归；总方案已补本轮摘要及逐轮进展。

本地新独立部分API包control-images-add6327/delivery，无.git／HEAD／index，整个目录及辅助发布脚本不上传。只上传显式白名单，最终commit／远端读回／CI见PR180回执。没有PC执行、控制RTL／Block或服务器作业；下一步独立二进制PC执行模型。

## 第4步：二进制取指与有限控制执行

[正式说明](../../../docs/local-blocks/CONTROL_EXECUTION_MODEL_V0_1.md)及[代码](../../../project/control_exec_v0_1/README.md)包含独立运行端、观察比较器、外部peer输入、9次执行报告与26组测试，累计107组。control-exec-sources.json／control-exec-validation.json绑定父版本、输入、工具／实际命令和产物SHA。总方案已补目标、上游差异、产物、验证、限制、下一步及逐轮记录。

本地control-exec-8cb3109/delivery为独立部分API副本，无.git／HEAD／index；只上传本轮白名单，旧包和既有镜像／人工参考不改。最终commit／原文／CI见PR180。当前仅软件PC执行，原生宏／S／控制RTL、完整Block、系统物理及LLM数值未执行；无新增服务器作业／自动监测。下一步运行取消／协同复位及旧响应隔离。

## 第5步：取消、poison与复位研究

[正式方案](../../../docs/local-blocks/CONTROL_RECOVERY_PLAN_V0_1.md)及project/control_exec_v0_1新增恢复模型、独立native源、协调合同和独立检查。9取消／poison＋9恢复、2个模型cohort复位，共168次退休；新增30、累计137组。control-recovery-sources.json／control-recovery-validation.json记录源码父版本、来源、实际命令及SHA，旧回执／镜像／人工参考／旧9次报告保留。

独立部分API目录control-recovery-c22dde6/delivery无.git／HEAD／index，只上传白名单；最终commit／远端原文／CI见PR180。总方案已补本轮与下一步。无tag隔离有provider静默／复位合同前提；真实完整复位域／控制RTL及Block未验收，无新增服务器作业／自动监测。

## 第6步：局控RTL接口与状态机候选

[正式合同](../../../docs/local-blocks/LOCAL_CONTROL_RTL_CONTRACT_V0_1.md)及project/control_rtl_contract_v0_1包含92逻辑信号、状态／guard、内部配置编码、单PM端口、信用／holding及资源下界，生成SV声明和端口表。新36、累计173组检查；4人工期望时序非DUT运行。control-rtl-sources.json／control-rtl-validation.json保存来源、工具检测、实际命令和SHA。

新独立部分API目录control-rtl-contract-e079924/delivery无.git／HEAD／index；只上传白名单，旧代码／镜像／报告不改，最终commit／原文／CI见PR180。总方案已同步。PATH未发现HDL工具，HDL编译／lint／仿真未执行；下一步功能局控最小切片，无服务器／物理作业或自动监测。




