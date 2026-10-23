# openTPU H2：冻结资源与限定层互联

[Issue31](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/31)，负责人YUZE-LU，审查人/优先级待指定。依赖PR17@ce5896de47921fcdc422c4ac9c05cefcb6666bff；独立工作树/分支`task/31-opentpu-h2`。H1封存来源不修改。

## 工程合同与当前证据

沿用small、169109初始映射单元、37023 DFF、12 synthetic SRAM、40端口1662bit、685bit ACT/MXU边界、2.5ns时钟和0.5ns IO预算。H1拆分终态89829完整STA setup +0.102306ns/hold +0.036146ns；独立89834报告最小宏接口slew余量仅+0.001549039ns。接口预算需同时核算块内已有输出负载、父层RC与接收端负载。不得把归一化slew汇总值当ns。

本轮先从实际最终ODB提取所有父层有源实例、规格/位置/方向/连接、时钟网络与路由接入几何。H1中事后插入/增强的支持单元只能作为候选底座的预制资源计入面积和库存；冻结后不能再隐式插入、移位或升规格。候选定制层尚未批准为可行，不预写成功结论。

通过前后逐实例和几何比较确认冻结边界。块内M1–M9路由保留；若顶层选择的定制层与块内上层重叠，则块内这些图形属于后续固定图形，不能称为已提前制造。后续工序集合和改变的金属/通孔集合分开记录。目标条件化的H1资源/预埋线来源不构成多计算图复用证明。

## 实际执行

所有计算作业使用c64，`--time=0`，任务名`yzl-h2-*`；不设置耗时截止、不按耗时取消。远程输出根`/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-31/`；同名目录不可覆盖，runner先提交，输入/工具/容器/输出摘要归档。

1. `inventory-01`：Slurm提交拒绝（脚本CRLF），未启动作业；原目录保留。新目录使用LF，加入`.gitattributes`。
2. `inventory-02`/89839：自然FAILED1，实际UNLIMITED。原生OpenROAD为`-Python`，不支持`-python`；保留真实失败，改用原生Tcl/OpenDB和DEF，不安装新工具。
3. `inventory-03`：已提取实际父层实例与连接TSV、完整30MB DEF，原生Tcl出口0；调度终态/文件摘要仍需采集。仅只读源ODB，不是新布局或H2完成证据。

管理结构检查已PASS；不替代物理验证。登记沿用management-hub PR5 pending；本地无board.json，Projects访问/Issue31条目尚待核验，管理员待指定。H1 PR17仍OPEN、未合并，独立审查继续保留。
