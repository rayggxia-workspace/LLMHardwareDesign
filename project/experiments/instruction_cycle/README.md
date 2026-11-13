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

如需在 Slurm 复跑，在 Melodydt 自己的全新目录放置冻结的 `source.tar`、`probe_a2.py` 和 `run_a2_probe.sbatch`，按回执核验 `source.tar`，生成 `sha256sum probe_a2.py run_a2_probe.sbatch > probe.sha256`，执行 `bash -n run_a2_probe.sbatch` 后运行 `sbatch --parsable --chdir="$PWD" run_a2_probe.sbatch`。后续从双 U_64 的实际 MC/LC 与跨块事务开始，将 A2 独占服务的规则扩展到并发资源占用。
