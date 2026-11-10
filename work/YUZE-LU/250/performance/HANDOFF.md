# 性能子任务交接回执

更新时间：2026-11-11 00:26 +08:00。

- 规则：`rayggxia-project-collab 1.0.0`；提交前重新读取 AGENTS、完整 Skill、status-mapping。`config/board.json` 缺失。
- 仓库：`rayggxia-workspace/LLMHardwareDesign`，project_id=`llm-hardware-design`。
- 任务：[Issue250](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/250)。2026-11-11 00:26 +08:00 在线重读，负责人/实际认证身份均为 YUZE-LU，Issue open、`status:in_progress`，未改变状态。
- 分支：`task/250-shared-x-evaluation`，从 `85fe7989b11a95725c9b1bc6daee085f74a500b8` 隔离；本子任务只修改 `shared_x*` 及本 performance 目录。最终本地提交 SHA 由交接消息及本分支 `git log -1` 提供。
- PR：由 root 整合进已有 [PR251](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/251)，不另开重复 PR；本子任务没有发布或自合并 PR。个人进度和共同决策由 root 统一更新，避免并行覆盖。
- 验证：九包445成员逐 SHA 审计通过；46次完整decode时序回放；66配对/尾部、216有符号K128 lease重放、48协议负例通过；`python scripts/check_project.py`、Python AST、`git diff --check` 通过。
- 登记：沿用在线 Issue250 的管理中心 PR5 pending 回执，没有宣称已登记。
- 看板：无 board 配置/Projects字段能力，实际状态 unverified、同步 pending；沿用 Issue7 的管理员交接，处理人待指定。
- 审查：子任务交 root 独立复核，生产 RTL/物理、完整整数及 DP 验收仍在实施，不标 done。

继续入口：先运行 `shared_x_audit.py work/YUZE-LU/250/performance --out <输出JSON>`，再读 `README.md` 和 `summary-08.json`。
首选 NoPool S16 + 两个外部A256B槽 + planned-consumer tile lease + 有限early-copy；原基线9.21564723269，首选9.2237871361，联合ACK压力9.21743463751。
新增512B A寄存器+16B copy holding/P 要计逻辑/端点面积；原16KiB S不扩，S中X4KiB，最终S逻辑活跃11712B/P。
32KiB池、pool FIFO、4KiB X寄存器均不进入首版硬件；实验代码保留开关仅为比较。

下一步由 root 协调：把实际S128/双A前端、copy FSM、LC LOAD_JOIN/END_USE及tag/取消排空实现成RTL，并用新M/G的真实握手费用校准此时序模型；获得轻量面积和独立功能证据后再进行规定物理验收。
本子任务未启动后端长实验，没有整模型能耗或物理通过主张。
