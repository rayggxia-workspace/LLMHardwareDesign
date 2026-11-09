# 当前状态

2026-11-09：#219/PR220迭代16新增只读S/保护字/B银行跨元素连续程序、前序/周期独立核验及全部元素回放。
同九组/16KiB/18束，FFN新执行方式少3.47246%模型时间；同池强贪心与DP相同，非算法20%。
Windows/Linux各269项；三初态各48条8元素实际RTL链及保护字/银行负对照通过。
101593旧四循环全部元素接回完整36层整数图，三输入终态逐位通过；101590边界接口失败已修，101605补验；101604新连续整图回放运行。
迭代15已在线发布bf31827f；本轮发布以PR回执为准。外存中间结果中转/全S保留、算法20%/KV/SystemC能耗/token/s对照继续未完成。

2026-11-09：#219/PR220迭代15（本地阶段，尚待本轮在线发布）新增实测服务成本、凸区域驻留候选与单一图覆盖前沿。
真实FFN同4290驻留绑定/18束，超边估计较均摊强贪心少5.39681367%，新DP对新强贪心额外0；非整模型20%。
Windows/Linux各261项通过。101548旧完整选中计划三输入已终态逐位通过；101590真实边界、101591全图搜索、101593全部驻留元素接回整图均已提交，最近核验PENDING；101525继续RUNNING。
局部S仍有每元素冷启动和大范围保留的保守性；完整KV/SystemC时间能耗/token/s/充分适配对照继续未完成，目标active。

2026-11-09：[Issue219/PR220迭代14](../work/YUZE-LU/219/throughput-opt/ALGORITHM_ROUND_14.md)修复FFN切片来源闭合，
完整图重新独立核验通过。新增原生SSA/有限S驻留复制DP原型、216组合成边界数值、三初态各168程序实际M/E/S RTL及负对照；
Windows/Linux各248项通过。尚未接入完整综合器、无实际权重整网驻留或时间/能耗资格，外存问题仍未完整解决。
101516终态同池仅额外0.00010276037%，新选中数值101548及拓扑101525归档时运行；算法20%/KV/SystemC/token/s继续未完成。

2026-11-09：[Issue219/PR220迭代13](../work/YUZE-LU/219/throughput-opt/ALGORITHM_ROUND_13.md)验证未修改P/M/S上的多行S32 Add聚合：
三初态各384例、独立负对照及Windows/Linux各234项通过。23个真实FFN Add含原准备的串行成本机会少29.8194%、逻辑记录少29.4998%；
尚未注册共同候选/生成新调度，不是整模型或算法收益。一般脏驻留仍未实现。101500历史池终态更慢于当前强计划，保留负结果；四项旧作业仍运行。
算法20%/KV/SystemC能耗/token/s/最优适配对照未完成，继续in_progress。

2026-11-09：[Issue219/PR220迭代12](../work/YUZE-LU/219/throughput-opt/ALGORITHM_ROUND_12.md)新增未就绪长链下界与单金属诊断，Windows/Linux各231项通过。
真实FFN同池新greedy/DP/backbone-DP额外0，125个最大静态并集也未加强切片下界；完整新greedy更差，保留强计划及负结果。
101509完整phase池终态，条件DP仅额外0.0000192676%；101526其自身三输入数值终态逐位通过。101516新搜索、101525拓扑继续核验。
一般脏驻留/算法20%/完整KV/SystemC能耗/token/s/最优适配对照未完成，in_progress。

2026-11-09，#219/PR220[迭代11](../work/YUZE-LU/219/throughput-opt/ALGORITHM_ROUND_11.md)部分交付：
新增原生tile描述符阶段协作、独立重建/预约检查；Windows/Linux各221项、4个literal/native有限S双回放通过。
真实FFN101508终态：共同后端少3.07596%，同池搜索额外0，流量多48条；普通分片全图101506终态仍额外0。
新整网贪心167,410,873,122 ticks，较旧强计划少17.39470%是共同后端收益，不能计算法20%，流量多4048条。
101511新贪心三个输入逐位数值已终态通过，HF/argmax/SHA保持；101509策略、101513同池好前缀及101500/101501仍运行，4核/UNLIMITED。
一般脏驻留、算法20%及多轮、完整KV/校准SystemC能耗/token/s/最优适配对照未完成，Issue继续in_progress。

