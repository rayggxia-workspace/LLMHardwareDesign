# 0004：普通LEF原始几何与合法访问证据分层

- 日期：2026-10-22（UTC+08:00）
- 状态：提议，随Issue16/PR18待审查
- 负责人：Liangruizhi
- 关联：[Issue16](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/16)、[宏端点合同](../MACRO_ENDPOINT_CONTRACT.md)

## 决定与依据

将普通LEF原字节、捕获manifest、原始PIN/PORT/LAYER/RECT与OBS库存作为独立可重放输入，不将矩形中心或单PIN当作已经合法的access point。保留PG、多PORT、未知字段及ORIGIN/SYMMETRY未声明状态；坐标保存微米原字符串与精确整数DBU，未经DEF合同不做全局变换。同PIN不同PORT不自动连通为免费feedthrough。

本轮仅支持声明的单宏ASCII LEF5.8 RECT profile，不支持语法明确拒绝，避免静默丢几何。原始三文件共约1.1MB，轻量ZIP约0.5MB，随私有仓库保留以便离线复核；不扩展到大数据库、detailed LEF或ref-project例行检查。

捕获及导出先提交清洁源码；manifest固定源码commit、配置与文件SHA。上游只提供审计摘要时，实测SHA必须说明没有逐文件预期值对照；runnercommit不能替代底层RTL或工具版本。图表必须与实际export manifest关联，归档sidecar必须与ZIP原文一致。

## 后果

可以先研究明确标注的几何必要条件，仍需逐bit RTL/Lib匹配、DEF方向、技术层/via/spacing/enclosure/OBS规则才能声称合法访问。PG、时序、边界负载、等价和硬宏资格单独验收；本库存不能证明物理H2/PPA。后续输入变化保留旧版本，另建attempt，不覆盖本轮证据。
