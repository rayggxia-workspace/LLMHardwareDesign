# #270 ATT1 多块回填交接

2026-11-14（Asia/Shanghai）。负责人 Melodydt。[Issue #270](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/270) · [草稿 PR #272](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/272)。分支 `task/270-qwen-rtl-throughput`，本轮基点 `af29d7a5199095d63d3411245bb0e79ebb7366a0`。

原生 112990/112991、故障排空 113009 均通过。两步 Decode 112976、两位置短 Prefill 112977 在 `/public/home/yuzelu/Melodydt/runs/issue-270/att1-refill-03/tlm-final` 持久运行。前四层外推 2.609134 tok/s / 5.502848 输入 tok/s。接续先按[第三轮回执](../../work/Melodydt/270/refill-03/README.md)的命令核对终态、582/578 页、散列、两次退休和跨步 KV，再补完整吞吐及前缀误差。下一项为固定单 SRAM 端口和容量测回填/S→Dot 读出重叠。完整 P512/D128 和物理 STA 待执行。看板配置缺失，具权限维护者待核验，登记 PR #5 待合并。
