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
