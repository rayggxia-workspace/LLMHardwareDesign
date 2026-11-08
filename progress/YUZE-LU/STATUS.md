# YUZE-LU 的进度

2026-11-09 CST：Issue219/PR220算法迭代3加入完整K列分片与每前沿整数分配，134项、本轮六次完整Qwen2.5-3B B1/S2无KV数值逐位一致；独立审计及原件SHA核验通过。同池较强基线下整网九组18束0.706898%、真实FFN切片3.800989%，未达20%。官方SystemC原生命令阶段微实验及负对照通过；整服务锁通道掩盖重叠，下一轮做经校准的事件前沿，不能以微实验当算法/整网性能。见[证据及后续](../../work/YUZE-LU/219/throughput-opt/ALGORITHM_ROUND_3.md)。时间/能耗/KV token/s与充分优化3–4B对照仍未完成，持续in_progress；待独立审查，登记pending、看板unverified/同步pending。

2026-11-09 CST：Issue219/PR220算法迭代2完成原语阶段化、静态线束未来可行性与已知好解保留；122项/完整5、9组工作量与预算审计通过。修复九组10束有解却被窄beam丢失的问题；同候选/同预算DP执行收益仍0，新动作族九组仅剩约2.79%重排空间，20%目标继续。SystemC3.0.2安装/FIFO环境检查通过，未有校准性能结论。[本轮证据及后续](../../work/YUZE-LU/219/throughput-opt/ALGORITHM_ROUND_2.md)。待独立审查、Issue in_progress；登记PR5 pending、看板unverified/同步pending。

2026-11-09 CST：算法迭代1为当前候选族建立强制资源/依赖链乐观下界，五组/九组现计划剩余改善上限仅0.000323%/0.765027%；112项及Slurm100652通过，6份原件SHA核验。[诊断及下一轮](../../work/YUZE-LU/219/throughput-opt/ALGORITHM_ROUND_1.md)。需改进合法分阶段/分片/驻留决策，不能只调beam；不是硬件性能上限。算法20%及SystemC/能耗/token/s/ASIC-FPGA目标持续in_progress。

2026-11-08 CST用户追加：准备外提只作共享后端基线，不计入算法本身约20%目标；继续多轮。后续须有SystemC（若支持）的校准时间/能耗、prefill及带KV decode token/s，并与充分优化的3–4B ASIC/FPGA比较；若硬件瓶颈需关联独立PR。[验收合同](../../work/YUZE-LU/219/throughput-opt/OPTIMIZATION_CONTRACT.md)。当前持续in_progress，算法目标及系统比较未完成，不以约60%后端下降结束。

2026-11-08 CST：Issue219/PR220准备复用已完成完整3B复验，五组同10束降60.5851%、九组同18束降59.9470%，搬运约降72.058%。110项和六次完整数值逐位一致，30份原件SHA核验。显式外存增加83.824MiB，实际容量未资格化；非DP单独收益、未新增RTL/物理资格。[结果与源回执](../../work/YUZE-LU/219/throughput-opt/RESULTS.md)。成果进入待独立审查，不自合并/关闭；登记pending、看板unverified/同步pending。

2026-11-08 CST：Issue219/PR220继续优化，隔离分支 task/219-throughput-opt。原生工作剖析发现Dot重复准备A分量；已实现通用循环外提、显式外存地址、独立成本检查与数值接入，本地110项通过。完整3B相同范围/预算复验待运行，不宣称收益。入口[迭代记录](../../work/YUZE-LU/219/throughput-opt/README.md)；远端PR仍1d284bdc、待审，登记pending，看板unverified/同步pending。

2026-11-08：PR220新增每次转移的状态求值与部分前缀命中，完整Qwen2.5-3B五组/九组各三输入及105项检查通过。五组/同10束预算结果不变，九组模型完成时间增加约0.00007686%；未取得新增性能收益。见[结果](../../work/YUZE-LU/219/STATE_COST_RESULTS.md)。成果待独立审查；登记pending、看板unverified/同步pending。

## 2026-11-08 CST：综合只读分片复用

[Issue219/PR220](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/220)：新增真实Dot分片、相同SSA输入驻留和缓存感知DP状态。完整3B五组/九组各三输入逐位一致、100项服务器测试通过；搬运减25.40%，同10束无DP额外收益。见[回执与图册](../../work/YUZE-LU/219/READ_CACHE_RESULTS.md)。待独立审查，不自合并或标done；一般脏缓存、整网控制编码、实际布线另验。登记pending，看板unverified/同步pending，待有权限维护者处理。

