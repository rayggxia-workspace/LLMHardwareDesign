# 0007 五类组合 Block 与同源综合闭环

- 状态为 proposed，等待方案 PR 审查及实际验证。
- 关联 [Issue #184](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/184)、[#176](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/176)、[#180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)。
- 延续 [0004 的分阶段冻结](0004-block-library-base-freeze.md)。实施范围与验收详见[五类 Block v1 计划](../local-blocks/FIVE_BLOCK_V1_PLAN.md)。

## 取舍

1. P/U/C/F/J 采用九实例与私有真 SRAM。原样复用独立验收的 16 KiB P4/N4/N5 真 SRAM 叶宏，封装和顶层另行验收。P2 首选两个已验收 P4 组成一个 32 KiB 逻辑 S，组选、feeder 归属、ACK 与父层时序一并验证。
2. 控制、供数和必要的存储骨干随底座实现。指定块内数据边与块间边通过真实 M10 落点进入同一份 M11/M12 布线。选择器和驱动在底座冻结前落实。资源或下层几何发生变化时建立新底座版本。
3. 由同一映射生成程序和逐位线束。局部实现先枚举候选，产品级 DP 比较整版线束并集。用正式后端核对联合可布性、电气与时序，回传已证明的冲突或软代价。现有叶宏、控制和私有存储的证据按来源范围引用。

## 后果

需要在固定资源承诺前同时核对逻辑服务、SRAM、端点和至少两种上层需求。正式验收要将同版程序执行、实际连通、原生几何与提取后时序一起归档。
