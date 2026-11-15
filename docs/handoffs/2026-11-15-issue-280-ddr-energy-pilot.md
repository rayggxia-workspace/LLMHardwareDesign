# Issue #280 DDR 能耗试点交接

2026-11-15（Asia/Shanghai）。仓库 `rayggxia-workspace/LLMHardwareDesign`，负责人 Melodydt，任务分支 `task/280-seven-model-energy` 基于 `fbff1bd0e455739f28d9b7dd00b97216fe7bb847`。已交付的速度数据固定在 `d8f775b661c511d6450d5cbe63f4519563114895`。 [Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) · [试点源码与执行入口](../../work/Melodydt/280/README.md)

本地任务文件位于 `D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/280`。当前本机为无 Git 元数据的工作副本，远端文件用 Melodydt 的 GitHub 连接交付。结构检查、Python 语法、基于固定 DRAMsim3 的双通道读写实验通过，原生统计与采样版回调对齐。最终本地回归产物在 `tmp/energy-280-smoke-003`。作业 115618 和 115619 属于速度基线。

本轮读取到与项目记录匹配的 ED25519 主机公钥。对 `yuzelu@10.129.166.172` 的批量身份认证仍失败。服务器试点和新 Slurm 作业未启动。恢复由 Melodydt 启用已授权登录身份并复试。随后从 `/public/home/yuzelu/Melodydt/runs/issue-274/three-p-full-01` 读回速度基线，在本人的 `/public/home/yuzelu/Melodydt/runs/issue-280/ddr-pilot-01` 准备隔离探针构建。通过两阶段的数值、退休时间、命令、驻留和原生统计核对后再报告 Qwen3 模型能耗。

后续为单 P／三 P 消融、代表组件门级标定、七模型逐项扩测、能耗覆盖和不确定度汇总。看板缺项目配置，实际条目待具权限维护者核验。
