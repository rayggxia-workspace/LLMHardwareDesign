# 在已分配c96节点内补入独立重测任务

Issue #121 / PR #122。用户要求本任务最多6～8节点，节点内默认6×16、即完补位；不因单任务扩核差而让其余核等待。当前8个allocation已满，322原生P&R只占其节点的0–15核，325七项独立重测已有真实前置，却在等新allocation。

不改已开始的322不可变queue/source/state，不取消原任务。使用同一个真实Slurm job的独立srun step，在16–95核运行326替代暂存325的七项工作；原physical16＋最多5项独立16CPU任务，共96CPU。新step不是新sbatch/allocation，不增加节点计数。原325从未分配，只有核实后才退役其未来选择，原文件保留。

复用native_node_queue的原claim、硬taskset、内存准入、即完补位、receipt和失败保留逻辑。保留原96CPU不可变队列SHA，派生该worker运行预算80CPU并明确记录。启动和每次内存准入核对：同job/node、父queue SHA、父活动任务16CPU掩码、真实父计算进程树及所有计算线程掩码。其余80CPU必须恰为补集；缺核、重叠或父进程缺失拒绝执行。

每次内存准入从MemTotal预留父P&R的192GiB×1.2（或更大的实际进程树RSS），保留原MemAvailable实测及子任务各32GiB×1.2和16GiB guard。只有这些具体数值限制时才少于五个子任务，限制会保留在queue-live/result；父原任务不扩核、不重启、不减门。

native_cohost_queue的独立控制覆盖正确分区、重叠、缺核、错误allocation、低内存与超过forecast的实际RSS；尚未在服务器执行，不把本地控制等同实际并行或宏资格。工作只重测当前RTL的占用和有限S/V/模型长度，不新增宏或产品范围；物理选择322/323/324和R311/312/313不变。
