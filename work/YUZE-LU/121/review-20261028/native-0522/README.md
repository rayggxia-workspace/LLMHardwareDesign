# V原生完成与281实际接续

Refs #121 / PR #122。实际捕获时间为2026-10-28T21:21:32.768068UTC，目录名不是捕获时间。

V270完整六阶段原生流程已通过，receipt `a0dcc1629a034b47054972b1f78bf26436abcdb1c3e43bef1f8bcc9b2616252d`。保持原1240×1240µm候选外框；原生LEC、提取和最终报告完成不替代独立四门。

只有真实native回执通过后才实际提交已暂存281；93019在node18运行。当前final-source-v已通过，独立physical-v/drc-v/final-function-v三个16CPU任务并行，严格formal-v依功能通过后即补位；交付/几何仍待四门全部通过。R分支仍在同队列等待236真正native通过，不新占节点。

15份原始小文件逐份SHA见index；V270全部275个archive Git blob及281全部285个blob逐字节核验，当前捕获的同源输出3条绑定通过，见verification。281复制的constraints-control具有其自己的原封存源，不将其错误归属到281新源；下游门继续核验控制工具/输入。

S280仅余完整DRC，严格LEC已过；R236 GRT继续。285和288仍只有暂存、无allocation。五宏最终结果尚未齐，Issue保持in_progress、PR保持draft。
