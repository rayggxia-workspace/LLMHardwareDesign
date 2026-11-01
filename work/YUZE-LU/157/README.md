# R架构探索：独立实验 Issue157

任务 https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/157 。按rayggxia-project-collab v1.0.0记录；独立分支task/157-r-architecture，不修改Issue143/PR144生产、验收或作业。

冻结基线为Git e836741d334429be7d991cdc260f1ba955a7562e，实际输入字节/Git blob见BASELINE.json。A0 R源SHA4032c5ed，与run342映射及run030 GP ODB匹配。92059负载仅属于这个历史候选，不转移到A1/A2。

本地复现：python project/experiments/r_architecture/freeze.py；python project/experiments/r_architecture/candidates.py。远程固定镜像SHA49eae8...，Yosys0.68+post，Nangate45 typical库SHA8d540a...。完整候选源和原综合脚本在inputs/candidates；远程结果按独立attempt目录存放，源码归档和每份回执绑定SHA。

阶段：A0/A1/A2回归与小规模正负形式控制→严格完整等价→同配置综合；SystemC建模并行。完整证明失败/超时禁止该候选综合。最多1—2个通过系统筛选的新候选进行物理，不提前批量P&R。模型指标、分析预测、RTL测量和物理测量分别记录。

S合同：四个256×128bit单1RW Bank，总16KiB；只有一个窄请求口。宽读独占所有bank，同周期窄请求失去仲裁；各响应寄存器可背压，不把四个bank虚构为四个并发窄端口。现有SystemC #145是无时钟事务模型，不能直接当周期模型。

输入数值取自冻结test_recurrent_macro.cpp的独立宽整数定义。project/experiments/r_state/reference.py为不同算法/重试合同，不用作当前R oracle。

当前结论均待实验，FINAL_RECOMMENDATION不提前选择。没有标定能量参数，只记录事件和参数化能量；新增控制/互联硬件未综合前不报告系统总面积数字。登记management-hub PR5 pending；无board.json/Projects条目工具，看板unverified/同步pending，管理员待指定。
