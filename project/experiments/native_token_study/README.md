# Issue247：新版 P 与整模型 token/s 的接口核验

关联 [Issue247](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/247)、[PR243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)。

冻结的旧整模型条件仿真使用 S32 输入、96 位累加和理想 1R1W；当前原生 P 只接受 S8/S16，段和 S40、累加 S64，且四个 1RW bank 总服务上限为 64B/cycle。两者不能通过替换一个计算常数互相等同。

`run_legacy.py` 首先在服务器 Slurm 分配中重跑旧 SystemC 模型，要求四个完整 RESULT 对象与 run05 完全相等。输入、旧依赖、参考结果和部署源码均校验 SHA-256。此阶段只证明历史条件结果可重现，不证明新版原生 RTL 的端到端吞吐。

```bash
python3 -B project/experiments/native_token_study/run_legacy.py --root /path/to/allocated/run
```

`calibration/run_calibration.py` 在实际 P/SRAM RTL 上校准三行 S16、宽窄 B、K 尾块、scale、八组上下文、读回/写 ACK/释放。run13 六次运行全部通过。`run.py` 先严格拒绝四份原始 trace 的原生准入，再执行独立整数 oracle、用实际模型头文件对比 RTL 回执，最后运行九个完整图条件场景并独立审计工作和存储。

```bash
# 均在本人独立 Slurm 分配、固定容器、新 run 目录中；先核验部署 manifest。
python3 -B source/project/experiments/native_token_study/calibration/run_calibration.py \
 --repo source --out results --manifest inputs.json --workers 4
python3 -B source/project/experiments/native_token_study/run.py --root "$PWD"
# 只读结果分析，可在本地执行；不重新仿真。
python -B project/experiments/native_token_study/analyse_results.py \
 --result /path/run14/receipts/results/result.json \
 --legacy /path/run12/receipts/results/result.json --out NEW_ANALYSIS_DIRECTORY
python -B work/Melodydt/247/token-throughput/verify.py
```

输出路径必须新建，不能覆盖既有实验。`job_legacy.sh`、`job_calibration.sh`、`job.sh` 都使用四核 Slurm；第三项需要包内 `run13-result.json` 的精确 SHA 及一致的生产 RTL/校准 helper。工具为容器中的 GCC11.4、SystemC3.0.2、Verilator5.042；真实工具哈希见各次回执。

条件对照沿用 300MHz、2P/1U、17.1GB/s 和每 P16KiB S。`contract.json` 明确每 P 额外2712B未实装适配器寄存器；原生既有结果RF512B另列。S32无损三limb、S96有限合并、128bit实际费用、K32、最终RNE和释放全部收费；U仍是冻结候选模型。串行P程序不宣称消费者优先或bank并发整网收益，LOAD跨入口额外一拍是保守调度选择。没有真实权重生成或物理频率资格。[报告](../../../docs/experiments/issue-247-native-token-throughput.md)与[证据](../../../work/Melodydt/247/token-throughput/README.md)区分原生、条件与历史结果。
