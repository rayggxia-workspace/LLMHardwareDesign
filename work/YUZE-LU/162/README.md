续接核验：11种新增叶宏已有通过的最终交付回执（C、端点队列、AXI-Lite、M/N/E/G/S/T适配器、固定路由、S仲裁）；本次逐份重新计算实际六文件及门回执SHA，见continuation-evidence-01.json。它们不能替代组合300MHz验收。D当前d-07/job94862在node25运行，复用source-21已验证映射，source-23实现器增加保持裕量；d-gates-07/job94864依赖afterok，失败不发射。上层upper-03/job94866在第15条路由后失败，保留source-24/日志，不授予接入资格。真实三组合system-06三初态通过，每次485893检查/152836周期；八模型轨迹、声明组合最终物理/RC/时序及完整接入仍未完成。R禁用，main六宏RTL相对4b1df2c7无改动。

资源：当前只有D实现和上层接入两个独立前置，各16CPU；不是扩核。D门队列仅physical/DRC/function三项初始ready，formal依赖function、delivery依赖四门，因此最多3个同时ready采用3×16，具体内存守卫保存在memory-admission.json。更宽组合队列沿用6×16动态补位；未启动无意义填充或操作其他任务。

# Issue162 控制与搬运物理闭环

Issue https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/162

SystemC先行已提交既有PR146：65f9741a，原524425断言/新723检查/4项CTest通过。独立RTL PR163基于main4b1df2c7，六个已验收宏RTL未改，R禁用。

2026-11-01：C和端点队列分别通过300MHz最终物理/完整原生及GDS DRC/三初态最终门级功能/严格LEC，最终文件保存在本地任务runtime及服务器issue-162。C：c-gates-01/deliver，队列：endpoint-drc-02/deliver。C面积208755.204um²，die740×740um；这是叶宏资格，不是系统资格。

真实S接入发现窄口写也有返回确认，已修复D和向量适配器；旧D物理候选仅保留基线。修正后的D独立/真实S组合各三初态通过，当前d-02 job94806重跑P&R，d-gates-02 job94809按依赖启动。六适配器并行P&R adapters-02 job94814（node13，6×16）；原node16排队项94812因其他用户占满而取消，仅取消本任务尚未启动项。AXI-Lite桥P&R job94813/node18。

完整参考control_system真实三组合source-15/job94811全部通过；每初态485893检查/152836周期、CPU张量搬运0。包括12288元素Softmax三窗口同上下文回放。适配器叶宏门/控制公共线物理接入/八模型代表轨迹及最终汇总尚待完成，不能报告整套交付。

登记management-hub PR5 pending；看板无board.json，unverified/同步pending，处理人待指定。Issue in_progress，待用户审查，不自行合并。
