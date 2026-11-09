# Melodydt 进度

更新时间：2026-11-09（Asia/Shanghai）。Issue 是状态与验收的事实来源；本文件为当前任务分支摘要，不表示其他未合并分支已进入 main。

## 当前研究：结合 PR220/241 提高 token/s

- [Issue247：固定SRAM的面积换速度研究](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/247) 已获用户授权按顺序开展，状态in_progress，沿task/242-r-load-bounds / PR243。先验证多组96位部分和与K块A复用，再验证P输入弹性缓冲/完成协议，随后研究S端口并发、M/P规模、U流水。仅隔离模型/实验RTL；生产RTL未改。新增面积预算单列，SRAM容量保持16KiB。
- 开始检查：本人GitHub账号Melodydt、PR243 head7e4fe6980c9d126b6a4152ddec5806a3d0966ba2及无新评论；本地管理结构、Issue245/246全部既有轻量证据及功能源SHA验证通过。源码仍为本人非Git快照；新服务器仿真尚未提交，提交后登记作业、源码与SHA，不把准备描述成已执行。登记pending，看板unverified/同步pending，独立审查人与管理员待指定。
- 用户当前决定：**SRAM扩容研究保留，暂不实装**；Issue246既有结论与证据保持。下一步是Issue247固定容量研究，不启动48/64KiB生产S实现。

- [Issue246：P私有S容量](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/246) 沿PR243待审交付。[报告](../../docs/experiments/issue-246-sram-capacity.md)：W8/context512两P从16→64KiB，原调度+7.13%，前轮组合上容量增量+11.05%；48KiB已近64，128KiB该decode无新增收益。prefill2+21–23%，端口吞吐成本可能抵消容量收益。43KiB只是A，保K256至少W8 48.09375KiB/W16 52.09375KiB；真实S地址/描述符/1RW仲裁及新物理资格待实现，不改生产RTL。
- 246已测源8b18e0cb3efd3e8558d9930132282fbe551caf4e，Slurm101620/mdt-sram-cap、c64/node1/4核/UNLIMITED、4分02秒COMPLETED0:0，28case/16KiB完整结果回归/225kernels/4validation/5smoke/负例通过；35回收输出SHA匹配，四源码/15依赖保持。负责人Melodydt；待独立审查合并、不done，CI以PR回执为准，登记pending/看板unverified与同步pending。48/64KiB真实S_P实装按用户决定暂缓，保留研究候选；[恢复入口](../../docs/handoffs/2026-11-09-issue-246-sram-capacity.md)，无活动作业、无自动监测。

