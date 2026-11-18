## 2026-11-18 20:18 三项补齐 v5 进展（Asia/Shanghai）

[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) / [草稿 PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281)，负责人 Melodydt。保持 300 MHz、512-bit 数据 SRAM、三 P；M 时序闭合不作前置条件。

BSCC 可登录；四版读 DMA 综合后无寄生配对标定 38855808–11 全部 COMPLETED 0:0，不再等待布局布线。母控外围 38850581 与特殊函数/Conv4 引脚复标 38855639/40 已通过。Qwen3、Llama、Granite 的 E32 18 周期双阶段通过，连同 Falcon prefill 已对 10 窗积分四种互斥 DMA 场景并核对单位/去重；Falcon prefill 4.234239 tok/s 已通过；另 7 个 E32 阶段仍运行且均 UNLIMITED。七模型基线观察全部通过。特殊候选替换场景单列，保持复合运算/转换/新周期尚未集成的限制。

完整物理部署、原生 provider/路由参数、实际门控及整模型 RTL 状态驻留仍需实现验证；不能把上述 TLM 审计或局部候选测试写成三项全部完成。PDF 持续更新，原 v4 的 25 页保留为历史快照。源码积分 03cc4e99、引脚校准 30b6095c；[完整回执、结果、作业命令与全部剩余步骤](handoffs/2026-11-18-issue-280-closure-v5.md)。

任务 in_progress，PR 草稿未合并，审查人待指定；登记 PR #5 pending，看板 unverified/同步 pending，维护者待指定。长任务日志/结果独立保存；未配置聊天自动监测。

## 2026-11-18 七模型控制能耗补项 v4（Asia/Shanghai）

[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) / [草稿 PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281)，负责人 Melodydt。完成母控核心启动/运行及 PM 取指、局控外壳/分发、交换机活跃增量三个方向的条件估算，覆盖七模型 21 窗。512-bit 数据 SRAM、300 MHz、三 P 与冻结 TLM 时间/DDR/算术不变。纠正母控 SERVICE_STALL_LIMIT 为真实实例 2000000；母控新项替换旧核心，PM 与交换机只增加尚未计入的动态项。

旧服务器最终作业 120297/120300/120304/120313 全部 COMPLETED 0:0、12 核、UNLIMITED。21 窗单位/分项/哈希/去重校验通过；25 页 PDF 的 651 组数值与最终全页目检通过。第 2 步 Decode 相对 v3 控制净增量约 1.706–6.692 mJ/token；完整双口径数值、模型优化及逐模型未覆盖项见[报告](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/task/280-seven-model-energy/docs/experiments/seven-model-energy-evaluation.pdf)。

[本轮交接与全部剩余步骤](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/task/280-seven-model-energy/docs/handoffs/2026-11-18-issue-280-control-energy-v4.md)。本轮四项最终作业已结束；16:29 +08 旧服务器个人队列无活动作业。BSCC 仍拒绝 loginCluster，旧 DMA 当前状态未核验，不能沿用历史 RUNNING 快照。下一步是各模型真实控制部署绑定及母控外围/精确驻留；读 DMA 待恢复 BSCC 授权。仍为条件估算，非完整芯片实测或 RTL 数值/物理验收。Issue in_progress、PR 草稿未合并、审查人待指定；登记 PR #5 pending；看板 unverified、同步 pending（缺配置/Projects 能力），有权限维护者接续。未配置自动监测。

## 2026-11-18 七模型算术能耗估算 v3 已交付（Asia/Shanghai）

