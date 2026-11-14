# #270 FFN 最慢一路和 WAIT 对账交接

2026-11-14（Asia/Shanghai）。Melodydt。[Issue #270](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/270) · [草稿 PR #272](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/272)。任务分支 `task/270-qwen-rtl-throughput`，本轮基点 `a7ff9e5b06405f518300bc90e18490635b854e62`，PR 基分支 `task/234-whole-system-throughput-handoff`。本机是项目管理资料副本，在线任务分支和隔离服务器目录保存本轮成果。后续优化仍用相同短负载。**每完成一步，报告当时的两项速度、验证范围和之后的全部剩余步骤。**

服务器为 `yuzelu@10.129.166.172`，主目录 `/public/home/yuzelu/Melodydt/runs/issue-270/ffn-wait-06`。113287 `zny-ffn-wait` 以 `sbatch --parsable run_ffn_wait.sbatch` 提交，c64/node1、8 核。源码及输入 SHA 在 `run-113287/source.sha256`，结果在 `run-113287/replay-113287/`，日志为 `slurm-113287.out`。113287 与前序 113199 均已完成 0:0。两个工况的母控 WAIT、局控与 M 端全部对账，文件散列通过。FFN 短 Prefill 113166/113167 完成且对账，Decode baseline 113164 完成，候选 113165 在 FFN 第一轮目录。

```bash
cd /public/home/yuzelu/Melodydt/runs/issue-270/ffn-wait-06
squeue -j 113165,113287
sacct -X -j 113164,113165,113166,113167,113199,113287 -o JobID,JobName,Partition,AllocCPUS,State,ExitCode,Elapsed,Nodelist
tail -f slurm-113287.out
d=run-113287/replay-113287
(cd "$d"; sha256sum -c ffn-wait.sha256; tail -5 verified-proof.log)
for mode in 0 1; do
  python3 -B audit_ffn_wait.py "$d/ffn-wait-$mode.log" "$d/generated/assets.txt" > "results/mode-$mode.json"
done
ffn=/public/home/yuzelu/Melodydt/runs/issue-270/ffn-weight-05
(cd "$ffn/tlm"; for j in 113164 113165; do sha256sum -c "run-$j/output.sha256" || exit; done)
PYTHONPATH="$ffn" python3 -B "$ffn/compare_ffn.py" decode "$ffn/tlm/run-113164" "$ffn/tlm/run-113165" > results/decode-full.json
sha256sum results/{decode-full,prefill-full,mode-0,mode-1}.json
```

留下的工作按下列顺序执行。

1. 收齐 113165。Decode 核对 582 页、两次退休、跨步 KV、72 个 Down 散列和 DDR/SRAM 流量，报告完整吞吐和外推误差。
2. 用固定输入单独 A/B 局控的配对准备与 EXEC 交接。保留有界 credit、标签、A 读取证明、M result 到 S ACK 和取消排空。对照正常、背压、取消发生在 EXEC 前/中、迟到回包。RTL 和同机制 TLM 通过后，按第一轮口径报两项最新吞吐。
3. 对 `HEAD16` 分离权重、计算、输出读回、argmax、退休，依次试已有权重预取和输出重叠，每项对照全部 151,936 列及退休 token。
4. 根据新时间分布决定是否把供数推广到 QKV/O。完成 ATT1 共享端口错误 ACK、背压/排空和分片取舍。
5. 冻结组合做完整短程、原生联合和 300 MHz 面积/时序回归，核对组合共享 DDR/SRAM 争用及收益。
6. 通过 PR #272 向 #234 交付冻结配置、功能与吞吐回执。#234 正式验收 B1/P512/D128、自生成 KV、连续反馈、数值、TTFT、127 个 Decode 间隔及能效。

规则 `rayggxia-project-collab 1.0.0`，项目 `llm-hardware-design`。Melodydt 接续，独立审查人待指定。#270 保持进行中，PR 草稿。登记 PR #5 待合并，Projects 缺 `config/board.json`，看板和同步由具权限维护者核验。
