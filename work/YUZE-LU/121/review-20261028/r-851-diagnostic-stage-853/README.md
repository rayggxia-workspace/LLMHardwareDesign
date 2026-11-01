# R851 只读诊断提交证据（853）

Refs #121 / PR #122。94488已在node13实际RUNNING。源commit为73b5ee036f71e4b6e6929458c8adfb63dea3d0d3，归档SHA为f34d360eda64390281398b06a7ae8e26a2ca4427d2f6407f4c7e76bb7c7f437e；366个源码Git blob与实际远程源逐项核对，归档、manifest、queue、argv和运行目录身份一致。

[index.json](index.json)保存11份实际调度原始文件SHA/大小及Slurm观察。[stage851.py](stage851.py)和[capture853.py](capture853.py)分别保存提交与采集方式。本队列只执行一个16CPU只读前置任务，64GiB为预估，另有1.2安全系数、16GiB节点guard及live RSS保护；修复候选尚依赖这次真实邻域数据，不能伪造独立任务填满节点。

诊断结果尚未完成，原828数据库不改。850的原生584项失败、完整GDS0项和已过物理/功能/LEC分别保留，不能授予R资格；原829没有提交。M/V/S/T及其有限RC边界不变。
