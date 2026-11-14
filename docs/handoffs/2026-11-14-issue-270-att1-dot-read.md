# #270 ATT1 双窗口回填与 Dot 读出交接

2026-11-14（Asia/Shanghai）。Melodydt。[Issue #270](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/270) · [草稿 PR #272](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/272)。分支 `task/270-qwen-rtl-throughput`，起点 `c2d14050c66d3e479952ae9b88a4c30bf6f33ccb`。

原生 113104/113105 在 c64/node1 均退出 0:0。逐字读回一致。两步 Decode 113070、两位置短 Prefill 113071 在 `/public/home/yuzelu/Melodydt/runs/issue-270/att1-dot-read-04/tlm` 持久运行，基线 112976/112977 仍在第三轮目录。前四层外推 2.739536 tok/s / 5.504623 输入 tok/s。按[第四轮回执](../../work/Melodydt/270/dot-read-04/README.md)追踪、核对 582/578 页、退休 token 和跨步 KV，再报完整吞吐与外推误差。接续人 Melodydt。

原生候选在同分片下两工况均改善。与第三轮大分片相比存在背压退化，保留对应工况。新增共享端口故障注入、整机 P512/D128 和物理 STA 待执行。项目登记 PR #5 待合并，Projects 由具权限维护者核验同步。
