# Issue162 最终单块交付（S内部驱动及S适配器ready修复）

21类物理块全部原生四门及固定PG/新鲜RC/300MHz验收通过。S1350内部788个BUF_X32无新增状态；S适配器两个预测ready状态位明确归该物理宏，保持原协议拍和有限包槽。其余19类型、S本体均复用精确已合格文件。S/T为标准单元存储。R保留并由并行任务修改，此表不宣称已接入。

**单块通过不代表系统通过。** 全网M11/M12/真实全PG/low-base-high分布RC/300MHz/实际代表程序及联合交付须独立验收。旧失败/基线索引完整保留。

[六文件、SHA和全部源绑定索引](../work/YUZE-LU/162/block-delivery-ready140/index.json)。所有图片均为实际交付PNG。

| 物理块 | 功能 | 实例数 | die（µm） | 活动面积（µm²） | setup/hold（ns） | 版图 |
|---|---|---:|---:|---:|---:|---|
| block_v2_m | M矩阵计算 | 1 | 930×930 | 304,530.90 | 0.039857/0.018500 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/block_v2_m.png) |
| block_v2_n | N归约/归一化/统计 | 1 | 510×510 | 68,015.67 | 0.140712/0.017753 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/block_v2_n.png) |
| block_v2_e | E逐元素/格式 | 1 | 600×600 | 63,751.69 | 0.412125/0.019608 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/block_v2_e.png) |
| block_v2_g | G函数计算 | 1 | 400×400 | 22,831.05 | 0.512034/0.017721 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/block_v2_g.png) |
| block_feed_s_macro | S16KiB标准单元工作存储与feeder | 1 | 1680×1680 | 1,191,739.58 | 0.017823/0.005295 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/block_feed_s_macro.png) |
| transaction6k | T6KiB结果交接 | 1 | 1040×1040 | 431,244.79 | 0.429092/0.007988 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/transaction6k.png) |
| control_c | 可编程C | 1 | 740×740 | 209,902.20 | 0.340552/0.000705 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/control_c.png) |
| control_d | 有限DMA搬运D | 1 | 1170×1170 | 123,455.12 | 0.058717/0.008420 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/control_d.png) |
| control_endpoint_queue | 任务/完成队列 | 7 | 470×470 | 12,159.66 | 1.564079/0.000901 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/control_endpoint_queue.png) |
| control_axil_bridge | AXI-Lite配置桥 | 1 | 400×400 | 3,254.51 | 1.255634/0.008345 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/control_axil_bridge.png) |
| control_adapter_m | M块旁适配器 | 1 | 770×770 | 10,567.91 | 1.357095/0.005789 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/control_adapter_m.png) |
| control_adapter_n | N块旁适配器 | 1 | 1110×1110 | 22,220.58 | 0.365794/0.001216 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/control_adapter_n.png) |
| control_adapter_e | E块旁适配器 | 1 | 1220×1220 | 25,744.01 | 0.268239/0.006154 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/control_adapter_e.png) |
| control_adapter_g | G块旁适配器 | 1 | 790×790 | 15,269.20 | 0.559934/0.004560 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/control_adapter_g.png) |
| control_adapter_s | S块旁适配器 | 1 | 1740×1740 | 27,024.80 | 1.444169/0.019669 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/control_adapter_s.png) |
| control_adapter_t | T块旁适配器 | 1 | 1020×1020 | 13,605.63 | 1.301787/0.007043 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/control_adapter_t.png) |
| control_route | 固定控制派发/完成路由 | 1 | 400×400 | 2,581.00 | 1.284751/0.047432 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/control_route.png) |
| control_s_arbiter | S端口仲裁与交接 | 1 | 1330×1330 | 14,599.41 | 1.331618/0.021265 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/control_s_arbiter.png) |
| control_status | 错误/状态汇总 | 1 | 400×400 | 72.88 | 2.082342/0.015338 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/control_status.png) |
| control_reset_distribution | 固定复位分配 | 1 | 400×400 | 404.32 | 2.110863/0.156328 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/control_reset_distribution.png) |
| control_link8 | 8lane固定驱动与1bit复位隔离 | 209 | 100×100 | 180.08 | 1.458625/0.154350 | [图](../work/YUZE-LU/162/block-delivery-ready140/layouts/control_link8.png) |

实际图共235实例、209个Link8。原生die面积加总21,516,200.00µm²，活动面积加总2,673,569.99µm²，不含宏间留白。
