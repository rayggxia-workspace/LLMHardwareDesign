# Algo1 从算子前沿到 tile 驻留和多组归约

2026-11-15 CST · [Issue #219](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/219) · [草稿 PR #273](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/273)

## 1. 从哪里改起

初始建议是把 tile 交接放在算子候选内部，外层 DP 一次仍选一个完整算子。实现随后分成三步，搜索粒度逐步下沉。

| 阶段 | 提交的改动 | 搜索在哪一步做选择 |
| --- | --- | --- |
| 自动发现切片与驻留 | 早期手工指定上下游的配置入口和样例已移除。类型化图从张量形状、切片轴、读写依赖和硬件配方发现切分；原生整数图用范围命令发布完整输出行，随后加入特征轴切片、窗口版本及 DDR 回退。 | 普通 Algo1 为整图和若干自动生成的固定布局分别搜索。布局内的 tile 是前沿任务。深度限制按原算子统计。 |
| 同一前沿搜索范围和归约 | 给定访问映射和服务合同，范围 DP 在同一次搜索选择输出宽度、顺序归约的下一段、以及产出留在 SRAM 或写到 DDR。 | 一次动作可只推进某个算子的一个输出区间或一段 K。256 个数据片段是可寻址单元，不是 256 个预先写好的实现。 |
| 多个输出组交错推进 | 为每个算子记录多个未完成输出组，单独跟踪各组归约前缀、部分和占用及已发布输出。最后一个读者决定旧片段何时可释放。 | 在已有组和新组之间选动作，以同一个状态比较整 K、单组续接、多组复用。 |

前两种编译入口的关系见 [普通图与原生范围命令](TILE_FRONTIER.md)、[特征切片与块级投影](TILE_FRONTIER_FOLLOWUP.md) 和 [范围原型](TILE_FRONTIER_RANGES.md)。范围 DP 是独立评估入口 `tile_frontier.py`，普通 `run.py` 的原生指令与布线导出仍由既有事件编译路径负责。范围 DP 的通用性来自参数化的访问关系。现有范围实现支持一个连续输出轴及一个可选的顺序归约轴。张量的轴映射与合法服务仍需由 lowering 和硬件合同提供。

## 2. 算法公式

### 2.1 普通 Algo1 的前沿

给定算子图 $G=(V,E)$，以及一种已经下降为 tile 任务的布局。令 $D$ 为**已选实现并排入计划**的任务集合，$C_e$ 是阶段 $e$ 真正完成的时刻。前沿与时间约束分别为

$$
\operatorname{Ready}(D)=\{i\notin D:\operatorname{Pred}_{\mathrm{sched}}(i)\subseteq D\},
\qquad
R_e=\max\!\bigl(\{C_f:f\in\operatorname{Dep}(e)\}\cup\{\text{所需窗口的释放时刻}\}\bigr).
$$

各依赖由对应的发布或完成事件产生。边能表达“第 $j$ 块写确认后可读”时，消费者可以排在生产者整算子完成之前。若依赖只暴露整命令 DONE，最早可读时刻仍取该 DONE。对不可中断、服务时间为 $d_e$ 的预约阶段，阶段执行时刻为

$$
S_e=\min\{t\ge R_e:O_s(r,u)+q_{e,r}\le K_r\quad
\forall r,\ \forall u\in[t,t+d_e)\},\qquad C_e=S_e+d_e.
$$

$O_s$ 是当前部分计划的已预约用量，$q_{e,r}$ 是本阶段对端口、宏或窗口等资源的容量需求，$K_r$ 是合同规定的容量。可重叠阶段按各自的资源和依赖约束预约。普通编译路径比较模型工期、DDR 字节和静态线束开销，并检查可执行的完成事件。

先固定布局时，记 $T_i$ 为原算子 $i$ 在该布局中的任务集合，其部分排定标记为 $o_i=\mathbf 1\{0<|D\cap T_i|<|T_i|\}$。在原算子 DAG 上限制

$$
h_i=o_i+\max_{p\in\operatorname{Pred}_G(i)}h_p,\qquad
\max_i h_i\le L,\qquad \max\varnothing=0.
$$

$L$ 限制一条依赖链上同时部分排定的原算子数。独立分支仍可各自开放。这个约束和 beam 宽度分别控制可行状态与保留状态数。

### 2.2 一次范围动作和状态更新

把输出轴和 K 轴按硬件对齐粒度划为单元。用 $J_i$、$K_i$ 表示算子 $i$ 的输出和归约单元数，无归约时令 $K_i=1$。跨 tile 的状态写作

$$
s=\bigl((u_i,Y_i,\mathcal G_i,R_i,B_i)\bigr)_{i\in V},
\qquad \mathcal G_i=\{(l_g,r_g,k_g)\}.
$$

$u_i$ 是已分配的输出前沿，$Y_i$ 是已发布输出的位图，允许不同组乱序完成。$\mathcal G_i$ 的每组记录输出区间 $[l_g,r_g)$ 与已完成的 K 前缀 $k_g$。$R_i$、$B_i$ 是仍有读者的串行 SSA 片段在 SRAM、DDR 的有效副本。开放标记改为 $o_i=\mathbf 1\{u_i>0,\ |Y_i|<J_i\}$，沿用上面的依赖链深度公式。并行开放的输出组另受服务给定的上限约束。

一个动作 $a=(i,g,k',z)$ 选择算子、已有输出组或从 $u_i$ 起的新组、下一归约终点，以及最终产出的驻留选择 $z$。若 $k'<K_i$，只更新该组前缀。若 $k'=K_i$，按整数合同做最终舍入，发布整组并移出活动集合。访问映射 $\Phi_{p\to i}$ 按输出区间、K 区间或整张量给出要读的单元。令 $M_{p,a}=\Phi_{p\to i}([l_g,r_g),[k_g,k'))$，动作需要

