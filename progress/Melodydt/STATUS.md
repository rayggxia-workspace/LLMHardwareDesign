# Melodydt 进度

更新时间：2026-11-09（Asia/Shanghai）。Issue 是状态与验收的事实来源；本文件为当前任务分支摘要，不表示其他未合并分支已进入 main。

## 当前研究：结合 PR220/241 提高 token/s

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
