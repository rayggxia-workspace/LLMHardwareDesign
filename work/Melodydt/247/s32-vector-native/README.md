# Issue247 S32 vector evidence

用途：本轮 S32 ABI、真实 U 队列周期、同库面积、原体系条件模型的可追溯证据。
负责人 Melodydt；Issue247 / PR243。版本、服务器位置和 SHA 见 evidence-index.json；分析见 analysis.json。
run48/49/50 保存有界回执；collection.json 列出的全部回收文件在外层本地辅助目录及服务器。
原始 build/log/netlist 留服务器，output-files.sha256 索引。模型原始 result.json 未整体纳入仓库。
trace-audit 是形状候选映射；构造数值通过、部分周期校准不代表完整模型 RTL 或物理验收。

字节级复现：以服务器 run49/run50 的 payload.tar 与 source-files.sha256/input-files.sha256 为准。Git 文本提交规范化为 LF，而部署归档分别有 12/6 个 CRLF 文本；29/23 个源码路径经换行规范化后与对应 Git commit blob 全部一致，其他字节无差异。冻结 baseline 的 raw SHA 绑定归档字节，不能直接用新 checkout 替代；按保留归档重新部署，或明确重新生成清单后另立新实验。详见 source-snapshot-verification.json。
