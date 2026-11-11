# S16桥接与E流水化证据

用途：Issue247 / PR243 / Melodydt的本阶段辅助记录；正式报告位于docs/experiments/issue-247-s16-vector-native.md。
analysis.json由project/experiments/s16_vector_native/analyze.py从回收日志重算；evidence-index.json记录来源、工具、作业与209份回收文件SHA。
run41/42/43子目录保留输入、部署源码及全部输出SHA清单。原始results、容器内编译目录和网表留在授权服务器个人run目录，位置见evidence-index.json。
本地回收位于工作区work/Melodydt/247/runNN/receipts，属于辅助副本；远端提交文件不代表main已合并。
analyze.py仅做本地证据处理，不运行EDA。完整复现命令见ARCHITECTURE和阶段交接。
