# Issue27 调度模型接口与严格边界

输入为 `tasks: list[dict]`，每项必须有 `id`、`duration`、`deps`、`resources`；`metadata`可选且不参与调度。id非空且唯一，duration为正整数，deps为无重复的已知id列表且整体为DAG。resources是已声明累计资源的**正整数**占用；无占用用空字典。capacity是正整数，单任务需求超过容量直接拒绝；零需求不隐式忽略，必须由builder显式省略。输入不被修改。

`schedule(tasks, capacities, policy='critical')` 返回 makespan、events、policy、下界和 `proven_optimal=False`。events逐项为 `{id,start,end}`，区间为 `[start,end)`；同刻完成可供同刻启动使用。任务不可抢占，启动时一次性预留全部资源并一直占用到结束，无内部释放或分阶段使用。

四个list策略统一调用：critical按包含本任务的最大剩余duration路径降序；fifo按所有前驱已结束的首次时间；shortest/longest按duration。平局按原始任务输入顺序。每个完成事件释放全部完成资源后扫描全部就绪任务；前面的任务不fit时可让后面的fit任务启动。因此不是只看队首；这些启发式也没有主动留空优化。

`validate_schedule(tasks, capacities, result)` 返回 `valid/errors/makespan/resource_peaks`。独立检查所有id恰好一次、整数非负开始时间、正区间和精确duration、每条完成—开始依赖、报告makespan；按边界时间排序、结束先于开始，用独立累计量sweep检查各容量。不调用list scheduler、oracle或其资源可用状态。输入schema/DAG核验共用，但事件合法性算法独立。校验器不证明任务图、数据精度、生命周期或资源合同本身正确。

`exact_schedule(tasks, capacities, max_tasks=9, max_states=250000)` 是有限小模型的精确event DP。状态为已完成集合及运行任务的剩余时间。枚举**所有**fit的就绪任务子集，含非极大子集；有运行任务时允许一个任务都不启动、留空到下一结束事件。无运行任务时不考虑整个系统空转，因为没有外部释放时该动作只整体拖后后续工作。它不假设non-delay最优。相同最优值确定性优先选择本时刻更多启动的子集，再按输入索引。

event时间枚举的完备性仅对这里的模型成立：恒定累计容量、正整数duration、零滞后完成—开始依赖、所有根任务在0可用，无外部release/deadline/预约/时变容量，目标仅最小makespan。在这些条件下存在最优active schedule：把任何可左移启动向前移直到0或某个前驱/竞争任务结束，不会增加makespan；所有启动因此可取完成事件。枚举全部启动子集和等待完成事件覆盖这种最优解。该说明不把工作保持(non-delay)当作最优性条件。达到state budget或任务数超限时抛异常，绝不把未搜完的结果标为optimal。

反例：x/y容量各1。A用x执行5；B用y执行1；C在B后用x执行1；D在C后用y执行5。四个非延迟策略都在0启动A和B，makespan=11；主动留空x可 B[0,1)、C[1,2)、A/D[2,7)，makespan=7，且路径B-C-D下界7证明最优。可直接否证“尽早启动所有fit工作总是最优”。

测试另有独立整数start枚举：逐任务按拓扑序给出0至串行上界内的整数开始，逐整数slot计容量，允许任意等待，不复用event决策。18个固定seed随机4任务DAG及边界fixture与event oracle的最优值一致；同时校验四策略的可行性。小规模最优和随机核对不能证明大图启发式最优。

本模块不持有静态buffer、不进行bank地址分配、不计buffer跨多个任务的全活区间，也不解释INT8/INT32转换、scale、FIFO、背压、突发、包头、外存latency、流水、时钟或物理连线。root的builder与buffer checker必须独立建模这些部分。bank“端口”和“带宽”若是累计资源，其单位、服务时间、全双工/半双工、读写是否互斥必须先由合同明确；不得凭此抽象执行时间声称真实硬件周期、可布线或PPA。任务拆分（read/compute/write）、前驱和同时生存数据的正确性仍是调用方义务。

不支持preemption、可变duration、setup/切换代价、最小启动间隔、pipeline内部多阶段reservation、优先级deadline、连续时间、buffer-dependent admission或任务运行中资源变更。需要这些语义时应先扩展合同和独立oracle，不能静默复用当前最优性标签。动态存储占用若随调度改变，精确最优结论也不适用，必须由独立buffer约束oracle重新验证。
