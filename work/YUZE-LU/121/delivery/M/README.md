# M 基础宏最终单块交付

2026-10-28 CST，Refs #121，待项目独立审查。唯一基础实现 `block_v1_m`，完整矩阵乘加引擎，原生 Nangate45 M1–M10。规格与命令见[五宏规格](../../../../../docs/BLOCK_LIBRARY_V1.md)和[接口合同](../../../../../docs/BLOCK_V1_COMMANDS.md)。

| 项目 | 实际结果 |
| --- | --- |
| 外框 | 560×560 µm，313600 µm² |
| 有源 / 物理专用单元面积 | 115631.264 / 153645.856 µm²，分别据实际ODB计入保护、时钟、修复与填充 |
| 时序条件 | 10ns时钟；0.1ns不确定度；输入/输出延迟max2ns、min0.2ns；BUF_X2输入驱动；输出2fF |
| 最小setup / hold余量 | 1.737254 / 0.014780 ns，全部实际端点及电气检查通过 |
| 原生全片DRC / 完整FreePDK45 GDS工艺检查 | 0 / 0，无豁免 |
| 精确最终信号网表 | 三种初始状态均通过1200组tile回归；保护与修复单元保留 |
| 严格LEC | 全部10558输入、10549输出匹配；UNSAT/IDENTICAL |
| 实际信号接点 | 275个M10矩形，每个0.8×0.8 µm；宽数据位于块内部窗口 |

[最终文件索引](five-macro-delivery.json)列出V/SDC/DEF/ODB/GDS/SPEF的真实服务器路径、字节数和SHA-256，以及四项同源接收回执。大文件保存在获授权的项目服务器目录；本目录保留小型交付入口。

- [完整最终GDS版图图](block_v1_m.png)：1600×1600、全部层、只读渲染；图不是DRC报告。
- [实际M10接点](pins.json)：从最终ODB原生导出，保留DBU和µm坐标。
- [接点位置图](pins.svg)：由上述真实矩形生成，含整体位置与两个宽接口放大图；不表示内部布线或OBS。
- [完整203接收快照](../../results/run203-five-macro-001344/index.json)：全部四项检查与交付通过。

来源链为M193原生布线→204单网M2补铜精确几何证明→205最终report/寄生重新提取→203独立四项接收及交付。补铜发生在本版冻结前；没有沿用193的旧SPEF或接收资格。197/201/202失败保留。

当前验收的是该原生单块结果。通用层次Lib和M11/M12系统资格仍单独标false，项目审查、V完整几何与R剩余验收仍待完成；不以此关闭Issue121。

重生接点图：

```powershell
python project/experiments/block_v1/render_pin_map.py work/YUZE-LU/121/delivery/M/five-macro-delivery.json work/YUZE-LU/121/delivery/M/pins.json work/YUZE-LU/121/delivery/M/pins.svg
```

[完整原生占用/OBS与M10底部几何合同](native-geometry/README.md)：2026-10-28 03:07 CST只读导出并完成独立DEF RECT补全，原ODB未改。候选LEF的抽象覆盖和未来M11/M12系统资格仍未通过。
