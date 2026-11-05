# 005 · 固定叶宏的 LEF/Liberty 提取

- 远程 `005-leaf-views`，作业 97473。M/G/E/T 与 P4/N4 六个子任务同一 c96 节点各 4 核，整轮 92 s。最高实测进程 RSS 3,407,532 KiB（T）。每个 worker 的峰值和工具输出保存在 `views/*-worker.log`。
- M/G/E/T 以 #143 发布索引的六文件及压缩包 SHA-256 为准。P4/N4 以回收的六文件为准，摘要见 `project/experiments/block_pj_v1/sram-inputs.json`。OpenROAD 按实际 ODB/SDC/SPEF 和原 Liberty 读回。SRAM 还读入 #158 银行库。
- 运行 `run_leaf_views.sh <source> <005-leaf-views>`，输出各叶的详细 LEF、导出 Liberty、电气报告和逐项摘要。六份通过源摘要及 master 一致性检查。完整输入和输出 SHA-256 见 `views/<leaf>/receipt.json`。
- 这些 Liberty 先用于父层试装。最终还要展开叶网表、分别读入寄生后重查实际内部路径与父层时钟。