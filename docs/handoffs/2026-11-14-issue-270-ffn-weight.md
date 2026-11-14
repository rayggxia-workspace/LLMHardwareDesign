# #270 FFN 权重供数实验交接

2026-11-14（Asia/Shanghai）。Melodydt。[Issue #270](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/270) · [草稿 PR #272](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/272)。任务分支 `task/270-qwen-rtl-throughput`，本轮基点为 `bbee060feceab03829515713c2b94fecfc47b2eb`，PR 基分支为 `task/234-whole-system-throughput-handoff`。本机为项目资料副本，任务分支由 Melodydt 的 GitHub 连接交付。服务器隔离运行目录使用冻结的代码文件和 SHA-256 清单。

登录 `yuzelu@10.129.166.172`。工作根 `/public/home/yuzelu/Melodydt/runs/issue-270/ffn-weight-05`。TLM 四组在 `tlm` 目录执行下列命令，分区 c64，均为 1 核。退出后结果位于 `tlm/run-<作业号>/`，日志位于 `tlm/slurm-<作业号>.out`。

| 作业 | 节点 | 实际命令 |
| --- | --- | --- |
| 113164 | node9 | `sbatch --parsable --job-name=zny-ffn-dec-b run_ffn_tlm.sbatch decode baseline` |
| 113165 | node12 | `sbatch --parsable --job-name=zny-ffn-dec-c run_ffn_tlm.sbatch decode candidate` |
| 113166 | node12 | `sbatch --parsable --job-name=zny-ffn-pre-b run_ffn_tlm.sbatch prefill baseline` |
| 113167 | node12 | `sbatch --parsable --job-name=zny-ffn-pre-c run_ffn_tlm.sbatch prefill candidate` |

113181 在工作根以 `sbatch --parsable audit_native_ddr.sbatch` 提交，c64/node12、1 核、COMPLETED 0:0。输出 `results/native-ddr-113181.json` 与 `results/native-ddr-113181.sha256` 已核验。113199 在 `native` 目录以 `sbatch --parsable run_native_probe.sbatch` 提交，c64/node1、8 核，构建完成并开始发出握手记录。113195 为前次编译前失败，退码 1:0，日志保留。源清单在 `native/run-113199/source.sha256`，Verilator 输出在 `native/run-113199/replay-113199`。

```bash
cd /public/home/yuzelu/Melodydt/runs/issue-270/ffn-weight-05
squeue -j 112976,112977,113070,113071,113164,113165,113166,113167,113199
sacct -X -j 112976,112977,113070,113071,113164,113165,113166,113167,113181,113195,113199 -o JobID,JobName,Partition,AllocCPUS,State,ExitCode,Elapsed,Nodelist
tail -n 12 tlm/slurm-11316{4,5,6,7}.out native/slurm-113199.out
tail -n 12 native/run-113199/replay-113199/replay-0.log
cat results/{decode-prefix,prefill-rebased,native-ddr-113181}.json
(cd tlm; for j in 113164 113165 113166 113167; do sha256sum -c "run-$j/output.sha256" || exit; done)
python3 -B compare_ffn.py decode tlm/run-113164 tlm/run-113165 > results/decode-full.json
python3 -B compare_ffn.py prefill tlm/run-113166 tlm/run-113167 > results/prefill-full.json
d=native/run-113199/replay-113199
(cd "$d"; sha256sum -c m-weight.sha256; tail -5 verified-proof.log)
for mode in 0 1; do
  python3 -B audit_native_m.py "$d/m-weight-$mode.tsv" "$d/generated/assets.txt" > "results/m-113199-mode-$mode.json"
done
sha256sum results/{decode-full,prefill-full,m-113199-mode-0,m-113199-mode-1}.json
```

- 完整 TLM 判据为四项退出 0:0、582/578 页、每场景 72 个成对 FFN Down 散列一致、DDR/S 流量一致、Decode 退休 token 和跨步 KV 一致。用实际值计算前缀误差。ATT1 112976 的输出已通过散列，两步 Decode 2.609346 tok/s。113070 完成后在 `att1-dot-read-04/tlm` 校验原 `output.sha256`，核对第四轮 Decode 基点并更新证据。
- 原生 113199 的判据为退出 0:0、旧数值与读写审计通过、两模式探针散列校验、每模式三类投影各 44,032 个权重记录且身份与票据闭合。将 P1 尾部事件与其余两路对齐，按实测选择优先优化 bank/DDR 调度或本地 EXEC 交接。
- 负责人 Melodydt。Issue 进行中，PR 草稿，独立审查人待指定。登记 PR #5 待合并，Projects 缺 `config/board.json`，看板及同步待具权限维护者核验。
