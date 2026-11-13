# 五类 Block V2

这批 V2 使用 P2545、U39 v02、C V3、F19、J03 的窄口物理快照。每类是一个局控管理的独立叶宏组。组装 RTL 分为 `p/`、`u/`、`c/`、`f/`、`j/`，逐字节一致的适配和控制文件集中在 `common/`。宏实现按各自接口使用，同名复用宏见源码清单。

| 组 | 源码入口 | 实际宏 |
| --- | --- | --- |
| P | [p](p/) | M60、G32、16 KiB S_base |
| U | [u](u/) | N32、E16、16 KiB S_base、程序 SRAM |
| C | [c](c/) | R256、E16、E32、G16、16 KiB S_base、程序 SRAM |
| F | [f](f/) | E16、E32、G16、16 KiB S_base、程序 SRAM |
| J | [j](j/) | E32、T6、16 KiB S_base、程序 SRAM |

[源码清单](source-manifest.json)按每类保留有序输入、原始路径和 SHA-256。使用单组清单编译，U 的 include 路径加 `u/`，N32 加 `macros/n32/`。C 和 F 的 `block_cfj_cf.sv` 内容不同，各自保留。J 的已映射旧服务 `cfj_group_j_legacy.v` 在原工程目录，由清单锁定其路径和哈希。各组清单仍须绑定原物理库，按组分别编译。

[本批更新的叶宏](macros/)包括 M60、N32、G32 和 E32。S_base、E16、G16、R256 和 T6 沿用原实现，源码入口在清单中。MC06 单列在同一清单中，指向其独立交付包内的源码归档。

P、U 的清单收录可追溯的上游映射 RTL，P2545、U39 的最终网表和物理 ECO 以各自回执哈希为准。P2545 使用 S_base，正式 S_P 的候选另有物理验收范围。九组联合底座尚未冻结。详见[版图图册](../../../docs/experiments/assets/five-leaf-bases-v2/README.md)。
