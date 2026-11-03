# Issue162：远程执行通道中断，继续入口与实际证据

更新时间：2026-11-03T08:46:37.943127+08:00。Issue [162](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/162)，Draft PR [163](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/163)，负责人YUZE-LU；分支task/162-programmable-control，当前代码415069fbe00e9706eee8bfcfeec842ec4b0ac878。

S1350内部驱动及所选S适配器1391的单块资格与21类交付继续有效，见CONTROL_V1_BLOCK_DELIVERY.md。尚无实际完整组合几何/PG/三角点RC/300MHz/联合六文件通过。所选1391最终程序仍须读取实际完成回执，不能继承1390的成功结果。

本次实际观察：Windows SSH在标识交换前超时/重置；现有Git SSH也有重置，部分连接完成密钥交换、按原known_hosts核验服务器，使用Windows现有配置选择的id_rsa_windows公钥后仍超时。没有改写凭据、known_hosts、服务器设置或远程Slurm作业。原始时间/错误及本地辅助脚本见[索引](../../work/YUZE-LU/162/continuation-network-29/index.json)。只能确认最后一次读取时的八个自有分配和20路新图搜索，当前远程状态待核实；不能断言持续运行或完成。

本地阻塞的只读收集器链已按确切PID/父子关系核实后替换为带SSH超时和传输失败重试的收集器。只读监视继续；非传输错误仍明确停止并保留日志。未改已冻结source140/141/142或任何既有队列规格/结果。

已有1470/1471/1472外部留白诊断及两个实际native地电容/输入负载后继在中断前追加。新的1480–1482路由发射器只在本地准备，尚未提交；严格等待1391真实程序及两个实际三角点必要筛查成功，仅选择全部角点0违例的场景。相对宏位置/内部版图不变，新面积照实计入，每路仍带完整几何→全PG→low/base/high实际RC/300MHz→联合交付六个后继。收集器已准备发现该新记录，不预授资格。

恢复第一步：执行本地control162-bounded-status142.py，读取1391真实最终程序、1470–1472及两个halo筛查回执和现有20路搜索；有实际合格候选才运行control162-halo-route142.py --submit。按实际需求精确核验并释放本任务旧搜索step，绝不取消父分配或其他任务；八节点、c96 6×16/c64 4×16及原内存门保持。当前通道恢复需服务器/网络侧状态变化，处理人待指定；已经向用户询问是否维护，本地继续重试。

原失败完整保留；R及并行修改保留、不接管，不自行合并。规则rayggxia-project-collab1.0.0；登记management-hub PR5 pending；缺config/board.json，看板unverified/同步pending，处理人/审查人待指定。任务未完成，此记录不授予系统资格。
