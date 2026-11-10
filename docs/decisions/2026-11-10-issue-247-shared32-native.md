# 共享32KiB与P本地逻辑1R1W

状态：本阶段已实现并服务器验证，PR正式审查待完成。Issue247/PR243，Melodydt。

用户选择共享32KiB以降低面积。使用8颗已有4KiB1RW宏、单个不可变A对象、两组有限4-beat FIFO和原生128bit A出口。现有P默认参数关闭，新双P顶层显式开启；不自动扩为96KiB，不提供免费广播或任意byte写。

本地S逻辑16KiB通过双物理位置和live-location table提供1R1W，实际32KiB/P。同址读旧值；warm保留映射，cold使内容失效。总2P+U+pool物理112KiB，不把逻辑容量当物理面积。RELEASE必须等外层LOAD完成回执消费，统一复位覆盖池与两P。

保留负面性能证据：实际共享A出口16B/拍，旧模型假设32B；端口敏感性prefill ideal4.398913降至3.496459，不是原生全图性能。后续先研究入口供数及实际DMA/控制再宣称系统吞吐。

详细方案、实测回执与边界见../experiments/issue-247-shared32-native.md及其证据索引。
