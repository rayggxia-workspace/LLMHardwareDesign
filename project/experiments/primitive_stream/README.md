# 固定校准、完整GQA组和不可变KV的本机参考

Issue47，复用已有Qwen3-0.6B权重；CPU层0的KV头0及其全部query头0/1，独立32token校准文本、
两段独立40token评价文本，32token prefill＋8步teacher-forced decode。无新权重、GPU或远程任务。

```powershell
python -B scripts/check_project.py
python -B project/experiments/primitive_stream/test_stream.py
& D:/Projects/Codex/qwen3-inference-20261022/environment/.venv/Scripts/python.exe -B project/experiments/primitive_stream/capture_qwen.py --weights D:/Projects/Codex/qwen3-inference-20261022/environment/weights --output D:/Projects/Codex/primitive-stream-20261023/capture01
python -B project/experiments/primitive_stream/run.py --capture D:/Projects/Codex/primitive-stream-20261023/capture01 --output D:/Projects/Codex/primitive-stream-20261023/numeric01
python -B project/experiments/primitive_stream/run.py --capture D:/Projects/Codex/primitive-stream-20261023/capture01 --output D:/Projects/Codex/primitive-stream-20261023/numeric02
python -B project/experiments/primitive_stream/audit.py --capture D:/Projects/Codex/primitive-stream-20261023/capture01 --numeric D:/Projects/Codex/primitive-stream-20261023/numeric01 --repeat D:/Projects/Codex/primitive-stream-20261023/numeric02 --output D:/Projects/Codex/primitive-stream-20261023/audit01.json
```

正式执行要求干净、逐文件commit绑定，拒绝覆盖输出；开发加--development，不作正式证据。
捕获器仅观察post norm/RoPE和eager输出，不修改模型算术。固定原模型/分词器SHA与框架源码SHA。
校准只用calibration；g由该KV组全部query头共同决定，评价不重拟合K/V scale或g。
Q exponent/M/r按当前行离线浮点编译，明确未实现在线整数前端。矩阵dot/score RQ/LUT/P15/PV/RNE是整数参考，
浮点norm/RoPE/转换辅助仍在边界外；没有全量化模型、语言质量、真实INT8速度或硬件能力结论。

canonical full捕获按相同输入逐token/分块重放，检验整数输出与KV不可变性；实际full/cached源差异单列。
独立Fraction oracle不调用目标整数内核；P15×V8、wide RQ、恢复除法等计数继承C1，不能按单周期8位MAC处理。
cache.py只是软件epoch/顺序契约，不证明DMA、gather/scatter、物理广播、异步事件队列或RTL无死锁。
