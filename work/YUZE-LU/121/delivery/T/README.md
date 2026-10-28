# T 基础宏交付入口

选定transaction6k C，1120×1120um，384×128bit=6KiB标准单元结果缓冲。最终原始V/SDC/DEF/ODB/GDS/SPEF、同源回执和SHA见[索引](../../library-v1-t6k-C-20261027.json)；体积较大的文件保存在该索引指向的授权服务器路径。完整叶块DRC0/全部端点时序电气/三初态最终网表功能沿用161实际结果，本次未重跑。

| 项目 | 实际结果 |
| --- | --- |
| 外框 / 面积 | 1120×1120 µm / 1254400 µm² |
| 有源 / 物理专用单元面积 | 415495.990 / 748496.070 µm² |
| 时序条件 | 10ns时钟、0.1ns不确定度；输入/输出延迟max2ns、min0.2ns；BUF_X2输入驱动、输出2fF |
| 全部实际端点 | 49544；最小setup / hold余量5.228821 / 0.016969 ns |
| 电气 / 寄生 / 供电 / 连接 | 全部通过；cap / slew最小余量3.909312 fF / 0.098314 ns |
| 原生全片DRC / 完整FreePDK45 GDS工艺检查 | 0 / 0，无豁免 |
| 严格LEC | 98886输入、98892输出全匹配，UNSAT/IDENTICAL |
| 最终网表功能 | 三初态各242事务、264051周期、3295817检查，实际信号单元保留 |
| 实际信号接点 | 386个M10矩形，见pins.json |

表内物理与严格LEC取自[161-C接收回执](../../results/run161c-receive-terminal/index.json)，功能取自[161-C最终网表回归](../../results/run161c-final-terminal/index.json)。LEC验证状态边界的组合对应，三初态回归单独验证控制复位和数据有效性；逻辑操作与接口成本见[命令合同](../../../../../docs/BLOCK_V1_COMMANDS.md)。

- `transaction6k-C.png`：从索引绑定的实际187318230B完整最终GDS只读渲染，1600×1600，全部层，SHA25634419a1f73ea39eb78f857cedd68d000423d881451a8fe21beafcce23337c8ee。已目视核对有完整边界/供电及布线。图不是DRC报告。
- `pins.json`：从同一选定C实际ODB导出386个信号位的M10真实矩形，保留DBU和um坐标；本次工具原生读回，不由RTL端口数猜坐标。

T通用层次Lib/flat-abstract等价资格仍false；既有candidate.lib/lef只列候选视图，不能宣称任意M11/M12父层连接或完整系统已通过。五宏原生单块验收均通过，项目独立审查待完成，见[统一入口](../README.md)。

[完整原生占用/OBS与M10底部几何合同](native-geometry/README.md)：2026-10-28 03:07 CST只读导出并完成独立DEF RECT补全，原ODB未改。候选LEF的抽象覆盖和未来M11/M12系统资格仍未通过。
