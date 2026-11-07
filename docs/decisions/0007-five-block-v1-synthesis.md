# 0007 五类逻辑 Block、独立叶宏与同源综合闭环

- 状态：proposed，文档待 PR 审查。2026-11-07 按用户已确认的架构约束修订；实现资格独立验收。
- 合同版本：`five-block-v1/2026-11-07`。关联 [Issue #184](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/184)、[PR #185](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/185)、[#176](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/176)、[#180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)。
- 延续 [0004 分阶段冻结](0004-block-library-base-freeze.md)。详见[实施与验收合同](../local-blocks/FIVE_BLOCK_V1_PLAN.md)。本记录此前为 proposed，本次原位修订；[旧 c60dd412 记录](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/c60dd412caa1d2a01c7275ed07b788060d321769/docs/decisions/0007-five-block-v1-synthesis.md)保留历史。

## 决定

1. P/U/C/F/J 是局控归属形成的五类逻辑执行组，每类只选一个实现和 ABI，联合底座实例数为 3/2/1/1/2。全局布局直接摆放独立功能叶宏和标准单元局控/辅助电路。聚拢和规整仅作软约束；联合顶层不得把五类组合硬宏外框或组合 LEF 作为拼装单元。
2. 使用 #203 的 16 KiB S_base/S_P 与 #205 的紧凑 G/E，其他叶宏按匹配合格视图锁定。客户端仲裁、S 响应归属、E 分拍输入、预制选择和 RX/TX 保持由真实辅助资源承担。局控、有限程序存储、取指和装载均落实并计价；暴露 PM 接口不构成程序 RAM 已实现的证据。#213/#214 的最新修改与最终合格源码/物理包须逐项绑定后集成。
3. 控制归属及必需 PG/CTS 等共同资源随底座固定。主要数据路径，包括组内路径，默认留待顶层后制；少数预连逐项说明用途与限制。真实叶宏或适配单元 pin/M10 导体作为端点，逐条记录固定、候选和不支持路径。选择器、驱动、保持和必要中继在冻结前落实。五类均须验证实际局部后制路径。
4. 同一映射生成程序和逐位线束，保留一个产品级 DP，对 Attention/GDN/FFN 及 prefill/decode 的真实物理需求取并集。候选只改变已锁定硬件上的服务、实例、分片、调度和路径。根据真实接点、轨道、负载和时序反馈重选；未接候选不得作为合格部署。交接签名必须保留全部未来相关状态，近似搜索公开剪枝与误差。
5. 面积从真实叶宏和新增标准单元出发，明确程序存储、仲裁、算术、选择、保持与驱动的成本。报告父层实际面积分类、空白和保留区依据，比较相同资源下至少两份紧凑布局。旧组合外框、旧 S 尺寸和约 28.28 mm² 估算不再作为实施约束。
6. 冻结完整底座的有源清单、master/位置/方向、原生层图形、PG/CTS、有限预连、端点及规则版本。所有产品沿用同一冻结底座；改变底座则更新版本并重验受影响证据。独立源完全相同且未受影响的叶宏资格无需重复取得，父层负载和联合验收须重新核对。

## 验收影响

联合验收涵盖 28 个独立功能叶实例、九个正确局控身份、实际 PM/MEM 和辅助单元，同源 SystemC/RTL 程序与连接清单、紧凑全局布局及至少两版产品上层互联。来源资格、逻辑服务、控制协议、完整物理和模型覆盖分别记账。历史组合封装保留功能及后端参考范围，不能替代本版底座通过证据。
