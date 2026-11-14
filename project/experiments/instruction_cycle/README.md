# 片上指令周期模型

从该分支开始 Qwen Decode 快评，见[适用条件、可变参数和命令](QWEN_DECODE_GUIDE.md)。

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

## Qwen2.5-3B 原生短窗 DDR 对账

`qwen_native_ddr.py` 对 case 2 的两个独立 Verilator 归档核验母控页及共用局控镜像的散列、逻辑长度、填充、CRC32 和指令终止位。核验描述符工件、控制传输计数、物理写地址和 tag、逐拍接收与归还、DDR 回调及已提交数据。读事务的物理通道由源 lane 决定，激活与写事务按地址交织。`DDR-0` 与 `DDR-1` 分别是基准与带压力的两次测试台运行，每次均含两个 DDR 通道。

| 上游作业 | 测试范围 | MC 页／调用 | 原 RTL 周期，模式 0／1 | 每模式回调数 |
| --- | --- | ---: | ---: | ---: |
| 106093 | layer 0 的 prompt 位置 497–499，嵌入、RMS、QKV 与 KV 写回 | 9／261 | 1,141,401／1,238,816 | 263,085 |
| 105530 | 位置 636–638 的三位置上下文，layer 0 到 layer 1 首个 RMS | 8／393 | 1,795,357／1,927,341 | 1,319,741 |

`replay_native_ddr.cpp` 以归档中的**已接受请求**及其 DDR tick 驱动同版本 DRAMsim3 的两个实例。独立比较每个通道、tick、方向和物理地址的回调多重集，保留同址重复次数。该对账验证 DDR 后端。发射、仲裁、背压和片上退休仍需由快速模型独立生成。106093 的测试台周期为 10 ns，DDR 桥按 `10000/3 ps` 推进，该窗口只用于 DDR 事件核验。105530 的 DDR 桥绑定实际 10 ns 测试台边沿，归档给出整个窗口周期和层间结果，层间交接两端的统一时标待补。归档 strict-write 回调按上游仿真库定义；107731 的 WR 数据结束仍使用独立候选模型。

`qwen_kv_reference.py` 审计 case 2、3 的逻辑整数回放。针对 decode step 11–13 的 layer 0/1 检查残差到下一层归一化的依赖和 KV 追加。在 11→12 边界独立重算每 case 四份 S32 张量的字节散列，12→13 由固定回执追溯。这两组逻辑输入和原生 RTL 窗口的地址及周期分别登记。

在服务器的全新个人目录放置 `qwen_native_ddr.py`、`qwen_kv_reference.py`、`replay_native_ddr.cpp`、`run_qwen_native_ddr.sbatch`，把所用源提交写入 `git-commit.txt`。运行目录和输入散列见 [107931 回执](../../../work/Melodydt/265/qwen-native-ddr-107931.json)。

```bash
sha256sum qwen_native_ddr.py qwen_kv_reference.py replay_native_ddr.cpp run_qwen_native_ddr.sbatch git-commit.txt > source.sha256
bash -n run_qwen_native_ddr.sbatch
sbatch --parsable run_qwen_native_ddr.sbatch
sha256sum -c output.sha256  # 作业成功结束后
```

## 105530 指令、地址与独立周期预测

`qwen_native_control.py` 解码 `LBCISA01` 母控 V3 和驻留局控 V2，执行静态 CALL、WAIT、指针递增和循环。四个目标的服务签名与冻结 RTL 路由核对。描述符、KV、投影、FFN、Attention 和输入读均从冻结部署恢复。第 5 页是 64 组 P0/P1/P2 并发调用，每组 WAIT 等三个目标退休，组内完成顺序由实际服务决定。

| 指标 | 每种模式 |
| --- | ---: |
| 母控页／服务调用 | 8／393 |
| 普通 DDR 读地址（含控制、描述符和服务） | 1,318,877 |
| 独立 FFN 激活读／DDR 写 | 128／736 |
| 首行 prompt、嵌入、gamma 与首次 LC/MC 镜像的逐时标 DDR 读 | 267 笔／1,068 个事件 |

