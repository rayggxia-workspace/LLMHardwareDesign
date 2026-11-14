# Issue #270 ATT1 首轮短程仿真

2026-11-14（Asia/Shanghai）。负责人 Melodydt。[Issue #270](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/270) / [草稿 PR #272](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/272)。任务分支 `task/270-qwen-rtl-throughput`，实验材料提交 `6dc853fd138ef52f6e1fb609d07a5e171b026919`，原始 PR #260 基点 `55620f173f2ad540efade8a552c35e9dba0f43c0`。Windows 管理参考目录另有同一组本地实验文件。服务器登录 `yuzelu@10.129.166.172`，独立目录 `/public/home/yuzelu/Melodydt/runs/issue-270/att1-selected-01`。

原生基线 112602 与候选 112603 已在 c64/node1、8 核完成，0:0。封存 S128/MC/LC 和 C380 样本，两种工况逐字通过。正常周期 227,431→163,454，背压周期 436,458→371,268，KV 回包 15,200→9,120。源、输入、工具、输出散列及失败重试见 [实验回执](../../work/Melodydt/270/README.md)。本地 `python scripts/check_project.py` 和补丁解析通过，物理 STA 及正式 P512/D128 未执行。

112559 Decode 在 c64/node2 单核运行，112560 Prefill 在 c64/node1 单核运行。回执读回时分别完成 134/582 与 190/578 页。两项前四层估计分别为 2.455394 tok/s 与 5.507167 输入 tok/s，完整短程吞吐待审计。每次继续时用完整页数、Slurm 退出码和散列确认。

```bash
cd /public/home/yuzelu/Melodydt/runs/issue-270/att1-selected-01/tlm
squeue -j 112559,112560
sacct -X -j 112559,112560 -o JobID,JobName,Partition,AllocCPUS,NodeList,State,ExitCode
tail -n 10 slurm-112559.out slurm-112560.out
for job in 112559 112560; do
  sha256sum -c "run-$job/output.sha256"
  cat "run-$job/timing-audit.json"
done
reference=/public/home/yuzelu/project-circuit/issue260-sram-pipeline-qk3uTFl1
python3 -B ../compare_att1_selected.py decode "$reference/run-110382" run-112559
python3 -B ../compare_att1_selected.py prefill "$reference/run-110383" run-112560
```

恢复第一步由 Melodydt 读回两项终态，核对 582/578 页、DDR 回调、两次退休 token 和跨步 KV，并报告候选完整吞吐及前缀误差。ATT1 后续工作沿用同一测试口径，分离 DDR 回包额度和 S 写 ACK，再评估读出与回填重叠。登记 PR #5 待合并，Projects 配置缺失，具权限维护者待核验和同步。
