# 片上指令周期模型

这是 [#265](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/265) 的单时钟实验原型。`model.py::simulate` 接受每个 Block 按 PC 排序的操作、依赖、服务表、物理资源和接收端配置，返回发射、服务完成、入队、ACK、退休的边沿和最后完成周期。发射仅查看该 Block 的队首操作；其他 Block 可以独立推进。地址相关的 RAW/WAW 依赖由上游 lowering 绑定到相应写入的可见完成事件。共享物理 bank/端口或同一算子映射到同一资源；端口宽度和地址冲突由拓扑绑定决定。

每种服务分别指定延迟与最短发起间隔。资源声明在途槽位数及客户端顺序，支持固定优先级和轮询。轮询指针只在请求被接受后推进。需要 ACK 的操作在 ACK 前占用资源。接收端同一周期最多接受一次入队，保留旧 FIFO 顺序，同周期到达按配置的物理端口优先级、同端口按发起顺序排队。已完成服务但未进入接收端的结果继续占用在途槽位。接收端和依赖均在下一拍观察 ACK 带来的释放，模拟时钟可跳过空闲拍。未知服务、缺路由或无进展均显式失败。

通用模型每个操作只预留一种主资源，接收端按给定延迟确认。该注册式规则与本轮对照的 S 仲裁器相符；允许同拍出入队的 SRAM FIFO、同拍多端口、多资源分阶段占用、实际母控/局控镜像 lowering 及 RTL 整段发射至退休仍待绑定。`s_arbiter.py` 单独实现已冻结的真实 S 仲裁器的 IDLE/SEND/RETURN 协议，允许 SRAM `ready` 和回包 `ready` 在不同边沿阻塞。

## 验证

```bash
python -B -m unittest discover -s project/experiments/instruction_cycle -p 'test_*.py' -v
python -B project/experiments/instruction_cycle/compare_arbiter.py <107488-日志目录>
python -B project/experiments/instruction_cycle/copy_reference.py work/Melodydt/265/copy-rtl-input.json
```

- 通用模型的定向测试覆盖算子占用与发起间隔、共享端口和独立 bank、队首等待和独立 Block、固定与轮询仲裁、输出阻塞和 ACK、同周期端口竞争及死锁。共 8 项。
- `arbiter_tb.sv` 使用实际 `block_local_s_arbiter.sv` 与可控的存储/响应对端。两组独立输入均有三路并发，每组比较 9 次仲裁接受、9 次存储发出和 9 次回包，逐项对齐事件类型、客户端、序号、地址、读写和周期。详细版本、作业和散列见 [107488 回执](../../../work/Melodydt/265/onchip-rtl-107488.json)。
- 双 U_64 案例使用 [#220 已归档 RTL](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/a326d04e170cb84d273e96e7906bdf23775a0ca8/work/YUZE-LU/219/MUTEX_CONTROL_RESULTS.md)。固定输入给出目标端接受 WRITE 的边沿和地址，模型按实际 SRAM、仲裁器及测试台 ready 规则独立预测 COMMIT 和源端 RELEASE。正常、背压和复位后各三个用例，共 27 笔，全部逐拍一致。日志来源和校验值在 [copy-rtl-input.json](../../../work/Melodydt/265/copy-rtl-input.json)。这一窗口从目标端已接受写开始，尚未覆盖发起端调度或复位前未完成的事务。

## 服务器复跑

在 Melodydt 自己的全新任务目录放置当前 `arbiter_tb.sv`、`run_arbiter.sbatch` 及冻结 DUT `project/rtl/block_local_s/block_local_s_arbiter.sv`，复核 [回执](../../../work/Melodydt/265/onchip-rtl-107488.json) 中的源码 SHA-256 后运行。

```bash
sha256sum block_local_s_arbiter.sv arbiter_tb.sv run_arbiter.sbatch > source.sha256
bash -n run_arbiter.sbatch
sbatch --parsable --chdir="$PWD" run_arbiter.sbatch
```

下一轮需要把实际 MC/LC 镜像、短用例的 SRAM bank/端口与分阶段算子占用接进同一事件图，再与完整短窗口逐指令对账。当前 RTL 证据覆盖局部 SRAM 仲裁和跨 Block COPY 的目标端阶段，尚无独立的 Qwen2.5-3B 整机周期、模型加速比或 tokens/s。
