# S 基础宏最终单块交付

2026-10-28 CST，Refs #121，待项目独立审查。唯一基础实现 `block_v1_s16k`，16 KiB、1024×128bit、单1RW标准单元工作存储，固定原生 Nangate45 M1–M10。它是独立工作存储，不含计算阵列，也不以旧C8中的存储或SRAM宏代称。

| 项目 | 实际结果 |
| --- | --- |
| 外框 / 占地 | 1610×1610 µm / 2592100 µm² |
| 有源 / 物理专用单元面积 | 1071968.030 / 1389447.010 µm² |
| 存储实现 | 131072bit payload；总131201个映射DFF，包括128bit响应及有效控制 |
| 时序条件 | 10ns时钟、0.1ns不确定度；I/O延迟max2ns、min0.2ns；BUF_X2输入驱动、输出2fF |
| 全部实际端点 | 131331；最小setup / hold余量5.995658 / 0.008125 ns |
| 电气 / 寄生 / 供电 / 连接 | 全部通过，实际M10接点与封存接口合同一致 |
| 原生全片DRC / 完整FreePDK45 GDS检查 | 0 / 0，无豁免；完整deck SHA见同源回执 |
| 严格LEC | 262545输入、262532输出全部匹配，UNSAT/IDENTICAL |
| 最终网表功能 | 三种初态各通过1024地址、10000随机事务、91035项检查 |
| 实际信号接点 | 273个M10矩形；128bit din与128bit dout位于实际内部接入窗口 |

[最终文件索引](five-macro-delivery.json)保存最终Verilog/SDC/DEF/ODB/GDS/SPEF的授权服务器路径、字节数、SHA-256及四项同源接收回执。最终ODB为`de0775b46044c99879cc7907766cb7f156604677638e645f9b539348f2f417b4`，GDS为`fb271dfca469b0f1a59358791265e95ce2d3755973092eb4ddcbc9937e45a679`。大体积数据库保存在索引所指服务器目录；本地保留小型索引、回执、真实接点与图片。

- [完整最终GDS版图](block_v1_s16k.png)：1600×1600，全部层，只读渲染；已查看完整边界、供电及布线，图不替代DRC报告。
- [实际M10接点](pins.json)：最终ODB导出的DBU及µm矩形，SHA与交付索引一致。
- [接点位置图](pins.svg)：从上述真实矩形生成，包含完整宏和din/dout放大图，不表示内部布线或OBS。
- [同源接收快照](../../results/run225-five-macro-061939/index.json)：完整物理、完整DRC、最终网表功能、严格LEC及交付均通过。
- [完整原生几何](native-geometry/README.md)：包括wire/via/PG/pin/OBS、封存DEF的RECT独立补全及M10底部接入合同；与上述同一最终ODB/DEF绑定，原数据库未变。

请求在接受沿后形成寄存响应，take前保持；消费沿不接下一请求，无背压时读写合计最短间隔2拍。reset不清payload，读前必须写入。10ns条件下128bit/2拍对应协议上界0.8GB/s，未新增端到端峰值测试。完整字段、逐拍约束及复位边界见[命令合同](../../../../../docs/BLOCK_V1_COMMANDS.md#s工作存储协议)，资源与数值定义见[五宏规格](../../../../../docs/BLOCK_LIBRARY_V1.md)。

来源为原S190最终几何的三个实测M10接入网修正→225原生最终输出/fresh RCX→225独立四门与交付；保持同一RTL、外框与全部接点，不沿用190/207旧资格。原失败保留，本次没有添加裕量实现。

通用层次Lib、候选LEF抽象覆盖和M11/M12系统资格仍单独标false；项目审查及R剩余验收未完成，不据此关闭Issue121。

重生接点图：

```powershell
python project/experiments/block_v1/render_pin_map.py work/YUZE-LU/121/delivery/S/five-macro-delivery.json work/YUZE-LU/121/delivery/S/pins.json work/YUZE-LU/121/delivery/S/pins.svg --input-bus din --output-bus dout
```
