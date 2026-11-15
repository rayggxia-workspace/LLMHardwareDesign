# Melodydt 的进度

## 2026-11-14（Asia/Shanghai）七模型短程吞吐准备

- [Issue #274](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/274) 进行中，任务分支自 [PR #260](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/260) 的 `55620f17` 建立。六模型归档核验通过。Qwen3 功能复跑 114275 与归档逐字节一致。指令驱动 Gather 114290 两位置通过，DDR 读取与回调 144/144。
- [作业、验证和复跑记录](../../work/Melodydt/274/README.md)保留首次失败 114273 与修订重跑。两步 decode 和短 prefill 的整模型吞吐尚未测得。
- 下一步接 Qwen3 输入 RMS、Q/K Norm、16Q/8KV 及状态回读。Llama 需要可访问的真实整模型检查点。登记待合并，Projects 待核验和同步，审查人待指定。

## 2026-11-15（Asia/Shanghai）七模型数值参考完成

- 114294 和 114313 完成七套 FP32 数值参考与状态/输出散列。Llama 固定 ModelScope 版本及八文件上传核验完成。
- 114340 完成 Qwen3 28 层投影与全词表共 197 张量、582,016 个记录。详见 [草稿 PR #275](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/275) 与上面的作业记录。
- 下一步生成 Qwen3 首层部署指令、运行 Q/K Norm 与写确认后跨步 KV，再扩至 28 层。两步 Decode／短 Prefill 整模型吞吐仍待测，Issue 保持进行中。

- 114376 的 1,024 维输入 RMS 和 128 维 Q/K Norm 使用真实 gamma 与独立向量，6/6 成功，214/214 DDR 回调对账。下一步串到真实 QKV 与跨步 KV，全部已提交作业均终态。

## 2026-11-15（Asia/Shanghai）七模型短程回放

- Qwen3 115055 正常结束，短 Prefill 13.481376 输入 token/s，Decode 3.585938 token/s，两个 token 均与零历史 FP32 一致。已保存日志、输出、审计和散列。
- Llama 已完成短 Prefill，六个模型的整模型 Decode 作业已提交。Gemma 的残差定点饱和、64 维头填充及混合递推服务记录在[结果与复跑索引](../../work/Melodydt/274/RESULTS.md)。
- [Issue #274](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/274) 进行中，[PR #275](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/275) 草稿。后续按模型核验实际退出码、两阶段回执、零历史数值及输入输出散列。登记 pending，Projects 看板待核验。

- Qwen3 逐周期和加速回放两个阶段时间、状态、logits 与 DDR 计数均一致。Llama 两阶段完成，短 Prefill 7.178705 输入 token/s，Decode 2.523063 token/s，FP32 两个 top-1 一致。Granite 两阶段完成，短 Prefill 8.055319 输入 token/s，Decode 2.376006 token/s，第二步 top-1 分歧已登记，另有路由诊断。Phi 的 Prefill 2.165252 输入 token/s，Decode 继续运行。

- 七个模型的两个全层回放阶段均已审计，统一使用 512-bit SRAM 端口和 512-bit 程序存储写宽。所有 Slurm 作业终态，日志和输出备查。包括阶段重跑在内的实际回执见[结果索引](../../work/Melodydt/274/RESULTS.md)。Qwen3、Llama、Phi 两步 top-1 均与 FP32 一致。Granite、Gemma、Qwen3.5 和 Falcon 有数值分歧，已补路由和同输入对照。PR 保持草稿，Issue 进行中，待数值资格、RTL／物理校准和独立审查。

## 2026-11-15（Asia/Shanghai）七模型第一轮优化

- 全部模型的权重窗口四层或首层 A/B 已结束，结果逐位和状态证据见[优化记录](../../work/Melodydt/274/OPTIMIZATION.md)。另完成 FFN Context 缓存及 64 维 KV 前缀 A/B。
- Qwen3 全层 Prefill 17.897215 输入 token/s，较基线提高 32.76%。Decode 115262 运行中，其余六模型的整层作业 115282–115287 已进入 RUNNING。待核验两步词表、状态、DDR 对账及整层增幅。
- [Issue #274](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/274) 继续进行中，[PR #275](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/275) 草稿。登记 pending，Projects 看板无项目配置，审查人待指定。

- 首轮优化整层 Slurm 115262、115282–115288 均正常退出。七模型用 512-bit SRAM 完成两阶段 A/B，候选和原基线最终残差、词表 logits 逐字节一致。短 Prefill 提升 33.89%–53.98%，两步 Decode 提升 20.82%–97.53%。输出清单已复验。另完成 Qwen3 独立 V 读取复用，Decode 达 4.948742 token/s。见[完整优化记录](../../work/Melodydt/274/OPTIMIZATION.md)。PR 保持草稿，Issue 进行中，基线数值资格与 RTL／物理校准待完成。

## 2026-11-15（Asia/Shanghai）PR #272 调度重测

- 代码 `209482b226456a7fdc328692470b26ef42ac05e6` 接入 ATT1 双窗口和四权重 bank。115340–115346 在 512-bit SRAM 下完成 14 个全层阶段，3,601 项输出清单和程序、残差、logits、反馈及状态事务均通过对账。6 个模型的 Decode 提速，七模型短 Prefill 降速。详见[重测和复跑记录](../../work/Melodydt/274/PR272_RETEST.md)。
- C380 原生 RTL 115329/115330 正常／背压周期减少 13.11%／0.91%。C639 原生 FFN 115347 正常／背压周期与 PR #272 归档一致，98 项散列通过。
- [Issue #274](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/274) 进行中，[PR #275](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/275) 草稿。由 Melodydt 续办数值资格和整模型 RTL／物理校准，审查人待指定。登记 pending，Projects 缺看板配置，已留交接。

## 2026-11-15（Asia/Shanghai）七模型三 P 与非零历史

- 七模型全层短 Prefill 与代表性历史两步 Decode 已通过，两个阶段均无残差限幅。14 个 top-1 与同历史 FP32 一致。115618/115619/116000 全部正常退出，116181/116182 独立验收通过，6,699 项输出清单已验。见[完整记录](../../work/Melodydt/274/THREE_P_LIVE.md)。
- Gemma Q12 修正残差与后归一化写回的限幅，旧混合模型的 FP32 零历史清理已修正。范围为 512-bit TLM，整机 RTL／物理校准待续。Issue #274 进行中、PR #275 草稿，审查人待指定，登记 pending，Projects 无配置。

- 2026-11-15（Asia/Shanghai）发布[七模型速度评估交接](../../docs/handoffs/2026-11-15-issue-274-speed-evaluation.md)，集中记录最终速度、实际生效的模型专项路径和冻结复跑入口。项目结构检查通过，七组速率与最终回执逐项一致。下一步为增加分窗活动计数以接入能耗评估，整模型 RTL／物理校准仍待完成。
