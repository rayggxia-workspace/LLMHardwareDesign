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
