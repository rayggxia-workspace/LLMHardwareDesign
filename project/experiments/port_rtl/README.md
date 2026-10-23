# 有限响应缓冲的 bank 控制器 RTL（Issue29）

本阶段把Issue27的理想原子burst服务替换为可执行的逐beat仲裁与有限响应credit。正式验证结果以实验报告为准；开发运行不冒充正式证据。

## 硬件合同

- 单时钟，同步高有效reset。两个bank，各1024×512bit，即64KiB。reset不初始化存储，访问前必须写入所读字节。
- 三个端点M/V/D，每个具有独立请求控制信号和512bit半双工payload路径。读响应valid期间阻止同端点写请求grant；读请求控制和读响应可并行，写ack不占payload。
- `PORT_MODE=0/1/2`分别表示每bank每拍最多1RW、1R1W、2RW。不同mode是不同硬件条件，不能当同面积比较。任何同bank同64B行的两个访问，包括R/R，均禁止同时grant。
- 每bank轮询仲裁；每端点每拍至多一个grant。禁止的link在编译期固定，bit `2*endpoint+bank`；不会在prefill/decode切换时重接线。
- 每端点RESP_DEPTH个响应槽，每槽保存512bit数据、32bit tag及write标记，另计指针/计数/仲裁状态；深度1/2/4为不同资源条件。写也生成ack。读在grant边沿取旧memory值并注册到FIFO；无组合旁路，最早下一拍消费。允许同拍旧响应pop和新请求push。
- 不另设请求FIFO。上游必须持有未被接受的请求并保持全部字段稳定。测试平台实现上游控制，不能把它的队列、scratch或算术视为已实现RTL。
- 写按64bit byte strobe修改；读物理传送完整64B，语义比较限请求的有效字节。未初始化的非请求字节不用于数值结论。

## 与Issue27的关系

固定其名义key tile16、Q/K/V等静态地址、每对象版本与两种实际观察shape：prefill q32/k32/d128和decode q1/k48/d128。逐beat控制器不持有整burst的bank锁；每个endpoint只运行一个完整transfer，全部响应消费后才释放任务依赖。M/V原有计算延迟仍是假设，以测试平台计时器实现，未实现矩阵乘、softmax或在线数值状态。

因此这是新的实现合同下的受控实验，不是把Issue27的预测周期直接认定为硬件时延。原FP32数值验证也不转为INT8参考。SRAM是行为模型，尚无宏映射、布局布线、时序、面积或功耗结果。

每transfer有2拍上游准备延迟，不独占bank；D写grant至少相隔2拍，D读response仅偶数拍消费，对应外部接口64B beat/2拍的离散节流。其他端点的响应接收可始终ready或每8拍停3拍。所有对照使用相同策略集合和相同控制器库存。策略排序仍来自Issue27的service DAG，不能称最佳硬件调度。

## 验证与工具

`generate.py --output <新目录>`生成程序和拒绝原因。`sim.cpp`独立维护逐字节memory scoreboard、每端点期待响应、实际grant时的对象版本、端口/同址/半双工约束、完成性与watchdog。压力测试先通过接口初始化完整存储，再测试随机partial write、争用及反压。独立Python审计工具不导入RTL仲裁实现。

工具使用既有服务器Verilator5.042，位于`/public/home/yuzelu/opt/eda/verilator-5.042/`，在ORFS26Q1只读Singularity容器内运行。直接运行的glibc不兼容失败保留；容器内已验证版本可执行。上游选项说明见[Verilator官方文档](https://verilator.org/guide/latest/exe_verilator.html)，精确实际版本/命令/二进制与容器SHA在运行清单固定。

服务器任务仅在`/public/home/yuzelu/RuizhiLiang/issue29-port-rtl-20261022/`，作业名`lrz-`前缀。本机临时目录为`D:/Projects/Codex/port-rtl-study-20261022/`。不修改共享工具及其他成员工作。
