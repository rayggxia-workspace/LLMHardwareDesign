# 两级控制当前接续入口

Issue179 / Draft PR180；Melodydt；2026-11-07 Asia/Shanghai；task/179-local-block-continuation。本页列当前能力、证据与接续入口。

源码交付`4061f10f925879022531548c3df9efc663c9f863`；[31页研究与ISA报告](CONTROL_RESEARCH_AND_ISA_QUICK_REFERENCE.pdf)原位更新。

## 当前实现

综合前第1-7步已有实现和验证：规格、可综合PM、公共装载、五类统一接入、四条异构提交链、取消/故障/协调恢复、统一受限任务编译。MC/LC执行ISA保持v2/64 bit，两个目标、单时钟域，每端一任务/一在途服务。目标周期3.333333333 ns。

新增control_task_compiler_v1输入命名缓冲区、端点原生操作和受限传输边，生成三端镜像、128 bit PM字、SHA/CRC及装载计划。准入五类同型five/U/F/C/P/J和四条recovery/U/F/C/J源0→P1链；无裸native字段逃逸口。两个CALL先于共同WAIT；局控串行EXEC/WAIT，异构链自动插入SEND及目的RESERVE/RECEIVE，预约服务序号从源程序计算。

类型/拓扑、ABI/容量、16 B对齐及S范围、别名/先读后产、原生上下文和展开后16条服务容量均校验。J保留片段输入和提交输出空间及lease，不伪装普通S。独立audit不导入compiler/codec/image，构造完整规范字节并核对SHA/CRC；另有明示有限域的数值参考。旧45个SV（含测试）不变，新增的SV仅为主机回放testbench。

原恢复顶层继续保持实际源S响应/J输出，目的写响应形成commit，完整身份及提交资格匹配后释放源。取消/局部复位请求/故障先排空再协调整组复位；1024拍不能排空时隔离显式重试，不强制复位活动义务。已写不回滚，失败输出无效；监督层保持终态/epoch水位。

| 内容 | 入口 |
| --- | --- |
| 研究与ISA及当前进展 | [共享详细报告](CONTROL_RESEARCH_AND_ISA_QUICK_REFERENCE.pdf) |
| 统一任务、服务及复现命令 | [compiler README](../../project/control_task_compiler_v1/README.md) |
| 输入形状与实际目标 | [schema](../../project/control_task_compiler_v1/schema.json) / [targets](../../project/control_task_compiler_v1/targets.json) |
| 可直接编译的示例 | [task](../../project/control_task_compiler_v1/example-task.json) / [inputs](../../project/control_task_compiler_v1/example-inputs.json) |
| 独立核对与镜像导出 | [audit](../../project/control_task_compiler_v1/audit.py) / [emit](../../project/control_task_compiler_v1/emit.py) |
| 第7步源码/输入/输出SHA | [compiler validation](../../work/Melodydt/179/control-compiler-validation.json) |
| 第6步恢复、命令15和时钟复位 | [recovery README](../../project/control_recovery_boot_v1/README.md) |
| 五类/J接口与可综合PM | [five](../../project/control_five_boot_v1/README.md) / [boot](../../project/control_boot_v1/README.md) |
| 输入版本 | [upstream lock](../../project/control_frontend_v1/upstream-lock.json) |

## 实测与限制

第7步软件1218/1218检查点：27正例、1134自洽SHA/CRC编码变异、52拒绝、3 CLI保护及2清单核对；服务器RTL回放162/162（九目标×两PM后端×三配置×三初态），每目标18。核对真实程序写/读/CRC、部署、S/T输出、结果身份、确认写字节、提交/ACK及主机背压。r001回放与r002最终软件补验的八个核心编译/参考/回放文件相同；软件重复运行只计一套。第6步624项为此前通过证据，本轮未重跑。

当前编译器只面向两个常驻任务和已绑定的原生配方，不是完整LLM/ONNX前端；无动态形状、循环/分支生成、任意规模调度、任意路由或格式转换。RAW128不证明数值兼容，initial声明是主机义务，数值参考域有限。定向通过率不是覆盖率。单clk_i、同步主机；无新多时钟CDC/RDC或物理资格。新增组合STA/面积功耗/CTS/物理未执行。

PR176固定08f2ea20，PR213固定b308f416、PR214固定f5fb8115，选用blob未变。完整内部历史与原STATUS本地维护，远端当前指南/共享报告/源码/技术索引保持可接续。

## 下一步

8．完整类型、状态和异常组合及覆盖；明确当前固定拓扑与有限数值域的资格边界。

9．冻结综合源码、参数、宏边界、SDC及复现交付。

Issue179仍in_progress，PR180 Draft未合并，审查人待指定。登记PR5 pending；看板缺board.json/Projects能力，状态unverified、同步pending，待具备权限管理员核验。全部本轮作业已结束，无聊天外自动监控。
