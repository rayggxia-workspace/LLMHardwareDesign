# Issue247：最多四轮的RTL提速迭代

## 第二轮RTL与评估通过（2026-11-10，Asia/Shanghai）

Issue247 / PR243，负责人Melodydt，in_progress。R2源码863492081f0f512fc64fb73c787fcdcaf145a6b4，31文件blob读回通过。run18/101852/mdt-r2-nexp-rtl，2:37；run19/101854/mdt-iter2-nexp，2:53；均c64/node1/4核COMPLETED0:0。R2实际费用[7,7,9,9,16,16,18,18]，默认/DIRECT0兼容、数值、持久状态及完整U通过。16旧体系case/8默认精确回归、2prefill fallback、128篡改及profile/CLI负例通过；独立复核完成。

主W8 decode512 ideal3.66958239533（比R1+0.90184%）、shared3.37834376557（+0.83026%）；Dot224.101536667ms占82.2359%，未达5。run18结果SHAfb0b4d0d1251140655feea5bd671c196e5ae13b1fd47066dc22d6e1e1a2eac78，run19结果SHAb16ff9a0209add1227177d1899bbf9928ae7e83d724a0c113469e7c860c97098。两run在/public/home/yuzelu/Melodydt/issue247-area-speed/，源码、日志和结果持久保存；追踪`sacct -j 101852,101854 -X --format=JobID,State,ExitCode,Elapsed,NodeList`，查看各目录results/result.json。所有作业终态，无自动监测。

第二轮4页PDF及110内容单元、全部页面视觉QA完成，当前2/4轮完整交付。PDF源文档固定e531a9944ff1ae4bc55e3b6e204be48f425af1a3，PDF SHA1c28b2f2ee7a736b92d4e84308e6a067a6ec761976e78d547310248ac9850a66。第三轮在隔离目录研究/实施S32/S96 M有限供数；正式生产未改R3。恢复第一步核对PR最新head，审查R3真实buffer/nextK/commit/ACK与旧模型收费边界，并在新增大面积候选前创建独立备份。SRAM不扩容；大面积候选另备份。登记pending、看板unverified/同步pending、审查人待指定，未合并main。

负责人 Melodydt；2026-11-10，Asia/Shanghai。[Issue247](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/247) / [PR243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)。本次是新的迭代周期，历史研究和原生P三个优化不计入本次四轮。

## 目标与轮次

每轮依次完成瓶颈研究、方案选择、RTL实现、服务器验证、原评价体系性能评估及详细实施PDF。达到旧体系 W8 decode、context512、ctx8、16KiB、理想1R1W主参考层的 5 token/s，或者完成四轮后停止；该层是本轮起点3.49616888299的条件目标，不称当前四1RW硬件已达5。共享口ctx8始终并列报告，prefill吞吐另列，不用其较高数字替代decode目标。当前用户可进一步指定目标场景，在收到明确变更前沿用以上主场景。

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
