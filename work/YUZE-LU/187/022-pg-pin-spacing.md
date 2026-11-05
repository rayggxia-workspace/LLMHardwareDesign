# 022 · 避开 M10 父层电源条带

- 019 的 J 传统 DRT 第 10 轮标记 22 个，其中 13 个是信号与 VSS 短路，9 个是间距。原始报告在 `019-grid-study/pnr/guide/J/flow/reports/nangate45/block_j16/base/5_route_drc.rpt-10.rpt`。实例宏 GDS 保持原样。
- 标记的条带边缘与父层 DEF 的实际金属宽度吻合。父层 M10 VDD/VSS 交替中心每 30 µm。最近的信号落点和 PG 条带中心距约 1.045 µm。改在放置 M10 信号 pin 时按实际 core snapped origin 与 5 µm PDN offset 计算，中心距离至少 4 µm。外露信号继续保持 2×2 µm 与既有后制网格相位。
- 代码 `b44fb6f90`，`022-pg-pin-spacing/overlay.sha256` 记录输入。P/J 作业 97515 同一 c96 两个 12 核步骤。后继 97516 以八个 12 核独立验收步骤提交，只有 P&R 成功才启动。