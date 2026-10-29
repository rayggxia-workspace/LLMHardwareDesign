# V 的时钟 NDR 与提取后几何解释

Refs #121 / PR #122。仍只有一个基础 V；本次改物理时钟策略，不改变 RTL、数值、操作周期、接口或 300 MHz 约束。

V380/93441 自然失败，原始产物不改。384–388 检查原最终 ODB 的 wire/via、引脚及障碍物，没有在 PSM 报告的 M3 位置找到 clk；原生 DRC 为零。386 的完整 DEF 提取证明 clk 没有 RECT 补片。不能据此放行 PG。

390 在提取前直接检查 VSS 通过；392 在提取前依次检查 VDD/VSS 都通过。391 用同一原 ODB、同一提取规则执行 RCX，随后稳定复现 PSM-0043/0069；不需要先求解 VDD，也不需要读回 SPEF。391 的路径迭代器导出在提取前后矩形并集相同，DEF 路径编码改变。

397 对安装程序的 `dbWire::getShape` 实际读回进一步确认：M3 线从 `[1050680,681030,1051340,681170]` 变为 `[1049950,680300,1052070,681900]` DBU，即宽度 140 变为 1600。后一矩形与实际 VSS 通孔 M3 矩形 `[1051820,680260,1052740,680540]` 的交集为 `[1051820,680300,1052070,680540]`，2000 DBU/µm，精确对应失败日志。路径迭代器与 getShape 对同一提取后编码的解释不一致，不能将其中一个出口当作充分资格证据。

固定上游 [RCX 入口](https://github.com/The-OpenROAD-Project/OpenROAD/blob/6ea4ca224f3589dd91809933f50f39af66053634/src/rcx/src/ext.cpp#L252)在提取前进行 wire connectivity normalization；[顺序形状迭代器](https://github.com/The-OpenROAD-Project/OpenROAD/blob/6ea4ca224f3589dd91809933f50f39af66053634/src/odb/src/db/dbWireShapeItr.cpp)和[路径迭代器](https://github.com/The-OpenROAD-Project/OpenROAD/blob/6ea4ca224f3589dd91809933f50f39af66053634/src/odb/src/db/dbWirePathItr.cpp)提供解释线索。下载文件核对 Git blob；这不是安装二进制源码版本的证明。安装程序版本 banner 为 unknown，程序 SHA 为 `0a4cdf08482bab2d99543e8b32b4b142e013becc7f2c1598afb39ba058193f53`。具体上游缺陷归属仍不作超出证据的判断。

## 选定的唯一后续实现

V400 使用原生 CTS `-apply_ndr none`，保留原 `-sink_clustering_enable -repair_clock_nets`，以原生默认宽度重新构建并布线时钟。399 已在相同安装程序验证 setter 接受 none，并在启动前核对 SIF SHA。CTS 后逐时钟网读取 NDR 必须为空，记录 TSV 和 SHA；实际时序、原生/完整未修改 GDS DRC、PG、电气、RC、三初态最终网表功能、严格 LEC、六文件及完整几何仍必须全部通过。不是删去/关闭短接检查，也不修改原380或提取后的旧数据库。

378/379 的 RTL/映射/功能/测量资格仅按逐文件一致性复用，物理阶段全部重跑。V401 最终门读取实际400，V402 接口读取实际401。检查选择器时发现 native V 仍指向旧374，现明确改为400；原381/382未获得合格前置，旧归档保持，不会用旧374验收新版本。

384–399 诊断均在 R344 已有 allocation 的独立16CPU槽运行；389、394、395的API错误及385的解析失败原样保留。R344不取消、不重启；M/S/T资格保持。403控制器和400–402尚待实际部署，不能把计划写成已运行。

原始证据位于 `work/YUZE-LU/121/review-20261028/v-380-pg-diagnostics-384-388`、`v-380-rcx-diagnostics-389-398`、`v-cts-none-api-399`。147205318字节的终端表及368241757字节的提取后DEF留在服务器，仓库有路径/大小/SHA索引。
