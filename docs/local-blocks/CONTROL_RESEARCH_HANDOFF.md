# 两级控制当前接续入口

Issue179 / Draft PR180；Melodydt；2026-11-08 Asia/Shanghai；task/179-local-block-continuation。

## 当前进度：R8.1、R8.2有界交付完成，待独立审查（2026-11-08，Asia/Shanghai）

已形成五类main64接口/能力/身份合同，以及统一main64_boot_top候选：1母控、2局控、3个16KiB程序SRAM、12程序bank，Block私有S/T另计。每次只选两个端点，九配对是九种编译期变体，不是九局控同时驻留。main原始225份源保持一致；模块名字隔离可逆，P/U未使用close输入固定0，诊断/未用输出显式空接，J的十个未用输出绑定可逆补齐。

R8.1软件45/45，五类实际生成接口逐位核对；R8.2主矩阵189/189、同DUT部署保护补充27/27，合计216次执行，九配置完整native/control lint及通用结构综合、层次和1MC/2LC/3PM/12bank/2原生组计数9/9。无LATCH、MULTIDRIVEN、UNOPTFLAT、PINMISSING、WIDTHTRUNC控制禁项；其余警告保留。旧compiler1218、matrix141共1359软件检查重跑通过，与新45项分列，不扩大旧编译器能力。

全部程序从主机口写入、实际读回CRC、VERIFY/PREPARE/DEPLOY后执行，DUT无network_pm；三个PM及私有S使用既有SRAM封装与OpenRAM bank功能模型，控制综合将bank作为宏边界。本轮不替代存储器或组合物理验收。普通S预部署初始化，J每次join补充片段；U以真实SEND和对端S写后再读出回送核对数值；U/F/C到P验证被动RAW128复制，J/P只验证同组独立计算，不宣称J→P提交链。

源码已上传PR180，提交38fc1920；实际主矩阵DUT快照36f9b9bb，保护测试快照9113b585，补充逐文件证明DUT相同。输入/镜像/日志/结果SHA已在服务器及本机核验，主矩阵与结构100472_0-8、保护100484_0-8全部结束。先前失败轮次保留为历史，不计入216。执行ISA64位、单时钟、3.333333333ns目标不变；没有新增覆盖率、映射STA或物理结果。

下一步R8.3把新合同接入编译器和独立audit；R8.4完整身份/传输/取消/恢复（含J→P）；R8.5有界矩阵覆盖闭环；R8.6按新top重新冻结源/宏/SDC，再做组合时序及后端。当前为有界候选交付，不标全部前端完成。Issue179 in_progress，PR Draft未合并，独立审查待指定；登记pending、看板未核验。

## 当前实现入口

| 内容 | 入口 |
| --- | --- |
| R8.1机器合同和软件核对 | [contract.json](../../project/control_main64_boot_v1/contract.json)、[contract.py](../../project/control_main64_boot_v1/contract.py)、[test_contract.py](../../project/control_main64_boot_v1/test_contract.py) |
| R8.2顶层、主机和端点 | [README](../../project/control_main64_boot_v1/README.md)、main64_boot_top / main64_control_top / main64_host_front / main64_endpoint |
| 原始main源和选择 | [main64来源锁](../../project/control_main64_v1/main-lock.json)、[原生基线入口](../../project/control_main64_v1/README.md) |
| 原生生成与来源核验 | [stage.py](../../project/control_main64_boot_v1/stage.py)，五类实际端口和可逆名字隔离，补齐未用输出 |
| 完整主机驱动回归 | [run.py](../../project/control_main64_boot_v1/run.py)、[部署保护](../../project/control_main64_boot_v1/guards.py)；手写程序，不冒充R8.3编译器 |
| 结构及原始回执核验 | [structure.py](../../project/control_main64_boot_v1/structure.py)、[collect.py](../../project/control_main64_boot_v1/collect.py) |
| 本轮技术验证 | [R8.1/R8.2索引](../../work/Melodydt/179/control-r81-r82-validation.json) |
| 方案及指令详解 | [共享详细PDF](CONTROL_RESEARCH_AND_ISA_QUICK_REFERENCE.pdf)；完整原方案MD/PDF在本地原位维护 |

