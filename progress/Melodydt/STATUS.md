# Melodydt 的进度

## 2026-11-14（Asia/Shanghai）七模型短程吞吐准备

- [Issue #274](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/274) 进行中，任务分支自 [PR #260](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/260) 的 `55620f17` 建立。六模型归档核验通过。Qwen3 功能复跑 114275 与归档逐字节一致。指令驱动 Gather 114290 两位置通过，DDR 读取与回调 144/144。
- [作业、验证和复跑记录](../../work/Melodydt/274/README.md)保留首次失败 114273 与修订重跑。两步 decode 和短 prefill 的整模型吞吐尚未测得。
- 下一步接 Qwen3 输入 RMS、Q/K Norm、16Q/8KV 及状态回读。Llama 需要可访问的真实整模型检查点。登记待合并，Projects 待核验和同步，审查人待指定。
