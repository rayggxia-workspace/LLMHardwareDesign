# 300MHz与粗金属接口审阅修订

Refs [Issue121](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/121) / [PR122](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/122)。用户要求实施两份审阅建议并完成新版五块最终布局布线。

- [原件身份和归档副本](source-manifest.json)，外部原件未改；副本仅统一UTF-8/LF。
- [逐项实施/验收计划](../../../../docs/plans/block-v1-review-300mhz.md)。
- [演示几何规则](../../../../docs/technology/M11_M12_DEMO_RULES.md)。
- 原100MHz最终包固定在ad3c2b3，不回写服务器封存物；本目录新run与后续交付保存新版证据。

当前仅本地三个16位样例与九项负例通过，独立GDS及旧最终源新约束诊断待远程执行。诊断结果不是新版验收。最终交付仍须五块各一个实现，真实300MHz最终物理、同源四门、完整端口引出与有限预连检查、周期/流量及面积/接口前后对比。
