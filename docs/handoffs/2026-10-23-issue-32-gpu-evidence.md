# Issue32 GPU证据交接

2026-10-23（Asia/Shanghai）。仓库[LLMHardwareDesign](https://github.com/rayggxia-workspace/LLMHardwareDesign)，project_id=`llm-hardware-design`；已核验本人GitHub身份YUZE-LU。任务[Issue32](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/32)，[PR36](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/36)待审查、不自行合并或done。独立目录`D:/Data/LLMHardwareDesign-gpu32`，分支`task/32-gpu-model-evidence`，base main=`0cc36f3238c7084d7126d94c314fe7d8bf0f9c5d`。最终交付commit以PR HEAD读回为准；运行源码commit与文件SHA逐组保留。

## 用户确定的验收范围

给定计算语义下拆分等价、数据依赖和状态传递正确；硬件准确实现指定的位宽、累加、舍入、饱和；容量、端口、通信与实现成本有依据。**完整整数模型语言质量通过不是EDA前置条件。** 已取消排队的追加FP32规范辅助语言质量及8192联合状态质量评估，未执行不记数值失败。旧质量仅作敏感性，不再给主线设置阻塞。

## 交付与实际证据

- [后续报告](../experiments/issue-32-qwen-repair.md)、[格式及预算](../decisions/issue-32-qwen-local-precision-candidates.md)；[首轮报告](../experiments/issue-32-gpu-model-evidence.md)保留历史失败。
- 正式代码`project/experiments/gpu_model_evidence/`及相邻repair/capture/batched目录；结果`gpu_model_evidence/results/issue-32/`含JSON/CSV、逐运行metadata ZIP、官方model-manifest、逐文件SHA、失败和package-index。字段在README与逐运行manifest中说明。
- Qwen2.5 FP16显式efficient SDPA，无静默后端回退或CPU权重卸载，512/2048/4096/8192一次/固定256分块通过；8192峰值6.671/6.114GiB。
- Qwen3.5原生FP16/BF16失败保留。大权重FP16存储、FP32计算参考延续到8192通过，最大cache L2约1.71e-4。固定INT8/INT32 K32矩阵+FP32规范辅助语义（源码4806b903147d65a74478cbd0d54c2c3a48cd69cb），128+16及512/2048/4096/8192+32的输出与全部所比较cache误差0；8192一次/分块峰值7.459/5.777GiB。此诊断不作为性能或完整整数模型证据。
- 两模型各3个layer0投影prefill/cached调用，取2行/4列但保存所有K组INT8 A/B、INT32部分和、FP32 scales与输出；CPU INT64全部部分和相等。Qwen3.5层0/14/30、head0/31，2048/2049/8192/8193共12个有限窗口，Q/K/V捕获在内部L2归一化前、卷积之后，含g(log-decay)、beta(sigmoid后)、初末状态和输出。FP64独立重放及另一次离线复跑12/12通过，最大L2约6.53e-7。
- 相关原始输入gzip在`selected-repair-inputs/`；旧layer0检查点在`selected-qwen35-layer0/`。不含每层每步大状态。模型和完整logits仍在`D:/Data/llm-gpu32/models/`及`runs/`，本机路径不是团队共享链接；完整共享存储待项目指定，处理人待指定。

## 格式与成本限制

真实整数验证覆盖替换投影/FFN的INT8×INT8→INT32及独立INT64样本。未包含embedding、lm_head、卷积的整数化；FP32 scale/反量化/分组部分和、attention、非线性及递推仍需浮点，不能声称目标全整数格式或RTL已通过。INT24/32状态量化—反量化敏感性不等于整数状态更新。给定模块M/r、round/saturate等合同由主线固定并验证，本任务不接管小模型整数参考、划分搜索或RTL。

Qwen3.5缓存固定49.5MiB+32KiB/token，Qwen2.5为36KiB/token；8224token分别306.5/289.125MiB。K32/K128 scales分别增加12.5%/3.125%逻辑payload，部分和INT32/FP32端口另算。INT24打包/宽整数40/47/63位只是附条件预算，不是已实现合同。逻辑读写、allocator实际分配、WDDM共享显存与实测流量分开；没有目标芯片物理流量。无观察器原生性能CSV必须筛`performance_eligible=True`、`warmup=False`；诊断/采集耗时不进性能结论。

## 实际检查与恢复

结构检查、旧协议5项通过；批量CUDA整数/融合缩放/规范辅助共4项通过，精确整数和缩放输出核对。新12窗口离线重放通过；源文件结束SHA未变，产物SHA与包索引另读回核验。具体检查在`work/YUZE-LU/32/validation.json`。不把这些当硬件舍入/饱和证明。

恢复第一步：读取最新AGENTS、Skill、Issue32/PR36/主线PR26，核对PR HEAD与package-index，按`gpu_state_capture/README.md`运行不需权重/GPU的重放命令。用户通知主研究线检查仓库并整合；审查人与共享存储处理人待指定。主线按其拟实现模块的明确合同核验整数部分和重定标、状态传递及硬件实现，完整模型质量不作为前置。

协作规则[rayggxia-project-collab](../../.agents/skills/rayggxia-project-collab/SKILL.md) v1.0.0。登记management-hub [PR5](https://github.com/rayggxia-workspace/management-hub/pull/5)仍pending；无board.json，status-mapping已读，候选[Project1](https://github.com/orgs/rayggxia-workspace/projects/1)缺read:project，条目/字段unverified、同步pending。由具权限管理员（待指定）核验Issue32、Project ID/Status/Priority并读回，不自行扩大凭据权限。在线读回证据随PR更新。
