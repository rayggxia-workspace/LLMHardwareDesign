# 014 · 区分叶宏同网金属与障碍

- 013 的 P/J 都走过 CTS。P 过引脚接入并进入 GRT，J 仍在 `store/req_data[276]` 停止。以 `013-signed-reference/overlay.sha256`（SHA-256 `c6a02210c021091d7d9aa476bd7162f89e8e1f16d4330feb35b7c49940d9ae35`）固定物理配置。
- 诊断作业 97492 以相同 J CTS ODB 在同一 c96 节点用两个 4 核步骤。独立读取到 pin 的实际包围盒。旧调试命令的 `-bottom_routing_layer` 已弃用，原输出保留，后续用 `set_routing_layers`。
- 从已验收 N4 原 ODB 导出 M10 同网段。 `req_data[276]` 的实际线段框为 `581790 688900 583390 696140` DBU，和匿名障碍交叠，也与原 pin 相接。原始源、工具输出与 TSV 保存在 `014-access-diag`。TSV SHA-256 `027fcd376ebf1cc95af1edc298f7ff30724f2c0ae1e9c67d44e1b93a9b4585b9`。
- 007、009、010 的原详细 LEF 接入在同一阶段分别消耗 23、17、11 分钟仍未完成，且源或 CTS 条件已被替代。保留源、日志和摘要并回收这批作业的核，取消它们的无效后继 97482。作业及峰值快照见 `superseded-before.txt` 与 `superseded-resources.txt`，摘要分别为 `c259f838feacbffff5c47debffa309066bcce53e4435fe01e77541ad41e7646d`、`033091d7983e8b0d9faa567574bdaafec9e49f01ad5e48b00e58206bc5c9e694`。