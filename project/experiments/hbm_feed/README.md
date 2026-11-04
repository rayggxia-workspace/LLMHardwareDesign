# 多私有S／HBM供数架构实验

Issue [#181](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/181)。用户授权范围为架构与仿真、服务器运行和PR交付。

## 证据边界

- 原版main `4b1df2c7` 的S存储、feeder和M不修改。验证顶层实际实例化16份16KiB S及其feeder、一份共享M数值验证器；不宣称16个并行计算Block。
- 每S新增两份16深、155bit异步FIFO和一个等待S响应的transport状态位。请求为`write1|tag16|word_address10|payload128`，字地址0..1023。响应返回同一metadata和实际S输出；LOAD保留信用直至S真实写ACK经响应FIFO返回。
- `hbm_s_endpoint`是可综合的事务搬运原型，**不是现有control_d的多实例实现，不是AXI桥，也不是HBM协议控制器**。分组仲裁、tag账本和外存调度由C++架构模型执行，不作为已实现的控制RTL计价。
- 异步FIFO两侧由真实独立RTL时钟驱动。仿真验证数字行为，不证明亚稳态MTBF、CDC物理约束、500MHz时序或P&R资格。
- C++内存数组是实验数据源/结果接收端，不绕过S。M输入必须由原S内feeder读出，按独立整数矩阵oracle检查所有64个结果。

## 模型参数

时基为1/3 ns，核心周期10 tick=300MHz；默认外存用户接口周期6 tick=500MHz，支持相位偏移及200/300/600MHz对照。这个时钟不是HBM引脚时钟。

默认4S／2组／2通道；最大16S。每组含相同数量S，`group_id % channels`映射通道。每通道有限64项队列、4 bank、每bank一次命令间隔2个用户周期、固定20周期返回基延迟、行切换额外6周期、读写翻转停4周期、每512用户周期前16周期刷新停顿。地址映射`bank=(word_address/4)%4`、`row=word_address/64`。每通道默认256bit用户总线，每用户周期最多两个128bit数据字，读写共用预算。刷新期间不传数据；模型允许控制器在停顿时有限接收请求和提前安排bank服务，是简化假设。

这些参数是**显式架构假设，不是某个HBM2/3器件的JEDEC时序**。不宣称模型与Ramulator、厂商VIP或真实HBM校准过；未实现HBM命令/训练、ECC、完整bank时序、总线电气或封装。

两级轮询先选组，再选组内S，每次LOAD最多burst个字，默认4、上限16；每S默认16信用。信用包括HBM队列、在途、CDC、S等待及返回FIFO。已无信用者不参与新的请求仲裁。每组还有最多2字的用户侧链路token桶，300MHz每周期补1，防止把一条128bit组链路当作无限带宽。STORE发S读请求，再把真实S返回写到外存模型，收到模型写完成才还信用。

每S输入为8×32 A、32×8 B的S8矩阵（48个128bit容器，A每容器低64bit有效），及默认256字隔离压力数据。每S的A/B由不同公式生成；核对S写ACK、全部S读回、STORE最终数组和64个S64矩阵结果。M验证顺序复用一个M；计算耗时与LOAD/STORE吞吐分开报告，不冒称完整模型tokens/s。

## 运行

先在新分支提交所有输入，再从Windows本地运行：

```powershell
python -X utf8 -B scripts/check_project.py
python -X utf8 -B project/experiments/hbm_feed/launch.py --attempt <全新名称> --package-dir <全新本地目录>
```

启动器仅打包显式输入，并核验HEAD原字节；只向`/public/home/yuzelu/PingyangHuang/issue181-hbm-<attempt>`的新目录写入。Slurm为c64、4CPU、UNLIMITED；使用现有只读ORFS容器和Verilator5.042，不修改已有目录、其他任务或软件。输出包括lint/build日志、逐例JSON行、profiles、失败/负例日志、工具SHA及最终results。源码归档与可执行文件留服务器，轻量证据进Git。

默认矩阵包括2/4/8/16S、共享/分通道、信用1/2/8/32、队列4/64、不同用户时钟和相位、总线128/256/512、burst1/16、S0阻塞、在途协调复位、长延迟、刷新对照、三初态两随机种子。负控制覆盖坏数据、非法S数、地址越界及零信用。错误注入是模型/夹具检测，不等于AXI或HBM硬件错误恢复已实现。

## 当前待扩展

完整AXI4五通道及位宽/AXI3适配、硬件两级仲裁与D多S、异步单端复位恢复、同一S计算/补料并发和长模型数值质量均不在本原型通过声明内。真实PHY/封装和300MHz/500MHz物理验收另行开展。当前reset负载采用全平台协调flush并重放，禁止将其描述为可接受任意旧响应的独立复位。
