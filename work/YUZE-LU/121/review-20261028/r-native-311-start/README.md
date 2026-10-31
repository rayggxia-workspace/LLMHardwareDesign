# R311 新原生布局布线已启动

Refs #121 / PR #122。2026-10-29 10:14:32 CST捕获；自动准入335在R309自然完成释放节点后，于10:13:15提交R311，作业93125实际RUNNING/node18/96CPU，未取消、重投旧EDA。本任务仍8个allocation，V330仍等待空位。

实际队列revision300-route-r已claim 16CPU，192GiB预测×1.2及16GiB guard；其余任务受真实前置限制。源14b4746002cc6f088b31594f2438acf42512c9cd，302份归档源Git blob核验；原manifest源绑定一致。7份原始小文件SHA、Slurm状态和控制器读回见index.json。

此时尚无revision300-native-flow.json，不据队列RUNNING推断任一物理阶段通过。后续必须取得六阶段完成及312最终四门/六文件/完整几何、313接口；不继承236 CTS或最终资格。仅启动证据，R最终尚未接收。
