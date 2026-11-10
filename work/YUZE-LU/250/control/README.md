# Issue250 控制适配准备回执

规则版本：rayggxia-project-collab 1.0.0。
项目：`rayggxia-workspace/LLMHardwareDesign`，project_id=`llm-hardware-design`；[Issue250](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/250)。操作者已通过GitHub connector核验为YUZE-LU。

分支`task/250-shared-control-prep`从PR249 `85fe7989b11a95725c9b1bc6daee085f74a500b8`隔离。正式准备资料在[`project/experiments/shared_x_control`](../../../../project/experiments/shared_x_control/README.md)。本工作只新增该目录和本回执目录；没有修改生产RTL、根文档、他人进度或在线任务状态。

`run-index.json`保存四个Slurm实际终态、执行源commit与失败原因；`runs/`完整保留各次小型源文件、结果与失败日志。102062的35例以及102066的44例全部通过；102059/102061没有开始功能检查，不算通过。六个分片各一个Python进程，c64分配6×10，TotalCPU分别0.323/0.337秒，未人为占满核。

这些结果只证明独立抽象事务检查器接受预期正例、拒绝指定非法轨迹。它们不证明MC/LC运行生成程序、新M/G整数正确、SRAM周期吞吐、能耗、面积或物理合格。102066尚不包含同kk多个M消费者的A lease复用；后续须按新finite lease协议追加证据。

本地实际执行`python scripts/check_project.py`通过；`git diff --check`通过。EDA/协议仿真均经Slurm；本地只做文本、Git和证据回收。

生产修改点、版本化服务、三P shared-X与无pool双A槽替代的边界见准备目录README。下一步在性能gate选定唯一来源后实现有界服务适配器、描述符与真实ACK/取消排空RTL，再接母控/局控并做联合验证；接口编码不能代替集成或物理验收。

登记沿用management-hub PR5 pending；看板事实及同步由root最终交付核对，当前本子任务未修改。PR/审查/合并未完成，不标Issue done。
