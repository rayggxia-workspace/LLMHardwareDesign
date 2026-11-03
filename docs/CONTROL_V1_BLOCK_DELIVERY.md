# 当前复位分组版本：23类型/138文件，系统仍待独立验收

[实际场景359的规范索引](../work/YUZE-LU/162/block-delivery-r256-current363/index.json)替代298作为当前入口：只把reset28更换为单独完整验收的reset53，其余22类型逐文件复用。reset53六文件/版图及[本地接收回执](../work/YUZE-LU/162/block-local-reception-r256-reset53-361/RECEPTION.json)均逐CRC/SHA验证；全部固定主动逻辑仍归M1–M10，53分支只共用一个复位状态位。实际345实例/316Link8/11147逻辑网的程序/原生/布局布线与三档RC/300MHz继续独立执行。以下旧清单与实验作为历史保留，不能推断新系统通过。

# 当前23类物理块：C8/R256固定PG全门与六文件实收

2026-11-03，中国标准时间。以[规范当前索引](../work/YUZE-LU/162/block-delivery-r256-current298/index.json)为准，23类型/138个最终文件逐项匹配实际合格清单274；原21类保留16类，替换5类控制并新增R256和其适配器。C8/R256在五类新增控制之后完成本轮原生及固定PG全门：[C交付](../work/YUZE-LU/162/block-delivery-r256-c285/index.json)、[C实收](../work/YUZE-LU/162/block-local-reception-r256-c285/RECEPTION.json)、[R交付](../work/YUZE-LU/162/block-delivery-r256-r296/index.json)、[R实收](../work/YUZE-LU/162/block-local-reception-r256-r296/RECEPTION.json)。全部ZIP成员已重新读回CRC/SHA，两张实际PNG已查看。[Checkpoint44](../work/YUZE-LU/162/continuation-checkpoint-44.md)给出新鲜setup/hold和原失败解释。

单块验收不授予345实例/11,122逻辑网组合资格。完整实际M11/M12、PG、三RC/300MHz、八程序及联合六文件仍继续全门。以下五类/旧21类记录按其原快照保留；涉及“C/R仍执行”的段落是历史阶段，最新单块交付以上方规范23类清单为准。

# R256 组合新增单块交付：五类已实收，C/R 独立验收继续

2026-11-03，中国标准时间。下表五类新配置均完成原生四门、固定 PG 完整 DRC、原几何精确保持、PG 连通、新鲜 RC、300MHz 及六文件交付；[逐块源绑定索引](../work/YUZE-LU/162/block-delivery-r256-five260/index.json)保留实际输入、检查和原始结果 SHA。

| 新物理类型 | die（µm） | 固定PG后 setup/hold（ns） | 实际版图 |
|---|---:|---:|---|
| control_route_r8 | 410×410 | 1.202418/0.003972 | [图](../work/YUZE-LU/162/block-delivery-r256-five260/images/control_route_r8.png) |
| control_status_r8 | 400×400 | 2.115414/0.033135 | [图](../work/YUZE-LU/162/block-delivery-r256-five260/images/control_status_r8.png) |
| control_reset_distribution_r28 | 400×400 | 2.100343/0.156889 | [图](../work/YUZE-LU/162/block-delivery-r256-five260/images/control_reset_distribution_r28.png) |
| control_s_arbiter_r7 | 1470×1470 | 1.237522/0.021788 | [图](../work/YUZE-LU/162/block-delivery-r256-five260/images/control_s_arbiter_r7.png) |
| control_adapter_r | 1490×1490 | 0.757920/0.007943 | [图](../work/YUZE-LU/162/block-delivery-r256-five260/images/control_adapter_r.png) |

本机已实收五个 ZIP／30 个最终文件，原六文件合计 422,207,592 字节，ZIP 合计 69,239,145 字节；每个成员 CRC／SHA 解压回读通过，五张实际 PNG 已查看。[本地回执及源绑定](../work/YUZE-LU/162/block-local-reception-r256-five260/RECEPTION.json)。存储目录 `D:\Data\电路实验\LLMHardwareDesign-deliveries\issue-162\blocks-r256-five260`，大文件不入 Git。

C8 新配置 2371 的原生布局布线、完整 GDS DRC、功能和严格等价均通过；固定 PG 后独立复验继续。R 复用已合格 R256 的原始固定信号几何；新 PG 仍须完成独立全门，不能继承旧六宏组合资格。R 的完整刚体位移为 (+0.095,+0.07)µm，使原生 (0,0) 接点相位接入既定全局相位；未移动单个接点或改动原 M1–M10 图形。345 实例／23 类型／11,122 逻辑网已真实提取，包含 316 个固定 Link8；尚无完整系统通过。

下面保留旧六宏参考组合的 21 类已合格单块基线及其真实交付。该旧表中 C/route/arbiter/status/reset 的参数配置与新增 R256 组合不同，不能直接替代新配置验收。

# Issue162 最终单块交付（S内部驱动及S适配器ready修复）

21类物理块全部原生四门及固定PG/新鲜RC/300MHz验收通过。S1350内部788个BUF_X32无新增状态；S适配器两个预测ready状态位明确归该物理宏，保持原协议拍和有限包槽。其余19类型、S本体均复用精确已合格文件。S/T为标准单元存储。R保留并由并行任务修改，此表不宣称已接入。

**单块通过不代表系统通过。** 全网M11/M12/真实全PG/low-base-high分布RC/300MHz/实际代表程序及联合交付须独立验收。旧失败/基线索引完整保留。

[六文件、SHA和全部源绑定索引](../work/YUZE-LU/162/block-delivery-ready140/index.json)。所有图片均为实际交付PNG。

2026-11-03 13:10 CST：本机已完整实收21个ZIP，含126个最终文件、21张实际版图及105份验收回执。原六文件共7,633,691,838字节，ZIP合计1,637,695,602字节；每个成员均完成远程原字节SHA及本地ZIP解压读回CRC/SHA核验。文件位于 `D:\Data\电路实验\LLMHardwareDesign-deliveries\issue-162\blocks-ready140`，不将大文件提交Git。[本地实收回执](../work/YUZE-LU/162/block-local-reception-ready140/RECEPTION.json)及[接收器/原索引绑定](../work/YUZE-LU/162/block-local-reception-ready140/SOURCE_BINDING.json)保留各ZIP和全部成员SHA。此次实收只覆盖上述已合格单块，完整组合验收继续。

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
