# Issue162 已验收单块结果

**本表保留的是新版 S 重做之前的合格单块基线。** 用户已选择在 S 内补驱动并重新验收其版图；本表中的原 S、309 个 Link8 和 335 实例计数不属于新版 S 的最终交付。新版 S 原始P&R已完成，局部M10修复已使完整native DRC归零，新鲜最终RC/LEC仍在执行；全部独立原生门、固定 PG、六文件及新组合接入均须重新验收，不继承本表资格。最新执行证据见 [Checkpoint21](../work/YUZE-LU/162/continuation-checkpoint-21.md)，边界决定见 [S 内部驱动决策](decisions/2026-11-02-issue162-s-internal-drive.md)。其他五宏及原 S 交付保留。

本清单来自实际固定PG交付回执，21类单块均完成原生最终布局布线/300MHz/完整DRC/最终单元功能/严格等价，以及独立固定PG连通、完整DRC、新鲜RC/300MHz、实际六文件和版图。原M/N/E/G/S/T RTL及原合格文件保留；固定PG封装为独立输出。S/T使用标准单元存储，不称SRAM宏。

**这是单块交付。旧335实例组合尚未通过完整实际M11/M12、三角点RC/300MHz及联合验收。** 表中setup/hold是该单块的固定PG结果，不是跨块时序。实例数对应旧335实例参考组合；新版 S 接入后的实际图另行计数和验证。R保留、由正在修改它的任务负责，适配接入尚未完成。

[六文件路径/字节数/SHA及源绑定索引](../work/YUZE-LU/162/block-delivery-11/index.json)列出每块V/SDC/DEF/ODB/SPEF/GDS、原交付源、PG物理和新鲜时序回执；大文件在获授权远程项目目录。以下版图为实际交付PNG逐字节复制，每张已核对交付image_sha256，没有重绘或裁剪。详细资格链与历史失败见[Checkpoint10](../work/YUZE-LU/162/continuation-checkpoint-10.md)，后续组合证据见[Checkpoint11](../work/YUZE-LU/162/continuation-checkpoint-11.md)。

| 物理块 | 功能 | 声明实例数 | 固定die（µm） | 活动单元面积（µm²） | setup / hold裕量（ns） | 实际版图 |
|---|---|---:|---:|---:|---:|---|
| block_v2_m | M矩阵计算 | 1 | 930×930 | 304,530.90 | 0.039857 / 0.018500 | [图](../work/YUZE-LU/162/block-delivery-11/layouts/block_v2_m.png) |
| block_v2_n | N归约/归一化/统计 | 1 | 510×510 | 68,015.67 | 0.140712 / 0.017753 | [图](../work/YUZE-LU/162/block-delivery-11/layouts/block_v2_n.png) |
| block_v2_e | E逐元素/格式 | 1 | 600×600 | 63,751.69 | 0.412125 / 0.019608 | [图](../work/YUZE-LU/162/block-delivery-11/layouts/block_v2_e.png) |
| block_v2_g | G函数计算 | 1 | 400×400 | 22,831.05 | 0.512034 / 0.017721 | [图](../work/YUZE-LU/162/block-delivery-11/layouts/block_v2_g.png) |
| block_feed_s_macro | S16KiB标准单元工作存储与feeder | 1 | 1680×1680 | 1,181,315.84 | 0.028545 / 0.007200 | [图](../work/YUZE-LU/162/block-delivery-11/layouts/block_feed_s_macro.png) |
| transaction6k | T6KiB结果交接 | 1 | 1040×1040 | 431,244.79 | 0.429092 / 0.007988 | [图](../work/YUZE-LU/162/block-delivery-11/layouts/transaction6k.png) |
| control_c | 可编程C | 1 | 740×740 | 209,902.20 | 0.340552 / 0.000705 | [图](../work/YUZE-LU/162/block-delivery-11/layouts/control_c.png) |
| control_d | 有限DMA搬运D | 1 | 1170×1170 | 123,455.12 | 0.058717 / 0.008420 | [图](../work/YUZE-LU/162/block-delivery-11/layouts/control_d.png) |
| control_endpoint_queue | 任务/完成队列 | 7 | 470×470 | 12,159.66 | 1.564079 / 0.000901 | [图](../work/YUZE-LU/162/block-delivery-11/layouts/control_endpoint_queue.png) |
| control_axil_bridge | AXI-Lite配置桥 | 1 | 400×400 | 3,254.51 | 1.255634 / 0.008345 | [图](../work/YUZE-LU/162/block-delivery-11/layouts/control_axil_bridge.png) |
| control_adapter_m | M块旁适配器 | 1 | 770×770 | 10,567.91 | 1.357095 / 0.005789 | [图](../work/YUZE-LU/162/block-delivery-11/layouts/control_adapter_m.png) |
| control_adapter_n | N块旁适配器 | 1 | 1110×1110 | 22,220.58 | 0.365794 / 0.001216 | [图](../work/YUZE-LU/162/block-delivery-11/layouts/control_adapter_n.png) |
| control_adapter_e | E块旁适配器 | 1 | 1220×1220 | 25,744.01 | 0.268239 / 0.006154 | [图](../work/YUZE-LU/162/block-delivery-11/layouts/control_adapter_e.png) |
| control_adapter_g | G块旁适配器 | 1 | 790×790 | 15,269.20 | 0.559934 / 0.004560 | [图](../work/YUZE-LU/162/block-delivery-11/layouts/control_adapter_g.png) |
| control_adapter_s | S块旁适配器 | 1 | 1740×1740 | 28,015.92 | 1.366617 / 0.017095 | [图](../work/YUZE-LU/162/block-delivery-11/layouts/control_adapter_s.png) |
| control_adapter_t | T块旁适配器 | 1 | 1020×1020 | 13,605.63 | 1.301787 / 0.007043 | [图](../work/YUZE-LU/162/block-delivery-11/layouts/control_adapter_t.png) |
| control_route | 固定控制派发/完成路由 | 1 | 400×400 | 2,581.00 | 1.284751 / 0.047432 | [图](../work/YUZE-LU/162/block-delivery-11/layouts/control_route.png) |
| control_s_arbiter | S端口仲裁与交接 | 1 | 1330×1330 | 14,599.41 | 1.331618 / 0.021265 | [图](../work/YUZE-LU/162/block-delivery-11/layouts/control_s_arbiter.png) |
| control_status | 错误/状态汇总 | 1 | 400×400 | 72.88 | 2.082342 / 0.015338 | [图](../work/YUZE-LU/162/block-delivery-11/layouts/control_status.png) |
| control_reset_distribution | 固定复位分配 | 1 | 400×400 | 404.32 | 2.110863 / 0.156328 | [图](../work/YUZE-LU/162/block-delivery-11/layouts/control_reset_distribution.png) |
| control_link8 | 8lane固定驱动与1bit复位隔离 | 309 | 100×100 | 180.08 | 1.458625 / 0.154350 | [图](../work/YUZE-LU/162/block-delivery-11/layouts/control_link8.png) |

335个原生实例的die面积之和为22,516,200.00µm²，活动单元面积之和为2,682,145.56µm²；这两个加总均不包含宏间留白，不能称为已验收的整机面积。Link8每实例1bit隔离状态、8条组合payload lane，309实例共309bit状态，均属于这些固定原生物理块。
