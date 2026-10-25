# Issue91：先保留整行X，流式读取gamma

状态：有结构证据的候选，尚无新RTL实现。负责人Liangruizhi；[Issue91](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/91)。

决定：下一步以H2560 X/Y10KiB常驻、gamma256×I32=1KiB流式为优先，512B V frame和4KiB A均保留在同一16KiB单1RW S中；剩余512B不隐式用于缓冲。先实现gamma controller与全行stats→den→in-place Y barrier，再接通用非线性，不同时改变算术精度。

原因：原fullX+fullgamma超过16KiB，但不必同时流式化X。独立符号行接收显示，X常驻相对X/gamma都流式省640外部行读取与640 S写入；相同容量/格式下地址与寿命合法。全H统计必须先完成，分块gamma不改变数学。此计数基线X/G最初在外部；接M后的spill/producer成本须重新计算。

资源条件：通用V需新增有价byte非乘ALU/控制/mux；共享M lane0不能只旁挂旧8个乘法器。C0外置LUT与C1片内128KiB ROM是不同库存；程序1.93MB外存与数据LUT分开，不能称相同资源改善。所有控制/metadata/holder必须后续综合计费。

替代方案：更大S、多bank、double-buffer、保留片内ROM均可单独研究，但本轮没有证据必须增加它们。先用最小变更解决已知非法布局，可将失败定位在地址/credit或数值，而非同时改变库存。

验证与限制：8布局、4符号trace、23测试、18原Git源及4交付负例接收；无新模型、真实数组/RTL/周期/面积/STA执行。详见[报告](../experiments/issue-91-v-integration.md)、[合同](../V_S_INTEGRATION_CONTRACT_V1.md)。根审阅认为候选自洽，正式PR/项目验收仍待交付与审查。
