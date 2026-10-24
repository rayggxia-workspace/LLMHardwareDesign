# Issue74取舍：完整MoE合同与可选M/V驻留

2026-10-24 Asia/Shanghai；状态：提出，PR75待审查；负责人Liangruizhi。[Issue74](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/74)，承接Issue72，细化既有划分，不覆盖原失败。

实际证据见[报告](../experiments/issue-74-moe-grouped.md)和[统一索引](../../project/experiments/moe_grouped/results/issue-74/index.json)。全部真实计算在本人CPU Slurm；无新模型、其他机器、Phi解封或成员55/63工程接管。

决定保留六逻辑模板与可选物理归属。Granite完整cut整数重放证明动态router/ID/gate/同单位expert down/宽merge/完整consumer合同，不能固定所见expert或免费堆8份完整output。M接口须区分同单位PARTIAL32、混合组ALIGN64和最终宽RQ；V/ROM/缓冲与宽SFU必须作为候选资源登记。

不固化近M独占RQ或M/V合宏：Falcon同g同资源12服务全部接收，6label零差，近M完整链slots仅省0.001007%–0.016005%。bank-select共享VR8与串行调度是候选假设，不是物理locality；不把不同g函数或新旧费用跨排。

不追加midF20：原8条件posthoc显示最终Q12 RNE能量远小于上游及A8误差，delta最低6/7、无未满量程行，增加小数位会增加A8右移，不能预设收益。局部L2和路由最终0差均不构成应用质量接受；层13 token42误差抵消必须保留。

代价与后果：保留动态dispatch、带单位/版本的宽接口和重读/spill自由会增加接口/控制需求，需实际RTL/端口/物理校准。Granite grouped服务和整模型质量未执行；Falcon端口比较不能代替它。下一优先是宽微程序/SFU/ROM/bank-select校准及Granite有限容量expert/merge调度，不扩品牌或盲扫精度。物理实现由后续明确任务与成员55/63协调，当前不接管。
