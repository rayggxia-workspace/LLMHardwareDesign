# Block V2 预制底座排布提案

- 日期 2026-11-14（中国标准时间）
- 状态 proposed，待九组联合物理验证
- 任务 [Issue #250](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/250)
- 归档基准 [PR #268](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/268) 合并提交 `7a809d1e8dcda063c66f5ca18e9c186fb23ec668`
- 继承 [0004 叶块与共同底座分阶段冻结](0004-block-library-base-freeze.md)

## 首选试摆

保留 `3P / 2U / 1C / 1F / 2J` 和一套 MC06。P/U/C/F/J 定义局控归属，顶层直接摆放各叶宏、局控、程序 SRAM 和必要适配器。下图表达邻接和出线方向。实际 PHY/封装边界、可用端点、宏朝向和走廊宽度由物理输入决定。

```text
      J0                 MC06                 J1
                  控制分支 → 各组局控

      C0         U0               U1          F0
  ────────────── P↔U 数据走廊 ──────────────────
      P0   ↔     P1       ↔       P2
       共享 DMA 从靠近实际 PHY 的边缘接入
```

1. **三 P 齐平并排。** 优先保住组内 M60、S、G32 的短路径，让组间接点密集的一侧朝数据走廊。为三个 P 的 Mid 交换留连续横向轨道，评估 P0 到 P2 的直达路线。FFN 回放中的 86 个 Mid tile 分属三个 P，Down 从实际 owner 读出并送往三个输入窗口。P 侧 DMA 落点、四个 S bank 和 Dot 供数口应一起定位置。局部 S 对照把 P/U 公共服务从 64 B/拍收窄到 16 B/拍，固定外存条件下模型吞吐由 9.223787 降到 7.595433 token/s。该差值用于给供数路径排序。 [三 P FFN 回放](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/4b66e5859d30bb6285e75e8dc5a7df5e146aa41a/docs/experiments/issue-250-three-p-ffn.md) · [局部 S 位宽对照](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/docs/experiments/issue-250-local-s-width.md)
2. **两个 U 面向三个 P，C 靠 U0。** U0/U1 各留数据和握手出口。双 U 原 SRAM 阶段已覆盖向三个 P 交接概率的真实写 ACK，完整 QK/AV 仍待联合验证。C 邻 U0 对应已有数据链路候选。F 和两个 J 先放外侧，按各产品真实静态网及 I/O 方向复查。 [双 U Attention #254](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/254) · [C/U 映射候选 #256](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/256)
3. **控制从中部分叉，DMA 从边缘进出。** MC06 靠近控制分发分叉，先按现有协议做母控发送的实体分支缓冲和返回路径分配。九组直连初筛的共享网最差电容裕量为 ground 模型 −24.324 fF、isolated 模型 −68.075 fF。共同 CTS、复位、启动/配置和 512 位 DMA 各自按真实端点留资源。DMA 数据、返回槽、写 ACK 和 FENCE 依赖都进入同一物理与功能账，按已选 PHY 位置定边。 [负载初筛](../experiments/assets/five-leaf-bases-v2/evidence/nine-control-load-screen.json)

图册使用 1,438 × 2,145 µm 的 P2545 夹具、1,216 × 984 µm 的 U39 v02 和 2,112 × 1,176 µm 的 C V3。P2545 的 M60 为 1,390 × 1,390 µm，密集接入主要围绕其下方的 S/G 区。夹具外接框、尺寸和图册中的间隙用于初步估算。最终视图须重新核对叶宏合法朝向、M10 端点矩形、信号逃逸、PG 和 OBS。 [五类夹具图](../experiments/assets/five-leaf-bases-v2/blocks-m10.png)

## 预制与后制边界

| 阶段 | 连接和资源 |
| --- | --- |
| 底座冻结前 | M1–M10、via1–via9。固定叶宏和局控/适配器的内部连接、PDN、时钟与复位、跨产品共用的已确认连接。母控分支驱动器和候选组合中继提前落位、供电并导出可用 M10 接点。 |
| 产品后制 | M11/M12、via10/via11。按产品的静态逐位连接选择 M10 落点、走线及已预制的中继，覆盖有方向的数据、命令、握手和必要的组内叶宏旁路。 |
| 协议与布线资源 | 时序按现有握手合同检查。需要插寄存器时回到底座设计并重验延迟、背压和 ACK/FENCE。每颗产品的每条不同物理网占轨，只有同一物理网可按现有协议分时复用。不同产品分别在同一底座试布。 |

## 对照和冻结判据

- **基准**采用更新后的同一套物理输入，在图册邻接关系下试摆。**方案 A** 为三 P 齐平。**方案 B** 将中间 P 向 U 侧错列，初扫可从约半个 P 横向节距的位移量开始，之后按合法位置调整。B 用来检验 P1 附近的出口分散收益能否抵消 P↔P 的绕行以及 P↔U 走廊变窄的代价。A/B 保持相同资源、PHY 假设、外存 51.2 GB/s、TT 300 MHz、产品映射与布线规则。
- 先做真实逐位绑定。优先补正式 S_P 版 P 的端点与物理视图。P2545 的现有回执覆盖 S_base 窄口子集，实时启动、K-window、完整邻 P 和最后 86 个 M FENCE 接点待补。J03 两路各 128 位外读仍位于 M6，若产品依赖该接口，需在冻结前补真实 M10 落点或冻结经验证的固定路径。
- 每产品取静态网并集。先核对逐位端点、驱动及握手，再看最紧截面上的线轨需求/可用量、合法 via10 接入数、走廊峰值和失败网。计入间距、过孔规则、PG/OBS 和中继占用。保留 FFN 与 Attention 实际发包和 ACK 回放，另用不同算子图或合法映射检验底座的复用性。
- 路由后比较实际线长、via 数、实际中继用量、面积及全量电气。冻结门包括实际几何读回及连通性、预制层保持、共同 PG/CTS、RC 提取后的 TT 300 MHz setup/hold/cap/slew/fanout，以及最终网表的控制和数据回放。优先选择所有目标产品均闭合的方案，再比较最差拥塞、时序余量和面积。

## 相关文件与证据

| 用途 | 文件或记录 |
| --- | --- |
| 五类源码入口及绑定 | [Block V2 RTL](../../project/rtl/block_v2/README.md) · [按组的输入、路径和 SHA-256](../../project/rtl/block_v2/source-manifest.json) |
| 独立叶宏及组级物理视图 | [五类图册与独立回执](../experiments/assets/five-leaf-bases-v2/README.md) · [独立叶宏图](../experiments/assets/five-leaf-bases-v2/leaf-macros-m10.png) · [九组图](../experiments/assets/five-leaf-bases-v2/nine-placement.png) · [原始 DEF/LEF 索引](../experiments/assets/five-leaf-bases-v2/placement-source.json) |
| P 与 J 接点缺口 | [P2545](../experiments/assets/five-leaf-bases-v2/evidence/p2545.json) · [J03](../experiments/assets/five-leaf-bases-v2/evidence/j03.json) · [S_base 与 S_P 几何及引脚](../experiments/assets/compact-local-s/index.html) |
| 布线入口及可复验范围 | [逐位端点合同 #226](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/226) · [历史九组物理回归 #231](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/231) · [两层布线方案 #258](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/258) · [实际 M10 接入与中继回归 #259](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/259) |

本提案基于归档资料和已公开的回执。新的顶层坐标、通道宽度、中继数量、联合布线和系统签核均待实测。历史 #231 的 690 条晚接网和 #259 的独立接入、中继实验分别保留原范围。
