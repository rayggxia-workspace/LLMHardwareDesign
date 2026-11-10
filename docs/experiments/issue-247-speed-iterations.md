# Issue247：最多四轮的RTL提速迭代

## 停止场景澄清（2026-11-10 Asia/Shanghai）

用户确认：**任一原评估场景达到5 token/s（包括prefill），或者完成4轮，即停止。** 此前仅W8 decode512作为停止项是等待回复时的临时假设，现由此说明替代。直接解码复核72条本轮完整场景与21条历史完整场景（不含单算子诊断）：本次16KiB四轮最高为W8 prefill2、理想1R1W的3.69669737899 token/s；主W8 decode512最终3.67621308212。原21场景中的64KiB未实装容量参考最高4.54743400007，亦低于5。故停止原因仍为**已完成4轮**，不是达到5。

本次仅补充停止判定，无新仿真或第五轮。四份源绑定PDF保留冻结版，其中decode-only停止假设由本说明覆盖，数值及RTL证据保持有效。Issue247保持in_review、PR243待审查未合并；登记pending、看板unverified/同步pending及既有CI限制保持，处理人待指定。

## 四轮迭代交付完成，进入独立审查（2026-11-10 Asia/Shanghai）

Issue247/PR243，Melodydt，in_review（待正式审查/合并，不done）。四轮研究、方案、RTL和旧体系评估已完成；四份PDF均已完成内容和逐页视觉QA，4/4轮完整交付，按轮数上限停止。第四份5页/141内容单元，报告固定f4be5c50507fec202551e45e39fb2215fc18876c，PDF SHA85ae41e4c79712710e078af3f1bcf033d17a8fd35e7896cb90a705b46dc5a741。最终主W8 decode512 ideal 3.67621308212/shared 3.38396291561 token/s，未达5；本次不再增加第五轮。R4采用best R2基础仅op12四EXP lane，默认2，普通N保留；生产启用需BATCH1/DIRECT1/LANES4。R3双buffer退化独立保留，SRAM没有扩容，物理时钟/完整原生生成未验收。

run22/101884源7048c35ed2912e80e62bd7827deaec480d4a7e1a，5:45；run23/101888源e6209544086f2460662bf7edfc91cbfb2c63cd9b，00:02:55；均c64/node1/4核COMPLETED0:0。21build/63run（3预期非法lane拒绝）及11门通过，fee[7,7,7,7,14,14,14,14]；旧模型16case、8精确回归/2fallback、128篡改及原测试通过，独立审计完成。run22结果SHA5abb31227f0c7b2c7ac9ff7eb8f80687569fab0b64bf74eb1a9ea6ccb54b518d，run23结果SHA52c5faaad4d67a30577a5b4bc6d564866627105d492ea37aabc31d5b5b5372ff。

所有源码、日志、结果持久保存在yuzelu@10.129.166.172本人/public/home/yuzelu/Melodydt/issue247-area-speed/run16至run23；全部作业终态，无自动监测。R3/R4共92大raw由retention索引明确服务器/本地归档保存，仓库核验内容和远端索引不混称。扩通道备份task/247-nexp4-area-r4@7048c35ed2912e80e62bd7827deaec480d4a7e1a及R2/R3备份均读回。追踪sacct -j 101884,101888 -X --format=JobID,State,ExitCode,Elapsed,NodeList。

非Git本地快照work/Melodydt/242/r-load-bounds/repo，远端task/242-r-load-bounds供PR243审查，未合并main。恢复第一步核对最新PR head、四轮报告/PDF及正式审查意见；已达到四轮停止条件，不自动增加第五轮。登记management-hub PR5 pending；缺board.json/Projects能力，看板unverified、同步pending，处理管理员/正式审查人待指定；GitHub CI以最终PR回执为准，不冒称通过。

## 第三轮RTL与旧体系评估通过，候选未超第二轮（2026-11-10，Asia/Shanghai）

Issue247/PR243，Melodydt，in_progress。run20/101872（源a3149d69a23f52efb808dbbb46b5558dffce4df7）41秒；run21/101878（源010ae8d0d8839967f96b94227d2224fade0edf37）6:06，均c64/node1/4核COMPLETED0:0。RTL六run×66场景、有限控制299064周期比对及实际S数值通过；模型24case/8精确回归/8fallback、192篡改及原测试通过。R3双buffer主ideal3.66041657326/shared2.75864978939，低于第二轮；当前最快仍3.66958239533/3.37834376557，未到5。