Issue [#280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) / 草稿 PR [#281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281)，负责人 Melodydt。已按用户允许特殊算子运算级近似的口径完成七模型三窗估算；512-bit SRAM、名义 300 MHz、三 P 与冻结时间保持不变。公共 RMS/softmax/RoPE 采用真实输入标定；GELU/GDN/Mamba/浮点服务等明确使用成本代理，范围不是统计置信区间或保证误差界，不宣称 RTL 数值验收。

四项新作业 38837942/38838045/38838116/38838117 全部 COMPLETED 0:0、UNLIMITED。N/E32/scan 各 66 样本，96 分块覆盖 66 个完整 apply 向量，softmax 56、RoPE 54。七模型分项/单位/冻结时间/DDR 对账通过；18 页 PDF 的 462 组数值与全页视觉检查通过。数据/估算代码提交 `0d84209e10e898f17998e959157a760a80c2afaf`。

最新 [完整交接与所有剩余步骤](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/task/280-seven-model-energy/docs/handoffs/2026-11-18-issue-280-arithmetic-estimate-v3.md)、[持续更新报告](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/task/280-seven-model-energy/docs/experiments/seven-model-energy-evaluation.pdf)。本轮估算已完成；更广的硬件实现/时序/读 DMA 与物理覆盖仍未验收，Issue in_progress、PR 草稿未合并，审查人待指定。项目登记 PR #5 pending；看板缺配置/Projects 能力，unverified、同步 pending。11:27 快照旧 DMA 38769386/38795299 仍 RUNNING，另两项在综合后的引脚放置失败，不阻塞本版估算。未配置聊天自动监测。

# 当前状态

2026-11-18 00:56（Asia/Shanghai），[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) 已完成七模型 N/E32/scan 各 66 组真实输入标定；apply 36 组通过、30 个大向量显式排除；Llama/Granite softmax 16、RoPE 12 组通过。27 份结果/262 样本的 RTL 数值、配对活动与 SHA 已归档。E32 的 TLM 9 周期与 RTL 18 周期差已按 30 个窗口/site 对账，尚未校正系统调度或回填模型小计。Falcon 扩展采样已完成，74 个算子样本和冻结对账通过；系数超出现有 S16 Q14 范围，R 绑定需修改格式并验证。其余三模型采样继续运行，后继 38832101/38832112 等成功依赖，均 UNLIMITED。[实测表、作业追踪和全部剩余步骤](handoffs/2026-11-18-issue-280-public-arithmetic-calibration.md)。Issue in_progress、PR #281 草稿未合并；PDF v2.1 小计暂不变。

2026-11-17 23:02，[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) 的 Llama 三窗 N 核心真实输入标定已通过：130 次 RMS、6 组样本的定点/RTL 因子、433 位活动标注和 SHA 完整。其余六模型采样/成功依赖标定继续运行。此为 N 算术子项，尚不等于完整 RMS 或模型能耗；完整步骤与证据见[接续记录](handoffs/2026-11-17-issue-280-common-arithmetic.md)。


## 2026-11-17 七模型 RMS 缺项链启动

公共 RMS 的七模型采样及成功依赖 N 标定已提交，全部不限时。Llama prefill 的 64 次 RMS 重放/计数和两组真实输入 N RTL 因子已通过，得到约 299.43–301.14 nJ/次的 N 动态增量；不含 E、wrapper 与驻留，尚未回填模型小计。其余阶段继续运行，完整作业表与方法边界见[公共算术交接](handoffs/2026-11-17-issue-280-common-arithmetic.md)。Issue #280 in_progress，PR #281 草稿未合并。


## 2026-11-17 公共算术缺项标定启动

[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) 已完成 N/E/S32 softmax 候选映射和 N 的 RTL 因子、433 位边界活动、300 MHz 无布线寄生配对功耗短流程验证；合成样例不计入模型小计。Llama 冻结重放采样 38828362 正在运行，真实输入 N 标定 38828633/34 已建立成功依赖，均不限时。七模型新增算术能耗尚未验收，PDF v2.1 数值保持原状。[作业与后续顺序](handoffs/2026-11-17-issue-280-common-arithmetic.md)。PR #281 草稿未合并，任务 in_progress。


## 2026-11-17 七模型无布线寄生分项扩展 v2

[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) 已将普通投影 M、写侧/U/PM 桥驻留、局控 PM 启动及读取、描述符活动和九目标母控核心加入七模型的 21 个窗口，并重新计算全部既有无布线寄生分项。片上与片上＋DDR 继续分别报告；新覆盖使第2步 Decode 的同口径片上小计增加约 4.65-17.91 mJ/token。PDF v2 为十九页，输入 SHA、分项守恒、单位及所有页目检通过。[结果、回执与剩余覆盖](handoffs/2026-11-17-issue-280-no-wire-energy-extension.md)。四项读 DMA 综合仍运行，特殊算术、控制外壳、真实拓扑/门控及 PHY 尚缺；旧 M 的 300 MHz 时序未闭合。任务继续进行中，[PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281) 草稿未合并。

2026-11-17，[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) 完成六模型能耗扩测的最终十二项回放/积分，加 Qwen3 参考形成七模型双口径报告 v1.6（十八页）。冻结数值、DDR/SRAM、输入/输出散列和跨 Python 积分通过；报告区分片上已覆盖与片上＋DDR，读 DMA 代理及特殊算术缺项另列。旧 M 的 300 MHz 时序和完整物理覆盖尚未验收，后续采用综合后直接标定路线。[报告与复现](handoffs/2026-11-17-issue-280-six-model-energy.md)。PR #281 草稿，#280 继续进行中。

2026-11-17，[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) 的六模型能耗扩测已全部完成工件迁移。Granite 三窗通过冻结输出及 DDR/SRAM 对账，迁移分项估算与本地复算一致；其余五模型在 BSCC 不限时回放。结果、缺项和逐模型 PDF 更新见[扩测交接](handoffs/2026-11-17-issue-280-six-model-energy.md)。

2026-11-17，[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) 已完成 Qwen3 三窗的 TLM 分项能耗 v1，补入四个局控描述符静默基线并单列读 DMA 动态敏感性。读 DMA 下一步以 300 MHz 综合映射网表直接估功耗，九目标母控和整机物理归属仍待补。[结果和接续](handoffs/2026-11-17-issue-280-qwen3-tlm-power-v1.md)

2026-11-17，[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) 完成局控 PM 驻留静默、局控描述符取指 300 MHz 标定及 C639 共同时钟核验。Qwen3 参考小计补三类开钟空闲。读 DMA 待物理输出，九目标母控外围需匹配工件。[控制进展与接续](handoffs/2026-11-17-issue-280-qwen3-control-power-progress.md)

2026-11-17，[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) 已按真实 PM 页类与四站点 TLM 次数生成 Qwen3 SRAM／母控 PM 三窗参考小计，两种 SRAM 配置保留固定时长情景。实际部署与开钟驻留待核对，读 DMA 仍待物理输出。[三窗数据与复现](handoffs/2026-11-17-issue-280-qwen3-macro-window-reference.md)

2026-11-17，[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) 已完成 S_P／S_base 后布线 SRAM 等长配对功耗，以及母控三档真实页的四宏标定。三套 300 MHz 物理预检通过，下一步按实际实例和驻留积分到 Qwen3 三窗，读 DMA 仍待物理结果。[标定回执](handoffs/2026-11-17-issue-280-sram-mother-pm-calibration.md)

2026-11-17，[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) 已恢复旧归档访问。S128 bank、S_P／S_base 后布线和母控 PM 归档原件在 BSCC 解包并通过散列与网表实例核对，待结合实际活动执行功耗标定。[恢复回执](handoffs/2026-11-17-issue-280-macro-views-recovered.md)

2026-11-17，[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) 将真实载荷写 DMA 与 U ADD2 增量并入 Qwen3 三窗小计，完成旧版 M 保留作用域数据的等待对照及 C639 局控 PM 运行时的活动核验与后布线分项标定。已定位 SRAM 与母控 PM 的原工件归档，旧服务器身份认证待恢复，读 DMA 仍在映射。[结果与恢复](handoffs/2026-11-17-issue-280-bscc-t6-covered-power-and-bindings.md)

2026-11-17，[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) 完成 Qwen3 旧版 M 的 18 窗 300 MHz 功耗及三窗参考估算。旧版留有 setup 和 hold 违例。新版 M 的 CTS 中止，读侧 DMA 仍在 ABC 映射，SRAM 与母控 PM 等待宏工件。[结果与恢复](handoffs/2026-11-17-issue-280-bscc-t6-m-baseline-power.md)

2026-11-16，[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) 完成 Qwen3 真实载荷写侧重测、局控阵列和 U 算术／控制 300 MHz 标定。M 进入 CTS，读侧原综合及跳过 SHARE 对照持续运行，剩余 SRAM 和母控 PM 等待物理工件。[本轮结果](handoffs/2026-11-16-issue-280-bscc-t6-actual-payload-and-leaf-calibration.md)

2026-11-16，[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) 完成 Qwen3 共享写侧 DMA 和 PM 拆拍桥的 300 MHz 配对功耗，以及 M 候选两工况产品回归。两项读 DMA 综合及 M 物理重跑仍在执行，整模型功耗待归属。[本轮物理标定与恢复](handoffs/2026-11-16-issue-280-bscc-t6-physical-calibration.md)

2026-11-16，[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) 已验收 Qwen3 三窗 TLM 事务与逐拍分项，确认 U/SRAM 残差的片内归属。读侧 DMA 两版仍在综合，M 的 300 MHz 路径修复候选已通过组合等价检查，整模型功耗待物理标定。 [结果与作业追踪](handoffs/2026-11-16-issue-280-bscc-t6-independent-calibration.md)

2026-11-15，Issue #280 已确认 C639 与实际布线 M60 的权重分配握手差异，六个原生活动窗未触发同拍冲突。当前 C639 的 M 叶块 18 项独立回归通过，同源映射通过，修订布线 116976 已开始。 [握手测试及同源实现](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/8a58ca82721a50939f2e4e4e988d4a556b7a6e5a/work/Melodydt/280/C639_M_PHYSICAL.md)

2026-11-15，Issue #280 的 C639 G32 两种工况门级回放完成。首次有效握手触发的两个 81.92 µs 窗口均有 64 笔 G32 输入和输出，普通／背压 G32 平均总功耗为 1.381／1.377 mW。M 同源布线、512-bit 写和控制链路校准待做。 [结果与追溯](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/524d0f1ae7e03a38114ae356bc4f4c8f81b0e253/work/Melodydt/280/C639_G32_POWER.md)

2026-11-15，[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) 完成 C380 普通 128-bit SRAM 的同初态空闲对照，正常／背压窗口增量 37.945／8.170 nJ。P SRAM 的 512-bit feeder 读四 bank 同址选通通过门级验证，实测 PM 接口仍为 128-bit。C639 G32 正常工况门级回放已读回，背压及四窗功耗作业持续执行。 [结果与作业追踪](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/bc7ac38b5aaa8fa8d908ca6da999ed45ddbcbe76/work/Melodydt/280/PAIRED_SRAM_AND_C639.md)

2026-11-15，[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) 通过 C380 布线 SRAM 的完整门级回放。普通 128-bit SRAM 端口在 100 MHz 的两个 20.48 µs 活动窗口分别估算 35.664 与 34.210 mW，标注覆盖率 99.18%。空闲差分、C639 物理绑定和真实 512-bit SRAM／PM 校准待完成。 [门级回放与功耗回执](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/cdc1acdc83594a8240ace568a002af9fc41411fc/work/Melodydt/280/C380_ROUTED_POWER.md)

2026-11-15，Issue #274 完成七模型 512-bit TLM 三 P 并行 FFN 和代表性历史复测。七模型两步 top-1 均与同历史 FP32 一致，Gemma 使用 Q12 残差和后归一化写回。短 Prefill、Decode、独立验收和复跑见[结果记录](../work/Melodydt/274/THREE_P_LIVE.md)。PR #275 为草稿，整机 RTL／物理时序验证仍待完成。

2026-11-15，[Issue #274](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/274) 完成接入 PR #272 保留调度后的七模型 512-bit 全层 TLM 重测。6 个模型的两步 Decode 提速，七模型短 Prefill 降速。独立 C380 注意力和 C639 FFN 原生 RTL 夹具复跑通过。全层吞吐、作业及散列见[重测记录](../work/Melodydt/274/PR272_RETEST.md)。草稿 PR #275 待审查，整模型 RTL／物理及尚余数值资格待完成。

2026-11-15，[Issue #274](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/274) 已完成七模型的短 Prefill 与两步 Decode 候选 TLM 回放，全部采用 512-bit SRAM 端口。吞吐、状态对账与 FP32 分歧详见[结果索引](../work/Melodydt/274/RESULTS.md)。[PR #275](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/275) 为草稿，第一轮七模型全层优化 A/B 已完成，短 Prefill 提升 33.89%–53.98%，两步 Decode 提升 20.82%–97.53%。测量使用 512-bit SRAM，优化前后两位置残差和完整词表 logits 逐字节一致。[优化结果](../work/Melodydt/274/OPTIMIZATION.md)保留分项及 SHA-256。数值资格、RTL 和物理时序校准待完成。

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


### 2026-11-17：七模型算术覆盖扩展

Issue #280 的 Llama/Qwen3/Granite 真实 RMS E32 共 14,208 包数值一致，四项 E32/scan/apply/RoPE 映射完成，Llama/Qwen3/Granite 共 24 样本 E32 无寄生分项标定通过。发现 compact E32 连续无阻塞 18 周期与 TLM 9 周期叶节点存在待校准差异；整模型新速度/能耗未验收，PDF 小计不变。六模型特殊算子采样 38830188–93 已实际 RUNNING；[证据与后续步骤](handoffs/2026-11-17-issue-280-operator-expansion.md)。任务仍 in_progress，草稿 PR #281 未合并，不构成物理签核。


## 2026-11-18 200 MHz 递推状态第一轮候选标定（Asia/Shanghai）

Issue [#280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280)，负责人 Melodydt；独立分支 `task/280-recurrent-first-round`，[PR #295](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/295) 已提交，待独立审查。Qwen3.5/Falcon 最终作业 120399/120413 均 COMPLETED 0:0、12 核、UNLIMITED；48 个配对功耗窗口全部原生引脚标注通过，原网表/STA 兼容视图逐位连接一致。

200 MHz 第二步 Decode 片上已覆盖小计为 Qwen3.5 1.083–1.232 W、Falcon 1.111–1.291 W；片上＋DDR 为 3.648–3.796 / 3.662–3.842 W。相对固定 v3 基线，候选区间宽度缩小 84.88% / 92.76%。保留 512-bit 系统 SRAM；候选 R 的状态存储为触发器。短 Prefill 仅零初态外推，端点不是置信区间；精度、实际共享 R 调度、注入/格式转换与物理签核仍待验收。七模型默认值及主会话 300 MHz v5 不变。

[9 页报告](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/task/280-recurrent-first-round/docs/experiments/recurrent-state-first-round-200mhz.pdf)与[完整交接](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/task/280-recurrent-first-round/docs/handoffs/2026-11-18-issue-280-recurrent-first-round.md)保存范围、源码/输入/工具 SHA、作业和剩余步骤。公开版排除商业仿真器整段原始日志，保留项目数值与来源 SHA，独立复算与完整本地包一致；原始捕获 ZIP 仅留本地/获授权存储。本轮任务不再等待仿真，进入独立审查；整体 #280 保持 in_progress。登记 PR #5 pending，看板缺配置/Projects 工具而 unverified、同步 pending，处理人待指定；未配置自动监测。
