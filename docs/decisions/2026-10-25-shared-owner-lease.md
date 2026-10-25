# Issue106：先以互斥 lease 实现真实共享服务

2026-10-25，Liangruizhi；Issue106，task/106-shared-services。本决策的功能与成本证据见[实验报告](../experiments/issue-106-shared-services.md)，不改变未完成的物理资格。

采用单一16KiB/128bit 1RW、8个S8、一个S32、一个SFU和一个128bit外部桥，由互斥owner lease交替服务专用M/V、materialized完整GQA A及Falcon单head R。三个控制器保留原数值函数和各自局部寄存，不能把它们隐藏的资源复制算作共享。

先选择互斥而非多owner并发，是因为当前首要问题是实际同一容量/端口下的状态重建、已接受操作的排空和结果提交；并发会增加仲裁、活跃上下文和缓冲，无法用本批单owner证据定价。lease直到结果完整导出、状态决定及DONE ACK才释放，防止下一个控制器覆盖尚未消费的S内容。M/A结果前缀在成功DONE前仍是provisional；真实下游事务缓冲或可撤销消费尚未实现，环境测量接收器最大6KiB存储不计作免费core能力。

soft_abort停止新服务请求，排空所有已接受操作后才局部复位。R accept后的原子root提交不可取消；INIT是空白外存的破坏性配置，与STEP旧状态保护分开。硬reset要求外部fabric协调，不能据空闲RESTORE测试宣称任意提交时断电安全。

A的单owner/单调version注册信息跨lease和soft_abort保留；host必须为变更的不可变KV快照分配新version。length由调用方声明已提交前缀，当前RTL不自主验证append提交。R持久状态仅在外部root/双bank，M每次重新构建A缓存；禁止假设跨A/R切换保留M暂存。

全量控制器、宽重定标、地址/数据选择器和导出成本进入实际综合，logic-only为125,966.694µm²，已超过旧98网表79,600.5µm²预算。选择共享是本批经验证的容量/端口实现，不意味着面积、周期或PPA优化已成立；旧独立核面积和不能当同资源对照。下一步应以真实新增profile和面积主项决定资源复用，保持精度函数和物理预算，不先扩大预算再宣布成功。

GDN104未接入，通用V ISA、通用GEMM、KV append/online、宏/时序/物理及制造后定制仍为独立资格。本批结果不解除这些限制。