第三轮5页PDF、134内容单元及全部页面视觉QA通过，当前完整交付3/4轮。报告固定809f9820cc13157077e4399a789779aac52925db，PDF SHA00b0b6c2d6c44829808d316cb3e6658c378d8bf51e5cb7632320e790e969940d。大面积候选独立备份task/247-m-k16-area-initial@a3149d69a23f52efb808dbbb46b5558dffce4df7与前态备份均读回；S仍16KiB。run20结果SHA87842b59e42fb0773eedb82dce4981614432868fa12218c3aa15166b0b839eff，run21结果SHAbccd917afba10bb9c3f65f62b26b1eab588a85d73c364a4b4d54962b5197afb8。

服务器本人/public/home/yuzelu/Melodydt/issue247-area-speed/run20、run21持久保存source/、slurm-job.log与results/；62大raw另有retention SHA索引，不声称Git内含所有raw。追踪sacct -j 101872,101878 -X --format=JobID,State,ExitCode,Elapsed,NodeList。全部终态，无自动监测。第四轮在隔离目录实施R2基础op12四EXP lane；1KiB A缓存受DDR上限约束，仅保留方案。恢复第一步核对最新PR head/本轮报告，继续第四轮源审查、Slurm实测和旧体系复评。非Git本地快照work/Melodydt/242/r-load-bounds/repo仅根整合，R4子任务各隔离目录；远端task/242-r-load-bounds未合并main。

登记pending、Projects unverified/同步pending（缺board.json及工具能力）、审查人/管理员待指定；GitHub CI此前失败原因未核实，未绕过。当前候选不具备完整P/DMA、原生整图生成或新物理资格。

## 第二轮RTL与评估通过（2026-11-10，Asia/Shanghai）

Issue247 / PR243，负责人Melodydt，in_progress。R2源码863492081f0f512fc64fb73c787fcdcaf145a6b4，31文件blob读回通过。run18/101852/mdt-r2-nexp-rtl，2:37；run19/101854/mdt-iter2-nexp，2:53；均c64/node1/4核COMPLETED0:0。R2实际费用[7,7,9,9,16,16,18,18]，默认/DIRECT0兼容、数值、持久状态及完整U通过。16旧体系case/8默认精确回归、2prefill fallback、128篡改及profile/CLI负例通过；独立复核完成。

主W8 decode512 ideal3.66958239533（比R1+0.90184%）、shared3.37834376557（+0.83026%）；Dot224.101536667ms占82.2359%，未达5。run18结果SHAfb0b4d0d1251140655feea5bd671c196e5ae13b1fd47066dc22d6e1e1a2eac78，run19结果SHAb16ff9a0209add1227177d1899bbf9928ae7e83d724a0c113469e7c860c97098。两run在/public/home/yuzelu/Melodydt/issue247-area-speed/，源码、日志和结果持久保存；追踪`sacct -j 101852,101854 -X --format=JobID,State,ExitCode,Elapsed,NodeList`，查看各目录results/result.json。所有作业终态，无自动监测。

第二轮4页PDF及110内容单元、全部页面视觉QA完成，当前2/4轮完整交付。PDF源文档固定e531a9944ff1ae4bc55e3b6e204be48f425af1a3，PDF SHA1c28b2f2ee7a736b92d4e84308e6a067a6ec761976e78d547310248ac9850a66。第三轮在隔离目录研究/实施S32/S96 M有限供数；正式生产未改R3。恢复第一步核对PR最新head，审查R3真实buffer/nextK/commit/ACK与旧模型收费边界，并在新增大面积候选前创建独立备份。SRAM不扩容；大面积候选另备份。登记pending、看板unverified/同步pending、审查人待指定，未合并main。

负责人 Melodydt；2026-11-10，Asia/Shanghai。[Issue247](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/247) / [PR243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)。本次是新的迭代周期，历史研究和原生P三个优化不计入本次四轮。

## 目标与轮次

每轮依次完成瓶颈研究、方案选择、RTL实现、服务器验证、原评价体系性能评估及详细实施PDF。按用户已确认口径，任一原评估场景达到5 token/s（包括prefill），或者完成四轮后停止。W8 decode512继续作为优化收益的固定主对比，但不再是唯一停止场景；共享口与理想1R1W分列，并明确prefill吞吐与decode速率的区别。旧体系数值属于条件估计，不称当前四1RW硬件或原生LLM生成已达5。