$$
M_{p,a}\subseteq R_p\cup B_p\quad\text{对每个输入成立},
\qquad
Y'_i=\begin{cases}
Y_i\cup[l_g,r_g), & k'=K_i,\\
Y_i, & k'<K_i.
\end{cases}
$$

同一个上游片段可以服务多组输出。只要还有未分配的组，或者任一未来消费者仍可能读，该片段就要有副本。对一条按 K 读取的边，只有全部输出组已分配后，源的 $[0,\min_{g\in\mathcal G_i} k_g)$ 才能按该边释放。算子完成后该边无剩余读者。多条出边的需求取并集。已用完的片段可直接释放，仍活跃且只有 SRAM 副本的片段被挤出时先写回。

### 2.3 容量、增量代价和 DP 递推

设 $\beta_i$ 是每个输出元素的部分和存储字节，$n(g)$ 是组的实际输出元素数，$\mathrm{bytes}(R_i)$ 按真实对齐和尾块长度计算数据容量。共享 SRAM 时检查

$$
P(s)=\sum_i\sum_{g\in\mathcal G_i}\beta_i n(g),\qquad
\sum_i\mathrm{bytes}(R_i)+P(s)+W_{\mathrm{scratch}}\le K_{\mathrm{SRAM}}.
$$

采用独立部分和 bank 时，数据 SRAM 只承担数据和工作区，另查 $P(s)\le K_{\mathrm{partial}}$。当前评估入口使用一个抽象数据池，读完后才回收本动作已经消耗的输入空间。容量不足时按固定次序淘汰旧片段。已保留的数据无需再次写回。

令动作处理 $n$ 个输出和 $m$ 个实际 K 元素，$B_D$ 是动作的 DDR 字节数，由缺失副本的读、落盘或溢出的写、外部输入、静态权重组成。$B_S$ 计入本地读取和新驻留的写。部分和的读写量为

