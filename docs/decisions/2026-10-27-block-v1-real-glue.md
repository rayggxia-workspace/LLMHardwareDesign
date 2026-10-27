# 真实父层 glue 的映射与边界验证

Issue [121](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/121)，草稿 [PR122](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/122)。本项补齐批准计划中全部 glue 计价与最终组合验证的前置输入，不改变四 profile 算法或冻结层边界。

`shared121.sv` 在 C8 与 T6K 之外含实际有源逻辑：命令与 ACK 门控、abort/reject/error 撤销、commit 条件、owner 对应输出长度及就绪反馈。两个叶块合格不能证明这些逻辑已经布线或计价。新增 `native-glue-map` 只映射这一真实 wrapper，保留唯一 `core:shared109` 和 `sink:transaction6k` 两个接口实例，禁止把其余未映射硬件当作零成本。

映射使用实际 Nangate45 Liberty。所有 glue 单元（含 LOGIC0/LOGIC1 常量驱动）逐 master 计数及面积，两个叶块的面积明确另计；不会再综合一份 C8、S16K 或 T6K。通过精确逆重建检查新增 tie cells 与原常量逐位一致。

从 Yosys 实际 generic 与 mapped 图构造组合边界：所有叶输出成为符号输入，所有叶输入成为待验证输出，并保留全部外部端口。未连接的叶输出仍有独立符号接口，缺少叶输入则拒绝。不引入行为存储。Yosys 对原 RTL 图与功能 Liberty 展开后的 mapped 图作完整等价检查；实际 Kepler 再核 literal/tied 映射视图，并对 core.cmd、core.ack、sink.revoke_valid 三个真实连接分别改错，要求反例。宽有符号端口只清除结构声明元数据，全部 cell 参数及连接不变，保存证据。

四个 Kepler 正/负案例在同一个8CPU allocation内并行，每进程OMP两线程、BLAS一线程，保留独立日志、返回码与时间。实际库、网表、formal输入输出均由源码归档和回执绑定。

实际136/92214在node21/8CPU自然失败57秒，回执不改写：Yosys功能Liberty展开后的原RTL/实际映射图4788个等价点全部证明，但Kepler将14个LOGIC0_X1/Z列为额外PI，literal/tied正例虽UNSAT/IDENTICAL仍被严格边界检查拒绝。三种实际坏连接均产生SAT。后续Kepler改为同源完整tied网表的identity正例与三个实际坏连接控制，两个方向都保留原14个常量单元；仍要求identity所有PI/PO完整匹配，不过滤或豁免。原RTL与实际常量函数的非平凡等价继续由独立Yosys功能Liberty证明，Kepler案例只声明接线错误检出控制。本修正尚未实际运行。

后续必须将这份有源 glue 纳入实际父层 placement/PG/CTS/布线、成本与共同底座冻结，并与实际最终 C8/S16K/T6K 网表运行完整四 profile/恢复/背压接收。本项成功也不构成合格物理 Block、宏边界或十二层提取资格。