全窗读地址比较保留地址的重复次数。写回另比较地址与 tag，FFN 激活另核对同地址写返回先于读接收。控制比较保留 CALL/WAIT 依赖和局控目标。周期模型覆盖首行输入、两个串行 SRAM 载入、RMS 数据范围扫描、因子与归一化计算、控制器启动及首次 LC/MC 装载。启动用探针确认的 prompt 握手边沿 2，握手到首笔读的两拍按测试台固定；额外一拍的门控原因待定位。随后的时间从 RTL 状态机、资源规则和实时 DRAMsim3 回包推导。两种模式首个 LC 读均为 pre-edge 33369、DDR tick 529666。首个 MC 读分别为 pre-edge 33825／33835，模型复现了两种模式的背压与刷新差异。整窗权重调度、并发服务和后续 DMA 周期仍待独立预测。

`instrument_qwen_105530.py` 在冻结源码上增加被动探针，统一记录页启动/提交、程序和描述符请求、服务接收/退休，以及第 0 层残差提交到第 1 层 RMS 退休。探针使用 10 ns RTL 时钟。探针 `cycle` 从 1 开始，DDR `admit`/`return` 的核时钟计数使用 `cycle - 1`；DDR 的接受与回调按 630 ps tick。原生输入及产物散列、边界结果和恢复命令见 [105530 预测与探针回执](../../../work/Melodydt/265/qwen-105530-cycle-receipt.json)。

| RTL 模式 | Layer 0 残差提交 | Layer 1 RMS 退休 | 同域间隔 |
| --- | ---: | ---: | ---: |
| 0 | 1,759,875 | 1,792,258 | 32,383 拍（323.83 µs） |
| 1 | 1,891,889 | 1,924,242 | 32,353 拍（323.53 µs） |

两种原生模式均通过原有断言。后处理 108208 校验了 54 份冻结生成物、8 份 DDR/KV 产物和两组探针回执。两组各 1,652 条探针事件；其中 58 次 PM 和 786 次描述符发起及 393 次服务接收和退休与解码的目标及 WAIT 依赖一致。跨层间隔为 RTL 观测值，供扩展周期模型后对账。

```bash
python -B project/experiments/instruction_cycle/qwen_native_control.py "$ARCHIVE" --compare --read-traces
python -B project/experiments/instruction_cycle/qwen_native_control.py "$ARCHIVE" \
    --edge-log "$PROBE/edges-0.log" --edge-log "$PROBE/edges-1.log"
```

## 105530 首个指令页与首笔 Q 投影权重

`qwen_page_cycle.py` 在连续的两路 DRAMsim3 状态上继续推导母控程序读回及 CRC、PROVE/PREPARE、CALL 链路、局控描述符 DMA 和两次 DRL1。DRL1 建模 8 笔 DDR 读、32 笔窄口写及 SRAM 请求和 ACK 背压。两次 DRL1 完成后，首个 Q `P_SCOPE` 根据实际描述符推导激活窗口扫描、量化打包、Header 及权重上下文建立，然后经 typed DMA 的 slot、credit、注册 offer、lane FIFO 和回包 skid 处理首个 17 拍权重记录。

Slurm 108366 两种模式各与冻结 RTL 匹配 306 笔 DDR 读的 1,224 个事件和 11 个控制标记。DDR 逐事件比较 lane、tag、物理地址、接受与返回的核时钟边沿，以及 DRAMsim3 接收与回调的 DDR tick。模式 1 覆盖同拍双 lane 接受及双 lane 回包。首笔 Q 权重从物理地址 5,017,600 起，共 1,088 B。表中用 DDR 桥的零基核时钟 pre-edge。权重源端 offer 和 M 末拍接收为模型输出，RTL 探针直接核对其中的物理 DMA 边沿。

| 边沿 | 模式 0 | 模式 1 |
| --- | ---: | ---: |
| 第一条 DRL1 退休 | 34704 | 34777 |
| 第二条 DRL1 退休 | 35059 | 35184 |
| Q P_SCOPE 接受 | 35264 | 35390 |
| 首拍权重源端 offer | 35542 | 35700 |
| 首拍物理接受 | 35544 | 35702 |
| 末拍物理返回 | 35564 | 35720 |
| M 末拍接收 | 35565 | 35723 |

