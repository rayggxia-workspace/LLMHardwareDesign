# 两级控制当前接续入口

Issue179 / Draft PR180；Melodydt；2026-11-07 Asia/Shanghai。分支task/179-local-block-continuation。本页为当前控制合同、证据和接续入口。

## 当前交付

综合前第1-6步已有功能RTL与验证：规格、可综合PM、公共装载、五类统一接入、四条异构提交链、取消/故障/协调恢复。执行ISA仍v2/64 bit，母控6条、局控10条；两个目标、单时钟域、每LC一任务/一在途服务。目标周期3.333333333 ns。

recovery_boot_top以目标0为U/F/C/J之一、目标1为P。固定RAW128有向链、每任务双端各CALL一次，序号历史成对，无隐式格式转换。源保持实际S响应或J输出，目的真实写响应形成commit；完整job/epoch/task/service身份及提交资格匹配后才释放源。既有36个SystemVerilog（含测试）保持不变。

新增外层监督FSM与排空接口：NORMAL、DRAIN、RESET、WAIT_READY、FAILED、QUARANTINE。取消/局部复位请求/组故障停止新服务，保留已接受请求和实际响应；目的已offered请求不可撤销。排空且无主机回复在途后整组内层复位，监督层保留失败结果和epoch水位。单端复位请求提升为整组协调恢复。

1024拍无法排空进入隔离，不强制复位活动义务、不伪造信用或提交。结果消费后仍禁止START；底层恢复后显式RETRY_DRAIN，再以更高epoch重装及重建数据。已提交写不回滚，隔离计数仅为超时快照。有效RESULT与未就绪查询分别处理，保证回复稳定且作业终态不丢失、不重复。

| 内容 | 入口 |
| --- | --- |
| 研究、ISA及当前进展 | [研究报告](CONTROL_RESEARCH_AND_ISA_QUICK_REFERENCE.pdf) |
| 第6步顶层、恢复与管理命令15 | [recovery README](../../project/control_recovery_boot_v1/README.md) |
| 机器可读命令、状态及有效结果位 | [recovery profiles](../../project/control_recovery_boot_v1/profiles.json) |
| 单时钟与整组复位边界 | [clock/reset contract](../../project/control_recovery_boot_v1/clock-reset-contract.json) |
| 同版624项、结构与源码/输出SHA | [第6步技术索引](../../work/Melodydt/179/control-recovery-validation.json) |
| 原异构服务及提交链 | [hetero README](../../project/control_hetero_boot_v1/README.md) |
| 五类及J专用输入输出 | [five README](../../project/control_five_boot_v1/README.md) |
| 可综合PM及公共装载 | [boot README](../../project/control_boot_v1/README.md) |
| 执行编码及逐文件输入锁 | [ISA](CONTROL_ISA_V0_1.md) / [lock](../../project/control_frontend_v1/upstream-lock.json) |

## 实测与边界

第6步同版恢复456/456（4链×2后端×19模式×3初态）、正常回归168/168（原7模式），共624/624；结构4/4，时钟/复位合同静态核对4/4。功能用实际原生组和bank数据通路；结构明示黑盒，保留12个PM bank及一源组、一P目的。实际读回验证未提交毒值保持、已提交完整128 bit写保留，以及新epoch重装后的新任务。定向通过率不是功能覆盖率。

当前单clk_i、主机同步，外层和内层均异步断言/两拍同步释放。CDC对本实例不适用；合同静态核对不等同专用CDC/RDC或物理签核。恢复包溢出/饱和诊断未采集，ACK计数含负向取消确认。新增组合映射STA、面积功耗、CTS及物理未执行。

PR176固定08f2ea20，PR213固定39ce9aeb、PR214固定f5fb8115；本轮选用文件blob未变。早期失败及修复保留于索引，最终以同版矩阵验收。

## 接续

7．统一受限任务描述到MC/LC镜像，联结能力/拓扑校验与独立参考。

8．补齐完整类型、状态、异常组合与覆盖，避免把当前四链等同任意路由资格。

9．冻结综合源码、参数、宏边界、约束和交付清单。

Issue179保持in_progress，PR180 Draft未合并，审查人待指定。项目登记PR5 pending；看板缺配置/工具，状态unverified、同步pending，待具备权限管理员核验。
