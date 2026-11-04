# 母控／局控第2步：控制用例与独立预期轨迹 v0.1

2026-11-04 18:21，Asia/Shanghai（UTC+08:00）。[Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179) / [PR180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)，负责人Melodydt；父提交afd96b359c369c7ea039cca2c642677b0ab5f665。

本轮继续[总方案](TWO_LEVEL_CONTROL_PLAN.md)，落实8步路线的第2步“先定义程序用例和预期控制轨迹”。**这不等于原R2二进制执行器已完成。** 本分支只研究母控／局控；Block实现、数值计算和系统物理仍是外部任务。

## 1. 输入、输出和假设

输入为已交付的[ISA v0.1](CONTROL_ISA_V0_1.md)、[P接口合同](CONTROL_INTERFACE_CONTRACT_V0_1.md)及研究ABI65537。程序与描述符假定已经核验并驻留，装载器尚未研究完成。本轮产物在[control_cases_v0_1](../../project/control_cases_v0_1/README.md)，包含3组程序、11份分离记录、4条参考轨迹和轨迹属性检查器。

三组共7段程序、29条指令／464B；描述符／事件绑定共720B。这些只是编码片段，不包含完整镜像头、段地址布局或装载流程，不能直接声称可部署。

参考轨迹由人工独立编排，不由检查器或未来DUT生成。检查器读取观察事件，核验身份／信用／服务／对象／ACK条件；不解释PC、不逐指令执行，也不证明peer真的完成了存储。采样序号不是实际硬件周期，停顿长度不能作为性能数据。

## 2. 空任务：最小母局控调用

母控为 G_CALL(a0,b0,c0) → G_WAIT(x1) → G_END；局控程序仅 L_END。任务无对象、原生服务或保留上下文。

预期事件为：预约完成返回信用 → 整包CALL被接受 → 成功终态整包被接收 → 母控消费全局令牌 → 全局结束。CALL及终态均有valid=1／ready=0的保持采样，后续ready=1时payload和身份必须不变。

本用例验证参考协议的最小闭环，不包含程序装载；“通过装载接口启动空任务”的实际里程碑仍待后续实现。

## 3. 单服务：M清有效位

母控与空任务相同；局控为 L_EXEC(a0,b0,c0) → L_WAIT(x1) → L_END。execution记录为resource=M、service=NATIVE_CMD、native_op=6、native ABI65537；native字全0。

拟议原生字段为 cmd_op=6、cmd_index=0、cmd_data=0。先接收服务请求并分配局部token0，再等待M命令握手，最后消费匹配响应。L_WAIT须等响应消费，不能把命令接单或busy下降当成完成。清有效位不复位scale，完整M结果上下文处理仍遵守第1步合同。

参考中一次命令和一次响应均有背压保持；令牌与service_sequence在接受时关联。M本身没有job／epoch／服务tag，轨迹中的关联元数据属于适配观察层，不改变原生端口。

附加错误轨迹显式令peer返回rsp_error=1，要求TASK_ERROR／status9(NATIVE_ERROR)，并进入全局错误结束；不能报告成功DONE／G_END。**合法M op6正常应返回成功，这是一项非正常peer注入，不是原生M RTL结果。** 一般取消／协调复位和错误域处理仍待模型与RTL研究。

## 4. 有限依赖：接收先行的16B交接

测试只有局控0（生产侧）、局控1（接收侧）及一个有限输入peer。peer编号255是此用例的外部输入端点，不代表另一个已实现Block。端点需求为255→0的ingress、0→1的cross，各带反向ACK；拓扑ID只标记研究fixture，不是物理连通证据。

| 程序 | 指令顺序 |
|---|---|
| 母控 | CALL接收侧(token0) → G_EVENT READY → CALL生产侧(token1) → G_WAIT(mask3) → G_END |
| 接收局控1 | OPEN对象0 → RX → MOVI标量1 → REPORT READY → WAIT RX → DROP → END |
| 生产局控0 | OPEN对象0 → RX输入peer → WAIT → TX到局控1 → WAIT → DROP → END |

两侧均只有一个16B RAW对象、静态地址、无保留对象／上下文。生产侧RX与TX复用局部token0，必须先消费旧完成再复用，service_sequence分别为0和1。任务input mask只声明输入义务，不表示OPEN后的对象已经有效。

