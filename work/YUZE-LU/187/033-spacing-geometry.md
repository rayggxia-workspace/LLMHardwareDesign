# 033 · 对照每个标记的实际导体几何

- 032 的标记框补丁完全保留其余 DEF，但无法减少间距标记。使用精确 ODB 的 wire、via、顶层 BPin、变换后的硬宏/标准单元引脚和 DEF RECT 重新定位。
- P 的若干 M2 标记位于线和过孔形成的同网凹口。J 有短距的同网 M3 过孔对、E 边界 M10 拐角，以及一处 `words[2]` 与 `rx_tag[28]` 的跨网间距。后者对应外露 M10 pin 周边的父层走线。几何和候选区域在 `033-spacing-geometry/{P,J}/geometry.json`，未编辑原始数据库。
- 源 `ff0dac808`，97548 同一节点 2×12，脚本、输入数据库与 DRC 报告哈希在 `033-spacing-geometry/input.sha256`。
