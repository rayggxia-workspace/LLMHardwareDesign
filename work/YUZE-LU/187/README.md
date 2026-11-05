# P16 / J16 实施迭代

[Issue #187](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/187) · 父任务 #184 · 方案 PR #185。

- [000 规格和验收基线](000-baseline.md)
- [001 启动失败与节点运行库](001-host-glibc.md)
- [002 计算节点容器入口](002-node-launcher.md)
- [003 容器输入根](003-input-root.md)
- [004 首轮 RTL 功能](004-rtl-smoke.md)
- [005](005-leaf-views.md)
- [006](006-physical-load.md)
- [007](007-unique-lefs.md)
- [008](008-rtl-contract.md)
- [009](009-aligned-m10.md)
- [010](010-pipelined.md)
- [011](011-obstruction-envelope.md)
- [012](012-packed-lanes.md)
- [013](013-clock-and-reference.md)
- [014](014-access-attribution.md)
- [015](015-net-aware-access.md)
- [016](016-planar-probe.md)
- [017](017-net-aware-m9.md)
- [018](018-reset-rx.md)
- [019](019-grid-study.md)
- [020](020-command-tx.md)
- [021](021-feed-hold.md)
- [022](022-pg-pin-spacing.md)

每轮新增独立 Markdown，记录基线 SHA、目标验收门、失败现象与证据、根因假设、变更范围、命令、输入/工具版本、输出路径与摘要、对比结果及下一步。远程作业加记节点类型、作业号、并行任务数、每任务核数及峰值内存。保留失败记录和通过证据。