两种模式另各核对 123 次 WAIT 接续、246 个后续描述符接收边沿及最终页提交。此项的输入是冻结 RTL 中的服务退休边沿，整页独立周期仍依赖后续服务模型。测试台提供首个 prompt 握手和固定的两拍首读间隔；首笔权重后的多记录竞争、A COPY/LOAD 与 EXEC 重叠、服务退休、跨层及完整上下文 105572 留出验证待完成。

复跑时在本人全新任务目录放置 [108366 回执](../../../work/Melodydt/265/qwen-105530-first-page-108366.json) 中 `source_sha256` 所列文件。将回执的 `source_commit` 写入 `git-commit.txt`，按回执复核散列。两种模式先完成独立预测并封存散列，再读取冻结 RTL 进行比较。

```bash
sha256sum *.py dramsim_bridge.cpp run_qwen_page_cycle.sbatch git-commit.txt > source.sha256
bash -n run_qwen_page_cycle.sbatch
sbatch --parsable run_qwen_page_cycle.sbatch \
    /public/home/yuzelu/Melodydt/runs/issue-265/qwen-edge-verify-20261113-01 --with-first-weight
# 作业完成后，在运行目录核对预测、对照及环境清单
sha256sum -c output.sha256
cat comparison-{0,1}.json
```

## 107361 整机对照与 105530 第二条 Q 权重