2026-11-09，#219/PR220[迭代10](../work/YUZE-LU/219/throughput-opt/ALGORITHM_ROUND_10.md)部分交付：
完整已验计划关键链复原202,663,587,646 ticks；本轮分片前动作族最多剩8.6111%时间降幅，需增加真实可执行选择。
修正辅助窗口下界，新增独立多M原生tile分片/地址与临时区检查，Windows/Linux各214项及4个literal/native有限S双回放通过。
真实FFN18个新候选仍不胜最强旧计划，额外0；PU资格E均接通道1时整服务独占阻断并行，下一轮验证实际描述符阶段交接。
101504/101505终态通过，101500/101501/101506归档时RUNNING、4核/UNLIMITED；整网新数值及20%/一般驻留/KV/SystemC能耗/token/s仍未完成。

2026-11-09，#219/PR220[迭代9](../work/YUZE-LU/219/throughput-opt/ALGORITHM_ROUND_9.md)部分交付：
实际辅助窗口/三段外存物化、独立S/资源/成本审计及同宽度好前缀消融；Windows/Linux各204项，
三组指定SRAM初态各347例原生重排/ACK及负对照、68例有限S数值通过。新动作额外16条LOAD，非外存减少成果。
真实FFN最终仍选此前最强计划，额外0；保留退化和错误分母诊断，不凑20%。修正N后的完整旧DP三个输入数值已终态逐位通过。
完整窗口/好前缀消融101500/101501继续运行UNLIMITED；一般驻留、KV/SystemC能耗/token/s及最优适配对照未完成，Issue in_progress。
登记pending，看板unverified/同步pending，待独立审查不自合并。

2026-11-09，#219/PR220[迭代8](../work/YUZE-LU/219/throughput-opt/ALGORITHM_ROUND_8.md)部分交付：
新tile贪心/DP各三次完整3B整数数值通过；发现历史NExp原生模板与独立参考不一致，已改两次显式Stats，
三个初态各653例N RTL及负对照通过。旧向量数值不证明旧原生命令，重编译整图贪心三输入数值逐位通过；完整旧DP/条件DP均202,663,587,646模型ticks，新策略额外0，选中DP数值补验中。
Windows/Linux各187项；修正后FFN较最强同池基线3.890449%，价格下界无新增收益，保持消融；一般驻留/合法阶段预约继续推进。
100972已自然完成；算法约20%、完整KV/校准能耗/token/s与最优适配对照继续in_progress，待独立审查不自合并。
登记pending，看板unverified/同步pending。

2026-11-09，#219/PR220[迭代7](../work/YUZE-LU/219/throughput-opt/ALGORITHM_ROUND_7.md)部分交付：
受限tile共同候选、缓存失效、独立检查及有限S小例子数值通过，Windows/Linux各178项。
真实FFN规划搬运减67.0961%，该计划/新整网数值仍待验；按显式实例绑定外围服务，首轮C/F/J成本试验作废留证。
条件策略相对同池旧DP额外0，算法20%、完整KV/系统能耗/token/s与最优适配对照继续in_progress；登记pending，看板unverified/同步pending，待独立审查。

2026-11-09，#219/PR220[迭代6](../work/YUZE-LU/219/throughput-opt/ALGORITHM_ROUND_6.md)部分交付：
不变M/E/S的347例多列及真实S32转换、184例多行和Windows/Linux各169项通过；有包含转换/外存复制的共同成本配方，
尚未接入完整DP/缓存失效/新计划数值，不计DP20%。前轮阶段计划101213完整3B三输入逐位通过，HF误差/argmax保持；
100972早期源全图仍RUNNING/UNLIMITED。算法约20%、一般驻留、完整KV/校准时间能耗/token/s与最优适配对照继续in_progress。
登记pending，看板unverified/同步pending，待独立审查不自合并/关闭。

2026-11-09，#219/PR220[迭代5](../work/YUZE-LU/219/throughput-opt/ALGORITHM_ROUND_5.md)部分交付：
同池条件尾部DP在完整3B额外0.0716468%、真实FFN切片0.0871689%；资源尾部消融无收益。Windows/Linux各157项通过。
现有M/P/S/feeder不变的84个四态RTL多行场景通过，含R2/K2048；B staging减半，A不变，尚未接入全图候选，
不计DP20%或系统性能。完整Linux成本/调度审计已过，新计划数值101213待验；额外SystemC阶段微实验100970及搬运审计100971通过，
早期冻结源全图搜索100972仍运行。微实验不代表整机时间/能耗/token/s。
一般驻留、完整KV decode/能耗/token/s及充分适配ASIC/FPGA对照继续in_progress；登记pending、看板unverified/同步pending。

