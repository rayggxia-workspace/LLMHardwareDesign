# 300MHz与粗金属接口审阅修订

Refs [Issue121](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/121) / [PR122](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/122)。用户要求实施两份审阅建议并完成新版五块最终布局布线。

- [原件身份和归档副本](source-manifest.json)，外部原件未改；副本仅统一UTF-8/LF。
- [逐项实施/验收计划](../../../../docs/plans/block-v1-review-300mhz.md)。
- [演示几何规则](../../../../docs/technology/M11_M12_DEMO_RULES.md)。
- 原100MHz最终包固定在ad3c2b3，不回写服务器封存物；本目录新run与后续交付保存新版证据。

当前仅本地三个16位样例与九项负例通过，独立GDS及旧最终源新约束诊断待远程执行。诊断结果不是新版验收。最终交付仍须五块各一个实现，真实300MHz最终物理、同源四门、完整端口引出与有限预连检查、周期/流量及面积/接口前后对比。

## 2026-10-28 21:24 CST implementation checkpoint

Initial remote run233 job92802/node13 completed six independently claimed measurements, receipt/report SHA verified in [run233](run233/README.md). P1 independent GDS passed; all five old final timing diagnostics retain negative checks and never qualify revised leaves.

| Old macro at new budget | setup ns | cap violations | slew violations |
| --- | ---: | ---: | ---: |
| M | -3.729412 | 6 | 0 |
| V | -4.868114 | 77 | 1 |
| R | -3.310902 | 3 | 1 |
| S | 0.528991 | 3 | 0 |
| T | 0.710807 | 26 | 0 |

S revised RTL now permits retiring/refilling its one response register on the same edge, still exactly16KiB standard-cell1RW payload. T revised RTL refills the held committed word on each take edge, still one6KiB complete-batch lease, no producer/consumer double-buffer overlap. Fresh independent burst/backpressure/reset tests and fresh mapping/native300MHz flow are prepared but not yet run at this checkpoint. Shared store82 used by historical experiments is unchanged.

The candidate coarse layout distributes every actual port (including clock/control/observations) into <=16-bit directional strips, with2x2 realM10 pins. Horizontal routes avoid vertical-source M11 landing rows. Native footprint may grow only if complete mapped port track capacity cannot fit; outer32um receiver endpoints and40um test halo are charged separately. This is a planned geometry until actual native reconnect/readback and fullDRC pass.