## 2026-11-08 CST：#220 静态互斥修复与当前母控回放

[Issue219](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/219)/[PR220](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/220)。修复 loop DP 和独立检查器遗漏 incompatible_nets，固定／已选连接跨时间保留约束；100341 的 90 项测试含 150 个互斥小 DAG 穷举，100338 完整 3B 计划重验通过。100343 的当前独立母控含真实程序 SRAM，配两组 #221 修复后的 U_64 局控执行自动生成 Add/Mul 小图，9 次回放核对实际数值／写 ACK／源释放／连接，正常352拍、背压491拍、复位后486拍；这是固定放置控制子集，不是整网／九目标／物理覆盖。完整数值、零预连虚拟外存和同预算无整网收益结论不变。23 个最终控制输入 Git blob 对上，v1/v2 的 66/24 份输出 SHA 核对；失败环境作业100340保留后改用已有 CP 环境重提通过。见[本轮证据](../../work/YUZE-LU/219/MUTEX_CONTROL_RESULTS.md)。成果待独立审查，不自审、合并或关闭Issue；登记pending，看板unverified/同步pending。后续：任意整网计划控制编码、tile/cache及真实物理反馈。

## 2026-11-08 CST：完整3B生成程序与整网有限调度

[Issue219](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/219)/[PR220](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/220)。本轮属于#220的软件缺口已修复：Gather、真实量化/布局、完整S32原语、数值回放与同源成本。最终100224/100233/100234/100235均COMPLETED0:0，75项测试、完整Qwen2.5-3B B1/S2三输入数值和五组/九组16KiB独立计划检查通过。同连接预算无整网收益，九组多束需求时模型代价降低2.68%，不称系统性能；全部spill后端的tile/cache优化、更多完整模型和物理反馈仍待后续研究。见[完整结果](../../work/YUZE-LU/219/FULL_RESULTS.md)及离线图册。成果待独立审查，未自审/合并/关闭Issue；审查人待指定，登记pending，看板unverified/同步pending。下方11-07的Gather阻塞为已修复历史。

## 2026-11-07 CST：原生叶宏转换和五类混合计划

[Issue219](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/219)/[Draft PR220](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/220)。补入G/R/T、M跨K累加、流式N、实际E宽度/尺度转换和状态租约；服务器46检查、38任务三初态原生回放、两类S四银行验证通过。各S16KiB、数据预连0，搬运使用既有虚拟接口。完整3B重检首个未覆盖为Gather，后续仍需量化、动态矩阵布局及其余整网转换；不归因于控制/预连/物理。见[证据](../../work/YUZE-LU/219/LEAF_RESULTS.md)。Issue in_progress、PR Draft；审查人待指定；登记pending，看板unverified/同步pending。

## 2026-11-07 CST：算法范围修正、零预连与虚拟外存

[Issue219](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/219) / [Draft PR220](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/220)。撤回未经证实的硬件缺失判断；控制镜像、真实DMA和最终物理不作为算法前置条件。接入#182来源的虚拟外存，服务内连线纳入静态并集，增加独立流并行构造和真实N/E整行规则。服务器34项检查、三初态2048 RMS→残差与16 Softmax的17,792周期回放通过；5组16KiB对照完成。完整3B的矩阵/G/R/T、尺度/布局等软件lowering仍未全部完成，不称整网成功。证据、失败与入口见[修订结果](../../work/YUZE-LU/219/FIX_RESULTS.md)。状态in_progress/Draft；审查人待指定，登记pending，看板unverified/同步pending。

## 2026-11-07 18:50 CST：有约束规划器与真实 U 服务回放

