# Issue247：先落地固定容量原生P，再验证完整预取和物理成本

2026-11-09，Asia/Shanghai；关联[Issue247](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/247)、[PR243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)。

用户授权开始前三项优化，允许牺牲面积，SRAM扩容仍保留方案。本轮选择默认关闭、可分别启用的消费者优先、四1RW bank并发、1/2/8个S64上下文。数据S保持16KiB；八context复用原八行结果槽，新增325bit显式状态，不复制M或扩大数据存储。活动context与旧八行RUN互斥。

实际原生接口不具备模型的DMA描述符层和64B读＋64B写端口。因此消费者优先是完整预取方案的第一步；bank并发只利用异bank机会，受总64B/拍物理访问上限约束。后续真正1R1W需要新的宏与合同，不能改模型参数后称RTL已经实现。

run10/101756和run11/101758通过，生产RTL相同。无人工背压local LOAD＋64写95→71拍；独立仲裁与后端总工作分别516→516、99→99，只改善消费者延迟或等待分布。完整P的联合配置含释放：K59 2112→2032，K11 672→676；保留短K退化，默认不全局打开contexts。独立M8ctx44例中28改善、16退化，不能拿最佳12.5%局部工作率外推整模型。

首轮完整P的672→644只统计到最后S写ACK，补验计入32拍context释放后更正为676，旧证据保留。今后报告必须同时说明数据输出完成与资源可复用边界。下一步优先减少经合同确认的释放/控制开销、接入真实DMA信用和描述符，再做母控/局控程序、整模型数值与综合/STA/P&R。未给300MHz、功耗或真实token/s资格。

[详细方案及证据](../experiments/issue-247-p-native-optimizations.md) · [恢复入口](../handoffs/2026-11-09-issue-247-p-native.md)。待独立审查，不自合并，Issue不done。