2026-11-09，#219/PR220迭代4完成选中全图计划的逻辑搬运守恒审计：A重复读约65.8%，静态权重约23.4%。
一般tile与跨算子有限S驻留未完成，已写入[后续合同](../project/experiments/block_synthesis/MEMORY_REUSE.md)。
新增精确长循环阶段基础，本地145项通过，孤立候选诊断不计新算法收益；额外远程SystemC核对待终态。
独立[硬件容量PR237](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/237)不改变固定硬件算法基线。
实际20%、更多轮、KV decode/能耗/token/s及充分适配ASIC/FPGA对照仍未完成，继续in_progress；登记pending，看板unverified/同步pending。

2026-11-09：[PR220算法迭代3](../work/YUZE-LU/219/throughput-opt/ALGORITHM_ROUND_3.md)完成输出列分片及前沿整数分配，134项及本轮六次完整3B整数数值回放通过。同候选/预算较强基线下九组18束收益0.706898%，不将约29%动作池变化计入20%算法目标。SystemC原生命令阶段微实验及负对照通过，尚非完整系统性能；下一轮校准阶段占用与事件前沿。SystemC能耗、KV token/s及ASIC/FPGA对照未完成，Issue219继续in_progress、待独立审查；登记pending、看板unverified/同步pending。

2026-11-09：[PR220算法迭代2](../work/YUZE-LU/219/throughput-opt/ALGORITHM_ROUND_2.md)新增8,404原语/准备服务及独立工作量/依赖/容量检查，修复静态线束预算导致有解却丢失的问题；122项及完整5/9组预算复核通过。同候选/同预算DP额外执行收益仍0，阶段化与编译优化不计入20%目标；SystemC3.0.2环境已就绪，时间/能耗/KV token/s及ASIC/FPGA对照继续未完成。Issue219持续in_progress，待独立审查；登记pending、看板unverified/同步pending。

2026-11-08：PR220通用Dot准备复用通过完整Qwen2.5-3B B1/S2无KV复验，110项及五组/九组各三输入逐位一致。同10/18束模型代价分别下降60.5851%/59.9470%，搬运减约72.058%，每S仍16KiB；显式外存预留增83.824MiB，容量未资格化。收益来自循环配方，非DP单独收益；见[结果及边界](../work/YUZE-LU/219/throughput-opt/RESULTS.md)。待独立审查，登记pending、看板unverified/同步pending。

2026-11-08：PR220新增每次转移的状态求值与部分前缀命中，完整Qwen2.5-3B五组/九组各三输入及105项检查通过。五组/同10束预算结果不变，九组模型完成时间增加约0.00007686%；未取得新增性能收益。见[结果](../work/YUZE-LU/219/STATE_COST_RESULTS.md)。成果待独立审查；登记pending、看板unverified/同步pending。

2026-11-08 综合算法补充：[Issue219/PR220](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/220) 已加入有限S只读Dot分片及缓存感知DP状态；完整真实3B五组/九组各三输入与旧整数结果逐位一致，100项测试及独立地址/容量/静态互斥重验通过。复用贪心较原基线模型代价降17.16%、搬运降25.40%；九组DP另降26.14%但束数10→18，同10束无额外收益。仅覆盖只读Dot分量；整网控制编码与真实布线另验。见[本轮说明](../work/YUZE-LU/219/READ_CACHE_RESULTS.md)，下方“全部spill”系旧基线。

2026-11-08 审查修复及控制接入：[Issue219](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/219)/[PR220](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/220) 原整网 DP 与独立检查器遗漏 incompatible_nets，现已分别修复。90 项测试（含 150 个互斥小 DAG 穷举对照）、完整 3B 计划重验通过；当前独立母控含实际程序 SRAM、两组 U_64 局控的小图自动镜像完成 9 次数值／写 ACK／源保持与释放回放。原完整清单声明互斥对为 0，不代表物理无冲突；固定放置小图不代表任意整网 DP 控制编码、九目标或物理通过。见[修复与控制证据](../work/YUZE-LU/219/MUTEX_CONTROL_RESULTS.md)，旧数值及同预算无收益结论保留。

2026-11-08 算法整网里程碑：[Issue219](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/219)/[PR220](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/220) 修复Gather、实际量化、动态矩阵/地址与完整S32原语分解。完整真实Qwen2.5-3B B1/S2三输入生成IR数值回放通过（L2 0.5265%/0.7251%/0.5592%，两位置argmax一致）；各S16KiB、预连0、#182虚拟外存，整网计划与独立检查通过。75项测试、原语三初态通过；同连接预算DP尚无整网收益，全部spill后端仍需tile/cache优化。不继承系统RTL/物理资格，其他bench未获完整整网资格。见[完整结果及回执](../work/YUZE-LU/219/FULL_RESULTS.md)，下方11-07的Gather阻塞为已修复历史。

