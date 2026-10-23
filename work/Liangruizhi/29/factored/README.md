# 原RTL分阶段检查与factored原型

原916dcf9e RTL不修改。89939在单配置-defer/hierarchy的360秒前端限额内未完成（退出124），
不称综合通过/RTL错误。另立bank_port_fabric_factored.sv，把每bank/slot的endpoint地址/数据/strobe
选择提为共享组合信号，减少byte-lane表达式重复；没有增减存储或接口。它是新源码原型，不冒充原实验源码。

必须重跑原27配置/1872程序/54stress，对比原results中的各case完整result、exit与保存trace；
只能称有界仿真回归，不能代替形式等价。通用Yosys单mode0/depth1前端360秒与lowering720秒分别保存检查点，
不做工艺memory映射或PPA。8CPU内3×2编译＋1Yosys并行，不能超过分配。失败/未完成保留。
