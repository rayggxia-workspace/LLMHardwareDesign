# 固定 fabric 与两 bank：可证伪端口/状态归属模型合同草案

状态：供 Issue 后续实现选择的独立方法审查草案；没有修改仓库或 GitHub，没有实施硬件。2026-10-22。当前建议以固定 complete fabric、同一 FP32 attention 算法及同一任务 DAG 为第一阶段，仅改变状态的 bank 放置；静态 edge-disable 作为单独预算试验。

**核心判断：首先证明“状态放置改变了哪个可枚举的资源冲突或依赖”，再讨论固定 Block 边界。只改归属标签不能改变周期；禁用互联边也不能在相同资源语义下改善最优调度。若首轮只是获得一个更好的调度启发式结果，不能归因为硬件划分优势。**

## 1. 已有证据能支持什么

Issue 21 的 ledger.py 明确没有周期、端口、重叠或双缓冲模型。joined 只把相同传输计入 local_interengine_bytes 而非 cross_block_bytes，两个 bank 不合并。它不能单独给出速度差。

Issue 23 捕获的是 CPU eager 调用的真实张量、KV 和数值一致性；可用于校验维度、状态增长、操作边界和 FP32 数据宽度。它没有加速器逐周期地址请求、阵列操作数复用、端口事务、物理链路或时钟证据。不得把 event 顺序直接当成硬件串行顺序，也不得把一次 compute 的全部逻辑 read bytes 直接解释为真实 SRAM 总线事务。

首轮保留 FP32 与在线 softmax 的状态依赖；不引入未冻结的 INT8 nonlinear、额外 rescale 单元或“免费”累加器。需要改变算法、精度、算力或数据复用时，作为单独因素记录。

## 2. 预声明的任务级资源模型

以下全部应进入不可变配置和源哈希；数值只是将来 root 选择的参数，不能从 CPU 时间拟合成硬件事实。

| 对象 | 最少合同字段 | 审查要点 |
| --- | --- | --- |
| 时基 | 抽象服务 slot；读延迟、写提交延迟、计算延迟/II、链路延迟 | 没有 RTL/工艺标定时称“模型周期/slot”，不能称实测时钟周期 |
| 两个 bank | 各自容量、word/beat 宽度、端口模式、读写延迟、同址冲突规则 | 不因 joined 或 ownership 改变容量、端口、时钟 |
| 1R1W bank | 每 slot 至多一个 read beat 和一个 write beat | 同址读写另行规定；建议第一版禁止同 slot 读写同一物理 word |
| 2RW bank | 两个独立端口，每端口每 slot 一次 read 或 write；总请求≤2 | 可两读或两写，不等于 2R2W；双写同址第一版拒绝 |
| 地址 | tensor/version、base word、shape、strides、padding、bank selection、row address | word 与 byte 地址不得混用；partial beat、对齐和 padding 真实占容量 |
| fabric | 固定 endpoints、directed edges、每边容量/延迟、每 endpoint 注入/接收上限、仲裁 | complete 只表示可达性，不表示无限带宽；读请求、读返回、写数据不得隐去 |
| endpoint FIFO | 深度、beat 宽度、是否旁路、分配来源、占用/释放时刻、in-flight reservation | FIFO 不是 SRAM capacity 之外的免费缓存；复制后的两份数据同时存活时都计入 |
| 引擎 | 各任务可用的引擎、固定 latency 或 service profile、II、操作数/结果寄存器容量 | 不允许用 MACs/peak 推出 duration 后完全免除 SRAM/RF 供数约束 |
| 状态 | m、l、O 等的初始值、版本号、读者、最后使用者、更新提交点 | 图依赖必须包含 O 旧值读取与新值写回，和 softmax 重缩放依赖 |
| workload | q/k/head/d 维度、tile、因果 mask 计算政策、运算/精度、输入/输出协议 | prefill/decode 允许不同合法 schedule；布线、端口和 bank 映射硬件不随 phase 改变 |

