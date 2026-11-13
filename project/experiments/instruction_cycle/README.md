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

## A2 母控、局控与片上算子联合验证

`a2_images.py` 从实际二进制校验并解码 128-bit V1 的 `G_CALL/G_WAIT/G_END`、`L_EXEC/L_WAIT/L_END`、task 及 M 执行描述符。A2 的输入地址绑定到 S 的 4-bank 宽口，B 先于 A，两次各读 64 B。M 结果走窄口，按 `word & 3` 选 bank，写入 16 B。`a2_cycle.py` 将母控和局控 PM 握手、两次 feeder 发起与接收、M START/READ_RAW、S 写回和 ACK 放在同一时钟上，并用冻结种子的 S8 数据独立校验 S64 结果。程序部署与种子预装在 START 前完成。模型输入是两份镜像、种子、START 接受边沿及测试台的 `STALL` 参数。除 START 作为窗口起点，PM、运算、ACK 和 RESULT 的时标只用于对账。

该版本 S 的窄口在 SEND 后一拍可见响应，仲裁器接受写到 ACK 最早 2 拍。前一版双 U_64 对照使用不同 SRAM 实现，写到 ACK 最早 3 拍。A2 feeder 在接收上一笔宽口响应的同拍可以发下一笔。冻结测试台在运行期间保持 host 窄口空闲，故实际验证覆盖独占 feeder 及写回和 ACK 背压。并发宽窄口竞争、多目标发起、复位恢复、片外 DDR 及整机加速比仍待验证。

作业 [107535 回执](../../../work/Melodydt/265/a2-rtl-107535.json) 在 Verilator 5.042 上记录 5 次成功任务，从 accepted START 到 accepted RESULT 共 224 个事件，逐拍零误差。正常为 105 拍，原背压的两次连续任务为 217、219 拍，留出背压为 151、154 拍。旧作业 97305 从 CALL 开始记录，独立对账为 99、209、209 拍。两种窗口分别记录。原始用例的三个非法描述符仍由 RTL 拒绝，检查无确认数据移动。

从服务器保留的运行目录取回各 case 的 `mother.bin`、`local.bin`、`seed.bin`、`run.log` 和留出 `heldout.log`，按回执核对散列后运行。

```bash
RUN=/public/home/yuzelu/Melodydt/runs/issue-265/a2-onchip-20261113-01
python -B project/experiments/instruction_cycle/a2_cycle.py "$RUN/results/a2/single_signed" --stall 0
python -B project/experiments/instruction_cycle/a2_cycle.py "$RUN/results/a2/boundary_reuse_stall" --stall 2
python -B project/experiments/instruction_cycle/a2_cycle.py "$RUN/results/a2/boundary_reuse_stall" --stall 1 --log "$RUN/results/heldout.log"
```

如需在 Slurm 复跑，在 Melodydt 自己的全新目录放置冻结的 `source.tar`、`probe_a2.py` 和 `run_a2_probe.sbatch`，按回执核验 `source.tar`，生成 `sha256sum probe_a2.py run_a2_probe.sbatch > probe.sha256`，执行 `bash -n run_a2_probe.sbatch` 后运行 `sbatch --parsable --chdir="$PWD" run_a2_probe.sbatch`。

## 双 U_64 从 START 到 RESULT

