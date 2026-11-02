# Issue162 continuation checkpoint22

捕获：2026-11-03T02:29:52.896581+08:00；YUZE-LU；[Issue162](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/162) / [PR163](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/163)，继续in_progress，不合并。

[本次源绑定索引](continuation-proof-22/index.json)含316项远程记录/301项逐字节实收原文件，以及8项当前队列/上层/交付/渲染辅助脚本和1项精确Git回执。大文件留获授权远程路径/字节/SHA；活动日志只代表捕获时的字节。此检查点不表示停止工作。

## 修正版S原生收尾正式通过

1350完整raw receipt已通过：实际新鲜最终RC、普通LEC、最终完整native DRC、完整DEF读回、所有实际逻辑相同、固定接点/下层/所有过孔和非目标网保持、788个实际最终BUF_X32保留审计均通过。普通LEC在2026-11-03 02:09:59 CST得到UNSAT/Circuits are IDENTICAL；实际提取4,262,363条线，671394nets、3218936rsegs/caps、6780031ccs。do-6_report成功退出，实测峰值141657996KiB约135.1GiB，耗时51:55.86；预算256GiB仍有实际依据。

修复仅把dout[58]局部M10改成已核验的另一侧最短L形。全部有源器件归S M1–M10，S原RTL/功能保持，无新增寄存器/协议拍；1340只提供精确几何准备，失败准备未转授资格。1330与四原始候选的全部失败保留。

**raw流程通过不是独立四门或系统通过。** 封装、独立全端点300MHz/电气、完整native与GDS全deck、实际最终全部单元三初态功能、严格全部状态边界LEC，以及固定PG/新鲜RC/六文件仍须完成。捕获时的各门以索引内实际回执为准；没有从前序通过推断后继通过。

## 同一S1350硬件的并行验收

source136精确commit cb131c506f07a253ba4a05768be1fb75c9fc755c 已按原始Git对象身份发布/读回，force=false；939文件，归档SHA e8ad60ed6fb462f67c50b7431b9ff78b1bbe5caf88be945d55cc4cc84999ed31。唯一业务代码变化为S最终功能支持Verilator --output-groups 0，仍16路编译、同一完整物理导出视图/bench/全部三初态及门槛，无电路改动。

原1181完整最终网表功能也已实际三初态通过，各124440检查、46581周期、523描述符、9545窄口请求、CPU内部RAM访问0；其有DRC失败，不能转授合格资格。默认编译实际3558.342秒，其中build3394.175秒。新1350继续独立实际验收，不把原1181通过当新物理通过。

新gates02复用同一1350已通过的精确封装/物理/DRC路径，不重复制造几何候选；独立新功能与严格formal并行。严格formal只在同一完整不可变physical-functional-proof存在后开始，最终仍无条件等待并核验实际成功function receipt及完整视图SHA，不放宽门槛。其他20类精确合格叶复用。

8项新S原生/固定PG任务位于dynamic05/node4。条件发射器只在1350真实封装通过后，核实原95099为本人node4/mix4、活动任务均为旧335图system_upper，才保留证据并替换这个自有旧搜索分配；其他7个父分配/原生门/其他任务不动。实际是否已替换及新job以索引内submitted.json为准，不据准备脚本宣称运行。新控制器仍c64 4×16、256GiB最高预测预算和原sum(forecast)×1.2+16GiB保护，任务结束动态补位。

实际组合02使用同一1350新PG叶重新生成真实拓扑、最终全部单元三程序、原生STA、PG预检及精确native地电容界。7项已追加，不继承旧335组合资格。上层1370–1373共4路由及24后继门的发射器继续严格等待所有实际前置，只有缺项时返回ready=false，不能把准备当完成。旧组合01及全部immutable规格保留。

## 版图与最终交付

实际合格control_status GDS的三种无界面渲染已在自有95341 Slurm分配内独立执行成功：klayout -b、offscreen -b、offscreen -z，三张PNG逐字节相同，SHA44d1e59148c8016e901b0f876e8bc438b8b841ea04df02ca99f9b33cf6b7ab07。此为渲染预检，不是S或系统物理资格，不改KLayout流程掩盖问题。

新版单块收集器等待真实新S完整PG合格与实际图，核对六文件/实际PNG/回执SHA，复用其他20类同SHA合格文件；实例数和Link8状态数由实际图取得，并更新CONTROL_V1当前状态归属表，保留旧309/335历史。系统收集器只接收同一真实场景几何/全PG/三初态真实程序/low-base-high分布RC/300MHz全部通过的联合回执；未通过时不改写合格交付。两者与最新上层发射器均随索引保存，不表示已获得最终交付。

本地check_project、相关Python语法检查及排除原始证据快照的文档/代码差异检查通过。完整快照的git diff --check报告了原始日志行尾空白、报告末尾空行及原回执CRLF；保留这些原始字节并按索引SHA验证，不修剪证据，也不把完整快照差异检查记作通过。这些本地检查不代替硬件验收。实际M11/M12/完整几何/PG/三角点RC/300MHz/最终六文件、版图与源索引仍继续执行。R保留并由并行任务修改，当前六宏参考尚缺R适配接入；原M/N/E/G/T和原S基线保留，不操作其他任务、不自行合并。

协作规则rayggxia-project-collab1.0.0；登记management-hub PR5 pending；缺config/board.json，看板unverified/同步pending，处理人及审查人待指定。负责人YUZE-LU继续任务。
