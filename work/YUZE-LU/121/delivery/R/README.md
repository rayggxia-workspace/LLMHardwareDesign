# R 基础宏最终单块交付

2026-10-28 11:52 CST，Refs #121，待项目独立审查。唯一基础实现`block_v1_r`，内部固定原生Nangate45 M1–M10；8路共享乘加、广播和归约，按不同顺序执行GDN/SSM，另含四抽头因果深度卷积及显式历史访问。

| 项目 | 实际结果 |
| --- | --- |
| 外框 / 占地 | 1870×1870 µm / 3496900 µm² |
| 有源 / 物理专用单元面积 | 1542765.420 / 1802658.060 µm² |
| 时序条件 | 10ns时钟、0.1ns不确定度；I/O max2ns/min0.2ns；BUF_X2输入驱动、输出2fF；Nangate45 typical |
| 全部实际端点 | 146009；最小setup / hold余量2.155765 / 0.015269 ns |
| 电气 / 寄生 / PG / 连接 | 全部通过；cap/slew最小余量3.054929fF / 0.067521ns |
| 原生全片DRC / 完整FreePDK45 GDS检查 | 0 / 0；完整原deck，无排除规则或豁免 |
| 严格LEC | 291900输入、291886输出全匹配，UNSAT/IDENTICAL，差异边界均0 |
| 最终网表功能 | 三种初态各240组递推、100组卷积，397971检查/197111周期 |
| 实际接点 | 278个M10信号接点，cmd_data/rsp_data各128bit位于内部接入窗口 |

[最终文件索引](five-macro-delivery.json)保存最终Verilog/SDC/DEF/ODB/GDS/SPEF的授权服务器路径、大小、SHA-256和四项同源验收回执。最终ODB为`736d8e10d63c134b3ea81fb7eb34d69cd947c3d5be456f09240800d5459305e1`，GDS为`1ee28161412b9abdd7b86eef53f9612117f7e3f71493d90c9c43155a0c2be426`。大体积数据库保留服务器，本地提供小型证据与图片。

- [最终GDS版图](block_v1_r.png)：1600×1600、全部层，只读渲染；已查看完整边界、供电与布线，图片不能代替DRC。
- [实际接点](pins.json)及[位置图](pins.svg)：最终ODB的真实矩形，含完整宏及两个128bit总线放大图。
- [独立物理](../../results/r-physical-050943/index.json)、[三初态最终网表功能](../../results/r-final-function-065951/index.json)、[严格LEC](../../results/r-formal-074320/index.json)均绑定同一196最终源。
- [完整DRC通过快照](../../results/run230-five-macro-114545/index.json)：完整未修改FreePDK45 deck SHA为`4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147`，完整GDS报告0项；DRC回执`f05f5deb73c73d07535d8ab6c19f33bdbae83047ad2facea6033eb36bc211956`。
- [最终接收快照](../../results/run231-five-macro-114731/index.json)及[交付回执](receipt.json)，回执SHA为`2b3520abf1c76f4c79e93683757fe0f01f612c0dffdfc24014b0f9758d5492e9`。共享快照中的旧V222失败是保留的历史，不影响本R接收。

局部资源为8KiB活动状态、8KiB影子状态、1KiB Q/K/B/C系数、96B历史和96B候选历史；均为标准单元实现。8路S32×S33乘法、S65乘积与S128点积资源在两模式间共享。SSM衰减覆盖影子状态，不额外复制第三份8KiB状态。

GDN执行衰减、K点积、误差、beta/K外积更新、Q点积读出；SSM执行衰减、B×dtX注入、C点积读出和D×X skip。四抽头卷积显式装载历史与系数。状态与历史使用owner/epoch/position及影子提交/撤销协议，失败不能静默改活动状态；投影归M、外围归一化与门乘归V，组合次序未固化在R。

格式、范围检查、RNE及错误保持见[规格](../../../../../docs/BLOCK_LIBRARY_V1.md)和[命令合同](../../../../../docs/BLOCK_V1_COMMANDS.md)。接受EXEC到响应的逻辑延迟：GDN为8N+6拍，SSM为6N+4拍，四抽头卷积10拍；状态提交N行拍，纯历史提交1拍。装载、回读及背压另计，这些不代表完整模型层吞吐。最终功能保留所有承载信号的保护单元，是零延迟网表仿真；STA独立验收。严格LEC仅审计投影146个无输出输入负载，并通过负例资格检查。

候选LEF抽象覆盖、通用层次Lib和M11/M12系统资格单独标false。完整原生几何由原225队列在本块验收后只读导出；[完整原生几何和底部合同](native-geometry/README.md)已通过，同源绑定最终ODB/DEF，普通网络RECT独立核对0处，原ODB未改写；[五宏交付入口](../README.md)提供全库比较。

重生接点图：

```powershell
python project/experiments/block_v1/render_pin_map.py work/YUZE-LU/121/delivery/R/five-macro-delivery.json work/YUZE-LU/121/delivery/R/pins.json work/YUZE-LU/121/delivery/R/pins.svg
```
