# Qwen2.5-3B Decode 快速评估指南

本指南随 `task/265-qwen3b-system-evaluation` 维护。快评用于比较同一部署的 SRAM 位宽和缓存 Decode 区间。它从封存的母控页、局控镜像表和算子描述符重算 SRAM 请求及 ACK 等待，FFN 按三 P 的 WAIT 批次取最长路径。DDR 等剩余时间沿用 128-bit 首步校准，Attention 的剩余时间随上下文缩放。

## 开新会话或任务分支

1. 读取根目录 [AGENTS.md](../../../AGENTS.md)、[现有任务 #265](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/265) 和 [PR #266](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/266)。接续原任务时复用原 Issue。独立实验用自己的 Issue 和工作目录。
2. 在 Git 工作副本中获取评估分支，核对分支头包含本文件。以该提交为起点创建 `task/<自己的 Issue 编号>-<slug>` 和独立 worktree，记录实际起点 SHA。以下编号、分支名和目录均需替换成自己的值。

   ```bash
   git fetch origin task/265-qwen3b-system-evaluation
   base=$(git rev-parse FETCH_HEAD)
   git show "${base}:project/experiments/instruction_cycle/QWEN_DECODE_GUIDE.md"
   git worktree add -b task/ISSUE-SLUG ../llm-ISSUE-SLUG "$base"
   ```

3. 在新目录先跑 `python -B scripts/check_project.py`。使用服务器前阅读 [远程规则](../../../docs/REMOTE_RULES.md)，在本人有权限的目录保存产物。追溯所用代码提交、配置、封存输入、工具版本及结果 SHA-256。提交派生 PR 时核对比较基分支，避免把继承的 #265 内容作为本次变更重复提交。

## 可变参数

| 参数 | 取值和含义 |
| --- | --- |
| `predict --sram-bits` | 可指定一个或多个 `128`、`256`、`512`，默认全选。一个值同时作用于 U、P0/P1/P2 的数据 SRAM 和 PM 装载写口。 |
| `predict --through-step N` | `1–127`，默认 `2`。从封存反馈阶段 1 连续计算到阶段 N。第 i 阶段可见 KV 位置数为 `512 + i`，范围 C513–C639。 |
| `compare --step` | 选择核对阶段 `1` 或 `2`，默认 `2`。此参数用于选取对照窗口。 |

`--through-step` 只改变计算长度。初始 prompt、缓存起点和阶段顺序来自封存部署。单档与多档使用相同的校准；做位宽对比时应取相同的阶段范围。

## 固定条件

- **模型与部署**　Qwen2.5-3B Algo1，batch=1，拓扑 ID 25001，36 层并含完整词表投影。固定母控/局控指令、Block 连接、CALL/WAIT、U 与三路 P 分工、数据布局和描述符。两步参考从 512 个代表性 KV 位置开始，第二步消费第一步选出的 token 与实际新增 KV。
- **SRAM**　同一四 bank 结构、端口数量及应答规则。一个 128-bit 字为 16 B，各位宽每拍分别可装 1、2、4 个对齐字，跨口组拆拍。串行数据路径按两拍 ACK 加一拍接续，PM 和 Embedding 的装载写按两拍计。
- **DDR 与调度**　核周期 `3,334 ps`，双通道 DDR 周期 `630 ps`，每通道 `32 credit`，Attention 的 KV 读窗口 `8`，`pipeline_memory=false`。校准使用 `107947` 的第 1 阶段 291 页，程序验证完整归档的 SHA-256。
- **变更边界**　混合位宽、只加宽单个 Block 或 Attention、改变 bank/端口/ACK、改变频率、DDR 带宽/通道/额度、KV 窗口、算子并发和 SRAM/DMA 流水，都需要对应的模型和同配置对照。PR #260 的 `110382` 是 512-bit 流水配置，有独立 TLM 证据。旧 `107361` 是 128-bit、KV 窗口 1，使用 [单拍评估入口](README.md#qwen25-3b-整机-decode-速度估算)。

## 复跑方法

使用 Python 3.7 或以上版本。已验证本地 3.7.0 和服务器容器 3.10.12。估算使用标准库。若服务器登录 shell 的 `python3` 是 3.6，换用项目容器内的 Python 或本人已验证的环境。

在工作副本根目录运行。例子中的共享路径来自项目封存归档，可替换为有权限的逐字节副本。部署目录需要 `proof.sha256`、`witness.json`、三个 `mother-*.tsv` 表（`pages`、`targets`、`descriptors`）、`runtime-assets.tsv` 和所选阶段的 `phase-N/descriptors.bin`。保留原目录结构与文件字节。

```bash
bench=project/experiments/instruction_cycle
python_bin=python3  # 使用已验证的 Python，也可填解释器的绝对路径。
"$python_bin" --version
archive=/public/home/yuzelu/project-circuit
deployment="$archive/issue234-native-fixed-skip-request-H2gY5uiN/request-runtime-archived"
trace128="$archive/issue260-native-kv-window-jL6neTvA/run-107947/page-timing.jsonl"
trace512="$archive/issue260-native-sram512-SMbOWTw6/run-108284/page-timing.jsonl"
out=$(mktemp -d ./qwen-decode.XXXXXX)

"$python_bin" -B "$bench/estimate_qwen_sram.py" predict "$deployment" "$trace128" \
  --sram-bits 128 256 512 --through-step 2 > "$out/prediction.json"
"$python_bin" -B "$bench/estimate_qwen_sram.py" compare "$out/prediction.json" "$trace128" \
  --sram-bits 128 > "$out/compare-128.json"
"$python_bin" -B "$bench/estimate_qwen_sram.py" compare "$out/prediction.json" "$trace512" \
  --sram-bits 512 > "$out/compare-512.json"
sha256sum "$out/"*.json
```

部署证明的 SHA-256 是 `74078b0b40fdeb73aeae71e3091db3e6a25fc5f27bc03c9981214bfef92b39ef`，校准轨迹是 `422e89d190c43ac567b6e47898ffc38b4f96e4943339b6d177c46a2741e7ece8`。两者由脚本自动核验。计算全部反馈间隔可使用 `--through-step 127`。配套的 [Slurm 入口](run_qwen_sram_estimate.sbatch) 固定运行三个默认位宽和全部 127 阶段，可在服务器已获授权的 Bash 会话中，把分支代码复制到本人运行目录。用自己的作业名前缀提交。

```bash
# RUN_PARENT 使用本人获授权的服务器目录，JOB_NAME 用本人姓名缩写开头。
run=$(mktemp -d "${RUN_PARENT:?}/qwen-sram-estimate.XXXXXX")
cp "$bench/"{estimate_qwen_sram,qwen_request_geometry,qwen_sram_attention,qwen_sram_ffn,qwen_sram_spans}.py "$run/"
cp "$bench/run_qwen_sram_estimate.sbatch" "$run/"
git rev-parse HEAD > "$run/git-commit.txt"
(
  cd "$run" || exit
  sha256sum *.py run_qwen_sram_estimate.sbatch git-commit.txt > source.sha256
  sbatch --parsable --job-name="${JOB_NAME:?}" run_qwen_sram_estimate.sbatch
)
```

在作业完成后执行 `sha256sum -c output.sha256`，并读取 `prediction.json`。完整作业和散列见[作业回执](../../../work/Melodydt/265/qwen-sram-width-estimate-20261114.json)。

比较新的完整 TLM 轨迹时加 `--execution /path/to/execution.json`。比较器核对位宽、非流水标记、部署、缓存起点、实际退休边沿和跨步 KV 计数。它未逐项检查 KV 窗口、DDR credit 或时钟，须从运行命令和封存配置确认。对尚未完成的页前缀可显式用 `--prefix` 检查累计耗时，缺少完整配置证据时吞吐字段为空。256-bit 的复跑命令与产物见[交接](../../../docs/handoffs/2026-11-14-issue-265-qwen-sram-width-model.md)。

## 读结果和判断可用性

`estimates[位宽].phases` 给出每个阶段的 `context_positions`、`duration_ps`、`tok_s` 和 `stage_ps`。汇总吞吐为 `N × 10^12 / Σ duration_ps`。对照误差按 `(估算值 / 参考值 − 1) × 100%`，分别报告吞吐和耗时。单次实验合并不同阶段时应先累加耗时。第二步参考用两个实际 token 退休时刻之差。全部 127 个反馈间隔的口径为第一个生成 token 退休到第 128 个生成 token 退休。

| SRAM | 第二步快评 (tokens/s) | 同配置 TLM (tokens/s) | 吞吐误差 | 参考 |
| --- | ---: | ---: | ---: | --- |
| 128-bit | 1.20668 | 1.20653 | +0.013% | 107947，同宽下一步 |
| 256-bit | 1.72434 | 1.73083 | −0.375% | 111693，封存预测后的独立位宽 |
| 512-bit | 2.07739 | 2.09091 | −0.646% | 108284，未参与校准 |

表中是短窗相对 TLM 的误差。127 阶段的长上下文误差还需同配置的独立退休对照。TLM 复跑的逐页一致性只验证相同模型的复现。Prefill、首 token 延迟、硬件时序及数值验收使用各自的测量口径，正式整机验收见 [#234](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/234)。

[多位宽机器回执](../../../work/Melodydt/265/qwen-sram-width-estimate-20261114.json) · [独立 TLM 复跑回执](../../../work/Melodydt/265/qwen-sram-sweep-20261114.json) · [#265 实验说明](README.md)
