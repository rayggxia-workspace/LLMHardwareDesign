# Issue 121 计算与存储参考模块取舍

更新：2026-10-27。用户允许参考 openTPU、llaccel，包括计算资源模块。目标是减少已有问题的重复探索；下面区分已阅读实现、可借用方法与尚未采用的 RTL。

## 已阅读来源

openTPU 固定 [91df41092f612361c5bc22f83b31d23382ffabb0](https://github.com/FeSens/openTPU/tree/91df41092f612361c5bc22f83b31d23382ffabb0)。本轮读取以下文件；与本仓库历史 H1 对照的 `f237dab2f196855a59a083b1454786df8f01291f` 区分。

| 文件 | Git blob | 取舍 |
| --- | --- | --- |
| `rtl/mxu/otpu_mxu.sv` | `d5d1f1d161ad91bb1e742972714084473737ad26` | 参考分组累加、数据复用和流水控制；48 位整数组累加后转浮点并乘尺度，与当前四 profile 的完整 K 与一次 RNE 合同不同，不能直接视为替换成功。 |
| `rtl/tech/generic/otpu_tech_ram.sv` | `a025b75e556e2a28b18c10eb3f5545a84189976f` | 参考同步 RAM 与读地址/数据延迟的明确封装。 |
| `rtl/tech/asic/otpu_tech_ram.sv` | `8e71679152eb480b187113794d152fa0ef8949d0` | 参考宽深分块、bank 选择延迟和 leaf macro 适配；fakeram 不能当作已资格实体 SRAM。 |
| `rtl/exp/mx_mxu/otpu_mx_lane.sv` | `9bb34afaadd926be14693f3df5bd1c2cd0901d24` | 实验浮点转换/乘加 lane，可参考分级方法；不等价于本版整数 lane。 |

llaccel 只读使用获授权服务器共同项目已有工作树 `/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/llaccel-v1`，固定提交 `f7db8a22791a1ce9dc13e7c90b0b9b9386169aa5`。

| 文件 | SHA256 | 取舍 |
| --- | --- | --- |
| `rtl/gemm_engine.sv` | `0799d66ba8528b3b58f56f39d16cea040dbd134980daba3a8d0e21108cb27295` | 参考有符号 8×8→16 乘积、20 位局部和与 32 位累加、双缓冲和输出 FIFO 背压。阵列规模与本版 8 lane 不同；可评估抽取 leaf 算术/控制，须先证明位宽、尾块、完整 K、周期与资源合同。 |
| `rtl/sync_fifo.sv` | `45934c64d8389a49ecbf0617cf524fa2f7279bb2113996dbda527724954773ab` | 可借用 FIFO 的简单接口与边界用例；满时 push 被拒，即使同周期 pop，也不能假设支持满吞吐交换。它本身没有 T6K 的提交/撤销/owner 合同。 |
| `rtl/llaccel_pkg.sv` | `9fefcb4aba85cb45595cb923fdb17d7aa53eb59f34f469845e4c29e18e0b310f` | `mulshift64` 的低 64 位精确性依赖输入范围；不能直接覆盖本版宽乘积后一次 RNE。 |

## 当前选择与采用门槛

当前先复用已经验证的 RAM 周期/握手用例、宏边界完整负载与 RC 接续、修复全额计价方法。计算模块也可采用，但先对照精确整数模型，验证符号、溢出范围、舍入、完整 K、背压、复位及共享 owner，再比较同一资源预算下的面积/周期/时序收益。若只是替换写法却重置已运行物理候选，当前收益不足。

本轮未复制新上游 RTL、未替换现有计算资源、未构建上述上游新提交。现有 128 新源候选继续接收，后续出现明确瓶颈时优先评估能局部证明等价的 leaf 模块。采用 RTL 前另核对应版本许可证并记录来源；上游通过和历史 H1 通过不等于本版新候选通过。

本仓库可复用证据：[openTPU 同资源对照](../experiments/issue-15-opentpu-comparison.md)、[llaccel/openTPU 既有回归](../experiments/issue-7-parallel-blocks-wave2.md)。这些参考不会减免真实 S16K/T6K、全部 glue 与四 profile 的最终验收。
