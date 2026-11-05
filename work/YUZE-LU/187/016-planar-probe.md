# 016 · 单独验证 M10 平面接入参数

- 使用 015 J CTS ODB，作业 97496，同一 c96 node17 上两个 4 核步骤。几何查询测得 `rsp_data[141]` 无附近父层电源线。强制在 M9 以下使用 via 接入、允许 M10 平面接入，仍报告同一失败。
- `016-planar-probe/access.tcl`、`pin.log`、`geometry.log` 的 SHA-256 分别为 `7854a1b7e3b3835ef2c780c5a35fcd403007aac3367415c635ac6377d66deb0e`、`258567daba4fd29e3a6acec2b8aaa66d8158f7f9b1fcc2e5fbd856cadd3052c9`、`fafaefa026e648388c00d087c653d1c2f9250eb4b4eec4729e6deddd41bcb671`。
- 原 DEF 显示该信号确有 M9 和 via9 同网接入。下一轮把短 M9 同网矩形也划入真实 pin，保持两层金属几何。