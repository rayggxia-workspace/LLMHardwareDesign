# 七模型 SystemC / RTL 基准

对应 [Issue #197](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/197)。运行结果和统计口径见[报告](../../../docs/experiments/issue-197-seven-model-system-bench.md)。

## 输入与口径

| 实验 | 固定 Git 来源 | 输入与执行 |
| --- | --- | --- |
| 七模型 SystemC 整模型回放 | PR #154 `5bc9d4b58ca46101ec4c377de0fc5700ae06539a` | 历史七个短序列文本检查点。重新编译原 `llm_cd/run.py` 并执行完整模型，核验检查点 SHA、hidden/logits 的字节一致性、C/D 计数及逻辑流。 |
| 七模型投影 | SystemC 同上，RTL M 为 main `27eaaace1bc03cb4422954d1be343de556b757e3` | 每模型取第一个 token 的最终 norm 激活，取词表投影前八行，覆盖完整 K。用四种 A×B 整数位宽生成同一套 SystemC 和 RTL 输入。 |
| DMA 时钟和信用扫描 | PR #182 `24e20d13a71cf65f721a182451308f1ad01ebaec` | 原 RTL、有限外存模型及独立 oracle。五种时钟/相位和四种在途信用。 |
| 七宏控制顶层 | PR #168 `4f1a383049de5efa472f020e352c86be8c308614` | 原控制顶层 `--verify-only`，三个初态/种子。 |

投影输入来自冻结的 S16 检查点。各行或向量重新选择二进制尺度，最近偶数舍入。误差以冻结输入解码后的点积为参考，截在模型特定 logits 缩放之前。SystemC 和 RTL 各自对照同一个独立整数 oracle，完整读回 S64。RTL 逐周期计数覆盖从首笔操作数进入到最后读响应握手。执行命令周期包括启动与等待，预取重叠周期按另一银行的实际握手计算。A、B、响应数据线在上升沿各采样一次，时钟、控制线和内部节点另需仪表化。

## 准备任务目录

在服务器个人任务根目录下用新目录进行每次运行，以下 `ROOT`、`DMA`、`SCPROJ` 分别是整模型/RTL 主目录、DMA 目录、SystemC 投影目录。路径必须位于当前成员获准的根目录。冻结输入和软件路径均只读。使用 c64、SystemC 3.0.1、GCC 8.5 与容器内 Verilator 5.042。每个目录放对应的批处理脚本，上传前对输入文件写同名 manifest，上传后执行 `sha256sum -c`。此次使用的 manifest 和 Slurm 回执见[证据](../../../work/huangpingyang04-lgtm/197/README.md)。

| 目录 | 归档及文件 |
| --- | --- |
| `ROOT` | `systemc-source.tar` 由 PR #154 的 `project/systemc/` 排除各 `results/` 子树后生成。将同一提交的 `project/systemc/llm_cd/results/seven-cd-03/suite-final.json` 另存为 `frozen-systemc.json`。与 `run_systemc.py`、`systemc.sbatch` 一起纳入 `systemc-upload.sha256`。 |
| `ROOT` | 从固定 main 取 `project/rtl/block_v2/block_v2_m.sv`。与 `prepare_projection.py`、`projection.cpp`、`projection.sbatch` 纳入 `projection-upload.sha256`。 |
| `DMA` | `dma-source.tar` 按原目录打包 PR #182 的 `project/rtl/hbm_feed/hbm_{async_fifo,group_dma}.sv`、`project/rtl/block_feed_v1/`、`project/rtl/block_v2/block_v2_m.sv`、`project/experiments/hbm_feed/{hbm_dma_system.sv,hbm_s_pool.sv,test_dma.cpp}`。归档和 `dma.sbatch` 纳入 `dma-upload.sha256`。 |
| `ROOT` | `control-source.tar` 按原目录打包 PR #168 的 `project/rtl/{control_v1,block_feed_v1,block_v2,r_local_state}/`、`project/rtl/block_v1/transaction6k.sv` 和 `project/experiments/control_v1/{run.py,test_system.cpp,BUF_X16.v,native_r_lint.vlt,native_t_lint.vlt}`。归档和 `control.sbatch` 纳入 `control-upload.sha256`。 |
| `SCPROJ` | `systemc_projection.cpp`、`systemc_projection.sbatch` 纳入 `sc-projection-upload.sha256`。编译时开启 SystemC 3.0.1 的旧 API 兼容宏，复用冻结的宏头文件。 |
| `ROOT` | `summarize.py`、`summarize.sbatch` 纳入 `summary-upload.sha256`。 |

保留 Git 归档中的原相对路径。将 `INPUTS` 指向授权的 Issue #153 检查点根目录。该目录还包含 `cd-full-20261102-03/run-*/stage-final-post-norm.bin`，用于启动短投影，并在汇总时与本次新整模型激活逐字节交叉核验。 `SYSTEMC` 指向已安装的 SystemC 前缀。

```bash
sbatch --parsable --output="$ROOT/systemc-%j.log" "$ROOT/systemc.sbatch" "$ROOT" "$INPUTS" "$SYSTEMC"
sbatch --parsable --output="$ROOT/projection-%j.log" "$ROOT/projection.sbatch" "$ROOT" "$INPUTS"
sbatch --parsable --output="$DMA/dma-%j.log" "$DMA/dma.sbatch" "$DMA"
sbatch --parsable --output="$ROOT/control-%j.log" "$ROOT/control.sbatch" "$ROOT"
```

SystemC 作业完成源解包且 RTL 投影生成全部输入后，运行：

```bash
sbatch --parsable --output="$SCPROJ/sc-projection-%j.log" \
    "$SCPROJ/systemc_projection.sbatch" "$SCPROJ" "$SYSTEMC" "$ROOT"
```

全部业务作业完成后，传入各实际作业号的逗号分隔清单：

```bash
sbatch --parsable --output="$ROOT/summary-%j.log" \
    "$ROOT/summarize.sbatch" "$ROOT" "$DMA" "$SCPROJ" "$JOB_IDS"
```

汇总脚本复核所有投影、DMA 和 SystemC 投影回执，核对各模型的操作数与输出，并按 `flow-events.jsonl` 拆分 prefill/decode。prefill 包含最后一个 prompt token，decode 统计其后实际送入模型的位置。服务器保留原始张量、trace、日志及二进制，Git 只提交轻量回执。


## 序列长度扩展

[长度扩展报告](../../../docs/experiments/issue-197-long-systemc.md)和[RTL 缺项](../../../docs/experiments/issue-197-full-model-rtl-gaps.md)。复用已核验的短序列任务目录 `SHORT`，其中有固定 #154 的 `systemc-source.tar`、`systemc-upload.sha256`、`frozen-systemc.json`、原源码及短运行器。创建两个新的个人任务目录 `LONG` 和 `BUILD`。使用已有可离线加载原检查点的 PyTorch/Transformers Python `REFPY`，缓存和临时文件由脚本限制在新任务目录。

- `LONG` 放 `long_reference.sbatch`、`long_replay.sbatch`、`long_metrics.py`、`long_equivalence.sbatch`、`long_collect.sbatch`。分别按实际上传字节生成 `reference-upload.sha256`（参考脚本）、`replay-upload.sha256`（回放脚本和指标脚本）、`equivalence-upload.sha256`（短对照脚本）、`collect-upload.sha256`（汇总脚本）。
- `BUILD` 放 `instrument_long.py` 和 `long_build.sbatch`，生成 `build-upload.sha256`。构建脚本从旧归档复用冻结源，只给 C/D 实验副本加只读计数。两个旧 C/D 自测试仍执行。

```bash
sbatch --parsable --output="$LONG/ref-%A_%a.log" "$LONG/long_reference.sbatch" "$LONG" "$SHORT" "$REFPY"
sbatch --parsable --output="$BUILD/long-build-%j.log" "$BUILD/long_build.sbatch" "$BUILD" "$SHORT" "$SYSTEMC"
```

参考数组和构建成功后，设置 `REF_JOB` 为参考数组编号并提交：

```bash
sbatch --parsable --export=ALL,REFERENCE_JOB_ARRAY="$REF_JOB" --output="$LONG/sc-%A_%a.log" "$LONG/long_replay.sbatch" "$LONG" "$BUILD" "$REFPY"
sbatch --parsable --output="$LONG/eq-%j.log" "$LONG/long_equivalence.sbatch" "$LONG" "$SHORT" "$BUILD"
```

所有回放和短对照完成后，用实际作业号的逗号列表 `JOB_IDS` 收集证据。

```bash
sbatch --parsable --output="$LONG/collect-%j.log" "$LONG/long_collect.sbatch" "$LONG" "$BUILD" "$JOB_IDS"
```

数值门未通过时保留原失败和误差。运行覆盖完整、参考已对照、流量已对账分别核验。汇总收录每个 token 的参考/实际下一 token、逐步误差、KV/R 和搬运统计，以及完整原始参考和运行输出的 SHA-256。


## C/D 暂存流量及能耗复算

在计算节点上用 `audit_cd_traffic.py LONG long-systemc-results.json` 读取七模型的已完成轨迹。输出定向到新任务目录，保留 `sha256sum` 和 Slurm 终态。`estimate_energy.py` 读取已提交的冻结回执和新审计结果，换算算术和 SRAM 能量并将 DDR/HBM 标记为待测。见[接口与能耗报告](../../../docs/experiments/issue-197-seven-model-energy-estimate.md#外存访问核对)。