[Issue #219](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/219) / [Draft PR #220](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/220)，分支 `task/219-general-block-search`。新增链覆盖 DP、逐元素分片、流式初解、STORE/LOAD/spill、S 时间/地址联合约束、共享副本、跨层静态网任务组改进和独立回放。最终服务器25项测试通过；生成的4项真实 U/E/S 程序三初态均与80周期预测一致。完整 Qwen2.5-3B（30.86亿参数）HF/ORT前端验证通过，整网 lowering 明确未覆盖，未生成 MC/LC 镜像或物理验收。历史0.6B和假设架构结果撤出正式证据。图册、作业、哈希、失败和下一步见[本轮结果](../../work/YUZE-LU/219/JOINT_RESULTS.md)。后续接 M/N/G/R 数值 lowering、原生 DMA 和共同控制子集；状态保持in_progress、PR Draft、审查人待指定。登记pending，看板缺配置/权限，unverified/同步pending。

## 2026-11-07（CST）通用Block前沿搜索原型

[Issue #219](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/219) · [草稿PR #220](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/220)。服务器99698完成64组分析对照；完整Qwen3-0.6B浮点前端验证通过；23组分析计划独立重放通过，41组保留失败。输入与结果图册及哈希见[结果记录](../../work/YUZE-LU/219/README.md)。当前16 KiB场景均未完成，仍需多算子覆盖、分片/spill、原生控制镜像和pin/电气合同，不能称完整综合器或硬件通过。状态保持in_progress，PR为草稿，审查人待指定；登记pending，看板缺配置待核验。

## 2026-11-08（CST）U 原生入口和双向发送修复

[Issue #212](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/212) → `in_review`；[PR #221](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/221) 待独立审查。独立 TX 槽和普通三源入口修复后，两版重新综合并通过完整原版 GDS DRC 0、TT 300 MHz、电气/PG及三档代表上层 RC。U_128 setup/hold +255.014/+14.595 ps，U_64 +73.082/+0.212 ps；最终网表 48/48、78/78 全部通过。两包及全部 1,389/2,101 文件回收核验成功，31 硬件源文件与审查代码一致。[最终回执](../../work/YUZE-LU/212/u-native-fix.md)。P 不变。用户已授权将 #221 合入 main；五类图册 U 两版已绑定新验收包，P/C/F/J 图源不变。实际合并状态以 PR 在线回执为准，Issue 在线 assignee 未指定。登记 PR5 pending，缺 board 配置，Projects unverified/同步 pending，复用接入交接 Issue7。

2026-11-08 CST：用户已授权将 #223 / PR #224 母控双格式交付合入 main。新增五类 Block 与母控的[统一索引](../../docs/experiments/assets/five-leaf-bases/README.md)，原目录及交付散列保持不变。合并状态以 PR 回执为准；独立审查未代批，登记/看板缺项继续由 Issue #7 交接。

## 2026-11-08（CST）母控物理实现

更新时间：2026-11-08 CST。[Issue #223](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/223) / [PR #224](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/224) 已完成先64后128的工程验收，待独立审查。两格式各54项RTL、54项母控最终网表、69项实际Block/局控RTL回归；共用未改物理六文件，TT300MHz setup/hold +374.917/+7.629ps、完整原版GDS DRC0，电气/RC/PG/SRAM时钟通过。U绑定#221已验收31文件源。两包及3860/3148内部文件本地全部核验，见[报告](../../docs/experiments/mother-control-dual-format.md)与[执行记录](../../work/YUZE-LU/223/README.md)。下一步：指定独立审查人、审查PR；九目标扩展和联合布局布线另验。本任务未自行合并或标done；登记PR5 pending，缺board配置，Projects unverified/同步pending，待管理员核验。


## 2026-11-07（CST）C/F/J 独立叶宏组

更新时间：2026-11-07 21:40 +0800。

[Issue #211](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/211) · [PR #213](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/213) · [验收与回收索引](../../work/YUZE-LU/211/control64-acceptance.json)。C/F/J 独立紧凑叶宏、16 KiB 私有 S、局控与适配已交付；C/F 并发发送死锁修复并通过真实 SRAM 与双局控程序。原 `_128` 包保留，新增 `_64` 三类全部通过原版完整 GDS DRC 0、PG、电气、LEC、TT 300 MHz 及最终网表回放，本地包与316/273/548个内部文件全部核验。五类 _128/_64 摆放图及图源绑定已保存，用户已授权通过 #213/#214 主线整合，合并回执以 PR 在线状态为准；联合顶层重新绑定局控 ID、控制 profile 和实际布局并独立验收。审查人待指定；登记 PR5 pending，缺 board 配置，Projects unverified/同步 pending，待管理员处理。

## 2026-11-07 17:10（CST）P/U 紧凑指令物理版本

[Issue #212](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/212) · [PR #214](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/214)。已有合格交付保留为 P_128/U_128。P_64/U_64 均完成独立物理验收：完整原版 GDS DRC 0，原生 TT 300 MHz setup/hold 分别 +86.461/+7.498 ps、+100.376/+8.670 ps，电气/PG、信号路由、代表上层三档 RC、最终网表 9/60 次程序回归通过。两包已回收到本地，1122/1480 个清单文件和程序镜像逐项校验一致。[最终版本回执](../../work/YUZE-LU/212/compact64-physical.md)。64 指紧凑取指，PM/数据接口仍 128 位，控制仍是记录的原生服务子集。下一步独立审查和合并；Issue in_review，不自合并。登记 PR #5 pending；看板缺配置，字段 unverified、同步 pending。

## 2026-11-07 13:03（CST）P/U 独立叶宏底座

[Issue #212](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/212) · [PR #214](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/214) · [工程回执](../../work/YUZE-LU/212/README.md)。E 操作数个数 P1 已修复，[新 U 物理重验收](../../work/YUZE-LU/212/u-e-count-physical.md)通过：完整原版 GDS DRC 0，TT 300 MHz setup/hold +334.870/+3.787 ps，电气、信号和 PG 通过；130 根代表上层接入三档 RC 通过。正常/FMA 两套最终网表测试共 30 次通过。新包及 82 个清单文件已回收校验，取代旧 U 交付包。P 原包保留，新回放入口对原 P 网表三初态通过。下一步独立审查和合并；登记待合并，看板缺配置。

## 2026-11-06（CST）紧凑 SRAM S 版图图册

[Issue #207](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/207)由 YUZE-LU 执行。从 #203 最终验收产物补齐两颗 SRAM 的[版图、摆放和 M10 引脚图册](../../docs/experiments/assets/compact-local-s/index.html)，逐个比对 273／965 根引脚坐标。由 [PR #209](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/209) 交付。看板配置仍待管理员核验。

## 2026-11-06 G/E 独立宏紧凑化

[Issue #201](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/201) · [PR #205](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/205) · [源提交与作业回执](../../work/YUZE-LU/201/README.md)。G 220 µm 和单输入 E 340 µm 已通过独立叶宏全部工程门，完整交付归档回收并核对。父层互连与组合时序另验收。

[Issue #208](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/208)补齐[图册与接点坐标](../../docs/experiments/assets/compact-ge/index.html)，已核对图源、接点数及本地图册链接。

## 2026-11-06 紧凑双型局部 SRAM S

[Issue #200](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/200)由 YUZE-LU 执行。两个 16 KiB 独立宏完成详细布线和 273/965 位同时逃逸测试，实际有效占地为 82.45% 和 82.11%。结果、原生独立验收范围和复跑入口见[实验说明](../../project/experiments/compact_local_s/README.md)。[PR #203](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/203) 已合并。两颗的完整 GDS DRC 均为 0，TT 300 MHz 独立审计、选定 ODB 的三初态回归和四 bank 等价均通过。看板缺项目配置，登记沿用待合并的管理中心 PR #5。

## 2026-11-05 局部 SRAM S 交付

[Issue #155](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/155)的后续整合，执行账号 YUZE-LU。P4/N4/N5 的 300 MHz 独立叶宏验收、版图、六文件索引和 RTL 回归入口见[局部 SRAM S](../../docs/BLOCK_LOCAL_S_SRAM.md)。系统级接入单独验收。看板配置和同步由项目管理员核验。

## 2026-11-01：Issue143 六块成果进入整合审查

按用户决定先提交 M/N/E/G/S/T 六块，不等待 R；六块全部适用最终门及源绑定本地实收通过，R 标为未完成且不在合格清单。Issue #143 保持开放，研究 PR #144 保留；当前 `task/143-six-block-main` 基于 main a103da35，面向 main 的成果整合待独立审查。规格和结果见 docs/BLOCK_V2.md、docs/BLOCK_V2_RESULTS.md；核验命令见 docs/ARCHITECTURE.md。登记 PR5 pending；缺 config/board.json，看板 unverified/同步 pending；审查人待指定。历史记录保留在下方。

## 2026-10-30 计算积木规划文档同步

- 更新时间：2026-10-30（Asia/Shanghai）。任务：[Issue #139](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/139)，负责人/实际身份 YUZE-LU；独立分支 `task/139-compute-block-docs`，基于 main `6a681d66`。
- 已完成：原本地 V/M 分析重命名为 MVR 讨论总结，加入 R 的结构、数值、状态容量/共享存储、四抽头限制及首版独立保留结论；仓库[同文正文](../../docs/COMPUTE_BLOCK_BOUNDARIES_2026-10-30.md)。
- 同步：[项目说明](../../预制计算底座项目说明_v1.0.md)和 README/导读/简介/架构/状态；[决策 0005](../../docs/decisions/0005-compute-block-v-split-r.md)记录 V 三宏、R 保留、每种一个实现、逐宏最终布局布线。M/V 缩位宽和部分和精简仍为候选，未转移原 V 的物理资格。
- 验证：[本次交付记录](../../work/YUZE-LU/139/README.md)及 validation.json；仅文档/管理检查，未重跑模型、RTL、EDA 或服务器作业，未修改现有实现工作树。
- PR/最终提交与 CI 以 Issue #139 回执为准；待独立审查，不自合并或标 done。登记沿用 PR5 pending；缺 board.json 与 Projects 条目工具，看板 unverified/同步 pending，管理员待指定。
- 续补：已有 M/V/R/S/T 的电路图、存储、控制与固定源码来源已直接加入总项目说明第 5.6 节；规划中的新 V 三宏不画图，本次不新建 Block 说明文件。
- 交付：[PR #142](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/142)。用户本轮明确要求同步 main，将在检查后正常合并并读回；不代替他人审查或绕过保护。具体最终合并回执以 Issue #139 为准；主线另行落实逐宏物理验收，本次不接管运行任务。

## 2026-10-26 模型分析与计算图归档

- 更新时间：2026-10-27 14:25 CST，用户已明确授权提交到 main。
- 任务：[Issue #116](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/116)，负责人及实际账号 YUZE-LU；分支 `task/116-model-analysis-docs`。
- 本地成果：[模型分析目录](../../docs/model-analysis/README.md)，集中提供精简字符算子图、完整图册和原 PR #115 的实验分析报告；旧报告路径保留跳转，README 与导读更新入口。
- 原始图册、图结构、配置和回执按 SHA 原样复制；新说明明确 Falcon 旧手工图的已知差异。没有重新运行模型/ONNX、修改历史 Issue #114 的证据或接触服务器作业。
- 验证与导入清单：[work116](../../work/YUZE-LU/116/README.md)。本轮重验183份导入文件、196处本地引用、40张SVG、10组成功回执及原报告正文迁移均通过；正在通过任务分支和PR交付，实际PR/CI/合并回执保存在Issue #116，未合并前不标done。未重跑模型或物理实验。
- 接入：无 `config/board.json`，连接器未提供 Projects 条目能力，条目未核实、同步 pending；管理员待指定。现有登记和项目里程碑不变。

## 2026-10-27 共同文档阶段边界澄清

- 任务：[Issue #123](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/123)，负责人及实际账号 YUZE-LU。
- 成果：[决策 0004](../../docs/decisions/0004-block-library-base-freeze.md)，同步 README、项目简介、项目说明和共同状态。
- 已确认：Nangate45 原生十层预制与新增两层定制；叶块、共同底座与任务定制分别验收。同类实例/裕量版本组合、排布和固定预连线在底座阶段确定；共同底座冻结后不得按任务改变固定资源。
- 边界：保留 Issue #121 / PR #122 的既有范围与验收状态；本次没有修改实现工作树、RTL、实验配置或服务器任务。
- 验证与集成：[PR #124](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/124) 交付本次澄清；管理结构、44 处本地链接、3 张表格及暂存差分检查通过，PR CI/最终合并以 Issue #123 的读回回执为准。用户明确授权经 PR 正常合入 main，不代替独立审查或绕过保护。
- 接入：本次读回既有登记 management-hub PR #5 仍 open/未合并（pending）；无 config/board.json，当前工具无 Projects 能力，条目/字段 unverified、同步 pending，管理员待指定。此缺项不改变文档业务验收。
- 下一步：完成文档检查、PR/CI 与 main 内容读回；后续物理实现继续由原任务跟踪。

## 2026-10-26 模型实验分析报告

- 任务：[Issue #114](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/114)，负责人及实际账号 YUZE-LU。
- 成果：[阶段性分析报告](../../docs/model-analysis/MODEL_EXPERIMENT_ANALYSIS.md)，补充 README 与研究资料导读入口；来源与检查见 [work114](../../work/YUZE-LU/114/README.md)。
- 已完成：读取九份固定版本报告及十个来源 PR 的状态，梳理八个模型的目的、范围、结果、失败和能力/接口约束；读取后续 #102/#106/#109/#110 的范围，避免将旧批次限制误写为当前无 RTL。
- 集成：用户明确要求合入 main；本次通过独立文档 PR 交付，最终 PR/commit/CI 以 Issue #114 的读回回执为准。不合并其他实验 PR，不冒充独立审查批准。
- 验证：文档检查与管理结构的实际结果见 validation.json；未重跑模型、原始数值接收、RTL 或物理。
- 接入：登记 management-hub PR5 仍 pending；无 board.json，实际 Projects 查询缺 read:project，看板 unverified、同步 pending，管理员待指定。
- 下一步：完成当前文档检查、PR/CI 及按本次授权入 main 的读回；原实验审查和后续实现另按原任务推进。

## 历史阶段：Issue #7（2026-10-21）

- 更新时间：2026-10-21（中国标准时间，UTC+08:00）。
- Issue：[候选 Block 边界及分层布线流程](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7)，负责人 YUZE-LU，当前 `in_review`；审查人和优先级待指定。
- 已完成：读取两个项目的接口／RTL／报告和已有 ACT—MXU 实验；形成 [候选划分及对照矩阵](../../docs/experiments/openTPU-llaccel-block-plan.md)；核实用户授权的集群工程与工具可访问；在独立分支 `task/7-block-routing` 增加正式实验运行器，原参考包和原工作区改动保留。
- 实验：完整16-lane VECTOR的screening 89442通过；早期89443人工时限超时及89447恢复预检查失败保留。89448从checkpoint进入stage4、不重综合，仍在默认LEC、未得CTS完成产物，继续 `UNLIMITED`。89449因旧默认PDN已知不兼容，在确认PENDING后取消，非按求解耗时终止48。终态以[试验记录](../../docs/experiments/issue-7-vector-pilot.md)和[轻量索引](../../project/experiments/block_hierarchy/results/issue-7.json)为准。
- 运行约束：用户明确要求不设时限；后续作业取消人工有限时长，实读 c64/c96 `MaxTime=UNLIMITED`，每次提交后核验实际 `TimeLimit`。早期超时与恢复预检查失败保留，不通过删除历史制造成功。
- 新增验证：独立RTL回归89455通过，VECTOR 1203例／数学12000组／舍入16384组；测试副本唯一 `1u << 31` 兼容修正有diff/hash，原RTL与参考不改。89453及后续顶层是另开的 `LEC_CHECK=0` 物理路线，89448默认检查路线保持运行，不混用二者证明。
- 实际物理结果：89453完整Block和89472单宏顶层均完成最终布线，DRT错误0；89475最终只读审计通过，双网连通、唯一固定宏／2246位接口与逐位映射、M7–M9接入几何复算闭合。Block setup WS −4.16659 ns／287违例、最大电容59违例；父级setup WS −0.0429892 ns／3违例，质量仍未通过。父层新增2245个IO buffer，single-sink实际跳过CTS，无多宏时钟树验证。历史PG／hook失败均保留。
- 验证：`python scripts/check_project.py`、Python 脚本语法编译、远程 Bash 语法检查和 `git diff --check` 通过；镜像阶段门级 LEC 已调用、尚未得结论。完整 core 回归、原 RTL 到物理网表的完整形式比较、多计算图、受限定制和系统签核未执行。
- 下一步：审查本轮工程实现和失败证据，保留内部／父级时序、电容、异步复位抽象和缺少宏功耗模型的限制；再准备同资源F0/H1对照、多Block和H2冻结资源规则。89448继续无限时求解，其后续匹配模型必须来自其自身最终实现，不套用89453模型。
- PR：[PR #8](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/8)供审查；89472／89475实际运行代码快照 `357dd98a7a07f370a1cc2c67b066c7ecccf3bf9a`，75启动时仅文档／结果dirty并如实记录。最终采集器精简及成果记录由PR当前HEAD回执绑定；每个attempt的SHA-256独立保存，未合并或验收前不标 `done`。
- 接入：管理中心 [登记 PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5) 本轮读回仍 `OPEN`，登记 `pending`；Projects 缺 `read:project`，无 `config/board.json`，看板 `unverified`、同步 `pending`，由具备权限的管理员处理（待指定），见[持久交接](../../docs/handoffs/2026-10-21-issue-7-projects.md)。




## 2026-10-22 ACT/MXU 同资源物理对照

- 更新时间：2026-10-23 04:37 CST，中国标准时间UTC+08:00；负责人／实际GitHub账号YUZE-LU。
- [Issue #15](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/15)，分支`task/15-opentpu-compare`，[PR #17](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/17)，依赖PR10基线2b76f69；独立工作树，未修改PR8／PR10工作树、VECTOR或89448。
- 已完成：三种块内实现与拆分两宏／合并一宏父层实际布局布线。保持169109初始映射单元、37023DFF、12个SRAM及相同计算／状态逻辑；统一1662bit外部引脚、die、2.5ns时钟及0.5ns IO预算，全部物理支持成本计入。拆分89829／34:01自然COMPLETED0，五个物理来源和六类证明共十一份记录全部通过compare；功能89831、覆盖89832、完整ODB89833通过。旧20的act_data[145] slew违例经单一驱动X4→X8并重新DRT／提取消除，没有放宽门槛。
- 实测：拆分／合并总叶面积484240.4／482252.4µm²，总信号线6647739／6204600µm，通孔1322289／1284106，完整setup WNS +0.102306／+0.065642ns、hold +0.036146／+0.013027ns。拆分块内线长−249953µm，被父层+693092µm抵消；总线长+7.142%，不能将父层IO／时钟全归为685bit边界成本。
- 成果：[中文HTML和三类图表](../../docs/experiments/issue-15-opentpu-results.html)，[过程及失败证据](../../docs/experiments/issue-15-opentpu-comparison.md)。生成代码8a646d8，冻结输入SHA f65688a957f13ef70216e923891ef6ff539adfc6f81c3e29a74ba5d10332720d；report-manifest绑定9个产物。实际查看三PNG、浏览器核验页面／表格／三图／路径和完整ODB展开，临时页面服务已关闭。delivery-validation记录实际检查和两个成本证明负例，均拒绝且未改变合格输出。
- 补充已完成：全量清线重布21／89826自然COMPLETED0（1:02:26），匹配功能89827／RC89828／五ODB成本89835全通过；另存完整十一来源对照，快照72b9829d0df7ac7d30c5b7a6f8e602f11e317c2070cbacab4f55e466299cce0f。与主拆分叶面积相同，总线长多42µm、通孔少2、setup多0.000008ns；原主报告和9产物SHA不变，不能当作显著改善。两套合计15份唯一封存来源全部自然完成、UNLIMITED。Issue in_review、PR17待独立审查。
- 限制：H1允许新增有源缓冲和全父层路由，M10以下父层线长占比约99.39%／99.26%，不代表H2少量定制层冻结底座；单small／typical／固定布局与引脚，synthetic SRAM无GDS、上游RTL通用等价和制造签核未完成。
- 下一步：PR独立审查／合并及最终验收由人处理，审查人待指定。不自合并或标done；审查人／优先级待指定。H2预算及限定制层是后续独立实验。
- 接入：登记管理中心PR5本次核验仍OPEN未合并、pending；本仓库无board.json，连接器无Projects条目工具、CLI实际GraphQL查询返回INSUFFICIENT_SCOPES缺read:project，看板unverified、同步pending，管理员待指定。

## 历史记录：2026-10-21 资料与规则交付


- 更新时间：2026-10-21（中国标准时间，UTC+08:00）
- 当前任务：[Issue #3：同步两份布线报告并补入 llaccel 引擎分析](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/3)。负责人 YUZE-LU，优先级待指定。
- 已完成：同步最新总报告、线长报告及其引用资源；总报告增加 llaccel 三个引擎的中文分析与 9 张图。保持图片直接展示、长表可展开；不创建备份或多余首页。更新来源边界和包说明。
- 验证：管理结构检查、报告依赖/锚点检查、包内清单哈希、正文/表格保留和差异检查；具体结果见本任务 PR 回执与 `work/YUZE-LU/3/validation.json`。没有重跑物理实现或 STA。
- 交付：[PR #4](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/4)，分支 `task/3-update-routing-reports`，报告成果 commit `b041d53`；2026-10-21 按用户明确要求已合并到 main，合并提交 `1d80491`。
- 下一步：继续审查[管理中心登记 PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5)。登记仍为 pending。
- 阻塞/接入缺项：报告上传可独立完成；本仓库没有看板配置，当前凭据缺少 `read:project`，无法核验或同步 Projects。由有相应权限的管理员处理，处理人待指定；详见[交接](../../docs/handoffs/2026-10-20-issue-3-report-board.md)。不自行扩大凭据权限。
- 历史：Issue #1 的初期资料由 PR #2 导入，后续参考资料提交 `695587d`、`5c86109` 已进入 main。`ref-project/` 仍不属于 Agent 主动或例行维护范围。

## 2026-10-21 补充交付

- 按用户要求补入 `ref-project/llm-routing/模块与接口报告.html`，保留原文，并复制其引用资源；README、研究资料导读及阅读说明补充入口。
- 本次仅检查新报告的本地引用是否存在及管理结构、文档差异；不执行哈希检查，不重算参考数据，不修改原有清单。原清单不覆盖此次新增文件。
- 沿用 Issue #3、任务分支及 PR #4 上传；2026-10-21 已按用户要求合并到 main。看板权限缺项沿用上述交接。

## 2026-10-21 远程服务器规则

- [Issue #9](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/9)：记录服务器节点、`/public/home/yuzelu` 下的目录权限和 sbatch 任务命名要求，README、AGENTS.md 提供规则入口。
- 任务名采用“本人姓名缩写-任务缩写”，如 `hpy-block`；脚本和提交时覆盖的任务名均应遵守，便于在 squeue 的 NAME 中辨认。
- 验证：管理结构检查及所改文档的差异检查通过；未登录或修改远程服务器。通过 PR #4 上传，2026-10-21 已按用户要求合并到 main；看板同步仍待具备权限的管理员处理。

## 2026-10-21 main 集成

- 按用户“最新状态都提交到 main”的明确要求，将报告、远程规则及此前未提交的工艺互连资料补充一并纳入 PR #4 并合并。合并提交 `1d804912927602900aa074339db33156a805c582`；本地已同步到 main。
- 管理结构及文档差异检查通过；未重算参考数据。其他成员的独立 PR 未合并。登记、看板的既有待办继续保留，不宣称已完成。

## 历史记录：2026-10-19

- 更新时间：2026-10-19（中国标准时间，UTC+08:00）
- 当前任务：[Issue #1：初始化项目并导入初期资料](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/1)
- 已完成：初期研究资料已进入 `main`；PR #2 已合并。本次按用户要求直接在 `main` 提交并推送更新后的研究资料导读与用户提供的 `ref-project/` 改动；成果提交为 `695587d`、`5c86109`。
- 下一步：完成[管理中心登记 PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5) 的审查；由具备 Projects 权限的管理员核验或配置项目看板。`ref-project/` 不纳入 Agent 的主动或例行维护，用户更新后可按要求提交；无需逐项审查或做哈希检查。
- 阻塞：物理实现原始代码、数据库与工具环境未包含在当前资料包；共享存储位置和实际可访问性待核实。
- 本次验证：`python scripts/check_project.py` 通过；导读的 6 个本地相对链接存在；变更文档的 `git diff --check` 通过。未检查参考包内部改动或哈希，未执行业务构建／仿真。本地未配置 `config/board.json`，看板仍待管理员处理。

## 2026-10-23 布局与接口报告本地归档

- 按用户要求，沿用 Issue #7 并发工作树 `issue-7-parallel-blocks` / 分支 `task/7-parallel-blocks`，将两份报告集中到 `ref-project/llm-routing/docs/`，并修正相对资源 URL 与 README、资料导读、阅读说明中的入口。详见[报告目录说明](../../ref-project/llm-routing/docs/README.md)。
- 已核验移动前 56 个不同本地资源 URL 均存在；移动只调整 URL，报告正文和标签结构保持不变。新 Block 报告从外部生成产物原样复制，保留源文件。项目管理结构检查通过；未重跑 EDA。
- 交付状态：仅本地文件整理，尚未 commit / 推送，现有 PR #10 尚不包含此修改；Issue 状态、项目里程碑及看板未变。登记/看板缺项沿用原任务交接。下一步可按用户后续提交要求并入现有 PR，不能把本地归档视为已合入 main。

## 2026-10-23 按用户授权整合实验与 HTML

- 用户明确授权完成 PR #8、#10、#17 及两份 HTML 的提交与合并；H2（Issue #31）继续独立运行。HTML 的来源和范围不变，先前“仅本地”的记录为归档时快照。
- 本次技术复核：H1 主/补充对照从现有封存记录重算，全部成本与质量字段一致；9 个报告产物 SHA 未改变。缺少成本审计、错源审计两负例均拒绝；并发电气门槛、Tcl 修复与配置覆盖回归通过。不是新跑 EDA 或上游 RTL 通用等价证明。
- 合并权限来自本次用户明确指令；不冒充独立 GitHub APPROVED 审查，不绕过保护规则。登记 PR5 仍 pending；看板实读缺 read:project，unverified / 同步 pending。

## 2026-10-23 用户授权整合

用户明确授权将主线PR #8、并发PR #10及H1 PR #17合入main，并将两份参考HTML归档到ref-project/llm-routing/docs/。以上旧记录中的待授权／不自合并描述是当时状态，本次按用户的新授权执行，不伪造独立审查批准。H2工作树及运行任务保持独立。本次验证与限制见[整合回执](../../docs/handoffs/2026-10-23-h1-html-integration.md)。

网络恢复续办：PR #8 已合并为 a30d598，PR #10 已按匹配 head 成功合并为 a77d288；完整 H1 整合树由 PR #17 交付，最新 CI 和合并状态以在线记录为准。本地 8 项检查、58 份 Python 语法、两份 HTML 资源／锚点及 9 产物不变检查通过。Issue #7 的 VECTOR 质量缺口保留；H1 交付与 H2／Issue #31 分开，项目登记及看板待办不变。
