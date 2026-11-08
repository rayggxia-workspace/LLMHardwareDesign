# Issue232：main 审计交接

- 2026-11-08，Asia/Shanghai；负责人 Melodydt。仓库 rayggxia-workspace/LLMHardwareDesign，project_id=llm-hardware-design；[Issue232](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/232)。PR链接以同目录任务README和线上Issue为准。
- 分支 `task/232-main-model-readiness`，起点 main `c4d7b960599b9d292f27eb4429d5f226a7156c95`，tree `1ae905e08e375860ab19ebd4096b422d3781a37a`。交付commit以PR最新head读回为准。远端完整继承main；未合并main或其他任务分支。
- 本地工作目录 `D:\Study_material\Study_material\LLMHardwareDesign\work\Melodydt\232\audit-main-c4d7b960\repo` 为部分审计快照，不是完整Git checkout。根目录既有管理副本和Issue179各隔离工作目录不动；本轮新增文件仅为本Issue报告、辅助证据和本人进度。未提交远端的原始编译日志/源码包仍在本Issue本地及服务器目录。
- 正式报告：`docs/experiments/issue-232-main-model-readiness.md`；轻量证据：`work/Melodydt/232/`。不把本地/远端任务分支/已合并main/服务器运行状态混为一谈。

## 已完成的服务器作业

- 登录目标 `yuzelu@10.129.166.172`；工作/日志/结果根 `/public/home/yuzelu/Melodydt/issue232-main-audit/smoke-02`。
- 源码 commit c4d7b960599b9d292f27eb4429d5f226a7156c95；25文件main子集和输入包SHA见 `smoke-inputs.json`。没有新模型输入；测试向量固定在主干 `tb_u_native_entry.sv`。
- 实际启动 `cd /public/home/yuzelu/Melodydt/issue232-main-audit/smoke-02 && sbatch --parsable job.sh`；job.sh调用主干 `native_entry.sh`。
- Slurm100556，mdt-mainaudit，c64、4核、node1；已COMPLETED/0:0，TimeLimit=UNLIMITED；三初态3/3通过。源/容器/工具和输出索引见 `smoke-result.json`。首次100554在smoke-01目录，FAIL1:0、未进入RTL，保留失败。
- 日志 `slurm-100556.log`、`native-entry.log`、`native-entry/compile.log`；结果 `result.json`、生成入口 `native-entry/endpoint.sv`。本地回收并核验结果清单8项SHA；大构建目录保留服务器。

```bash
squeue -j 100556 -o "%.18i %.16j %.10T %.20N"
sacct -j 100554,100556 --format=JobID,JobName,State,ExitCode,NodeList -X
tail -n 30 /public/home/yuzelu/Melodydt/issue232-main-audit/smoke-02/native-entry.log
cat /public/home/yuzelu/Melodydt/issue232-main-audit/smoke-02/result.json
```

## 未完成与恢复入口

1. 首先读回main、Issue232/PR最新状态和本报告；检查Issue179活动分支，不覆盖其控制研究。审计报告待独立审查；审查人待指定，不自合并、不标done。
2. 需要整模型功能试跑时，先确定模型/层级，确认本人可用的获授权共享检查点、冻结输入和SHA；按报告锁定PR146/154/198等依赖并通过任务分支整合。输入就绪性尚未核验，不借用其他成员个人目录或GitHub身份。
3. 五项宏证据清单漂移需维护者定位；处理人待指定。保留历史清单和失败，不只替换SHA以取得通过。完整系统顶层、模型控制镜像和数据/状态编排仍待实现。
4. 登记pending：复用既有management-hub PR5，未改动登记。本仓库无config/board.json，当前GitHub工具无Projects条目能力；看板事实unverified、同步pending。具备工具和权限的管理员（待指定）核验适用看板及Issue232条目，按status-mapping填写Project ID/实际Status/已确定Priority，读回条目ID、链接和时间。
5. 本轮没有自动监测；作业已结束。未来长任务需重新提交并给出真实启动回执，不宣称聊天结束后继续监控。

审计交付：[PR233](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/233)，报告提交 `2f345e35de321fd1134c297e4c94d84854b460d7`，未合并；Issue232已读回 `status:in_review`。