2026-11-10，首轮[RTL与旧体系评估](issue-247-speed-round1.md)已通过：主理想端口3.63678454238、共享口3.35052563236 token/s；[首轮5页PDF](pdf/issue-247-speed-round1.pdf)已完成内容与逐页视觉核验，当前1/4轮完成。第二轮选择复用原N的单命令stateless relative-exp路径，后续以实际测量计费。后续方案必须根据前一轮真实结果选择，不能预先宣称收益。失败或退化的候选保留证据；同轮为修正实现缺陷而重跑不算新的优化轮次。

## 固定评价合同

- 固定PR241/Issue247旧S32/S96、K256条件模型、原Qwen trace、300MHz、2P/1U、17.1GB/s。16KiB不扩容；保留共享端口和理想1R1W两列。理想端口数字不成为当前四1RW-bank的硬件实测资格。
- W8采用 `adaptive_prefix_pair_combine`；W16采用既有 `adaptive`。主比较启用旧模型八组上下文。同时报告W16 decode512、W8 decode2048、W8 prefill2。
- 起点为run15（101800）结果：主W8 decode512共享口3.23081074122、理想端口3.49616888299 token/s。它们是条件整图估计；源生硬件、原始FP32/S32图准入和真实文本生成分别验收。
- 新模型必须关闭本轮开关后逐字段复现run15或上一轮结果。只替换有本轮RTL证据对应的局部费用，数据宽度、舍入、溢出、命令、尾块、背压及数据搬运必须显式计入。不得只调小成本系数或将重叠统计量直接相加扣减。
- 新RTL默认关闭；保留已测基线和原冻结生成器。依赖的旧源SHA和旧资格仍绑定历史版本，新实现不能继承未重跑的物理验收。

## 首轮瓶颈与选择

起点主场景总时间286.0273867ms，其中Dot224.1015367ms、非Dot61.92585ms。NExp18.4871833ms，canonical21.49358ms，reduce8.6253133ms，vector13.25398ms，其余KV/copy约0.066ms。M和adapter工作时间与这些阶段存在重叠，不能作为可直接删除的额外墙钟时间。

固定Dot流量3,216,967,168B和17.1GB/s时，Dot至少188.126735ms；保留非Dot串行阶段会给出约3.99916 token/s的必要上限。因此只改P/M而保持其余流量与调度，不足以达到5 token/s。全图字节除带宽的5.2808 token/s仅是更弱的必要上限，并非可达性能。

首轮选择复用已有单N核的NExp批处理。来源为PR241在 `189e43c77a6277955c1be54281b0d6b0b0d55c1f` 的隔离候选，本分支新增正式U入口适配、S读写/ACK、错误处理与数据容器合同。复用来源注明，既有作者成果不归为本轮原创。

旧模型canonical的SiLU41步与Reciprocal128步未提供完整的指令序列、Q格式和逐步舍入合同。当前不能仅用新查表核或降低常数宣称精确等价及提速，后续需先补齐可比数值合同。

## 面积与备份

用户允许适当面积增加，巨大面积方案需要额外备份。迭代前的远程完整基线已保存到 `task/247-speed-base-a22e199c`，指向 `a22e199c1dce7d1037995a26f71f8b1358d038e0`；本地工作目录为非Git快照，经本人GitHub连接按精确文件清单、父commit与租约交付。

新增并行乘法器、复制完整算术核或大寄存器阵列须列出资源差异；资源明显倍增的候选另存可恢复源码包和独立分支，再决定是否纳入主候选。寄存器位数/运算器数量只是结构账本，不能冒充综合面积、布局布线或300MHz时序通过。SRAM扩容仍保留为研究候选，当前不实装。

## 证据与交付

服务器主目录仅 `/public/home/yuzelu/Melodydt/issue247-area-speed/`；所有EDA和SystemC运行通过Slurm分配4核、`mdt-`任务名和既有固定容器。每个run记录源commit、source/input/output SHA-256、工具版本与SHA、实际作业、退出码、日志和结果路径。先交付代码再仿真，执行后回收校验。

每轮PDF覆盖瓶颈、数值/接口合同、数据路径与状态机、修改文件、面积代价、测试及负例、吞吐主副场景、限制和下一轮决策；PDF由同轮Markdown完整生成，内容、链接、字体、边界和全部页面视觉校验后交付。源码和结果单独可复核，PDF不替代机器回执。

本任务状态in_progress；远端PR未合并、审查人待指定。登记沿用management-hub PR5 pending。缺config/board.json及可用Projects能力，看板实际状态unverified、同步pending，待管理员处理。迭代停止条件与项目审查/合并完成标准分别记录。
