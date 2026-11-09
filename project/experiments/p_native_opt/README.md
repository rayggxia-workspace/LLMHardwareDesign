# 原生P前三项优化回归

关联Issue247/PR243。[设计、具体做法与实测结果](../../../docs/experiments/issue-247-p-native-optimizations.md)；[原件/SHA](../../../work/Melodydt/247/native-p/README.md)。

三项可选生产源位于`project/rtl`；P参数`S_CONSUMER_PRIORITY`、`S_BANK_RW`默认0，`M_CONTEXTS`默认0，可选1/2/8。固定四个256×128单端口bank，数据S16KiB。该目录提供实际RTL回归，不是性能模型或部署好的LLM。

在获授权服务器Slurm/container内，完整执行：

```sh
python3 source/project/experiments/p_native_opt/run.py \
  --repo source --out results --manifest inputs.json --workers 4 --components all
```

`inputs.json`包含已上传40位source_commit、精确code_sha256、components；每个源码与固定bank都先校验。`--components integration`只运行local S及完整P；`--components memory`仅local S；manifest必须匹配，不能将部分通过冒称四组件全通过。输出目录须新建，日志和`result.json`持久保存；子组件失败继续收集其余组件，但主作业仍失败。

`job.sh`为4核、UNLIMITED、`mdt-p-native`的Slurm入口，使用固定容器与Verilator5.042。提交前准备`source/`、`source-files.sha256`、`input-files.sha256`和`inputs.json`；源码包在SHA校验后解包。默认执行all；`sbatch --export=ALL,POPT_COMPONENTS=integration job.sh`选择补验。提交后立即读回作业号、节点与日志，详情见证据入口；不在Windows本地或服务器登录节点执行EDA。

具体单项：[仲裁](policy-implementation.md)、[SRAM](memory-implementation.md)、[M上下文](context-implementation.md)。`generate_m_context.py`锁定原M与test_m，并产生候选；运行器要求生成候选与正式RTL字节相同。原算法/scale/RNE保持，额外metadata325bit；物理成本仍待验。

run10四组件通过；run11针对无背压、B-only边界、完整context释放计时补验通过。不能复用run10旧P前缀周期当作含释放性能；最终数值见正式报告。未来更改生产源后必须重新编译验证，新结果不能继承旧物理资格。