生产侧对象的数据由输入peer经RX和存储确认建立，不能从初始RAM或TB内部注入推定有效。cross传输必须等接收侧RX准备并且母控已消费READY；数据头和ACK均为64B，payload仅一个128bit字。

完整事件链为：RX准备 → READY → 母控消费READY → 生产任务 → 输入DATA／本地写ACK → 输入ACK发送 → RX令牌完成／消费 → TX DATA → 目的写ACK → 目的ACK发送 → 源收到匹配ACK → TX令牌完成／消费 → 源DROP。目的端在ACK发送被反向端点接受后可结束自身接收义务，源仍须等ACK实际接收。

此用例保守地让RX token在“实际写确认且ACK发送被接受”后完成；该点比仅本地写确认更强，不应外推为所有未来RX profile。TX完成不能被降为接单、发送完或目的刚生成ACK。

## 5. 观察格式与检查条件

观察分为整包／原生接口的valid-ready采样，以及open／服务接受／wait／drop／全局退休等状态事实。CALL／READY／终态用真实64B记录布局；DATA／ACK头也按ISA位布局解析。状态事实可由未来执行器／RTL观察器提供，本轮只是参考输入。

检查内容包括：

- 完成返回空间先预约；全局／局部令牌不得重复分配或消费。
- 当前job／epoch／task_sequence、服务序号、镜像／拓扑以及DATA／ACK端点／边／分片／对象版本／16B确认相符。
- valid且未ready时，payload及观察关联元数据一直保持；原生响应只能出现在声明通道。
- M响应不能先于命令接受，WAIT不能先于相应完成；服务序号不能随令牌复用而回退。
- READY须在RX准备之后；生产CALL须在READY被母控消费之后。
- 存储ACK须有对应数据，ACK发送须有真实存储确认观察，TX完成须有匹配ACK接收。
- DROP／局部终态／全局结束不得留下未退休对象、服务、信用或事件。
- peer错误必须传播为错误终态，不能用成功完成隐藏。

模型硬上限为2局控、4服务、3对端点、256条观察；正常用例更小。每侧仅一个对象；原生M单在途，消息／端点保持均有限。没有一般调度器、PC执行器、逐flit网络或无限队列。

## 6. 实际检查与边界

27组检查覆盖4条参考轨迹、独立空任务机器字、消息／ACK位布局、背压、信用、READY、完成／释放、旧tag、重复ACK／响应／消费、服务序号、错误传播和通道关联。先前负例中额外借用复用了ingress端点而被更早的绑定检查拒绝；已改为独立有限端点，未弱化检查器，再完整重跑。

参考检查通过意味着人工轨迹及所覆盖属性一致，**不表示实际控制器执行了程序**。输出明确instructions_executed=false、rtl_tested=false、complete_image=false。取消／复位、循环／条件、多任务、多片段、任意图、完整数值和死锁自由均未验证。

```powershell
python -X utf8 -B project/control_cases_v0_1/oracle.py encode --output project/control_cases_v0_1/encoded_cases.json
python -X utf8 -B project/control_cases_v0_1/oracle.py check
python -X utf8 -B -m unittest discover -s project/control_cases_v0_1 -p test_oracle.py -v
```

本轮[来源](../../work/Melodydt/179/control-case-sources.json)与[验证](../../work/Melodydt/179/control-case-validation.json)记录实际命令／版本／SHA；未启动服务器、RTL或物理任务。下一步定义完整镜像装配、配置装载／有效互锁以及失败恢复，再用独立二进制执行器产生实际轨迹对照本参考。

## 7. 上游与总方案同步

每次开始／恢复及上传前检查PR176，差异写入[同步记录](../../work/Melodydt/179/pr176-sync.json)。本轮开始仍08f2ea20且无讨论变化，上传前再次读回；不创建定时监测。

按用户补充要求，每轮必须把目标、上游版本／差异、产物、实际验证、结论与限制、下一步及PR/commit入口补入总方案；不能只更新聊天、Issue或个人进度。总方案保留当前阶段摘要和逐轮记录，历史阶段不因参考测试通过而升级为硬件完成。
