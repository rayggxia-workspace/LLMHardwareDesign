# Issue #228：通用上层布线算法交付

关联 [Issue228](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/228)、PR227接口合同。
基于 `0513ca9470bc2ac28d56571d8eb1cdaf75c36818`，独立分支task/228-generic-router。
用户已澄清需要通用布线算法，未按Qwen3.5构造路线或修改其综合映射。

- 正式代码、输入格式与复跑命令：`project/experiments/upper_router/README.md`。
- `ripup-route.json`/`ripup-check.json`：合成两网例子，第一轮仅a完成，第二轮优先b后两网完成；
  实际逐位输出与独立几何检查保留。不是实际底座端点或制造规则验收。
- 21项路由测试通过，包括128位、30个独立Dijkstra对照、多接收端、障碍/包围/断连负例，
  以及#227 manifest适配、基于需求/底座/规则的失败反馈。
- 原有40项接口/DP/缓存相关测试回归通过；输入和源码SHA、实际日志见receipt.json和tests-*.log。
- 只声明给定粗网格/保守矩形规则内合法。未取得真实产品pin导出、GDS/ODB写出、foundry DRC、
  原生层XOR、RC提取、负载或300MHz时序资格。完整3B及任何模型整网未重跑。
- 未改DP、缓存、已有模型路径、他人工作树或远程作业，未使用子Agent。

规则rayggxia-project-collab1.0.0，项目llm-hardware-design，认证/执行人YUZE-LU。
工程实现待独立审查，不自批准/合并/关闭；登记沿用management-hub PR5 pending，
缺config/board.json，Projects unverified/同步pending，沿用接入Issue7。
