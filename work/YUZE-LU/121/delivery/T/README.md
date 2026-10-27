# T 基础宏交付入口

选定transaction6k C，1120×1120um，384×128bit=6KiB标准单元结果缓冲。最终原始V/SDC/DEF/ODB/GDS/SPEF、同源回执和SHA见[索引](../../library-v1-t6k-C-20261027.json)；体积较大的文件保存在该索引指向的授权服务器路径。完整叶块DRC0/全部端点时序电气/三初态最终网表功能沿用161实际结果，本次未重跑。

- `transaction6k-C.png`：从索引绑定的实际187318230B完整最终GDS只读渲染，1600×1600，全部层，SHA25634419a1f73ea39eb78f857cedd68d000423d881451a8fe21beafcce23337c8ee。已目视核对有完整边界/供电及布线。图不是DRC报告。
- `pins.json`：从同一选定C实际ODB导出386个信号位的M10真实矩形，保留DBU和um坐标；本次工具原生读回，不由RTL端口数猜坐标。

T通用层次Lib/flat-abstract等价资格仍false；既有candidate.lib/lef只列候选视图，不能宣称任意M11/M12父层连接或完整系统已通过。本轮五宏库尚未全部完成。