## 已确认的合同与取舍

topology为整组身份：main MC将它放入任务包[223:192]，LC要求相同才接收。故母控、两端LC、三份镜像及task记录共用0x01938000+KIND0*16+KIND1，类型单列，LC ID0/1。主机BEGIN错拓扑返回3。ABI0x01930001、capacity0x17630001；16字节对齐、128位PM口，镜像上限MC4736/LC8320字节，256指令、16 execution描述符。主机有完整CRC门，无proof旁路。

U E三源、N两源；main U无普通主机S_READ，明确拒绝而不等待。CF未预约写受部署状态约束，因此普通S初始化在DEPLOY前完成；部署后普通S_WRITE拒绝。J片段和已提交输出独立管理，每次join消耗片段租约，重复任务重新提交片段。CF主机读采用main已有verify_read选项的新封装，不能借用旧物理资格。可选对象close输入固定0，不将对象close程序授予当前三指令局控子集资格。

## 实际通过率和边界

| 检查 | 实际结果 |
| --- | --- |
| R8.1合同 | 45/45软件，五类实际接口一致 |
| R8.2功能主矩阵 | 9配对×7模式×3初态=189/189 |
| 部署后保护补充 | 9配对×3初态=27/27；DUT源逐项相同，保留坏ABI/拓扑BEGIN不破坏原部署等检查 |
| 控制结构 | 9/9；每配置1MC/2LC/3PM/12程序bank/2原生数据组；禁项为零 |
| 旧软件回归 | compiler1218/1218、matrix141/141；不等于接入新合同 |
| 管理结构 | check_project.py PASS；不替代硬件/物理/权限 |

主矩阵7模式：正常、重复任务、装载CRC期间复位、读回CRC破坏后重装、世代拒绝、ABORT恢复、非法native_op=0xffff（main返回5）后整组复位重装。三初态为(1,143)/(2,143)/(2,144)。216是执行次数，补充场景存在路径重叠；没有宣称216独立覆盖项或新的覆盖率。

U/U数值覆盖两/三源FMA、同时发送、目的S写后再次读出回送及实际写ACK；U/F/C到P仅指定被动RAW复制，不声称数值格式兼容；J/P只证明同组部署及两类独立计算。九种配对均为编译期双端点配置：U/U、F/F、C/C、P/P、J/J、U/P、F/P、C/P、J/P。

原始main64的123例、旧1690例及九配置旧综合回执保持各自源版本；当前候选不继承它们的物理资格。主存储器使用实际封装/已验收bank功能模型，不把功能模型里的数组视为重新完成物理验收；控制结构综合显式使用bank/native宏边界。新组合映射、WNS/TNS、等价、CTS/布线未执行。

## 接续顺序

1. **R8.3**：新合同接入task compiler、独立audit及装载计划；U三源/直接通路、整组topology和预部署初始化/J租约顺序一致；拒绝不支持项。
2. **R8.4**：补齐完整身份ACK、目的预约/所有权、取消排空、隔离/重试和协调复位，完成J→P提交链及适用的双向故障用例。
3. **R8.5**：上述统一系统的完整有界矩阵、断言和覆盖闭环，保留未覆盖清单，核对数值域和字节计数。
4. **R8.6**：按新top重建源/参数/宏及SRAM视图/SDC和复现包；再进入组合映射STA、网表和物理阶段。旧freeze仍属于旧top。

完整LLM图导入、动态形状及任意规模调度/路由仍属进一步目标。本分支当前母控仍两驻留目标；不能解释为五类同时存在或九局控系统。

## 状态与恢复

PR176再次读取仍08f2ea20，main仍c4d7b960。源码38fc1920已按显式清单上传。完整内部历史方案、STATUS、个人进度、ARCHITECTURE及服务器交接保持本地；共享当前指南、PDF、代码和技术索引单独上传。独立审查待指定、PR Draft未合并，Issue179保持in_progress。登记management-hub PR5 pending；无board.json/Projects工具，看板unverified、同步pending，待具备权限管理员核验。所有本轮作业已结束，不宣称聊天外自动监测。
