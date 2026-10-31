# M 实际完整接口图

Refs #121 / PR #122。actual-escape.json来自已通过262全端口P2任务，SHA逐字节匹配封存receipt，不重新跑物理或构造缺失连接。

- all-ports.png/svg：全部275个真实信号位。
- cmd-data16.png/svg：cmd_data[0:15]真实输入子集。
- response-data16.png/svg：rsp_data[0:15]真实输出子集。

三张PNG已查看，全部六文件SHA与来源/生成器由plot-manifest.json绑定。灰色区是固定原生宏边界，不是重绘的内部布线；上层只是已验收的P2几何，没有组合接口时序或12层工艺资格。使用独立M绘图入口，保持T原生成器及其既有证据不变。
