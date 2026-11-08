# 两级控制当前接续入口

Issue179 / Draft PR180；Melodydt；2026-11-08 Asia/Shanghai；task/179-local-block-continuation。

## 当前状态

R8.1/R8.2合同与实际三PM候选之后，R8.3正式任务编译/独立审计和R8.4有界传输/协调恢复已完成本轮研究验证。R8.3服务器81/81；R8.4集成279/279（81正常、198故障/恢复）、链路单元21/21、九配置控制结构9/9。最终软件main64 1301/1301、safe64 1304/1304；旧compiler1218和matrix141重跑通过。执行次数不等于独立覆盖项，尚无新覆盖率、映射STA、等价或物理签核。

原始main c4d7b960225份源保持逐字锁定；CFJ247、U31和共享母控4份依赖继续校验。R8.4在生成副本的服务边界加入halt/排空/观测，保留main自身LC与native逻辑，不以旧frontend局控覆盖P/U。PR176仍08f2ea20，本轮没有新增上游更新。

## 实现与复现入口

| 内容 | 正式入口 |
| --- | --- |
| 原始main64源锁 | [control_main64_v1](../../project/control_main64_v1/README.md) |
| R8.1/R8.2实际三PM与能力合同 | [control_main64_boot_v1](../../project/control_main64_boot_v1/README.md) |
| R8.3任务、独立审计、装载计划 | [task compiler](../../project/control_task_compiler_v1/README.md)、main64_compiler.py、main64_audit.py、main64_host.py |
| 新任务形状/目标登记 | [main64-schema.json](../../project/control_task_compiler_v1/main64-schema.json)、[main64-targets.json](../../project/control_task_compiler_v1/main64-targets.json) |
| R8.4受监督顶层与精确管理编码 | [recovery README](../../project/control_main64_recovery_v1/README.md)、[机器合同](../../project/control_main64_recovery_v1/contract.json)、generate.py/stage.py |
| R8.4编译/独立路由审计 | safe64_compiler.py、safe64_audit.py、[safe64-schema.json](../../project/control_task_compiler_v1/safe64-schema.json)、[safe64-targets.json](../../project/control_task_compiler_v1/safe64-targets.json) |
| 验证索引 | [R8.3](../../work/Melodydt/179/control-r83-validation.json)、[R8.4](../../work/Melodydt/179/control-r84-validation.json) |
| 指令与方案详解 | [共享PDF](CONTROL_RESEARCH_AND_ISA_QUICK_REFERENCE.pdf)，原完整历史方案MD/PDF本地原位维护 |

## 当前硬件合同

每次是两个驻留端点，九种编译期配对：U/U、F/F、C/C、P/P、J/J、U/P、F/P、C/P、J/P；不是九局控同时驻留。1MC/2LC/3PM，每PM16KiB/4bank；MC已有内部PM，仅增加两个LC PM。Block私有S/T另计。单时钟、64位执行指令、目标3.333333333ns保持。功能bench10ns匹配bank模型，不代表修改实现周期，也不能代替新组合STA。

三镜像共享cohort topology=0x01938000+KIND0*16+KIND1，类型另列、LC ID0/1；ABI0x01930001、capacity0x17630001。当前准入MC4736/LC8320字节，256条指令、16 execution表项。程序由主机WRITE16、真实READ16/CRC、VERIFY/PREPARE，再完整初始化后DEPLOY/START；无proof或测试台PM旁路。64位L_EXEC引用独立128字节执行记录，新的512位传输ticket不是加长执行指令。

U E允许两/三源，N最多两源；N统计8元素的归一化重放预算被普通N5与N→E配对共同消耗，禁止重复消费同一窗口。CF G→E、P M→G和J E→S保持main路径；P M→G为两S16结果打包，不能按单S32建模。U无普通S_READ，结果经真实SEND验证。J每次重新提交片段，普通J输出先消费提交FIFO再做普通S主机访问。所有ordinary S初始化写在DEPLOY前。

## 传输与恢复

R8.3 schema main64-native-tasks/1：U/F/C→P以源任务完成后再CALL P的顺序做RAW128被动复制；J/P为独立任务。R8.4另用safe64-native-tasks/1与受监督顶层，不给J编造SEND或给P编造RESERVE/RECEIVE。

