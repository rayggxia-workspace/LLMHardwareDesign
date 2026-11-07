# 两级控制当前接续入口

Issue179 / Draft PR180；Melodydt；2026-11-07 Asia/Shanghai。源码版本`dcd414b1fb313e6cc735a1daf9117af1b5b5a46f`，分支`task/179-local-block-continuation`。本页只描述当前控制接口、验证结论和下一阶段。

## 当前实现

综合前第1-4步已交付功能RTL与对应验证：规格冻结、可综合PM、公共装载管理器、五类统一接入。执行镜像为v2/64 bit，母控6条、局控10条实际执行指令；两个目标ID0/1、单时钟域、每局控1任务/1在途服务，8个全局令牌。目标周期3.333333333 ns保持不变。

`five_boot_top`编译期选择KIND=0..4对应U/F/C/P/J。每种变体是一母控、两个同类局控、三个16 KiB PM；五类同时驻留及异构数据连接不在第4步范围。MC/LC、PM及公共管理器保持原有源码，Block数据通路为冻结原生依赖。

| 阅读目的 | 入口 |
| --- | --- |
| 完整研究、指令字段和本轮进度 | [23页研究与ISA报告](CONTROL_RESEARCH_AND_ISA_QUICK_REFERENCE.pdf) |
| 五类接入、命令13/14、结果包和能力限制 | [五类顶层说明](../../project/control_five_boot_v1/README.md) |
| 公共装载命令0-12、PM和CRC32 | [PM/装载合同](../../project/control_boot_v1/README.md) |
| 执行指令编码 | [ISA合同](CONTROL_ISA_V0_1.md) |
| 机器可读能力和接口 | [profiles](../../project/control_five_boot_v1/profiles.json)、[host ports](../../project/control_five_boot_v1/host-ports.json) |
| 输入版本与逐文件依赖 | [上游锁](../../project/control_frontend_v1/upstream-lock.json) |
| 实际用例及输入/输出/源码散列 | [技术验证索引](../../work/Melodydt/179/control-five-boot-validation.json) |

U/F/C/P通过真实私有S路径预装和读回；J使用原生tag/slot/last片段提交及T输出释放协议，拒绝普通S_READ/S_WRITE。管理命令14写片段，13读提交结果；每J四项结果FIFO，最多一次JOIN/任务、1-4字，原生epoch为1-255。实际CALL的job/epoch/task_sequence随真实输出捕获，主机接受回复才归还结果槽；未消费RESULT/输出期间禁止新START和相关写入。执行ISA没有因此加长。

## 验证与边界

功能210/210：五类×两PM后端×七模式×三初态/种子；五类控制结构5/5，分别保留12个PM bank和两个对应原生组边界；同步输入后的相关回归66/66。功能验证执行真实原生组和存储模型，结构检查使用明示宏黑盒。场景通过率不等同功能覆盖率。初版非法epsilon输入及结构解析选项错误的修复记录保留于技术索引。

PR176固定08f2ea20，PR213固定e5daa288，PR214固定198e52c3；选用硬件未变，PR213两个生成/回归脚本按blob同步。新增组合映射时序、面积功耗、CTS和物理未执行，历史独立模块时序不替代当前组合。

## 后续顺序

5．选定支持的异构链，接通源保活、实际目的S提交和身份ACK。

6．补齐取消、复位、故障恢复及适用CDC。

7．统一受限任务描述到三端镜像编译，并独立核对。

8．收齐类型、状态、功能和异常矩阵。

9．冻结综合源码、参数、宏边界、约束和复现入口。

本任务继续in_progress，PR180为Draft且未合并，审查人待指定。项目登记PR5仍pending；看板缺配置及操作能力，状态unverified、同步pending，由具备权限管理员核验。

