# 025 · 检查硬宏高层 OBS

- 024 的 J 滤除 VDD 上两栈，分别接近 `arithmetic/out_data[53]` 和 `lease/write_index[6]`，VDD/VSS 通过 floorplan PG 检查。P 的 12 核步骤在 39 秒失败。PSM 报八处 VDD 短路，目标为 `gate`、`multiply` 和 `store` 实例内部未公开金属，位于 M8/M9。原始记录为 `024-pg-stack-filter/pnr/guide/P/pg-removed.tsv-VDD.rpt`。这些坐标与旧版 019 P 的最终提取报告一致。
- 扩展同一父层 PG 过孔筛选，纳入精确 LEF M8–M10 匿名障碍。仍只移除与已有几何近接的完整父层 M7–M10 过孔栈，逐栈输出位置。保护的 M7 宏电源接触和子宏 GDS 保持原样。
- 源 `2016e79b9`，脚本哈希 `337ce6a4ac92b53b7e173e5657f0c819f2ccb38a1a33add8642cbb828b5152d9`，其余输入列于 `025-pg-obs-filter/overlay.sha256`。作业 97524 两条 12 核步骤，后继 97525 八条 12 核步骤。先检查滤除后电源连通，再判断最终门限。
