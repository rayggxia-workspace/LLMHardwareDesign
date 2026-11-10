# Issue247 共享 S 直供研究接续

2026-11-10 Asia/Shanghai；负责人 Melodydt；in_progress。

- 仓库 rayggxia-workspace/LLMHardwareDesign；Issue247 / PR243 open/unmerged，沿用户既有任务分支 `task/242-r-load-bounds`，起点 `00a138bae558ccafa23514a7c1a8013dcc61b27f`。不是 main，也不是新增第五轮 RTL 迭代。
- 本地整合目录 `D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/242/r-load-bounds/repo` 为非 Git 快照；本机 Git 启动有 DLL 错误，沿已授权 Melodydt GitHub 连接用显式 tree/commit/ref expected_sha 交付，不借用其他身份。
- 并行子代理仅修改外层 `work/Melodydt/247/shared-pool-research/{model,runner,audit}/` 各自独立目录；根独占正式集成。正式实验 `project/experiments/shared_pool_study/`。
- 用户指定共享 S → 独立 FIFO → P A feeder；比较共享 32/48/96KiB，加 pool0 精确基线。固定旧 R4 四场景、两个本地端口层，保留各 Block 本地 16KiB。不实装生产 SRAM。
- 实际检查：管理结构检查通过（不是业务验收）；在线确认 Melodydt、Issue247、PR243 head；服务器连接、本人 run20–23 目录及 Slurm 队列读取成功。
- 尚未执行：新模型编译、SystemC 场景、共享 RTL、综合/物理、性能结果。准备独立 run24，尚未提交，没有作业号。
- 打包计划位于外层 `work/Melodydt/247/shared-pool-research/package-plan.json`，继承 R4 冻结输入并增加 run23-result.json，共15项。源码完成后必须先上传并核验，再绑定实际 commit 打包。
- 服务器目录 `/public/home/yuzelu/Melodydt/issue247-area-speed`；所有编译/仿真用 Slurm c64/c96、4核，`mdt-` 任务名；不能在本机或登录节点执行 EDA。
- 当前本地未提交变更：本 README/接续及隔离模型开发，成果未上传；不得把线上 Issue 已进入 in_progress 当作代码上传或看板同步。
- 登记 management-hub PR5 pending（历史证据）；config/board.json 缺失，工具无 Projects 能力，看板 unverified、同步 pending，管理员及正式审查人待指定。

恢复第一步：核对 PR243 最新 head 与当前代理工作，完成模型和独立审计后集成、上传源码并在新 run 目录启动 Slurm。每次提交立即给作业回执；实际进入 RUNNING 后报告节点；完成后按退出码、结果、输入/输出 SHA 验收。当前没有本研究活动作业，也没有聊天结束后的自动监测。
