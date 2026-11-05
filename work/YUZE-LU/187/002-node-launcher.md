# 002 · 计算节点容器入口

- 继承 001 源归档。运行脚本 `002-container/run_rtl.sh`（SHA-256 `2c1ea1a190a458e9d7d14e1f8355badf900ad692a3252969913b6308406fd619`）改为在两个 Slurm step 中调用容器。
- 作业 97468 在 c96 node17 分两个 12 核步骤。日志都报告 `execve(): singularity: No such file or directory`，SHA-256 均为 `228c190e0ca7bd63242c6f9c9c51e50518b2665970537420e678da80c2c6c044`。耗时低于 1 s，无有效内存采样。
- 登录节点可见的默认 `singularity` 在计算节点不可用。下一轮使用仓库既有批处理的共享绝对路径。