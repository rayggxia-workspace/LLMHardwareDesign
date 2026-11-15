# Issue #280 DDR 能耗试点交接

2026-11-15（Asia/Shanghai）。仓库 `rayggxia-workspace/LLMHardwareDesign`，负责人 Melodydt，任务分支 `task/280-seven-model-energy` 基于 `fbff1bd0e455739f28d9b7dd00b97216fe7bb847`。已交付的速度数据固定在 `d8f775b661c511d6450d5cbe63f4519563114895`。 [Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) · [试点源码与执行入口](../../work/Melodydt/280/README.md)

本地任务文件位于 `D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/280`。当前本机为无 Git 元数据的工作副本，远端文件用 Melodydt 的 GitHub 连接交付。结构检查、Python 语法、基于固定 DRAMsim3 的双通道读写实验通过，原生统计与采样版回调对齐。最终本地回归产物在 `tmp/energy-280-smoke-003`。作业 115618 和 115619 属于速度基线。

SSH 已恢复。默认身份列表未选中对应的本地身份，显式指定后主机指纹和公钥认证都通过。冻结 bridge 与 DDR 配置散列吻合。首作业 116477 在 c96/node15 运行 33 秒后 `FAILED 1:0`。生成的探针库可用，模型启动目录遗漏 `projection_math.cpp`。失败日志保留在 `/public/home/yuzelu/Melodydt/runs/issue-280/ddr-pilot-01/slurm-116477.log`。

修订作业 **116481**（`mdt-280qwen3`）使用源码 `ac2a7265d4510e0fc73164a83ebb5355da586a88`，提交包 SHA-256 为 `6c62cd23e7bbeba6a3741a6e0ae9f6ee3d4e9312c754d54865145ef50197c0af`。服务器 `yuzelu@10.129.166.172`，代码与提交目录 `/public/home/yuzelu/Melodydt/runs/issue-280/ddr-pilot-02`，实际命令 `sbatch --parsable run_qwen3_ddr_pilot.py`。c96 两任务各 12 核，已读回 `RUNNING`、node15，短 Prefill 已进入模型层回放。日志 `slurm-116481.log`，原始结果、能耗和核验清单位于 `pilot-116481/`。作业由 Slurm 独立执行。

```bash
cd /public/home/yuzelu/Melodydt/runs/issue-280/ddr-pilot-02
squeue -j 116481
sacct -X -j 116481 --format=JobID,State,ExitCode,AllocCPUS,NodeList,Elapsed
tail -n 30 slurm-116481.log
sha256sum -c pilot-116481/pilot-results.sha256
cat pilot-116481/ddr-prefill.json pilot-116481/ddr-decode.json
```

Melodydt 续办时先确认 116481 退出码与结果清单，再读取 `audit-three-p.json`、两个能耗窗口和原冻结速度基线。仅在两阶段与 FP32 及终态统计对账后发布模型数值。

后续为单 P／三 P 消融、代表组件门级标定、七模型逐项扩测、能耗覆盖和不确定度汇总。看板缺项目配置，实际条目待具权限维护者核验。
