# 第2步：控制用例与独立预期轨迹 v0.1

本目录定义空任务、单M命令、接收先行16B交接三组程序及描述符，另有非正常peer错误注入参考。它是[控制研究](../../docs/local-blocks/CONTROL_REFERENCE_CASES_V0_1.md)的预期结果依据，不是从机器码执行PC的解释器，也不是控制RTL／Block仿真。

- cases.json：人工定义程序、任务／对象／执行／传输记录、有限端点和观察边界。
- golden_traces.json：独立编排的3条正常＋1条错误参考事件轨迹，包含停顿采样。
- oracle.py：序列化指令／记录片段，检查输入轨迹的返回信用、身份、单在途服务、ACK／对象义务及握手保持。
- encoded_cases.json：7段程序共29指令／464B，描述符为分离片段；没有完整镜像头／段装配／装载器。
- test_oracle.py：27组正例及违规轨迹测试，包括独立机器字向量、ACK／序号／错误／释放与通道检查。

```powershell
python -X utf8 -B project/control_cases_v0_1/oracle.py encode --output project/control_cases_v0_1/encoded_cases.json
python -X utf8 -B project/control_cases_v0_1/oracle.py check
python -X utf8 -B -m unittest discover -s project/control_cases_v0_1 -p test_oracle.py -v
```

采样是整包级事实；没有模拟32bit控制消息的16个flit，也没有验证peer是否真实执行S写或宏计算。原生M无任务tag，轨迹中的task／service_sequence是观察器关联元数据，不是新增原生pin。M清有效位正常返回成功；错误轨迹为显式非正常peer注入，不是M RTL观察结果。

此子集仅2局控、1活动任务／局控、4服务、3对端点和256条记录以内；正常案例只用2对端点、3服务和单片16B RAW数据。不支持循环／条件／一般图／取消复位／多片段执行验证，也不证明死锁自由或性能。RX令牌采用“本地写确认＋ACK发送被接受后完成”的保守用例约定；TX必须收到远端ACK。状态事件用于检查控制义务，不证明相应指令已执行。

编码与记录打包复用control_isa_v0_1，单M服务字段复用control_contract_v0_1。后续执行器／控制RTL应独立生成实际观察轨迹，再对照本参考；不能把参考轨迹自检写成DUT通过。