`dual_u_images.py` 从 [#220 冻结用例](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/a326d04e170cb84d273e96e7906bdf23775a0ca8/work/YUZE-LU/219/MUTEX_CONTROL_RESULTS.md) 的三份 Compact V2 镜像恢复两个母控 `CALL`、两路局控的 11 个服务、等待掩码以及跨 Block 写地址和接收预约。`dual_u_cycle.py` 从已接受 START 的边沿开始推导母控 SRAM PM、两路独立局控 PM、E Add/Mul、Block 内共享窄口和跨 Block 事务。两个 64-bit PC 可能重复访问同一条 128-bit PM 行。两个局控可同时运行；母控收到两份 terminal 并释放 WAIT 后才进入 RESULT。`dual_u_services.py` 保留每个 S 仲裁器的轮询指针和单槽命令，发出数据后一直持有归属，源端只在目标端 SRAM ACK 接受后释放。

| 场景 | 接受 START 到接受 RESULT | 对账事件 |
| --- | ---: | ---: |
| 无背压 | 351 拍 | 210 |
| 原背压，写／ACK 相位 1／3 | 490 拍 | 210 |
| 留出背压，写／ACK 相位 2／5 | 470 拍 | 210 |

[作业 107643](../../../work/Melodydt/265/dual-u-rtl-107643.json) 的 630 个事件全部逐拍一致，并核对实际传输数据、每组 112 B 确认读与 80 B 确认写。留出组在读取新 RTL 日志前预报 470 拍。旧作业 100343 的正常、背压和复位后窗口额外核对 402 个事件，最终复位窗口为 485 拍。旧摘要在 RESULT 接受后的下一个观测点打印，比接受边沿多 1 拍。模型仅比较复位后的完整窗口。

该图的依赖在各私有 S 内错开了 E、接收写与源端读，三组新 RTL 均未观测到 `S_CONTEND`。本轮覆盖真实多目标控制重叠与传输背压。E/RX 同拍冲突在定向模型测试中检查，独立 S 仲裁 RTL 的竞争证据来自 [107488](../../../work/Melodydt/265/onchip-rtl-107488.json)。当前片上模型会跳过纯 PM 空闲间隔。活动服务仍逐边沿推进，运行速度未量化。片外 DDR 未接入。

```bash
RUN=/public/home/yuzelu/Melodydt/runs/issue-265/dual-u-20261113-01
python -B project/experiments/instruction_cycle/dual_u_cycle.py "$RUN/generated" "$RUN/results/dual_u/normal.log" --stall 0
python -B project/experiments/instruction_cycle/dual_u_cycle.py "$RUN/generated" "$RUN/results/dual_u/stalled.log" --stall 1
python -B project/experiments/instruction_cycle/dual_u_cycle.py "$RUN/generated" "$RUN/results/dual_u/heldout.log" --stall 1 --request-phase 2 --ack-phase 5
```

在 Melodydt 的全新运行目录复跑时，从 [107643 回执](../../../work/Melodydt/265/dual-u-rtl-107643.json) 的 `frozen_source_directory` 复制 `fixture/{design,staged,lc}` 和 `generated/{mother.mem,local0.mem,local1.mem,rtl-source-sha256.json,input-data.json,connections.json}` 到对应位置。放入 `probe_dual_u.py` 和 `run_dual_u_probe.sbatch`，生成 `sha256sum probe_dual_u.py run_dual_u_probe.sbatch > probe.sha256`，再执行 `sbatch --parsable --chdir="$PWD" run_dual_u_probe.sbatch`。运行器核验冻结源码和镜像后编译，原测试台断言继续运行。

## 有限 DMA 队列与实时 DRAMsim3

`model.py::DmaBinding` 将 DMA 描述符和 FENCE 绑定到片上操作。每个 Block 保留 DMA 描述符的发起顺序，准备更快的 FENCE 等待同 Block 的旧描述符先进入 DMA。同拍就绪的不同 Block 按显式端口顺序仲裁，未接受的请求保持原身份。`dma_ddr.py` 分别跟踪描述符、64 B beat、后端信用、返回槽和客户端退休。相同物理地址在已发 beat 完成前保持锁定。后端可在完成边沿接收其他地址，DMA 信用和同址锁在下一边沿才可复用。返回槽堵塞会继续占用描述符。绑定用例的响应端保持 ready，独立 DMA 测试另覆盖消费者停顿。这里的 FENCE 等待先前描述符退休、端口和后端排空后发布响应，后续 beat 在该响应被消费后才可发起。

| 验证范围 | 结果 |
| --- | --- |
| 有限队列参考后端，写入与读取使用不同新旧数据 | 第 4 拍写被接受，第 11 拍写可见，第 17 拍 FENCE 退休，第 19 拍后续同址读被接受，依赖该读的片上算子在第 24 拍启动、32 拍完成 |
| 冻结 DRAMsim3 DDR4，实时读回调 | 依次在第 0、50 拍提交同址两读，分别在第 50、78 拍回包，保留各自 ID，对应两条物理 RD 命令；同址未完成读阻塞第二笔入队 |
| 同时间轴上的实时读后端短例 | 3 笔读对应 3 条物理 RD 命令，FENCE 第 65 拍退休，后续读第 94 拍回包，依赖算子第 97 拍发起、第 105 拍完成 |
| 冻结 64 B typed DMA RTL | 作业 107669 的 24 个排空检查点全部匹配；独立归档六个 seed 各匹配 5,540 笔返回 ID，三种初始化的散列一致 |

实时桥使用 630 ps 的共同时间单位，只将 DRAMsim3 的读返回时间和身份接回模型，负载字节来自模型内存。冻结 DRAMsim3 写回调发生在写缓冲接收，历史 103220 的 64 个写回调对应 60 条物理 WR 命令，实时桥因此拒绝写入。参考后端的写可见和 FENCE 语义来自明确定义的有限队列协议。冻结 #264 RTL 提供读通道和排空证据。历史 #179 另有 12 笔 16 B RTL 混合事务和 24 次跨时钟域握手，其四次同址回读的写值与种子初值相同，无法用这些回读区分新旧值。证据分界、源版本和 SHA-256 见 [DMA／DDR 回执](../../../work/Melodydt/265/dma-ddr-receipts.json)。

```bash
python -B -m unittest discover -s project/experiments/instruction_cycle -p 'test_*.py' -q
python -B project/experiments/instruction_cycle/check_dma_ddr.py
python -B project/experiments/instruction_cycle/compare_dma_rtl.py <107669-运行目录>/quiescence.log
python -B project/experiments/instruction_cycle/compare_dma_typed_trace.py <归档>/candidate-1-0.csv <归档>/candidate-1-0.log
python -B project/experiments/instruction_cycle/compare_dma_mixed_legacy.py <97279-归档日志目录>
```

服务器复跑使用 `run_dma_quiescence.sbatch` 和 `run_dram_live.sbatch`。按回执在 Melodydt 的全新目录放入对应源文件，核对 `source.sha256`，执行 `sbatch --parsable --chdir="$PWD" <脚本>`。

## DDR 写数据结束与跨时钟采样

`patch_dramsim_write.py` 在独立目录复制并核验冻结的 DRAMsim3 `29817593`，为实际发出的 `WR` 增加观察点，并从原 DDR4 配置生成统一事务队列的候选配置。保留原版分离队列与只读桥用于回归。统一队列使少量尾写能进入命令队列。在选定配置中，`WR` 发出后按 `CWL + BL/2` 的 20 个 DDR 时钟记录写数据结束。控制器仍按本身的恢复约束调度后续命令。原写回调单独核对入队身份；写数据结束才解锁同址事务。回读数据由模型内存保存。这里验证的是 DRAMsim3 命令时序与模型的数据可见性，板上控制器写提交和持久性仍待绑定。

`DramLive` 使用精确有理数映射片上 300 MHz（`10000/3 ps`）和 DDR `630 ps`。候选 CDC 的请求、响应 FIFO 深度均为 2，两边均以严格晚于源事件的首个接收时钟边沿开始两级采样。请求槽信用在 DDR 接受后同步回片上，响应信用从 DDR 发出保留到完成被片上接收再同步返回。FENCE 核对先前事务已返回且描述符已退休。完整窗口结束后另检查 FIFO 指针信用已稳定；该检查只给出最晚核验边沿。

| 场景 | DRAMsim3 发出的 RD／WR | 最后写在片上可见 | FENCE 退休 | 同址回读首次发出到 CDC | 依赖计算完成 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 常规，相位 0 ps | 3／1 | 21 | 31 | 32 | 50 |
| 留出，相位 173 ps | 19／9 | 68 | 81 | 82 | 128 |

表中最后四列均为片上周期。`audit_dram_write_cdc.py` 从 DRAMsim3 命令追踪独立解码物理地址，逐笔核对 32 条 RD／WR 的 ID、发出和数据结束边沿、双时钟采样与 FIFO 信用。两个用例分别读回 64 B 和 576 B 新数据，核验写前值与写后值的 SHA-256。原只读桥仍在第 50、78 个 DDR tick 回包，原同周期片上短例仍为 105 拍。[作业 107731 回执](../../../work/Melodydt/265/dram-write-cdc-107731.json)记录精确配置、编译输入和输出散列。

```bash
RUN=/public/home/yuzelu/Melodydt/runs/issue-265/dram-cdc-20261113-01
python -B project/experiments/instruction_cycle/audit_dram_write_cdc.py "$RUN/result.json" "$RUN/results"
```

复跑时将回执中 `source_sha256` 列出的文件放入 Melodydt 的全新目录，生成相同的 `source.sha256`，再执行 `sbatch --parsable --chdir="$PWD" run_dram_write_cdc.sbatch`。该脚本对照冻结原库、配置及 `src`/`ext` 编译输入并在本目录构建。下一步是绑定同一部署的 Qwen2.5-3B 控制镜像、片外地址映射、KV 请求、时钟/CDC 与写提交协议，用实际单层和跨层 decode 窗口对账。当前短例使用候选时钟和 FIFO 参数，整机 tokens/s 及加速比待测。
