# Issue37：架构审查、选型与实验协议交接

- 仓库rayggxia-workspace/LLMHardwareDesign；project_id llm-hardware-design。
- [Issue37](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/37) / [PR38](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/38)。
  负责人Liangruizhi / 2663955430@qq.com / 182389313，认证已核对；审查人待指定。
- task/37-gemma-phi-protocol，D:/Projects/LLMHardwareDesign-gemma-phi，base task/33-int8-contract@4a3f5e4。
  正式分析/检查源码946281b9a90dd36b130e691c60667b9f7d1e4d32；结果/本交接交付commit以PR38最新head为准。
- 正式审查docs/MODEL_ARCHITECTURE_REVIEW.md；catalog/config/plan/analyze/test在project/experiments/model_selection；
  正式screen.json、checks/、audit.json、manifest.json在work/Liangruizhi/37。
- 仅本Issue修改，其他worktree/成员文件/ref-project未动；raw公开小型快照在D:/Projects/Codex/gemma-phi-20261023。
  当前交接随结果提交，交付后的实际git status在PR回执；恢复时先核状态，不覆盖后续改动。

## 本轮实际完成

按用户新增要求，扩大为所有已提家族/变体的架构审查，**暂停原拟Gemma/Phi缩小数值实验**。
本轮没有新增真实/缩小模型神经推理，没有权重下载、GPU/服务器或其他机器作业。
17个变体、12份官方config/SHA、5份门控401缺口，7类家族的计算/状态/通信/精度差异与取舍。
管理结构、8个协议/独立已知值测试、whitespace通过；源版本与原始日志绑定通过。
这些检查不能描述成模型“跑通”、INT8可用、质量或硬件收益通过。

拟定主测Qwen2.5-3B、Qwen3.5-4B和有条件Gemma3-4B；复用Qwen3-0.6B本机证据；
Phi是唯一默认的后续保留验证。Llama/R1蒸馏仅替代/可选holdout，Gemma12B重复规模/4bit暂缓；
原生R1/Qwen3-30B MoE/MLA仅研究轴，不宣称完整模型验证。选择理由/替代条件在正式审查。

## 不能越过的条件

- 当前new_numerical_runs_enabled=false仅代表架构/协议阶段，后续在已有授权内完成门槛核验再推进适合本机的工作，
  不能自动变为服务器/GPU授权或安排他人任务；不制造额外用户确认流程。
- Gemma/Meta授权与真实config、tokenizer/checkpoint SHA和适用backend未齐；不绕过或代接受许可。
- Qwen2 QKV bias、可能33位后加与动态scale bias定标；Gemma有效gamma/GELU；块级KV scale在QK/PV归约中的对齐；
  宽算术和物理工作区/端口仍是整数能力缺口，现有RQ32或KV单独误差不能代替完整数值路径验证。
- 正式数据版本/样本/SHA、质量容忍与95%区间规则尚属待冻结设计；没有看评价后调阈值。
- A浮点正确性→B量化/质量→C同精度同库存/物理约束→D保留验证，未过前项不扩大长上下文。
- Issue32/PR36仍由YUZE-LU优先修复Qwen；只读其任务范围，不整合其结果。等用户通知完成再核最新Issue/PR/数据/SHA。

恢复第一步：读最新AGENTS/Skill、Issue37/PR38、Issue32范围和成员交接；核catalog/config/plan版本及
审查中是否改变选型，执行README的metadata-only检查。若准备模型实验，先关闭方案列明的接入/整数合同/
质量门槛缺口，再冻结本轮计划；GPU执行人/排期待指定，不重复师兄任务。
登记PR5 pending；无board.json/Projects工具，看板unverified/同步pending，管理员待指定；PR待审查/合并，未done。