2026-11-07 算法后续：[Issue219](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/219)/[Draft PR220](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/220) 新增M/N/E/G/R256/T原生命令配方、跨片状态保留和显式格式转换。服务器46项检查、五类混合图38任务及R256跨片三初态回放通过，私有S各16KiB、预连0、虚拟外存。完整Qwen2.5-3B仍缺Gather、量化与动态布局等软件转换，未称整网通过。[结果与回执](../work/YUZE-LU/219/LEAF_RESULTS.md)。

2026-11-07 算法分支进展：[Issue #219](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/219) / [Draft PR #220](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/220) 已修正零数据预连、虚拟外存和算法验收边界；服务器34项检查、真实N/E客户端三初态回放及5组16KiB调度对照通过。[证据与未完成项](../work/YUZE-LU/219/FIX_RESULTS.md)。完整3B模型的数值/尺度/布局等软件转换尚未完成；控制镜像、原生DMA和最终物理不作为当前算法验收前提。此进展不改写其他硬件任务的资格或状态。

2026-11-08，#214 合并后 U_128/U_64 的普通三源 FMA 入口拒绝和双向 SEND 死锁由 [PR #221](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/221) 修复。两版均通过完整原版 GDS DRC 0、原生 TT 300 MHz 时序、电气/PG及代表上层三档 RC；最终网表 48/48、78/78 次全部通过。交付包及全部 1,389/2,101 个清单文件已本地回收核验。U_64 原生 hold +0.212 ps，只证明当前条件通过；九实例顶层和其他 PVT 不在范围。详见[最终回执](../work/YUZE-LU/212/u-native-fix.md)和[机器索引](../work/YUZE-LU/212/u-native-fix.json)。P 和 C/F/J 未修改，历史 U 功能覆盖不足已更正。用户已授权将 PR #221 并入 main，实际合并状态以在线回执为准；登记 pending，看板 unverified/同步 pending。

2026-11-08，用户授权将母控 [PR #224](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/224) 合入 main，并在[五类 Block 与母控统一入口](experiments/assets/five-leaf-bases/README.md)并列索引源码、图册及双格式验收包。工程证据不变；合并结果以 PR 在线回执为准，授权整合不冒充独立审查或九实例系统验收。

2026-11-08，[Issue #223](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/223) / [PR #224](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/224) 的母控64位后128位工程门均通过。两格式各54项RTL、54项最终母控网表、69项实际Block/局控RTL组合回归；共用同一组六文件，TT300MHz setup/hold +374.917/+7.629ps、原版完整GDS DRC0，电气/RC/PG/SRAM时钟通过。64/128包及3860/3148个内部文件均已本地校验。范围为两驻留目标、有限原生profile；不是九实例联合物理或完整ISA验收，局控PM仍为行为夹具。详见[正式验收报告](experiments/mother-control-dual-format.md)。进入待独立审查阶段，不自合并；登记及看板缺项沿用下方交接。

2026-11-07，[PR #213](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/213) 的 C/F/J `_128` 独立交付保留，C/F 同时发送死锁已由独立 TX 槽修复并通过真实 SRAM 和母控/双局控程序回归。新增 C/F/J `_64` 固定 #180 2a66b918，完整原版 GDS DRC 均为 0；PG、电气、LEC、TT 300 MHz 提取时序及最终网表回放全部通过。三包已回收并逐项核验全部316/273/548文件，工程交付按用户授权随 #213/#214 整合，最终合并回执以 PR 在线状态为准。后制 RC 为研究模型，九实例顶层及跨 PR 控制合同另验。详见[验收索引](../work/YUZE-LU/211/control64-acceptance.json)和[五类两版实际摆放图册](experiments/assets/five-leaf-bases/README.md)。

面向 main 的六块交付：[PR #161](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/161)；已提交待独立审查，尚未合并。R 仍未完成。

## 2026-11-01：六块成果先交付，R 未完成

按用户决定先提交 M/N/E/G/S/T 六块，不等待 R；六块全部适用最终门及源绑定本地实收通过，R 标为未完成且不在合格清单。Issue #143 保持开放，研究 PR #144 保留；当前 `task/143-six-block-main` 基于 main a103da35，面向 main 的成果整合待独立审查。规格和结果见 docs/BLOCK_V2.md、docs/BLOCK_V2_RESULTS.md；核验命令见 docs/ARCHITECTURE.md。登记 PR5 pending；缺 config/board.json，看板 unverified/同步 pending；审查人待指定。历史记录保留在下方。

- 更新日期：2026-10-30（中国标准时间；本次只更新共同文档规划，不重跑物理实验）
- 当前规划补记：[Issue #139](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/139) 记录 M＋V 三宏（归约与归一化、基础向量算术、激活与门控）＋独立 R＋S＋T，详见[决策 0005](decisions/0005-compute-block-v-split-r.md)。各种先一个实现，逐宏交付最终布局布线；新三宏尚待实现、具体规格仍待验证，原 V 结果不转移资格。现有 #121/#130 实验保留，阵列/多实例/裕量版本/预连后移；本次未改变原实施任务状态或服务器作业。
- 当前阶段：首轮 Block 实现与表征推进；共同底座和任务定制分阶段验证。具体实现状态以 [Issue #121](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/121) / [PR #122](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/122) 为准；历史 H1/H2 证据保留如下。
- 本次共同文档澄清：[Issue #123](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/123) 记录[当前实施边界与分阶段冻结](decisions/0004-block-library-base-freeze.md)：首轮叶块不要求同时确定多实例、不同裕量物理版本组合或预连拓扑；这些在共同底座阶段确定并统一冻结。原实施任务的多阶段范围和验收状态不因此缩减。
- 历史 H1 工程：[Issue #15](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/15) 已完成openTPU ACT/MXU同功能／资源的块内及父层对照。三块和两父层、六类证明共十一份封存来源严格通过；拆分叶面积+0.412%、总信号线+7.142%、通孔+2.974%，完整setup／hold两组均满足2.5ns／0.5ns预算。[中文结果与三类图表](experiments/issue-15-opentpu-results.html)已生成并目视核验，详见[实验记录](experiments/issue-15-opentpu-comparison.md)。独立全量重布线21亦已自然完成并通过十一项来源／证明对照；本次整合不启动、终止或改写既有远程作业。
- 资料接入：[Issue #1：初始化项目并导入初期资料](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/1)；资料已进入 `main`，[PR #2](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/2) 已合并
- 当前资料：项目说明 v1.0（含 2026-10-30 架构规划补记）、专题研究文档、来源笔记，以及五个参考项目七个案例的布线分析包；三份 HTML 报告、llaccel 引擎内部分析及远程服务器规则已通过 [PR #4](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/4) 合入 `main`；工艺互连资料的逐层资源评估补充已一并提交
- 已确认边界：第一版采用 Nangate45 原生 M1–M10、via1–via9 预制，新增研究 M11/M12、via10/via11 后定制；叶块冻结与共同底座冻结分别验收。技术模型、完整宏、共同底座及多产品结果须按实际证据接收，不能将本次文档更新视为实现完成。
- 关键限制：现有布线结果包含少量 RTL 片段，不含完整源工程、物理数据库、工具环境和日志，不能单靠本仓库复跑物理实现
- 历史 H1 工程里程碑（2026-10-23 04:37 CST）：拆分89829自然完成全部严格物理、PG及完整STA，功能89831／RC覆盖89832／五个完整ODB成本复核89833也全部通过。快照f65688a957f13ef70216e923891ef6ff539adfc6f81c3e29a74ba5d10332720d，主对照不随实时采集变化。全量DRT21／89826及功能89827／覆盖89828／完整ODB89835也全部自然通过；补充快照独立保存，不改写主报告。全部作业UNLIMITED，无耗时取消。
- 整合交付：PR #8、#10 已合入 main，H1 完整整合树通过本地核验并由 PR #17 交付，其最终 CI／合并状态以在线记录为准。后续 H2 由[Issue #31](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/31)独立推进，本次不修改其工作树或运行任务。项目登记及看板权限仍待管理员处理，详见[整合回执](handoffs/2026-10-23-h1-html-integration.md)。

- 首轮结果：完整 VECTOR 已完成详细布线并导出最终寄生／宏模型，DRT错误0；3 ns setup及电容检查未通过。修复宏PG接入后，89472完整顶层 `COMPLETED 0:0`，DRT错误0、最终双网PSM和2246位接口检查通过，89475最终只读审计通过；父级仍有3个setup违例。历次失败保留，这些工程结果不构成合格硬核或系统签核
- 任务入口：[本仓库 Issues](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues)
- 项目登记：[管理中心 PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5) 待审查；合并前状态为 pending
- Projects 入口：候选[组织看板 #1](https://github.com/orgs/rayggxia-workspace/projects/1)；本轮查询因缺少 `read:project` 失败，且无 `config/board.json`，实际看板与条目 `unverified`、同步 `pending`。恢复动作见 [Issue #7 看板交接](handoffs/2026-10-21-issue-7-projects.md)

本页只记录全项目阶段和关键限制；具体任务进度以 Issue 和 PR 为准。
