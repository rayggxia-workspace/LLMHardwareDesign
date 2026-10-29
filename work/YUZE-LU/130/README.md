# Issue130：M/S供数修改与原生合法候选

2026-10-30 02:34 中国标准时间；负责人YUZE-LU；[Issue130](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/130)／[PR132](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/132)。

本侧交付为Nangate45 typical、300MHz、输入BUF_X2/Z、输出50fF、固定M1–M10下的新M与配套S原生叶块候选。M的独立A128/B512、S的四bank供数和有限控制已计入实际电路。V/R/T相对固定父提交4a0b04ed8eb4b5cd818f04f3c1fb4c2b4d4f76bd保持原接口与RTL；18项RTL初态回归的结论仅对应该固定源，不替代父分支后续修改的验收。S最终组合功能使用完整S/M物理网表和原T RTL夹具。

| 宏 | 尺寸 | setup / hold | 完整GDS DRC | 实收成员 |
| --- | --- | --- | --- | --- |
| M | 980×980µm | +47.355000 / +9.898000ps | 0 | 32 |
| S | 1680×1680µm | +28.545000 / +7.200000ps | 0 | 44 |

两宏电气/全端点/实际M10接点/连通/PG/RC、完整未修改FreePDK45 deck、三个初态最终网表功能及严格全边界等价均通过，并绑定实际同一封存源。详见[M验收](validation/physical/ACCEPTED_M.md)、[S验收](validation/physical/ACCEPTED_S.md)和[物理执行记录](validation/physical/README.md)。

正式规格：[BLOCK_FEED_V1.md](../../../docs/BLOCK_FEED_V1.md)。运行入口：[ARCHITECTURE.md](../../../docs/ARCHITECTURE.md)。每种宏仅一个RTL实现，pair是测试夹具。

实际六文件、图、门回执与包分别位于D:/Data/LLMHardwareDesign-issue130-runtime/deliverables/M和S；ODB/DEF/SPEF/GDS/Verilog/SDC在各自unpacked/native，候选LEF和实际接点几何在geometry。服务端源与逐SHA索引在上述验收页；大文件不纳入Git。

```powershell
python scripts/check_project.py
python -X utf8 project/experiments/block_feed_v1/verify_evidence.py
python -X utf8 project/experiments/block_feed_v1/verify_bundle.py D:/Data/LLMHardwareDesign-issue130-runtime/deliverables/S
```

前两条为管理/已保存原始证据检查，不能描述为重跑EDA。六模型三个初态的18项RTL、实际S→M→T检查及物理工具/源/输入SHA绑定见validation目录。

层级Liberty、abstract coverage、M11/M12系统、完整M→V→R、四M阵列及制造签核未取得；50fF合同不能替代任意上层线长/负载验收。未声称父任务五宏全部完成。

两项物理候选已实收，代码提交供独立审查，不自审、自合并或关闭Issue。PR与持续推进的父分支存在已观察的合并冲突；集成时需保留父V/R并行成果，不能将固定4a0b04e回归写成最新父源测试。登记PR5未合并为pending；缺config/board.json且Issue projectItems为空，看板unverified/同步pending，管理员与独立审查人待指定。