R8.4每方向一个保持槽与512位ticket，绑定两端服务/预约身份、generation、START sequence、topology、两个image ID、两个Block ID、地址、tag和字索引。只有目的实际SRAM响应记commit；错误ACK不释放源。U/U双向写入后从目的S读出回送，J→P逐字检查提交FIFO身份，最多4字，源终端保持到完整路由提交/ACK，P随后启动。RAW128仍不提供数值格式转换。

halt阻止新的native服务，已接受的宏命令与存储回执排空。已提出的写valid不可撤回；尚未提出的字可以显式abort但不记commit。外层主机/失败终端与epoch水位跨内层复位保留。NORMAL→DRAIN→RESET→WAIT_READY；排空超时进QUARANTINE并保留所有权，消费失败结果后重试。用户mask只作诊断，实际为完整组协调复位，随后新epoch完整重装和供数。失败终端只消费一次。

op15为主机管理命令，sub0取消、sub1协调复位、sub2状态、sub3隔离重试、sub4路线配置。sub4在未运行/未部署且无待处理义务时接受：direction1、base10、count3、first_service_sequence32、stride8、tag32，完整位段见README。编译器/audit/目标登记同版绑定；没有改变执行ISA。

## 实际验证

| 检查 | 结果与版本 |
| --- | --- |
| R8.3 RTL | 81/81，快照ddfa9ae，九配对×三程序×三初态；Slurm100527_0-8均COMPLETED/0:0 |
| R8.3软件 | 1301/1301，含后补2项目标/形状核对；原1299项及初次失败来源保留 |
| R8.4 RTL | 279/279，快照8a42dba，Slurm100544_0-8均COMPLETED/0:0 |
| R8.4软件 | 1304/1304，独立字节/路由变异、语义拒绝、CLI与目标元数据 |
| R8.4结构/单元 | 9/9通用控制综合及禁项lint；链路21/21，单元目的回执由协议驱动器提供 |
| 来源与实际存储 | 输入607/628份、镜像/日志/结构SHA在服务器和本机核验；R8.4当前31份仓库源码（含主机测试台）与运行逐字相同 |
| 旧软件与管理 | 1359/1359，check_project.py与线上CI分别记录；不等同新硬件或物理资格 |

R8.4故障覆盖：精确取消/外来取消拒绝、外来native返回身份、非法native自动恢复、已接受写取消、错ACK与源保活、超时隔离及重试、未提出字取消、完整组复位和双U反方向错generation ACK。每次故障后使用不同epoch/地址/镜像/输入重新装载，验证正常执行、旧epoch拒绝、无重复终端、halt无新native接受。七类链路单元另查不可撤回offer和假ACK。

R8.3首轮100518、R8.4预检100537/100540保留原始记录，不累加到最终通过率。R8.3修正N预算、P打包参考和J消费顺序；R8.4修正未提出字故障注入的信号别名，并在最终同版完整重跑。没有删除检查绕过失败。

## 下一步

- **R8.5**：建立统一覆盖模型，扩展周期交错/回复背压/取消与结果竞态/错误身份等未覆盖清单，完成覆盖闭环；现有通过次数不是完备覆盖证明。
- **R8.6**：按受监督新顶层重新冻结完整源码、参数、层次边界、SRAM视图、SDC及综合复现包。当前9份通用结构综合不是映射时序。
- 随后组合映射STA、等价/网表、CTS/布线及物理验收。旧1690例、main独立时序或旧综合包不授予新组合资格。

完整LLM图导入、动态形状、任意规模调度/路由和数值格式转换仍是后续目标。当前Block RTL不再是这些控制侧工作的主要阻塞。

## 协作状态

本轮成果仍经Draft PR180交付，独立审查人待指定，未自合并；Issue179整体仍in_progress，R8.5/R8.6未完成。登记management-hub PR5 open未合并=pending；无board.json或Projects工具，看板unverified、同步pending，待具备权限管理员处理。完整内部历史方案、项目/个人进度、ARCHITECTURE和服务器交接只在本地维护；共享当前指南、PDF、源码和技术索引独立上传。所有本轮作业已结束，没有设置聊天外监测。

本轮源提交：[eb524aa7](https://github.com/rayggxia-workspace/LLMHardwareDesign/commit/eb524aa7cbededb89df681f8ffd8a6b853f8ff52)；41个源码与接入路径逐blob读回相同。共享PDF55页、原方案PDF53页，全部页面已渲染检查。最终报告提交、管理CI与协作回执见PR180的当前说明。
