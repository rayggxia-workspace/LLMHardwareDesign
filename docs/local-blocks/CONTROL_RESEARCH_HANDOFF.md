# 两级控制当前接续入口

源码交付`4d16eb64e9c15abd79f0581a24c8acb34ad7ff0c`；原位更新研究报告。

Issue179 / Draft PR180；Melodydt；2026-11-07 Asia/Shanghai；task/179-local-block-continuation。

## 当前进度：综合前第九步冻结交付待审（2026-11-07，Asia/Shanghai）

既有九配置已形成可搬移综合交付包：完整原生RTL与控制分区清单、顶层/参数、显式宏/PM边界、锁定标准单元库、SDC、源与输出SHA及复现脚本。九配置完整/控制lint、通用结构综合/实例计数、SDC逐位读回和搬移后层次检查均通过；54/54坏包保护通过。三个PM共12bank，每配置1MC/2LC/2原生边界；279非时钟输入位和604输出位max/min及负载核验。旧46个SV不变，64 bit与3.333333333 ns不变。第8步1690 RTL/1359软件保留为此前功能证据，本轮不重计。新增组合映射STA、宏物理视图绑定和物理验收仍未完成。

## 实现范围

第1-9步在九个固定目标、两常驻任务、单在途服务和单时钟合同内已有交付。MC/LC执行v2/64 bit ISA；实际PM装载/读回CRC/部署、五类接入、四条U/F/C/J→P提交ACK链、取消/排空/协调复位/隔离及受限任务编译保留。J用真实片段/T输出与lease，未授予native done缺失的SAT诊断。RAW128不证明数值兼容，initial声明是主机供齐输入义务。

第9步沿用five_boot_top KIND0-4、recovery_boot_top KIND0/1/2/4，综合PM_USE_SRAM固定1。三个16KiB PM各四bank；Block私有S/T在原生边界内，不能把12 PM bank当成全芯片bank总数。group只作控制逻辑分区，不是组合硬宏。全RTL清单保留真实原生源；控制综合禁止读入行为bank。

| 内容 | 入口 |
| --- | --- |
| 研究、ISA与当前进度 | [共享详细报告](CONTROL_RESEARCH_AND_ISA_QUICK_REFERENCE.pdf) |
| 顶层/参数/边界、库、复现 | [presynth README](../../project/control_presynth_v1/README.md) / [freeze](../../project/control_presynth_v1/freeze.json) |
| 实际SDC | [constraints](../../project/control_presynth_v1/constraints.sdc) |
| 本轮九配置与源/包/结果SHA | [synthesis validation](../../work/Melodydt/179/control-synthesis-freeze-validation.json) |
| 编译器、样例和装载 | [compiler](../../project/control_task_compiler_v1/README.md) |
| 第8步覆盖与未命中行 | [matrix](../../project/control_matrix_v1/README.md) / [validation](../../work/Melodydt/179/control-matrix-validation.json) |
| 恢复管理命令和时钟复位 | [recovery](../../project/control_recovery_boot_v1/README.md) |
| 输入版本 | [upstream lock](../../project/control_frontend_v1/upstream-lock.json) |

## 实测与接续

本轮9/9配置结构/约束/搬移、54/54包保护（六类×九配置）通过；不是新增RTL场景。第8步1690/1690 RTL、1359/1359软件、有界必测项零缺失，原生行覆盖932/1150（81.04%），218未命中行保留。控制源与此前一致，不冒充重跑；OpenROAD bazel-nostamp以实际二进制SHA绑定。

下一阶段按选定配置：绑定真实叶宏与SRAM视图→同版标准单元映射/组合STA→等价和网表回放→必要修复与功能回归→CTS/布线/物理验收。当前没有可信组合WNS/TNS；接口夹具只核对SDC对象/预算，不是计时电路。独立模块/Block时序不能替代组合资格。完整LLM图前端、动态形状、任意调度/路由/转换仍不在此有界实现内。

PR176仍08f2ea20；PR213最新4f7e534d、PR214最新46389f67已合并主干，47个选用blob与冻结输入一致。内部完整方案/STATUS/进度/交接本地原位维护；远端当前指南、共享报告、源码及技术索引可用于其他分支接续。

Issue179保持in_progress，PR180 Draft未合并、审查人待指定；登记PR5 pending；无board.json/Projects能力，看板unverified、同步pending，待具备权限管理员核验。所有本轮作业结束，无聊天外自动监控。
