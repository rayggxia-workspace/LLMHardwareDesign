# 015 · 同网 M10 矩形保持与重新分类

- `015-net-aware-access/overlay.sha256` 的摘要为 `8c2cb3aff7bd88b08c6fa6e6749bf7728dde36f1f257dd7eb03d8b9470f54cdb`。作业 97494，c96 node13，P/J 两个 12 核步骤。
- 由 ODB wire iterator 读取与端点相接的短同网线段，在 LEF 中把它和原有 M10 障碍的精确交集划入 pin。其余矩形按原范围保留，叶 GDS 与原始 M10 landing 不变。改动后 P 通过全部接入进入 GRT。J 越过 276，报新的 `store/rsp_data[141]`。
- 报告中的 P 最差 setup 为外部 reset 到 store（−0.98 ns），J 为外部 TX 地址到 RX READY（−0.83 ns）。它们仍是 CTS 阶段估算。下一轮以复位和接收保持槽切断这些边界路径。