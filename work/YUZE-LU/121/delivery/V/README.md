# V 基础宏最终单块交付

2026-10-28 06:36 CST，Refs #121，待项目独立审查。唯一基础实现`block_v1_v`，内部固定原生Nangate45 M1–M10；三条通路为8路逐元素/统计、两路独立函数流水及组级除法/平方根，另含2KiB回放与最多40选8的有限选择状态。

| 项目 | 实际结果 |
| --- | --- |
| 外框 / 占地 | 1210×1210 µm / 1464100 µm² |
| 有源 / 物理专用单元面积 | 626334.506 / 741196.764 µm² |
| 时序条件 | 10ns时钟、0.1ns不确定度；I/O max2ns/min0.2ns；BUF_X2输入驱动、输出2fF |
| 全部实际端点 | 21949；最小setup / hold余量1.798553 / 0.016960 ns |
| 电气 / 寄生 / PG / 连接 | 全部通过；cap/slew最小余量1.007366fF / 0.049695ns |
| 原生全片DRC / 完整FreePDK45 GDS检查 | 0 / 0；完整原deck，无豁免 |
| 严格LEC | 43776输入、43765输出全匹配，UNSAT/IDENTICAL |
| 最终网表功能 | 三种初态各416344检查/310231周期，包含逐元素、函数、组合、TopK、背压与错误保持 |
| 实际接点 | 277个M10信号接点，cmd_data/rsp_data各128bit位于内部接入窗口 |

[最终文件索引](five-macro-delivery.json)保存最终Verilog/SDC/DEF/ODB/GDS/SPEF的授权服务器路径、大小、SHA-256和四项同源验收回执。最终ODB为`4280498654d2ada1f1910008240c0b09b27d37ffe318e30a5f8aa8591f967c94`，GDS为`c71d7d281394f7038b0db62b8dacad265d5df8345b68027019150459b0eb0132`。大体积数据库保留服务器，本地提供小型证据与图片。

- [最终GDS版图](block_v1_v.png)：1600×1600，全部层，只读渲染；已查看完整边界、供电与布线，不以图片代替DRC。
- [实际接点](pins.json)及[位置图](pins.svg)：最终ODB导出真实矩形，位置图包括完整宏及两个128bit总线放大图，不表示内部布线或OBS。
- [同源验收快照](../../results/run228-five-macro-063534/index.json)：四门与交付均通过；完整原生几何导出仍在运行，不能用该快照宣称其通过。

基础容器S32，常用Q16.16；逐元素8lane数据需经128bit口分两拍传输。两路函数流水实测3级、II=1，独立组级除法/平方根分别128/64拍；不能把组级吞吐当逐元素函数吞吐。2KiB回放只容纳256×S32输入和同长临时结果，内置RMS/L2/Softmax组合组长1..256，更长组用统计命令和S分段；统计上下文计数最多65535。函数输入域、定点误差、RNE/饱和和逐操作周期见[规格](../../../../../docs/BLOCK_LIBRARY_V1.md#v一个宏三条固定内部通路)与[命令合同](../../../../../docs/BLOCK_V1_COMMANDS.md)。cos/sin由外部提供，TopK动态ID不等于实现专家寻址与搬运。

最终228保持原RTL、外框与接点；仅修复实际七个BUF和一个DFF驱动及PG接线次序，重新布线、fresh RCX并重新通过全部同源验收。原203/222失败保留，未转移旧功能/LEC资格。完整DRC回执`6aedb0c23b5294fe4e0c0c77d63d820c6273113704ed1079bcc589175e49f676`。

候选LEF抽象覆盖、通用层次Lib和M11/M12系统资格仍单独标false。R剩余验收及项目独立审查未完成，五宏整体尚未完成。

重生接点图：

```powershell
python project/experiments/block_v1/render_pin_map.py work/YUZE-LU/121/delivery/V/five-macro-delivery.json work/YUZE-LU/121/delivery/V/pins.json work/YUZE-LU/121/delivery/V/pins.svg
```