官方说明显示，“两个端口”并不是足够明确的模型定义。例如 AMD UG573 v1.14 规定 UltraRAM 每个端口每周期只能读或写，并说明其行为不能直接套用普通 SDP/TDP 标签。因此这里的 1R1W/2RW 是明确的抽象服务合同，不冒充已选中的 ASIC SRAM 或 UltraRAM。出处：[AMD UG573，Block RAM and UltraRAM Differences](https://docs.amd.com/r/en-US/ug573-ultrascale-memory-resources/Block-RAM-and-UltraRAM-Differences)。

地址映射同样需要冻结：Intel 的官方 memory attributes 区分 bank_bits（word 地址中的 bank 选择位）、bankwidth、复制以及双倍存储时钟。它们改变可服务的请求，不能静默当作同一资源。出处：[Intel oneAPI FPGA Handbook 2024.2，Memory Attributes](https://www.intel.com/content/www/us/en/docs/oneapi-fpga-add-on/developer-guide/2024-2/memory-attributes.html)。

## 3. 任务 DAG 与原子 reservation 的精确定义

推荐第一版只做有界任务级调度：

1. 每个 task 具有确定的输入版本、输出版本、计算引擎与读/写/传输服务阶段。依赖 ready 不意味着 SRAM 读已完成。
2. task 开始前，原子检查并保留其必要的输出存储、输入快照/寄存器、endpoint FIFO credit，以及将来必须使用的端口/链路服务时隙。任一资源不满足时，任务不开始，也不持有新的部分资源。
3. 若模型不能预约未来服务时隙，可保守地在完整 task 区间独占相关资源，但必须明确它是低并发的保守模型；不要把整个区间的资源占用误称为逐 beat 精确行为。
4. 使用明确的 slot 次序：前一 slot 完成的 read/compute 在当前 slot 开始可见；请求在当前 slot 发出；write 在约定提交点才使新版本可读。禁止未声明的同 slot 穿透。
5. 输入最后一次真实读取之后才可释放；输出从首次预留/写入开始到最后消费/回收结束都占容量。预留与已有数据占用必须统一计数，不能两者都忽略。
6. 输出 FIFO 预留深度应覆盖该 task 尚未被消费者接受的所有潜在输出，以及尚在飞行的数据。整 tile 生产且不可中停的 task，需要能容纳整 tile；不能按一 beat FIFO 假装自然流式。
7. 原地更新必须保留 WAR/WAW/RAW 约束。若改为版本化或 ping-pong，则明确多出的地址区间、容量与初始化/复制成本。
8. 若改变状态 bank 位置需要搬迁现存内容，显式加入 source read、路径、destination write、两份同时存活区间及控制依赖。冷启动时可选择初始放置；同一请求执行途中不能免费重映射。

**这个模型的保证边界：** 原子获得全部所需资源、有限完成时间和正确释放，可以避免已启动 task 的 midtask hold-and-wait。它没有模拟任意 streaming producer/consumer 的逐 beat 回压，因而不能证明目标 RTL 的有限 FIFO 网络不会死锁。容量长期被活跃中间值占据仍可能使后续 task 无法开始；这应报告为该映射/调度不可行，不自动扩容。完整 trace 的资源约束验证通过，仅证明该抽象合同下存在可行 schedule。

FIFO 大小不仅与平均生产率有关。AMD 的官方例子说明，同样的两个 FIFO 结构，生产/消费访问顺序变化就可能需要不同深度，并可能死锁；这正是原子 reservation 第一版有意避开的细粒度问题。出处：[AMD XD099 v2023.2，Deadlock Detection and Analysis](https://docs.amd.com/r/2023.2-English/Vitis-Tutorials-Hardware-Acceleration/Deadlock-Detection-and-Analysis)。

## 4. 三条必须成立的零效应与单调性合同

**C0：标签等价。** 只把同一 task/bank/link 的 owner 从 split 改成 joined，而地址、资源服务、容量和依赖都不变，最优 makespan 必须相同。调度器若 deterministic 且优先级不使用标签，逐 slot trace 也应相同。否则首先是实现 bug 或启发式 tie-break 差异。

**C1：complete fabric 是静态子图的调度上界能力。** 设 F 为完整 fabric，E 为固定禁用部分边后得到的子图；在相同剩余边/endpoint 延迟、带宽、FIFO、仲裁选择和 bank 服务下，任一 E 上合法 schedule 也能原样在 F 上执行，所以 T*(F) ≤ T*(E)。静态禁边出现更短最优周期，违反这一合同。启发式在 E 上更快，只能说明它在 F 上做了较差选择；把 E 的 witness 送回 F 作为暖启动即可检验。

若要宣称预制直连更好，应显式改变并标定仲裁/配置、wire、mux 或 clock 成本。这超出本轮“仅状态归属”的辨识范围。若仲裁是固定强制策略而不是可选择 schedule，则比较得到的是“该策略+拓扑”的效果，不能使用上述最优调度结论混淆。

**C2：只改变位置才可能改变冲突。** control ownership 标签本身没有周期效应。m/l/O 从 bank A 移至 B，而算术及访问完全相同，才可能改变与 K/V、score、权重的同 bank 争用。仅当新的 address/port incidence 改变时，才属于本轮可辨识的状态放置效应；如果两 bank 对称且把所有相关对象同时置换，应再次得到相同最优周期。

## 5. 必要条件、充分证据与固定候选边界

令 T 是 makespan；R_b/W_b 是 bank b 的实际事务数，p 是明确的方向端口数。没有重复地址合并/广播等额外语义时：

- 1R1W 的必要资源界：T ≥ max_b(R_b, W_b)；一般方向端口数用 ceil(R_b/pR_b)、ceil(W_b/pW_b)。
- 2RW 的必要资源界：T ≥ max_b ceil((R_b+W_b)/2)。同址和依赖约束可能进一步提高它。
- 每条链路以及 endpoint 各有自己的流量/服务下界；不能用全 chip 总带宽代替 cut/endpoint 的瓶颈。
- 加入真实延迟的 DAG 最长路径是另一必要界。周期性状态更新还受 loop-carried recurrence 限制；改变 O/m/l 放置如果延长这个依赖环，可能抵消吞吐收益。
- 这些下界的最大值通常不充分，不能直接当预测时间。最小反例：两项独立任务都按 M→V 各运行 1 slot，总资源界=2、关键路径界=2，但最优 makespan=3。

对于“所有请求已 ready、无其他依赖”的独立 read 批次，给定固定 bank 映射时，max_b ceil(requests_b/read_ports_b) 是该简化批次完成所需服务 slot 的必要且充分条件。若 word 地址为 a_j=a_0+j*s、bank=a mod B，则 bank 序列周期为 B/gcd(s,B)，可直接解释某个 lane/stride 为什么冲突，而不依赖大量模拟数字。

对于已给定的 producer/consumer 时序，FIFO 占用满足 q_e(t)=q_e(0)+P_e(t)-C_e(t)。在明确 token 可见时刻与无隐藏存储的条件下，所有 t 上 0≤q_e(t)≤D_e 是该既定时序的 FIFO 可行性充要条件；它不是任意任务图可调度的充分条件。当前原子模型可以使用这个条件验证输出保留区间，而不模拟任意网络协议。

**充分证据采用可回放 witness，而不是只给一个最优分数：** 输出每 task 开始/完成、每请求 bank/address/version/slot、每 link/endpoint 使用、每 buffer live interval、每 FIFO reserve/occupancy。独立 checker 验证所有依赖、资源、容量、值版本和最终释放。如果精确 oracle 已穷举所有更短 horizon 无解，才说“该有限抽象实例最优”；超时只能报告 incumbent 与 lower bound 的 gap。

固定候选边界应优先从以下机制生成：

| 候选依据 | 可解释原因 | 需要推翻它的条件 |
| --- | --- | --- |
| 状态更新依赖环 | 把反复读写的 m/l/O 与实际更新引擎放在低争用可达的位置，缩短 recurrence 上关键事务 | 新位置加剧 K/V 或 score 读端口争用；O update 引擎未获合法访问或容量不足 |
| 访问并发冲突 | 将同时需要的只读流与读改写状态放到不同 1R1W bank | 真实 schedule 可以无损交错同 bank 请求，实际 makespan 不变 |
| 单消费者短寿命通道 | 可能以有限 FIFO/RF 接收生产结果，减少显式 SRAM materialization | 必须双消费者、乱序访问或整 tile 容量；返回路径/重缩放仍需传输 |
| 大规模持久状态边界 | KV 的生命周期和增长是清晰的容量接口，不与临时 score/O tile 混算 | 不同请求共享/分页/搬迁要求超出固定映射；仅容量可放不代表端口可服务 |

这些是候选产生规则，不是固定答案。FlashAttention 已说明 tile 与在线状态可以改变 IO 行为；算法级 IO 减少不自动归因于 Block 连接。其结论针对明确的存储层次与计算组织，不能替代本轮逐端口合同。出处：[FlashAttention，arXiv:2205.14135v2，2022-06-23](https://arxiv.org/abs/2205.14135v2)。

## 6. 最小可执行的辨识实验

第一阶段固定算法、DAG、tile、bank 总容量、端口模式、fabric、endpoint FIFO、FP32 latency 假设，比较两三个 m/l/O 放置。每个放置使用相同调度搜索预算；小实例用精确 oracle，较大实例给下界+可行 witness。不要把 reference placement 的串行调度与 candidate 的优化调度比较。

在此基础上分开加入因素：

1. 1R1W 与 2RW 各是一组资源合同，不能混在同一“公平资源”配对中。
2. 改变 bank mapping 或 padding 是 layout 实验，计入容量与数据准备成本；先同时优化 baseline 与 candidate，再判断放置收益是否仍存在。
3. materialized/online 是算法/调度因素；不可给 candidate 在线融合，baseline 只给 materialized，然后把差值归因于布线。
4. edge-disable 用固定预算、固定 endpoint 限制单独跑，使用 C1 检查；整个 prefill→decode workload 保持同一禁边集合。
5. 同一硬件设计允许 phase-specific 调度指令、tile 次序和合法地址分配，但不能改变物理 bank 选择逻辑、线路集合、端口数或 FIFO 容量。一次请求内的迁移必须出现显式任务。
6. 先保留 prefill/decode latency 二维 Pareto；没有用户 workload mix 时，不擅自编造加权分数。固定设计的选择必须在 phase 集合之外完成，不能逐 phase 重新挑一套“最佳硬件”。

静态已知生产/消费量适合采用数据流图与静态调度；这是一种建模选择，并非新颖性本身。出处：[Lee & Messerschmitt, Synchronous Data Flow, Proceedings of the IEEE, 1987](https://ptolemy.berkeley.edu/publications/papers/87/synchdataflow/)。

## 7. 已实际执行的 7 个最小 oracle/反例

独立脚本 minimal_counterexamples.py，纯标准库，不调用仓库调度器。执行命令：

D:/APP/Python/python.exe -B D:/Projects/Codex/state-port-study-20261022/interface-audit/minimal_counterexamples.py

| 测试 | 实际结果 |
| --- | --- |
| 两个 M→V unit jobs | 精确 BFS 最优 3 slots；资源界/关键路径界均为 2 |
| 仅重命名资源归属为 joined | 仍为 3 slots |
| 2 bank，各 1 read/slot，word 地址 [0,2] | low-bit bank 映射需 2 slots；下一地址位映射需 1 slot；总 bytes 相同 |
| 同 bank 两个 read | 1R1W 需 2 service slots；2RW 需 1 |
| producer AAABBB、consumer 每次原子读 A+B，FIFO 深度 2 | 穷举所有合法交错均无法完成，存在容量死锁 |
| 同上 FIFO 深度 3 | 可完成，最短 7 slots |
| producer ABABAB、同一 consumer、FIFO 深度 1 | 可完成，最短 7 slots |

后面三个测试故意使用逐 beat transition system，展示原子任务模型没有覆盖的 FIFO 风险。其 consumer 的 A+B 是明确的原子动作，不能把此深度结论推广到可先读 A 再等待 B 的另一 consumer 协议。

结果文件 minimal-counterexamples-results.json，SHA-256：9e324ee25344ce5447e154cdaef068e67e7a65ee9c471495324cc97018b148fb。

建议 root 接入的反例还应包括：删除一个状态读取、同址双写、越 bank 容量、边禁用后仍使用、未消费就释放、空 FIFO 读取、超 FIFO 预留、途中换线、超 endpoint 吞吐。负例必须被独立 checker 拒绝，而不是让优化器自己保证所有事实。

## 8. 接受与拒绝标准

可以接受：“在冻结的任务级抽象服务合同下，placement A 的可行 witness 为 T_A，下界为 L_A；placement B 为 T_B/L_B；改善/无改善由具体 bank 争用与状态依赖解释，适用于声明的 prefill/decode 集合。”

不能接受：“CPU trace 验证了硬件周期”“同容量就是同硬件资源”“禁边天然提速”“没有模拟到死锁所以有限 FIFO RTL 安全”“某个启发式最短就是全局最优”“去掉跨 Block 计数就省掉了 SRAM/链路传输”“不同 phase 自动更换固定互联”“未标定 clock/area 的 slot 优势就是 DAC 所需 PPA 收益”。

本草案的价值是让无效候选和错误归因尽早可证伪。若最终同资源最优调度没有周期收益，这也是有效结果；下一步应转向有明确实现成本的 arbitration/mux/wire 约束或更加持久的状态接口，而不是放宽 baseline 来制造优势。