107361 的 [对照回执](../../../work/Melodydt/265/qwen-tlm-decode-107361.json) 固定 TLM 参考及归档 SHA-256。第二步 291 页的耗时逐页求和为 1,045.096187442 ms，与两个 token 退休时刻之差一致。Attention 708.546 ms（67.8%），FFN 147.380 ms（14.1%），词表投影 105.866 ms（10.1%）。这些百分比按各阶段页的完整墙钟计时分组，DDR 在途及 SRAM 等待等可重叠计数未再次累加。107361 的 Attention 为串行单拍 KV 读。部署、KV、时钟与退休窗口的匹配要求见[决策记录](../../../docs/decisions/0265-instruction-driven-cycle-estimation.md#2026-11-14-短程整机对照)。

105530 的第一对 Q 权重使用两个新 W 上下文。第二条在第一条 ALLOC 确认后即可接收并推进控制，复用上条权重传输结束后的 DMA slot 序号、轮询位置和两路 DRAMsim3 状态。在模式 0／1，第二条首拍物理接受为 35573／35731，末拍物理返回为 35593／35749，均用 DDR 桥零基核时钟 pre-edge。两种模式各匹配 323 笔读、1,292 个 DDR 事件及 11 个控制标记。两条记录的物理 DMA 窗口无重叠，下一条需要建模 A COPY/LOAD、两个 W bank 的就绪及 M EXEC 的依赖。

按上节准备同名源文件，用 [108930 回执](../../../work/Melodydt/265/qwen-105530-two-weights-108930.json) 的 commit 和散列替换旧值。在新的本人运行目录使用 `sbatch --parsable run_qwen_page_cycle.sbatch <108208 探针目录> --with-two-weights`，再核对 `sha256sum -c output.sha256` 和 `comparison-{0,1}.json`。

## 105530 首对 Q EXEC 与第三条权重

`qwen_projection_pair.py` 将量化打包后的同 P COPY、A LOAD、两个 W bank 的 FILL 回复、两条 EXEC 及第三条权重发起接到同一时间轴。COPY 从 P SRAM scratch 1008–1023 读出并写到 880–895，A LOAD 只在相应 COPY 写确认之后可读。模型核对 SRAM 两个 owner 槽、轮询和请求／回包门控。首条 EXEC 的 INPUT EOP 释放发起路径，第二条可继续准备，M 等上一条占用的 RF 路径释放后才接受第二条。同一 P 的第三条权重从地址 5,052,416 发往 DDR 通道 1。

| 关键边沿（零基 pre-edge） | 模式 0 | 模式 1 |
| --- | ---: | ---: |
| COPY末次 ACK | 35646 | 35858 |
| A LOAD proof | 35652 | 35866 |
| 第一条 M EXEC 接收 | 35659 | 35873 |
| 第二条 M EXEC 接收 | 35677 | 35891 |
| 第二条 EXEC 完成并交给范围迭代器 | 35696 | 35910 |
| 第三条权重源端接收 | 35723 | 35937 |
| 第三条权重 DDR 首拍接收 | 35725 | 35939 |
| 第三条权重 DDR 末拍返回 | 35745 | 35957 |

110583 用实时 DRAMsim3 每种模式独立预测并对齐 340 笔 DDR 读的 1,360 个事件及 11 个控制标记。整页 WAIT 仍以冻结 RTL 服务退休为输入。内部探针单独复跑同一个冻结输入，在第三条权重源端接收结束，110601 每种模式核对 1,292 个原始 DDR 前缀事件和 114 个内部边沿，COPY/A LOAD 地址、两条执行序号与 W 通道身份均核对通过。模型适用范围为第一对 K0 EXEC 及第三条权重传输，后续记录重叠、下一 K 窗和完整 Q 服务退休待建模。

```bash
# 独立预测，在本人新运行目录按回执核对源码和环境
sbatch --parsable run_qwen_page_cycle.sbatch <108208-探针目录> --with-three-weights
# 片上握手探针，在另一个新运行目录使用已封存的预测
sbatch --parsable --job-name=zny-qwenpair run_qwen_105530_markers.sbatch --pair <110583-预测目录>
```

[源码、作业、日志和校验回执](../../../work/Melodydt/265/qwen-105530-projection-pair-110583.json)

[PR #260 的 108308 对照](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/3584920d4e79ee45922be95df27e5193523d6313/work/YUZE-LU/234/native-sram-width/evidence/comparison-108308.json)另提供同样 8-beat KV 窗口和 3,334 ps 核周期的两组短程 TLM 结果。128-bit SRAM 为 1.20653 tok/s，512-bit 为 2.09091 tok/s。对照只在匹配配置下使用。107361 仍是单拍 KV 配置的参考。两组宽度的时序及吞吐仍需硬件校准和正式 P512/D128 验收。

## Qwen2.5-3B 整机 Decode 速度估算

使用 [107361 的 128-bit SRAM 和串行 KV 对照](../../../work/Melodydt/265/qwen-tlm-decode-107361.json)，读取冻结几何及第一页到末页的调度回执。估算仅从首步取得校准参数，第二步仅用于验证。

| 口径 | 数值 |
| --- | ---: |
| 127 个 Decode 间隔估算 | 143.489733463362 s |
| D128 缓存 Decode 吞吐估计 | **0.8850807437 tok/s** |
| 第二步预测 / 参考吞吐 | 0.9573886793 / 0.9568497254 tok/s |
| 第二步吞吐相对差 | +0.05633% |
| 127 间隔的资源上界 | 1.3317315170 tok/s |

```bash
# 用本人的新运行目录完成封存几何核验
sbatch --parsable run_qwen_request_geometry.sbatch
python -B estimate_qwen_decode.py <geometry.json> <107361-page-timing.jsonl>
# 完整两步 TLM 先在同节点逐字段核对九页，再检查两步全部退休和时间线
sbatch --parsable run_qwen_fast_tlm.sbatch
```

`run_qwen_page_cycle.sbatch` 的 `--through-k0`、`--through-k1`、`--through-q`、`--through-first-kv-store` 逐级验证权重记录重叠、M/COPY/A SRAM、投影退休、偏置与严格 DDR KV 提交。110720 两种模式各匹配 4,655 笔读、8 笔写的全部 18,652 个事件和 24 个控制标记。留出 105572 先锁定预测散列，模式 0 全部匹配，模式 1 首条权重物理接收预测晚五拍。留出只覆盖首个 K0，按真实定长请求保持并修复量化阻塞后，诊断两种模式均对齐；原始留出失败仍保留。详细边界和所有 Slurm 路径见[评估回执](../../../work/Melodydt/265/qwen-decode-evaluation-107361.json)。

`--through-qkv-page` 独立完成首个 QKV 页的 124 个服务及页提交。110962 每种模式匹配 492,620 读事件、384 严格写事件和 497 控制标记。覆盖底座对下一历史行的 embedding/RMS 补载、挂起描述符、跨调用 SRAM 驻留、投影 bank 复用和 RoPE。用 `--through-attention-page` 继续同一 DDR 状态，111002 覆盖第二页全部 16 组 ATT1/DWS1，两页每种模式累计匹配 500,572 读事件、896 写事件、631 控制标记。页提交 pre-edge 590747／643095。105572 后续扩展诊断到首个完整 Q 退休引导的下一描述符，两种模式各匹配 18,572 事件；该扩展的预测在读取超出原 K0 的时序前封存。

110666 在 c64/node10 使用单核完成同配置两步 TLM，582 页及 DDR 汇总逐字段对齐，读取 126,860,392 次、写入 48,384 次、回调 126,908,776 次，第二步复用前一步写入的 1,152 个 KV beat。两次退休 (20772, 1,043,184,915,264 ps) 和 (279, 2,088,281,102,706 ps)，间隔为 1,045.096187442 ms。Slurm 墙钟 01:30:11，启用 DDR 批推进。110666 在两步退休后因释放 DDR 后读取计数退出 1:0。111176 修复并核对真实双通道关闭，从原始轨迹复算汇总并逐字段对齐两份 JSON，六份 DRAMsim3 原件也逐字节相同。原作业的失败和恢复作业分别登记。九页同机对照为原版 170 s、DDR 批推进 70 s、DDR 批推进与原生整数运算 60 s。原生整数运算的完整两步适用性待验证。

`--through-residual-page` 在 111058 连续匹配四个完整页。`--through-ffn-ingress` 在 111111 进一步核验 FFN 激活搬运及三 P 首批描述符和接受。每种模式累计 781,100 条普通 DDR 读事件、512 条独立 FFN 激活读事件、2,432 条严格 DDR 写事件和 833 个控制标记。FFN 权重并发、执行退休和后续页仍待完成独立周期核对。

128-bit 串行单拍 KV 配置下，Attention 占 107361 第二步 67.8% 的页用时。127 间隔估算固定首步非 Attention 时间，Attention 随实际 descriptor 展开的串行 DDR beat 和 ACKed SRAM 字数量缩放。在两个校准分量均施加 ±5% 假设扰动时，阶段吞吐为 0.84293–0.93166 tok/s。需要 C576/C639 的同配置独立完整退休记录确认长上下文误差。完整 P512/D128 联合运行及数值验收由 [#234](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/234) 跟踪。

## 多位宽 Qwen2.5-3B Decode 快评

[快评指南](QWEN_DECODE_GUIDE.md)列出固定硬件条件、派生分支和复跑步骤。

八笔 KV 窗口的非流水配置使用 `estimate_qwen_sram.py`，可传入 128、256、512-bit。只用 107947 第一步校准，估算输入还包括封存的部署目录。二进制描述符、母控页及局控镜像表决定端口请求和 ACK 节拍，按配置分别估计各阶段。FFN 使用三 P 每个 WAIT 的最长并发链，加 Mid 汇集和搬运。未随位宽重算的 DDR 服务时间由对照误差约束。

```bash
python -B estimate_qwen_sram.py predict DEPLOYMENT TRACE_107947 --sram-bits 128 256 512 --through-step 2 > prediction.json
python -B estimate_qwen_sram.py compare prediction.json TRACE_108284 --sram-bits 512
# 完整 256-bit 独立参考，核对执行配置和实际退休边沿
python -B estimate_qwen_sram.py compare prediction.json TRACE_256 --sram-bits 256 --execution EXECUTION_JSON_256
```

`run_qwen_sram_estimate.sbatch` 在完整封存目录估算 127 个间隔。`run_qwen_sram_256.sbatch` 在独立工作目录生成 256-bit 匹配 TLM 参考。原单拍 KV 模型的输入和误差记录见上节。流水配置使用对应 TLM 回放，快评未建模其分片重叠规则。见[结果及恢复入口](../../../docs/handoffs/2026-11-14-issue-265-qwen-sram-width-model.md)。