$$
B_P=n\beta_i(\mathbf 1\{k_g>0\}+\mathbf 1\{k'<K_i\}).
$$

独立 bank 的串行代价为

$$
\Delta T=c_i+\left\lceil\frac{nm}{\rho_i}\right\rceil+
\left\lceil\frac{B_D}{v_D}\right\rceil+
\left\lceil\frac{B_S}{v_S}\right\rceil+
\left\lceil\frac{B_P}{v_P}\right\rceil .
$$

共享 SRAM 时把 $B_P$ 加进 $B_S$，去掉独立项。$c_i$ 是发令成本，$\rho_i$ 是服务计算速率，$v_D,v_S,v_P$ 为模型速率。此处的串行模型与上节普通事件编译器的资源日历是两个计价入口。

用 $\mathbf F(s)=(T,B,H)$ 记录到达状态的工期、DDR 字节和 SRAM 峰值。相同状态保留字典序更优的标号，工期优先以 $(T,B,H)$ 排，DDR 优先交换前两项。

$$
\mathbf F(s')=\min_{\mathrm{lex},\ a:\mathcal T(s,a)=s'}
\bigl(T(s)+\Delta T,\ B(s)+B_D,\ \max\{H(s),H(s')_{\mathrm{used}}\}\bigr).
$$

所有动作沿已执行的对齐计算量推进，桶编号增量为 $(r_g-l_g)(k'-k_g)>0$。每个桶按估计剩余成本保留至多 beam 宽度个状态。候选宽度枚举对齐单元的二次幂与合法边界。实验同时保留整算子、整 K 和单组备选，有限 beam 的结果是可行解，未做全局最优证明。完整实现见 [tile_frontier.py](../../../project/experiments/block_synthesis/tile_frontier.py)。

## 3. 评估与效果

### 3.1 从分块可行到真实首层

- **自动发现。** 小图测试覆盖 MatMul→Softmax、MatMul→ReLU、Add→RMSNorm，以及多节点链。16 行时，固定模型下 MatMul→Softmax 从 240 到 165 拍，Add→RMSNorm 从 192 到 147 拍（远端 113827）。这组隔离例主要核对 lowering 和开放深度。初始 Qwen 首层对照中，检查的 120 个原绑定只暴露整命令 ACK，深度 0 至 3 没有引出新交接。随后增加可独立提交的范围命令，整 K 计算仍完整。
- **真实首层与 SRAM 驻留。** Qwen2.5-3B、B1/S2、真实权重和整数图。23 个算子自动分段。相同范围布局下，相对强制走 DDR，beam 8 少 3 次回读、5,120 B，模型工期相同。beam 32 少 6 次回读、17,408 B，模型工期少 10,240 拍。四档写回均为 17,408 B。两组输入与整算子逐位一致。主要限制是跨站点合法链路和消费端依赖。见 [首层驻留评估](TILE_FRONTIER.md)。
- **特征轴与块级 Dot。** 特征分块相对整行驻留少读 380,928 B，整层 DDR 写入未下降。加入块级 Dot 后，整行驻留方案的模型工期从整算子的 93,582,477,980 降到 8,815,456,028 拍，DDR 从 50,583,128,704 降到 4,663,600,256 B。主要收益来自块级投影配方和权重、操作数复用。特征分块加块级 Dot 在这一模式下用 63,073,102,364 拍，说明切得更细会损失部分块级收益。Down 的 Gated 激活在该归档路径仍经 DDR。见 [两组输入与五档全表](TILE_FRONTIER_FOLLOWUP.md)。

### 3.2 由 DP 自选分块和续接

取真实整数图的 `v288 Product → v289 Dot`，一个 token 行、完整 $K=11{,}008$。下面是单组范围实验的 16 KiB 共享 SRAM 条件，含 2 KiB 工作区，数据按 16 B 记录，假定 SRAM／DDR 为 64／16 B 每拍。

| Down 计算输出列 | 整算子交接 DDR | 开放深度 2 的交接 DDR | 相对模型工期 |
| ---: | ---: | ---: | ---: |
| 128 | 344 KiB | 0 | −6.25% |
| 512 | 344 KiB | 0 | −1.57% |
| 1,024 | 344 KiB | 8 KiB | −0.30% |
| 2,048 | 344 KiB | 320 KiB | −0.03% |

128 列时，允许续接以后，从开放深度 1 到 2 使主前沿展开数从 1,393 到 2,539，交接流量从 320 KiB 到零。假设 SRAM 与 DDR 同为 16 B 每拍时，DDR 优先能保留零流量方案，预估工期增加 1.31%。完整 2,048 列的 S64 部分和已占 16 KiB，另外还需激活与工作区。单组全宽对照的 beam 增到 64 后仍选整 K。报告与作业 114341–114349 见 [范围搜索评估](TILE_FRONTIER_RANGES.md)。

### 3.3 多组全宽对照

固定相同图、2,048 列及 45,088,768 B 权重流量。多组上限为 4，独立 bank 的 S64 案例选了两组各 1,024 列。它们在一个 512 项激活块仍在 SRAM 时依次消费，然后再推进下一块。

| 资源情景 | DP 最终选择 | Mid 交接 DDR | 模型工期 |
| --- | --- | ---: | ---: |
| 数据与部分和共用 16 KiB | 整 K 加部分数据驻留 | 327,680 B | 3,216,672 拍 |
| 独立 S64 8 KiB，DDR 优先 | 同上 | 327,680 B | 3,216,672 拍 |
| 独立 S64 16 KiB、64 B/拍 | 两组交错 | 0 B | 3,215,248 拍 |
| 独立 32 KiB、64 B/拍，按 S80 图像密度计价 | 整 K 加部分数据驻留 | 327,680 B | 3,216,672 拍 |
| 独立 32 KiB、192 B/拍，按 S80 图像密度计价 | 两组交错 | 0 B | 3,211,008 拍 |

S64 两组路径增加 655,360 B 部分和片上读写。相对同池整 K，DDR 总量少约 0.72%，工期少约 0.044%。把激活改按 4 B 打包计价，独立 bank 情景工期收益仍约 0.04%。这些范围试验使用真实图形状和确定性随机整数，通过分块和整段算术逐位一致检查。S64／S80 bank、宽组续接和带宽是模型输入；32 项回归与完整模型数据见 [多输出组评估](TILE_FRONTIER_MULTI_OUTPUT.md) 和 [结果 JSON](TILE_FRONTIER_MULTI_OUTPUT_RESULTS.json)。

## 4. PR #269 的实际基线和当前 RTL 问题

| 问题 | 已有原生执行证据 | 还需要什么 |
| --- | --- | --- |
| Gate/Up→Down 的 Mid 落 DDR | PR #269 引用并复核的三 P 方案把 11,008 项激活量化为 86 个 A16 tile，共 21.5 KiB，按 29／29／28 放进三个原有 P.S。Down 从对应 P.S 取数，Mid 的 DDR 写回和回读为零。[三 P RTL 记录](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/docs/experiments/issue-250-three-p-ffn.md) | 正式 Algo1 的候选表应能表示已具备的三 P 本地路径，以及目标底座上确实绑定的窗口、复制端点和完成事件。 |
| 同一份 Mid 反复搬 | 现有三 P 运行按 6 轮输出范围执行。每轮跑完完整 K，把 86 个 tile 从源 P 送到三个 P 的输入窗。RTL 有 516 次 tile 重放和 24,768 个 16 B 目的写，共 387 KiB 片上写。该计数只包括目的写，不含读源、后续宏读或 DDR 权重。[PR #269 的 COPY 对照](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/3e696988d18829a583d573b8cb474ae587301660/project/experiments/block_synthesis/STATE_DEPENDENT_COST_PLAN.md#copy-与-a-读取共用-sram) | 现有范围内应按实际端口/ACK 核算本地读写及争用。减少轮数需要能复用已加载的 tile、保留多个输出组的部分和，或提供可跨 scope 的续接合同。 |
| Mid 全就绪才开 Down | 现有 RTL 验证程序在 Mid 发布并完成片上读回后再启首轮 Down。短程 TLM 明确检查 86 个 tile 全部提交。TLM `ffn-activation.tsv` 的 8 KiB 是 FFN 的归一化输入 $X$。[短程证据](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/3e696988d18829a583d573b8cb474ae587301660/work/YUZE-LU/219/native_ingress/request_retirement/REQUEST_SEQUENCE.md#pr-260-短程吞吐) · [执行器](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/dd423e5a8010e7371ee1ccbd589df00bc0ff6478/project/experiments/systemc_benchmark/native_tlm_ffn.py#L49) | 提前启动需要原生控制按 tile/版本发布、Down 在缺下一段时能等待、生产和消费的 SRAM 及计算资源能合法共占。之后由 Algo1 选择并导出相同依赖。 |
| 部分和跨命令 | 当前归档流式 Down 每个 P scope 最多 128 列，用范围供数跑完整 K。流式描述符拒绝部分 K scope。Attention 内部另有 S80 checkpoint，八路需 112 B 图像及匹配 ACK，此能力暂无 Down 的可执行绑定。[硬件合同核对](DOWN_NATIVE_CAPABILITIES.json) | 若要原生实现多组搜索，需要可验证的部分和位置、容量、端口、保存恢复成本、所有者、版本，以及分段完成接口。 |

**731 KiB/token 的出处。** 这是另一条 `U0/U1 → P0` 通用投影候选的静态命令量。该候选每 token 写 43 KiB S32 Mid，16 个 Down scope 各重读一次。已跑过的三 P 原生配方采用分布式 A16 驻留。项目的 Algo1 链接回执 109135 确认 192 条 CALL 及二进制与原归档一致。固定 K 窗口推进和阶段外层顺序由三 P 配方、控制器及测试夹具分担。短程 TLM 另有运行回执。全图同计划 Block V2 的执行与物理端点仍以各自的回执为准。[链接与范围](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/3e696988d18829a583d573b8cb474ae587301660/work/YUZE-LU/219/FRAMEWORK_INTEGRATION.md) · [另一条候选的静态审计](TILE_FRONTIER_MULTI_OUTPUT.md#原生硬件合同)

以三 P 路径为后续基线，应比较首个 Down 能提前多少拍、516 次片上 tile 重放能减少多少，以及部分和保存或资源争用会抵消多少收益。Algo1 负责合法配方、绑定和发令选择。原生服务仍需先给出能执行的发布、暂停、续接或局部复用动作。已有原生模板的 Mid 零 DDR 往返计入基线。如果原生服务之后已经能按 tile 发布，但生成的指令仍额外等待整行，额外的 WAIT 归 Algo1。