- 详细P/DMA专项 [Issue #245](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/245) 沿本PR243交付待审查，负责人Melodydt；原#242/#244独立待审范围保留。来源241@e7aeed20、220最新只读3a9f98a9；[详细报告](../../docs/experiments/issue-245-p-dma-study.md)。
- 已完成服务器26+18+18次完整trace执行（含重复基线），101612/101614/101615均c64/node1/4核/UNLIMITED/COMPLETED0:0。原版与仪表所有原指标、上游W8/W16基线精确一致；每轮225 kernels、4 validation、5 smoke、软件oracle及独立守恒审计通过，后两轮7个篡改拒绝通过。91份回收输出SHA通过，15份最终功能源与已测727f297cd0ec3436e108e351aad5799c013c0338一致；101611编译失败保留，-Werror未弱化。
- 发现W8权重占总线85.60%，A占11.90%，A的94.63%来自FFN下投影；原有驻留不重复记收益。有限前缀+1.10%；真正主要改善是按完整A驻留容量选择预取策略，单独+10.74%，叠加前缀/列组/512B写合并到3.063655条件token/s（+12.86%）。同组合context128/2048为+13.96%/+10.08%，prefill2吞吐+8.27%。W16仅容量策略1.871684、+11.27%，优于组合。全局关排队/减信用/单缓冲/小K负结果保留。
- 边界：同组合总线只减2.15%，17.1GB/s下必要上限4.84811仍不足5；容量策略切换/指令成本尚未实装。没有生产RTL变更、真实模型生成/新量化KV、DDR/物理/能耗资格。下一步优先验证有限预取与S消费者仲裁合同，再决定前缀/写合并硬件；实现负责人及审查人待指定。研究交付in_review，待独立审查/合并，不done；CI、登记pending、看板unverified/同步pending见PR回执。
- [本轮证据](../../work/Melodydt/245/README.md) · [恢复交接/作业命令](../../docs/handoffs/2026-11-09-issue-245-p-dma-study.md)。本专项无活动作业、未配置自动监测。

- [Issue #244](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/244)，负责人Melodydt，研究交付进入in_review；用户指定复用 `task/242-r-load-bounds` / [PR #243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)，待独立审查与合并，不done。
- 已读取最新PR220 `bf31827f7e039038ca2547046a13d29c4bf46901` 与PR241 `e7aeed2097f57a5f910cae70eb51a220c49a8a14`。形成[提速研究](../../docs/experiments/issue-244-token-throughput-study.md)：既有硬件改配方/有限S跨元素状态；新候选优先P/DMA流量、通道计数、2P/3P同带宽消融，后端/硬件/算法收益分账。
- 实际验证：900个图情景与独立路径穷举一致、关键链切换、五个非法/篡改输入拒绝；34组上游结果的算术/容量/阶段核验通过。本轮没有重跑这34组SystemC，没有修改生产RTL，也不转移物理/量化资格。
- 核心条件：241候选W8/context512约2.7146条件token/s；现流量/17.1GB/s下上限4.7438。达到5至少需减184.728MB/token，且其他阶段不变时Dot服务至少提速2.2195倍；不是已实现收益。
- 服务器 **101608 / mdt-tps-study**，代码 `81dfbd0e6e6d1432447750d5b2d4a106e2d786b7`，c96/node13、4核、22秒、UNLIMITED，**COMPLETED0:0**；`/public/home/yuzelu/Melodydt/issue244-token-throughput/run03`。复现旧attempt277图、完整图逐字节匹配，六源码/六回收输出SHA通过；服务器900情景/拒绝检查通过。101601因CRLF清单在读取源码前失败，LF重跑保持源码/校验不变，原件保留。
- 下一步：独立审查报告与研究工具，按报告验证可执行候选及真实KV质量；审查人/跨任务实现负责人待指定。本轮研究未取得新执行配方、RTL/物理/能量或实际生成速度资格。登记pending、看板unverified/同步pending，CI以PR实时失败/待核实记录为准。
- [交接与结果位置/追踪命令](../../docs/handoffs/2026-11-09-issue-244-token-throughput-study.md)。本任务无活动作业，未配置自动监测。

## R 原始 LOAD 边界修复（独立验收）

- [Issue #242](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/242) / [PR #243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)；主要负责人 Melodydt；当前 in_review，待独立审查及合并。
- 分支 `task/242-r-load-bounds`，基线 main `c4d7b960599b9d292f27eb4429d5f226a7156c95`；已测源码 commit `f034be2b7c87137b92f7bfce274a5485647e512d`。
- 已完成：R 原始端口按目标/容量检查完整索引，阻断地址截位别名及非法操作数更新；保留已有 C 地址错误合同。c64/4 核数组 101572 全部 COMPLETED 0:0；两容量及 C 适配器 9/9 正向通过、旧源码 3/3 检出缺陷，源码及 12 日志 SHA 核验通过；管理结构/运行器语法检查通过。
- 本地独立源快照：`D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/242/r-load-bounds/repo`（非 Git checkout）；服务器：`/public/home/yuzelu/Melodydt/issue242-r-load-bounds/run01`，节点 node1，无活动作业。
- 交付：文档/证据提交 `ea9fcefbc166c649a36e17878823fdd1de29f766`，链接回执提交不改已测源码，最终 head 与 CI 以 PR 记录为准。下一步为独立审查与合并，审查人待指定。新 RTL 的原 192 项最终网表回归、综合与物理重新验收未执行，后续如开展须另定负责人及范围。原物理结果不转移资格。
- 协作接入：登记管理中心 PR #5 pending；看板 unverified / 同步 pending（无 board.json 与 Projects 条目工具），管理员待指定。
- [实验与证据](../../docs/experiments/issue-242-r-load-bounds.md) · [可恢复交接](../../docs/handoffs/2026-11-09-issue-242-r-load-bounds.md)。

## 其他本人任务入口

- [#232](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/232) / [PR #233](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/233)：main 完整性与 RTL 审查；本任务承接其中 LOAD 缺陷，另一处母控超时仍按原任务记录。其完整审查资料在对应分支，不据本文件推断审查/合并结果。
- [#179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179) / [PR #180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)：独立任务及仿真/规则进度保留在其分支，本轮未修改该目录和任务状态。[已读取的个人进度快照](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/5a691e182466fb4a2d48da7ca31a1ae6ed9156ba/progress/Melodydt/STATUS.md)，最新状态以其 PR 为准。

本文件新增于 #242 分支。合并多个待审 PR 时保留各任务最新记录；不以新分支中的简短交叉索引覆盖既有详细实验与交接。
