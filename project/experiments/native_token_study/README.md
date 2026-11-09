# Issue247：新版 P 与整模型 token/s 的接口核验

关联 [Issue247](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/247)、[PR243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)。

冻结的旧整模型条件仿真使用 S32 输入、96 位累加和理想 1R1W；当前原生 P 只接受 S8/S16，段和 S40、累加 S64，且四个 1RW bank 总服务上限为 64B/cycle。两者不能通过替换一个计算常数互相等同。

`run_legacy.py` 首先在服务器 Slurm 分配中重跑旧 SystemC 模型，要求四个完整 RESULT 对象与 run05 完全相等。输入、旧依赖、参考结果和部署源码均校验 SHA-256。此阶段只证明历史条件结果可重现，不证明新版原生 RTL 的端到端吞吐。

```bash
python3 -B project/experiments/native_token_study/run_legacy.py --root /path/to/allocated/run
```

原生兼容性检查、付费格式转换及有限存储的条件对照正在实施；尚未执行的测试与尚未实现的接口不能标为通过。仿真沿用 300MHz 条件频率、2P/1U 和 17.1GB/s 带宽，不代表新的物理时序验收。
