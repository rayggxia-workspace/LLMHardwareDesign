# 准入控制496：正确新源依赖链

Refs #121 / PR122。配置八队列404/405/406/485/492/493/494/495，保持本Issue最多8 allocations、pending/unknown计入，所有历史jobID均纳入预算。源码沿用已验证准入器，实际配置SHA2ecb85cd491a5cd63a5641e451af4fb846768ca3434f16c9a35aaebd2bc4c00e。当前只完成staging/归档/dispatcher精确Git字节核验，尚待部署与两轮运行读回，不声称已运行。

仅替换登录节点的479控制进程，不触及任何Slurm EDA；仅将无allocation的478/487/488/489标为历史，保留所有原始文件。490从未部署。旧477及R404继续自然运行，M/S/T不重复。
