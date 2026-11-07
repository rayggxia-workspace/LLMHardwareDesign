# 两级控制当前接续入口

Issue179 / Draft PR180；Melodydt；2026-11-07 Asia/Shanghai。分支task/179-local-block-continuation。本页仅列当前接口、验证结论与代码入口。

源码交付`ce4042031dbe89654602b89332b77cd7cb10a21b`；[25页研究与ISA报告](CONTROL_RESEARCH_AND_ISA_QUICK_REFERENCE.pdf)原位更新。

## 已交付与范围

综合前第1-5步已有功能RTL及验证：规格、可综合PM、公共装载、五类统一接入、四条异构提交链。MC/LC执行ISA保持v2/64 bit，实际母控6条、局控10条；两个目标、单时钟域、每LC一任务/一在途服务。周期目标3.333333333 ns。

hetero_boot_top以目标0为U/F/C/J之一、目标1为P，支持U→P、F→P、C→P、J→P。固定有向RAW128链，每任务两个端点各CALL一次，任务序号历史成对；无任意路由或隐式格式转换。原29个控制/PM/五类RTL不变。

源保持实际S读响应或J提交输出；目的先预约地址及期望身份。实际P写S响应形成commit，源独立确认commit已见且job/epoch/task_sequence/service_sequence全匹配才接受ACK并释放源。早到或其他身份ACK不生效。SEND/RESERVE/RECEIVE分别是L_EXEC的原生服务0x101/0x103/0x102，不是新增执行指令；J片段主机命令13/14继续明确区分。

| 内容 | 当前入口 |
| --- | --- |
| 研究、指令格式与最新进展 | [研究与ISA报告](CONTROL_RESEARCH_AND_ISA_QUICK_REFERENCE.pdf) |
| 异构顶层及详细字段 | [control_hetero_boot_v1](../../project/control_hetero_boot_v1/README.md) |
| 机器可读拓扑 | [profiles](../../project/control_hetero_boot_v1/profiles.json) |
| 输入/输出/源码散列与用例 | [异构验证索引](../../work/Melodydt/179/control-hetero-validation.json) |
| 五类接入与J专用接口 | [control_five_boot_v1](../../project/control_five_boot_v1/README.md) |
| PM和公共装载 | [control_boot_v1](../../project/control_boot_v1/README.md) |
| 执行编码 | [ISA合同](CONTROL_ISA_V0_1.md) |
| 逐文件输入版本 | [上游锁](../../project/control_frontend_v1/upstream-lock.json) |

第5步功能168/168、控制结构4/4；四链×两PM后端×七模式×三初态/种子。验证正常、offer停顿、连续任务、链路中共同复位重装、四身份字段错误ACK、错误预约、提交前正确身份ACK。目的完整128 bit S读回与独立参考比较。结构以明示宏黑盒检查12个PM bank、一源组和一目的P；完整原生路径用于功能验证。场景通过率不是覆盖率。当前无新增组合STA或物理资格。

PR176固定08f2ea20，PR213固定2a6d0d51、PR214固定f5fb8115；选用文件blob未变。原始失败及修复原因见技术索引。第4步210/210和5/5证据继续保留为此前阶段结果。

## 下一步

6．取消、错误终止、复位和适用CDC；重点闭合在途写、源保活与残留预约。当前异常恢复限定共同复位及三端重新装载。

7．统一受限任务到三端镜像编译并独立核对。

8．完整类型、状态、异常矩阵。

9．冻结综合源码、参数、宏边界及约束。

Issue179仍in_progress，PR180 Draft未合并，独立审查人待指定。项目登记PR5 pending；看板缺配置/工具，unverified与同步pending，待具备权限管理员核验。
