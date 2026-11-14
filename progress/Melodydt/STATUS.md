# Melodydt 的进度

## 2026-11-14（Asia/Shanghai）Qwen2.5-3B ATT1 存储流水

- [Issue #270](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/270) 由 Melodydt 在 [task/270-qwen-rtl-throughput](https://github.com/rayggxia-workspace/LLMHardwareDesign/tree/task/270-qwen-rtl-throughput) 推进，通过 [草稿 PR #272](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/272) 交付，叠加在 [PR #260](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/260) 的 `55620f17`。首轮实现 AV 每行只取所需 V beat，并减少 RTL 的逐行控制交接。
- C380 Verilator 原生对照 112602/112603 均完成 0:0。两模式数值与参考逐字相符，KV 回包 15,200→9,120，正常/背压周期分别下降 28.13%/14.94%。项目管理检查通过，300 MHz 物理验收未执行。
- 512-bit 基础流水下，前四层外推两步 Decode 2.455394 tok/s，短 Prefill 5.507167 输入 tok/s。112559/112560 仍在 `/public/home/yuzelu/Melodydt/runs/issue-270/att1-selected-01/tlm` 保存全过程。下一步读回完整审计和散列，对照预测误差，随后做 ATT1 回填/读出流水。复现及追踪见 [#270 ATT1 回执](../../work/Melodydt/270/README.md)。
- 任务处于进行中，独立审查人待指定。项目登记 PR #5 待合并，Projects 配置缺失，条目和同步待具权限维护者核验。
