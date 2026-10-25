# 决策：保留完整归约/整head事务语义，共享有限服务，物理边界继续有界验收

日期2026-10-25；Issue109；负责人Liangruizhi。具体可实施规格及最小下一门槛见[电路候选v2](../BLOCK_CIRCUIT_CANDIDATE_V2.md)。

采用实际已实现的唯一16KiB128bit1RW、8S8、typed S32/两个响应槽、U128 SFU和外部桥，由D单owner lease控制。保持完整K归约/RQ/scale和R全head guard→trial→shadow→原子root；GDN两头发布、numeric_epoch与transport generation不能混同。S为可覆盖scratch，跨op持久状态在有版本外存；2048B候选与最多6KiB环境sink均有真实事务和容量成本。

依据：97通过PR111声明的研究logic-island物理范围，104通过完整两头GDN数学/RTL，109完整混合/恢复已接收（两路selected gate逐字节/独立数学通过，物理仍未验）。保留原失败和source绑定。97研究物理面积与109更多功能的logic-only面积不可作为同函数收益，不沿用97时序/预算或固定层资格。

固定数值/状态/响应所有权合同，尚不冻结M+A/R合宏、真实存储宏、产品制造边界或M9–M10拓扑。下一最小门槛为真实事务消费者buffer/commit-revoke、S宏与上下游drive/PG/PVT、实际新top物理及精确后网表接收；与55/63协调金属定制资格。等价位宽微优化仅在独立完整验收后可选，不扩大模型矩阵或提前改变分区。
