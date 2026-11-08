# 两级控制任务编译器

Issue179 / Draft PR180；负责人Melodydt。输入是有界语义任务JSON，输出是母控、局控0、局控1三份v2/64位镜像及装载计划。它用于本分支控制研究，完整模型图导入、动态形状和任意规模调度尚未实现。

## 版本与硬件绑定

| schema | target | 顶层及用途 |
| --- | --- | --- |
| main64-native-tasks/1 | main64/U/U等九配对 | main64_boot_top；R8.3编译与真实三PM执行 |
| safe64-native-tasks/1 | safe64/U/U等九配对 | main64_recovery_top；R8.4传输身份、J→P与协调恢复 |
| bounded-native-tasks/1 | five/*、recovery/* | 既有有界目标；保留原实现，不能代替新顶层资格 |

九配对为U/U、F/F、C/C、P/P、J/J、U/P、F/P、C/P、J/P。每次两个驻留任务，每端一个在途服务。三端共享cohort topology=0x01938000+KIND0*16+KIND1，类型与image ID另记；ABI0x01930001、capacity0x17630001。目标单时钟3.333333333ns；执行指令64位，L_EXEC引用独立128字节execution记录。

[main64形状](main64-schema.json)、[目标登记](main64-targets.json)、[safe64形状](safe64-schema.json)、[目标登记](safe64-targets.json)与编译器同版维护。JSON Schema只约束形状；逐类型源数、上下文、逐字有效性、路线和容量仍由编译器与独立审计强制检查。宽整数需无损处理，以bin/mem的完整字节为执行依据。

## 语义操作与资源约束

- U/F/C的ucf操作声明lane、meta、src、dst。U E支持两/三源FMA，N最多两源；CF支持已声明的G/E配方，C另有R上下文装载/读取。
- u_direct描述已配置N→E配对。N统计8元素的重放预算只能消费一次，普通N5和配对N5共享该预算。
- CF使用meta bit63选择已验证的G→E路径；P使用p_route/p_gate_direct选择M→G。P直连把两个S16结果打包，区别于普通矩阵S32存储。
- P提供p_load、p_config0/1、p_store、p_gate；J提供join、release，一任务一次JOIN、最多4字，epoch1..255。
- 不提供任意native字段逃逸口。缓冲区不重叠、读前完整产生、源/目的归属、上下文顺序和最大16条展开服务均检查。

母控程序使用G_CALL/G_WAIT/G_END；局控使用L_EXEC/L_WAIT/L_END。其他ISA编码的存在不等于本编译器已经开放完整ISA。

## 编译、审计与装载

compiler.py按schema分派。main64_compiler.py绑定R8.1能力合同；safe64_compiler.py另绑定恢复/路线合同。对应audit独立实现语义准入和完整字节构造，不导入编译器、codec或image。它检查头、指令、task、执行记录、填充、身份、SHA/CRC及路线计划。数值参考单独覆盖明确的有限样例域。

host.py按版本生成主机计划：RELEASE→三端BEGIN/WRITE16/READ16/VERIFY/PREPARE→完整供数→DEPLOY/START。emit.py对新版本只导出到PREPARED的镜像计划，调用方完整供数后再部署。普通S写只在部署前进行。J先消费提交FIFO，再读普通S；每次J任务重新提交片段。U无普通S_READ，数值通过实际SEND到目的私有S验证。

main64仅编译U/F/C0→P1的RAW128被动复制，母控等源任务提交后才CALL P。safe64增加双U写入后读回回送、J提交输出到P的四字链，以及op15管理路线配置。512位传输ticket是内部身份消息，不改变64位执行指令。P不生成RESERVE/RECEIVE，J不生成SEND；[恢复格式与边界](../control_main64_recovery_v1/README.md)单独说明。

## 使用入口

```bash
python -B project/control_task_compiler_v1/compiler.py task.json --output bundle.json
python -B project/control_task_compiler_v1/emit.py task.json bundle.json --out audited-output
python -B project/control_task_compiler_v1/test_main64.py --out main64-software.json
python -B project/control_task_compiler_v1/test_safe64.py --out safe64-software.json
```

main64_fixtures.py / safe64_fixtures.py提供完整语义任务与数据；相应generate脚本输出经独立审计的三端镜像和主机回放。仿真/结构综合需依项目远程规则在授权Slurm分配内运行，入口为run_main64.py、run_safe64.py和[监督顶层README](../control_main64_recovery_v1/README.md)。

## 本轮验证

R8.3软件1301/1301、服务器RTL81/81；R8.4软件1304/1304、集成279/279、链路单元21/21、控制结构9/9；旧compiler1218和matrix141重跑通过。输入、镜像、日志和源SHA在服务器与本机逐项核验；元数据对照在运行后补齐，未改变DUT或程序镜像。

[当前方案](../../docs/local-blocks/CONTROL_RESEARCH_HANDOFF.md)、[R8.3索引](../../work/Melodydt/179/control-r83-validation.json)、[R8.4索引](../../work/Melodydt/179/control-r84-validation.json)记录实际范围。执行次数不是完备覆盖证明；R8.5覆盖闭环、R8.6新综合冻结及后端时序仍待执行。PR未合并前不视为独立验收完成。

