# Issue250 控制适配准备回执

规则版本：rayggxia-project-collab 1.0.0。
项目：`rayggxia-workspace/LLMHardwareDesign`，project_id=`llm-hardware-design`；[Issue250](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/250)。操作者已通过GitHub connector核验为YUZE-LU。

分支`task/250-shared-control-prep`从PR249 `85fe7989b11a95725c9b1bc6daee085f74a500b8`隔离。正式准备资料在[`project/experiments/shared_x_control`](../../../../project/experiments/shared_x_control/README.md)。本工作只新增该目录和本回执目录；没有修改生产RTL、根文档、他人进度或在线任务状态。

`run-index.json`保存四个Slurm实际终态、执行源commit与失败原因；`runs/`完整保留各次小型源文件、结果与失败日志。102062的35例以及102066的44例全部通过；102059/102061没有开始功能检查，不算通过。六个分片各一个Python进程，c64分配6×10，TotalCPU分别0.323/0.337秒，未人为占满核。

这些结果只证明独立抽象事务检查器接受预期正例、拒绝指定非法轨迹。它们不证明MC/LC运行生成程序、新M/G整数正确、SRAM周期吞吐、能耗、面积或物理合格。102066尚不包含同kk多个M消费者的A lease复用；后续须按新finite lease协议追加证据。

本地实际执行`python scripts/check_project.py`通过；`git diff --check`通过。EDA/协议仿真均经Slurm；本地只做文本、Git和证据回收。

生产修改点及版本化服务见准备目录README。已优先选择NoPool双A槽作为唯一首版候选，共享池只留作对照。实验有界服务、A/copy/真实ACK/取消排空RTL已实现，尚需母控/局控程序接入和联合数值/性能/物理准入。

登记沿用management-hub PR5 pending；看板事实及同步由root最终交付核对，当前本子任务未修改。PR/审查/合并未完成，不标Issue done。

Slurm102100两套候选RTL各六seed通过，给出请求/ACK与A32B真实消费周期，见`timing-102100.json`。Slurm102110进一步接原`local_s_base`及每实例四bank真实行为视图，U与三P共四个S实例，六seed×三初态18/18通过；见`native-s-102110.json`及run15全源/CSV包。全部源与包SHA已逐项核对。

真实S集成：U读32个128bit字，三P各32笔真实写ACK；A只读两tile共32字，三次M use共24个32B容器，同kk第二次使用零重读。512B复制首U请求至最后三P写ACK164–169拍，包含有意5+seed拍响应背压；正常native S请求至响应2拍。bank原任意DELAY=3ns保留，功能时钟10ns，不能据此宣称300MHz、能耗或token/s。没有MC/LC程序、新M/G算术、DDR或新P&R资格。

首版S128仲裁借用原S两响应容量，只新增两份owner/tag元数据，A读与copy写各最多一笔在途。S不加端口或tag管脚，无新增SRAM、隐形64B FIFO或4KiB X复制。512B A寄存器及每P16B copy hold仍需单列新物理面积。
