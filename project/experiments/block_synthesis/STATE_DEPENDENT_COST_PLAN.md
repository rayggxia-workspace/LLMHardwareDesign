# Algo1 基于芯片当前状态的候选代价方案

关联 [#219](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/219) 和 [#257](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/257)。本文是实施方案。基准是 #257 的 461f533 和同一候选池下的严格贪心／DP。已有实现与证据见[事件前沿](EVENT_FRONTIER.md)。

## 实施检查点

在原有 `run.py --event-ir` 入口的硬件 JSON 中设置 `event_model.timing = "replay"` 启用重放。默认保留 `"calendar"` 用于旧代价对照。重放按各阶段声明的整数优先级、已就绪时刻、操作序号排序。已取得的授权持续到阶段结束，跨阶段的信用及命令槽持续到最终确认。新候选只能改变尚未发生的授权。

| 轮次 | 实现和对抗检查 |
| --- | --- |
| 1 | 加入共享资源的逐事件推进。高优先级新请求把旧 ACK 从 7 推到 10，后续信用也要等到 10。迟到请求不能抢占已经开始的阶段。交叉持槽导致无进展时报告死锁。80 个随机单阶段 DAG 与独立逐拍参考对账。 |
| 2 | 接入贪心和 DP 的每次扩展。按数据读写和任务依赖重建整个分支的预测，更新旧任务、后继和总代价。固定 32 B 读量的例子中，旧动作从 7 变为 11，消费者从 8 变为 12，整份计划从 18 变为 14。 |
| 3 | 从新操作最早可就绪拍之前的事件重建运行、待仲裁和持有资源。保留边界前已开始的阶段，重算边界拍的授予。120 个随机多阶段图逐步追加共 1,920 次，与每次从初态重放逐事件一致。 |
| 4 | 独立时间线检查授予顺序和释放。把容量合法的静态轨迹重新标记为重放轨迹时，检查器拒绝第 1 拍错误授予。固定候选池交叉测试两套代价和两种搜索，静态贪心选 16 拍，重放贪心和 DP 均选 14 拍。 |
| 5 | 支持声明计算、写回等原生阶段的资源和跨阶段命令槽。合成例中计算在 0–4 拍，写回在 8–9 拍，后继第 9 拍可读。整段同时占计算与写口的模型在第 13 拍才可读。提前写回的篡改轨迹被拒绝。 |
| 6 | 同一绑定的本地源、COPY 和 DDR STORE／LOAD 备选分别进入重放，包含活数据写回。合成对照中日历选 COPY 15 拍，重放选 DDR 14 拍。预算为 1 时复现旧选路并报告截断。快速 STORE 与 LOAD 连线冲突时保留合法的慢 STORE 路径。重放骨架保留并核对原选路。 |
| 7 | 从 #251 冻结 DMA RTL 合同加入通道滑动发放上限。合成饱和对照中，两条 lane 在第 0、1 拍各发两笔，第 2 拍虽空闲仍须等到第 3 拍。另一通道可在第 2 拍发放。检查点恢复保留已经完成但仍落在窗口内的发放。独立检查器拒绝超发轨迹。 |
| 8 | 重新读取 #251 的 102603、102604 冻结 RTL 回执，按 SHA-256 及固定 Git blob 核对来源。以原始 bank 日志重建物理字地址，逐个验证 K128 COPY 的三份目的区间。负对照保持写入总量但改成重复地址，或把 ACK 提到写入前，均被拒绝。 |
| 9 | 将 SRAM 输入捕获、输出写入、可见确认和命令退休拆成不同的依赖边。旧读者持有窗口至第 12 拍，新计算可在第 0–4 拍执行，再于第 12–14 拍写入，第 15 拍发布，第 23 拍释放槽位。独立检查器拒绝提前覆盖和提前读取。活数据外存保存与计算重叠时，16 B 写回保留，整份计划从 14 拍缩至 10 拍。 |
| 10 | 重新运行 #251 的四 bank SRAM RTL。8 个条件共 86 次请求／应答握手逐拍一致。新增宽读推迟旧窄写；双通道应答阻塞时，槽满的一侧会让另一侧推进，应答出队当拍即可复用槽。将复用推迟一拍的篡改轨迹被拒绝。两种读取同一份 64 B 数据的候选在反压下实际排序反转。 |
| 11 | 对 #251 typed DMA 的两通道分别推进寄存后的 lane 归属、上一拍发放数和轮询指针。18 次 RTL 运行逐拍核对 117,150 个通道采样、99,720 次真实 DDR 握手。已有 VALID 但未握手的请求占用发放额度，897 个通道拍因此少补发请求。提前一拍补发的篡改轨迹被拒绝。 |
| 12 | 将 #251 普通读 fabric 接入 DP 的 LOAD 重放，按地址生成 64 B beat，维护每通道 32 个预留 beat、32 个描述符、2 个发放 lane 和 3 个回传槽，并保留客户端回传锁。7 次 RTL 对照核对 267 个 beat 的预留、VALID、发放、接收和交付。新增请求推迟旧预留，交换客户端反压使同 128 B 候选的代价从 24／13 拍翻为 13／24 拍。地址或捕获拍被篡改时，计划检查器拒绝。 |
| 13 | 接入 #251 FFN 仿真后端的四条独立 lane，每条 FIFO 深度 16，两个通道分别在发放后第 7／8 拍可返回，按原规则叠加周期性反压。9 次 RTL 对照逐拍核对 2,728 个 beat 与 FIFO 满载拍数。允许候选从不同地址读取同一份已预置权重。旧请求的通道改变后，主副本与另一副本的排序反转。 |
| 14 | 本机重新编译并运行 #251 完整 11,008 列 FFN，采集真实 MC／LC 控制握手。4 组共 768 次调用和 1,536 个描述符 beat，重放逐拍对齐 CALL 到请求、DMA 预留与返回、CRC 后的服务 VALID，以及 DONE 后的共享回传仲裁。去掉 CRC 或终端帧的一个周期、改动描述符地址均被拒绝。 |

重放对每个绑定默认试算至多 32 组搬运组合，可通过硬件 JSON 的 `event_model.transport_limit` 调整，`null` 取消该上限。输出记录尝试数和发生截断的绑定扩展数。固定日历的预测只用于枚举顺序，完整后继由重放评分。

原生服务通过 `window_phases.read`、`write`、`publish` 指定阶段名。读取占用以 `read` 阶段结束为边界，覆盖必须等到旧读取和活数据写回确认。延后写入须用 `window_phases.result_hold` 引用已声明的 `hold_claims`，以约束计算结果暂存。数据可在 `publish` 结束时供后继读取，命令槽保留到退休。未声明的窗口沿用整段服务的边界；任务显式 `after` 和同绑定的串行服务仍等待退休，输入搬运仍须在服务起点前确认。

`event_model.issue_rates` 在重放模式用于抽象端口的滑动发放上限。对 #251 逐 beat 读路由，在硬件清单的 `event_model.typed_dma` 配置 `addresses`（片段 ID 到 DDR 物理字节地址）、`return_latency`（两个通道的返回延迟）、可选的 `ddr_ready` 与 `client_ready`（按拍列出半开区间及 READY 掩码）。在 phased DDR LOAD 路由上声明 `typed_dma.client`、`typed_dma.record_beats`。每条记录以基地址位 11 决定通道；范围必须是完整的 2 beat 激活记录或 17／18 beat 权重记录。一个客户端按候选发起顺序提交完整记录。通用日历的路由吞吐仍用于草拟；重放从实际客户端回传结束和目的写 ACK 得到可读拍。

逐 beat 读分支当前从初态重放，确保新增请求与旧请求一起推进，避免从旧轨迹恢复已过时的在途状态。选用 `typed_dma.ffn_provider` 时，填写 `mode`、`seed` 和可选的 `cycle_offset`，由 FFN provider 产生 DDR READY 和返回。读路由可用 `typed_dma.replica` 从 `addresses[片段]` 的具名地址中选择一份预置副本，未指定时查 `primary`。副本各自占用 DDR 容量，并检查物理区间互斥。DDR bank／行、读写切换、原生写路径和跨 token 的持续状态仍待补齐。普通读合同涵盖合法记录流，运行时模式切换、异常和长序号回卷的 flush 尚待接入。

固定轨迹回归入口为 `python -B project/experiments/block_synthesis/benchmark_event_ffn.py ARCHIVE --job 102603 --timing replay`。默认从 #251 固定提交读核对清单，也可通过 `--fixture FILE` 使用相同 Git blob 的本地副本。COPY 时序来自原轨迹，DDR 逐 beat 时序仍缺记录。源包和回执的来源见 [#251 冻结索引](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/work/YUZE-LU/250/native-services/ffnnative/index.json)。

Windows Python 3.12.4 全套 339 项通过。两份原始回执取 seed 25001、两种压力、三种 SRAM 初态，各用日历／重放和贪心／DP 验证。每个原始条件核对 1,444 段 COPY 和 69,312 次真实 P.S 字写入。最后一次写入到 COPY 确认，无额外压力时为 5 拍，有压力时为 5–9 拍。固定请求序列的四组总拍数仍为 849914、941907、860202、948626。24 条运行回执（包含编译耗时）SHA-256 为 `6e0697e0a463d918a44db8476989071ddf4dc68ad62a5cac0d78724e870122c0`，本机 Codex 证据目录文件 `round8-ffn-bank-24-cases.jsonl`。本次核对已归档仿真，未重新运行 RTL。

第 9–10 轮 Windows 全套 343 项通过。阶段依赖加入 120 个随机多阶段图，逐次追加的 1,920 份轨迹与从初态重放一致。第 9 轮修改后，#251 冻结 FFN 的 12 个条件在重放模式重新核对，贪心和 DP 都保持上述四组总拍数。回执 `round9-ffn-replay-12-cases.jsonl` 的 SHA-256 为 `00977b765210dfe76b4df1cd480a7e02a543d8a7a4d8ced15aad750688c15ad3`。

### 原生 SRAM 候选对照

第 10 轮用 WSL Ubuntu 22.04 的 Icarus Verilog 11.0 运行实际 feeder 与四个 256×128 bank 行为模型。`102603-source.tar.gz` 的 SHA-256 为 `058b32a84fbb7b3613dcf9fa6ab5fb74685d08a740ba417f569bedf6968d1d24`。从中提取 `block_feed_s16k_sram.sv`，SHA-256 为 `a1ba89671305fd76f99e1b0c2a6fdadcbc73c783a0383c2b9640b496577317ef`。bank 文件 `s_sram_256x128_freepdk45.v` 按同一源包的 `source/bank.sha256` 核对，SHA-256 为 `6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7`。

```bash
dir=/path/to/evidence
iverilog -g2012 -s native_sram_replay_tb -o "$dir/native-sram-replay.vvp" \
  project/experiments/block_synthesis/native_sram_replay_tb.sv \
  "$dir/block_feed_s16k_sram.sv" "$dir/s_sram_256x128_freepdk45.v"
for mode in 0 1 2 3 4 5 6 7; do
  vvp "$dir/native-sram-replay.vvp" "+mode=$mode" > "$dir/native-sram-mode-$mode.log" || exit 1
done
python -B project/experiments/block_synthesis/benchmark_native_sram_replay.py "$dir"
```

探针通过实际窄写初始化四个 bank，检查宽读和逐 bank 窄读返回相同的四个 128 位字。旧请求在每组对照中均为三笔窄写。重放比较每笔接纳和应答的采样拍，同时检查追加候选的恢复重放与从初态重放完全一致。

| 宽读应答条件 | 一次宽读，整份计划完成拍 | 四次窄读，整份计划完成拍 | 选择 |
| --- | ---: | ---: | --- |
| 始终可接收 | 5 | 8 | 宽读 |
| 从第 9 拍可接收 | 9 | 8 | 窄读 |

追加宽读时旧窄写的第一次接纳从第 0 拍移到第 1 拍，最后一次应答从第 4 拍移到第 5 拍。原始日志保存在本机 Codex 证据目录，`round10-native-sram-logs.sha256` 的 SHA-256 为 `f0b08712701751dcb5e012b83823cb0f785f652e436d5b30da13d41b82b5334c`，汇总 `round10-native-sram-check.json` 的 SHA-256 为 `33942b1cbe1bcbe5d4505eb2674c184c5b90ba2a2be3b8c6a081d12d99751780`。探针直接校准重放内核的仲裁与容量。将这一组物理请求接入 FFN 的候选生成、覆盖局控退休和 SRAM 时序分析仍待完成。

### 原生 DMA 寄存请求对照

本机用 Verilator 4.038 重跑了 #251 原 typed DMA 测试。6 个种子、3 个初始化参数均通过，每组 5,541 次源接纳、5,540 次真实 DDR 接纳及客户端返回、1 次预留取消。`mc_dma_fabric_typed_p.sv` SHA-256 为 `74c68493d5bd1f0c1310eab9d7c634384e8871f8a0d91b0ac4dc0dc0907b9b70`，`typed.cpp` SHA-256 为 `2d10af60a005c331e2a24f0b2d38a443515227aac23ba9f3762ed398837434bc`，本机基线日志索引 `native-dma-18-logs.sha256` 的 SHA-256 为 `9a4d82c5c69e9d943f9475553a4d9b31a1a77675d6ce13669eb73c81e27d5fa1`。

第 11 轮只在本地测试驱动插入采样。输入取 RTL 的已预留 beat 位图（排除当拍成功取消）和 DDR READY。输出从端口 VALID 和 tag 取物理槽位，并与原 `ISSUE` 记录互核。`DmaOfferChannel` 从复位推进 lane 归属、上一拍发放数和轮询指针。共观察到 27,387 个 lane 拍保持 VALID 等待。种子 1、初始参数 0 时，第 14 拍通道 0 的一条 lane 已握手，另一条保持。上一拍两次握手、本拍一次握手和一个保持请求用尽 4 份额度，所以第 15 拍第一条 lane 仍无 VALID，第 16 拍才补上新请求。将第 15 拍改成有新请求，检查器报告该拍槽位不符。

```bash
dir=/path/to/evidence
python -B project/experiments/block_synthesis/benchmark_native_dma_offer.py instrument \
  "$dir/typed.cpp" "$dir/typed-offer-probe.cpp"
verilator --cc --exe --build --assert -Wno-fatal --x-initial unique --x-assign unique \
  --top-module mc_dma_fabric_typed_p --Mdir "$dir/dma-build" \
  "$dir/mc_dma_fabric_typed_p.sv" "$dir/typed-offer-probe.cpp"
for initial in 0 1 2; do
  for seed in 1 2 3 4 5 6; do
    "$dir/dma-build/Vmc_dma_fabric_typed_p" "$seed" "$initial" \
      "$dir/typed-dma-offer-$seed-$initial.csv" || exit 1
  done
done
python -B project/experiments/block_synthesis/benchmark_native_dma_offer.py check "$dir"/typed-dma-offer-*.csv
```

采样驱动 SHA-256 为 `4a54fab85e159fb4bb8794e42b92467448731fc22dc953394d93ad7c72044620`。本机日志索引 `round11-native-dma-offer-logs.sha256` 的 SHA-256 为 `b0abbe3c0b95160070f26155667b6fae4d950022ad0f0dd40b592437b044e6d3`，汇总 `round11-native-dma-offer-check.json` 的 SHA-256 为 `427e9455a135a9506193a4185f7badac91bc9a42afb6631fbe2a7f73c36e00b5`。Windows 全套 344 项测试通过。这个对照验证预留到发放的子模型，DDR 的 READY 和源端预留目前由 RTL 探针提供。

### 原生 DMA 读候选对照

第 12 轮用同一份 #251 RTL 和 Verilator 4.038，驱动两个通道及全部 12 个客户端。探针用地址生成每个 64 B 响应并检查客户端收到的完整数据。重放对每个 beat 记录物理地址、通道、beat 槽以及五个事件拍。重压组包含 233 个 beat，最长待 DDR 握手为 57 拍，回传槽内最长等待为 45 拍。加入第三个客户端后，旧客户端 8 的第一笔预留从第 1 拍移到第 2 拍。用相同数据和两个替代客户端比较，改变哪个客户端受反压后，宽度 1 和 8 都选择原生 RTL 对照更快的路径。

```bash
dir=/path/to/evidence
python -B project/experiments/block_synthesis/benchmark_native_dma_read.py prepare "$dir/cases"
verilator --cc --exe --build --assert -Wno-fatal --top-module mc_dma_fabric_typed_p \
  --Mdir "$dir/read-build" "$dir/mc_dma_fabric_typed_p.sv" \
  "$PWD/project/experiments/block_synthesis/native_dma_read_probe.cpp"
for stimulus in "$dir"/cases/*.stim; do
  "$dir/read-build/Vmc_dma_fabric_typed_p" "$stimulus" > "${stimulus%.stim}.csv" || exit 1
done
python -B project/experiments/block_synthesis/benchmark_native_dma_read.py check "$dir/cases"
```

本机证据目录 `round12-dma-read` 下 `receipts.sha256` 的 SHA-256 为 `21944ef720c826aecd40a788acae6825e346483c5d0828e8a0bbc178a2efd5d9`，`verified.json` 为 `91840a49e872895ce6266065cc2a69fca9c731b022a34fe5061d5bc21a92ea6a`。Windows 全套 346 项测试通过。实际 `run.py --event-ir --event-width 8` 输入 3 个读任务，完成于 13 拍，384 B，计划核对通过。冻结 FFN 102604 的压力条件、初态 2 仍复现 948626 拍，使用其原固定轨迹合同。原生读探针校准 DMA fabric，DDR 服务由探针驱动；Qwen FFN 的动态逐 beat 合同仍需连接其有限 DDR 后端和局控。

### FFN 有限 DDR 队列与权重副本

第 13 轮从固定源包提取 `test_ffn_three_p_native.sv` 的 `finite_backend_lane` 和同版 DMA fabric，在 WSL Verilator 4.038 原样执行队列、READY／VALID 和返回延迟。探针仅替换响应数据的来源，用地址模式校验所有回传字。FIFO 满时依据时钟沿之前的占用，即使同拍发生返回也要等到下一拍才可发放。发放和回传必须走同一物理 lane，计划检查器拒绝更改回传 lane。

| 对照 | 普通布局 | Up 基址加 2,048 B |
| --- | ---: | ---: |
| 36,864 B，mode 0 | 380 拍 | 312 拍 |
| 36,864 B，mode 1 | 370 拍 | 312 拍 |

独立重压组中，lane 0 满 44 拍。去掉队列上限后，地址 320 的发放被错算为第 25 拍，实际到第 69 拍才握手，检查器因此拒绝。另对一个 1,088 B 权重记录预置两份互不重叠的真实地址。旧请求用通道 0 时，主副本 38 拍、另一副本 31 拍。旧请求改到通道 1 后，主副本 31 拍、另一副本 39 拍。两种搜索宽度均选择 RTL 对照更快的地址。

```bash
dir=/path/to/evidence
python -B project/experiments/block_synthesis/benchmark_ffn_dma_provider.py prepare "$dir/cases" \
  --archive "$dir/102603-source.tar.gz"
verilator --cc --exe --build --assert -Wno-fatal --top-module ffn_dma_read_probe \
  -CFLAGS -DNATIVE_FFN_BACKEND --Mdir "$dir/provider-build" \
  "$dir/cases/ffn_dma_read_probe.sv" "$dir/cases/mc_dma_fabric_typed_p.sv" \
  "$PWD/project/experiments/block_synthesis/native_dma_read_probe.cpp"
for stimulus in "$dir"/cases/*.stim; do
  "$dir/provider-build/Vffn_dma_read_probe" "$stimulus" > "${stimulus%.stim}.csv" || exit 1
done
python -B project/experiments/block_synthesis/benchmark_ffn_dma_provider.py check "$dir/cases"
```

本机证据目录 `round13-ffn-provider-final` 下 `receipts.sha256` 的 SHA-256 为 `d75a302bf7f480d8a5e9727a3cf471610a794c662dd75cc066adeead89c67610`，`verified.json` 为 `e196e42bd4be6d3a2b34c8ff321710ad4761859c96e65e8becb9f6a5a8f3e40f`。Windows 全套 347 项通过。重新编译第 12 轮的 7 组原生探针，CSV 与原回执逐字节相同。该轮复现 FFN 使用的 DDR 仿真 provider。真实局控发起请求与计算交叠、完整 FFN 的动态重排仍待联调。

### 完整 FFN 的 MC／LC 控制时序

第 14 轮在 WSL Ubuntu 22.04 用 Verilator 5.006 重新编译 102603 固定源包及匹配的 SRAM bank，沿用原程序、Down、四 bank、共享 DMA 和早算配置。为兼容工具版本，编译省略了用于其他测试文件的 `native_mc_lint.vlt`。先复跑未插桩的 seed 25001、mode 0、初态 0，Gate/Up 586103 拍、Down 263811 拍。再插入只读握手监控，用相同的原生程序和数值断言跑两种 seed、各两种压力模式。四组 Gate/Up、Down、DMA 和程序计数均与同组归档逐项相同，每组 1,123,200 次 DDR 发放及返回、71,884,800 B 确认读取、96,256 B 确认写入。

- 从 CALL 帧最后一拍到描述符第一笔 VALID 固定 46 拍。共享 DMA 重放按物理地址、通道、READY 和返程容量核对两个 64 B 描述符请求与返回。最后一个 beat 到服务 VALID 为 126 拍，其中 CRC 逐字节扫描 124 拍。
- P 服务 DONE 后第 5 拍具备发回终端的条件。MC 共享收口按目标号仲裁，4 拍传帧，额外 1 拍周转。最晚一次 DONE 到终端末拍用 18 拍。
- 服务 VALID 到 P 接纳最长 6,759 拍。接纳需要局控已准备描述符、外层 Gate/Up 或 Down 发出对应任务且 P 节点就绪。当前控制对照从实际 CALL 帧和 P 的 DONE 进入两个重放区间。外层调用生成、服务接纳和原生计算完成仍需接入同一个动态计划。

```bash
python -B project/experiments/block_synthesis/benchmark_ffn_control_trace.py instrument \
  SOURCE/project/experiments/block_local_native/test_ffn_three_p_native.sv TRACE_TESTBENCH.sv
# 按冻结 job_ffn_native.sh 的完整源表和 102603 参数编译，以 TRACE_TESTBENCH.sv 替换原测试顶层。
# 用原 seed 回执的 X、scopes、Mid、Down、mother、local、LC_CRC 启动，增加 +TRACE_CONTROL。
python -B project/experiments/block_synthesis/benchmark_ffn_control_trace.py check TRACE_LOG --mode 1 --seed 25001
```

原始日志和本地复跑脚本位于本机证据目录。`round14-control-logs.sha256` 的 SHA-256 为 `a806fa42e28c35465d4c8fa78892b4be8af7b85f689037d5cb4d560da64edcbb`，`round14-control-verified.json` 为 `920584e61e8482ff987a1684ac909e05d2c4d844a9d8d720285b685e701e7799`。未插桩日志 `full-ffn-local-25001-0-0.log` 为 `7c94e6e5c79f858d6a25ecfd2a7c790bd8ff72a9bc1eabc8a3cb60896f4fdaf9`。

### 服务放行与输入搬运的重叠

第 15 轮沿用 102603 固定源包、程序、数据和四组运行条件。在原监控上增加 stripe 接收、Down 分组入口和 P 的 range／exec READY 位变化。四份日志除新增行外与第 14 轮逐行相同。检查器用描述符 DMA 重放的完成拍、采样的控制器入口和 READY 预测 768 次接纳边沿，全部逐拍一致。

- Gate/Up 在 stripe 被 gather 接收的下一拍允许各 P 独立开工。每组 174 次中有 171 次在服务 VALID 后等待控制器。两种压力模式下最大等待分别为 853 拍和 1,576–1,578 拍。
- Down 夹具在进入 Down 后多等一拍，此后按组同时要求三路描述符和三个 P 就绪。最大控制器等待分别为 4,350 拍和 6,719–6,759 拍。控制器允许后，较早准备好的描述符还可能等同组其他描述符，最长 33 拍。四组的 P READY 在相应放行点均满足条件。
- 重放模式的候选可在输入搬运期间准备描述符。仅当服务合同用 `window_phases.read` 指定稍后的读取阶段时，输入搬运 ACK 依赖才移到该阶段。阶段资源及全服务持有的命令槽仍逐拍计入。合成对照中，输入需 DDR 搬运时日历版选短准备候选、10 拍，重放版选长准备候选、7 拍。输入已驻留时重放版选短准备候选、5 拍。两种搜索宽度均通过独立核对，搬运 ACK 前抢读被拒绝。

```bash
# 按第 14 轮命令生成插桩源，运行时再增加 +TRACE_ADMISSION。
python -B project/experiments/block_synthesis/benchmark_ffn_control_trace.py check TRACE_LOG --mode 1 --seed 25001 --admission
```

人为偏移 Gate/Up 放行一拍、令 Down 一路跳过同组描述符等待，以及屏蔽 P 的 range READY 均触发核对失败。本机证据 `round15-admission-logs.sha256` 的 SHA-256 为 `1f2280d0d598fb34106d7f1c5ac0fc33ad5a373db6d14ca4282f39b7e6319388`，`round15-admission-verified.json` 为 `1078e3cf219c40f2973893a2ec269a6ee356e5d0f00dc810463a3d51b3665093`。Windows 348 项测试通过。102604 的压力模式和 SRAM 初态 2 在原固定轨迹合同下仍复现 948,626 拍。FFN 放行对照使用 RTL 采样的控制器入口及 P READY。跨 scope 的控制依赖、P 完成和 Down 同组放行仍需由候选重放内生生成，再比较完整原生候选的排序。

### 跨任务阶段依赖与 FFN 放行

第 16 轮在事件 IR 中增加 `event_after`。例如消费任务写入 `[{"task":"gate","from":[0,"publish"],"to":[0,"dispatch"]}]`，其第 0 个服务的 `dispatch` 只能在 `gate` 的第 0 个服务完成 `publish` 后发放。前沿先确定生产者的绑定，运行时允许消费者提前准备描述符，依赖拍随前驱重放更新。单阶段服务用 `stage` 指名。阶段边限重放模式，任务图保持有向无环。覆盖单个任务的替代动作可以导出同一阶段。涉及这些端点的多任务融合需要明确的内部阶段映射。

- 受控争用例中，高优先级请求占用共享资源后，前驱放行从第 4 拍移到第 8 拍，已选任务的接纳随之推迟。无争用时短准备候选用 7 拍。加入争用后严格贪心保留该候选，整份计划用 11 拍。宽度 8 的 DP 保留长准备候选，整份计划用 9 拍。独立检查拒绝前驱放行前一拍发放的篡改计划，也拒绝无阶段映射、无效阶段名和循环。
- 在 102603 的四组原生 RTL 上新增生产者握手探针。Gate/Up 的第一组由启动握手触发，此后由 scatter 或最后一个满足条件的 Mid 提交触发，经 3 拍走到可开工。首组 Down 由最后一个 Mid 读 ACK 触发，经 2 拍允许开工。后续 Down 组在上组 DONE 后一拍允许开工，且三路描述符全部可用时才同时接纳。按这些规则重建控制器放行，四组的入口和之前记录完全一致。
- 256 组隔离回放使用同一套候选 IR 及检查器，贪心和 DP 各核对 768 次接纳边沿。已完成的描述符时刻来自第 14 轮的共享 DMA 重放，前驱提交来自采样的 RTL 握手。四组的 P READY 在放行时都已满足。把关键 Mid 提交或最后的 Mid 读 ACK 移一拍、删去 Down 完成握手，都导致检查失败。尚需在一份完整候选计划里生成这些生产者完成拍，并用原生可重排候选核对排序。

```bash
# 复用第 15 轮插桩与运行参数，新插桩同时输出 RELEASE 握手。
python -B project/experiments/block_synthesis/benchmark_ffn_control_trace.py check TRACE_LOG --mode 1 --seed 25001 --phase-release
```

Verilator 5.006，102603 固定 RTL 和数据条件同第 15 轮。每份新日志去掉 `RELEASE` 行后均与对应原日志逐行一致。本机 `round16-phase-release-logs.sha256` 为 `173d07d087aec3a70121e735b33a490cb0fdf6e942753e83f53405df20e2eba7`，`round16-phase-release-verified.json` 为 `5344c789a05992b5f42ee9fb25a7f2ffc8cbe6fd9814b67da03551ea92801385`。Windows 349 项测试及 `run.py --event-ir` 的阶段依赖输入通过。102604 压力模式、SRAM 初态 2 的固定轨迹仍复现 948,626 拍。

### Gate/Up scatter 的物理字与 SRAM 反压

第 17 轮把 P 的本地结果到环形缓冲的 scatter 改为逐字重放。六个片段由条带宽度、P 号和 Gate/Up 方向派生。每个 16 B 字经历源 SRAM 请求和响应、P0 目的 SRAM 写入与 ACK。使用不同的请求／响应资源，保持单字在途和 scatter 服务占用到 stripe 提交。目的字地址按实际交错规则和 64 字环形取模生成。分支中的源与目的均以实际 S 地址登记。

- 事件阶段可用 `ready_window` 声明外部周期性 READY。在 FFN 夹具里，请求在 `(tick + 2*p) % 7 < 2` 时停发，响应在 `(tick + 3*p) % 11 < 4` 时停收。门打开、资源释放和新请求到达均可使等待阶段重新参与仲裁。独立检查在 READY 关闭时拒绝接纳，并检查开启后是否及时发放。加入优先写后，旧请求的合法发放从第 2 拍移到第 3 拍。随机逐拍参考和 1,920 次增量检查点对照覆盖周期门与容量、速率限制、跨阶段依赖的组合。
- 用 102603 的原生 RTL 重跑四组。每组 58 个条带、348 个片段、5,504 个物理字逐事件核对，四组共 88,064 次逐字握手。scatter 提交由预测写 ACK 及控制时序产生，再送入第 16 轮的控制放行对照。192 列条带在无压力时用 690 拍，有压力时用 1,052–1,059 拍。例子是同一第 2 条带，入口分别为 24,285 和 24,315，重放得到 1,055 和 1,058 拍，两者均与 RTL 一致。
- 篡改目的环形字地址、提前写 ACK、错用源响应 tag 都被拒绝。原 FFN 数值断言通过，四份日志去掉新探针行后与第 16 轮逐行一致。

```bash
# 复用第 16 轮插桩与运行参数，运行时再增加 +TRACE_SCATTER。
python -B project/experiments/block_synthesis/benchmark_ffn_control_trace.py check TRACE_LOG --mode 1 --seed 25001 --scatter
```

使用 Verilator 5.006 和第 16 轮的固定数据。本机 `round17-scatter-logs.sha256` 为 `36ce257eb7417ba748fe256d5cc78cf14654453a06759c57da9cb1252c4f362f`，`round17-scatter-verified.json` 为 `556db18a7b4ba2afc169c551acac8c76119dc98afa05dbb094b7e47486b0741e`。Windows 350 项测试通过。该对照从采样的 P DONE 开始，固定控制次序保证 scatter 期间无其他 SRAM 客户争用。P 计算、G 和 Mid 提交、允许多客户同发时的 SRAM 所有权需要继续接入完整计划。

搜索与硬件实测的对照方法参考 [Ansor](https://www.usenix.org/conference/osdi20/presentation/zheng)。内存控制器的地址解码、队列、仲裁和完成回调的分层参考 [Ramulator 2.0](https://arxiv.org/abs/2308.11030)。当前实现使用项目自有合同。

## 目标和边界

每次前沿扩展都回答一个问题。在**这份部分计划产生的芯片状态**下，加入这个候选，会在哪一拍被接纳、如何与已在执行的工作竞争、何时让结果可见，以及会推迟或释放哪些资源？

先在项目现有硬件和有证据的 Qwen2.5 执行范围内，把影响候选优劣的行为算准。模型、数值、底座、连接预算及候选池在对照中固定。延续 Algo1 从同一映射生成控制程序和连接需求的接口。定量周期由代价模型预测，部署指令按硬件合同等待真实事件。

当前重放能用 S 副本决定是否搬运，用 K 的区间寻找连续空档，并用同一组阶段推进新增和未获授权的旧请求。服务的阶段精度取决于硬件合同。固定配方的 FFN 回放用于复现原轨迹。原生 SRAM 已有改变请求顺序和反压的证据，FFN 及局控／外存仍需同类对照。

## 1. 把硬件清单、芯片状态和试排计划写清楚

| 内容 | 要保存什么 | 例子 |
| --- | --- | --- |
| 静态硬件合同 A | 时钟和容量、宏接口、窗口对齐与地址到 bank 的映射、控制和 DMA 的队列深度、仲裁规则、各阶段的工作量和事件语义。为参数登记版本和测量边界。 | N 的某阶段用几拍、P 的写回确认由谁产生、DDR 通道的实际请求格式和信用深度。 |
| 前沿状态 s | 已选绑定和静态线束 E、仍有后继的依赖、候选可回填的时间范围，以及可恢复的芯片状态和未执行计划。保留 T、DDR 读写量等汇总。 | 前沿已经选择了 Attention 的绑定，同时 FFN 的预取仍可在一个较早的空档插入。 |
| 芯片状态 z(τ) | 在模拟时刻 τ，哪些命令已接纳或发出、未完成事务在什么阶段、资源归谁、剩余工作和等待条件。 | 一笔 DMA 写已接纳，某个 beat 还在等 DDR 仲裁，源窗口仍由该事务持有。 |

z(τ) 至少要能恢复本轮支持的下列状态。能从已提交事件唯一推导出的字段可以按需重建。

- **算术和控制。** 执行中的阶段、剩余工作、积累部分和或统计值的上下文、结果保持槽、母控／局控的命令槽、完成队列、屏障和回传反压。上下文归属和释放以真实接口为准。
- **存储和数据。** 片段身份、版本、地址区间、有效范围、何时可读及谁还有权读写。用真实地址派生 bank 和端口请求。KV 保留跨 token 的版本及可见性，私有 S 和共享 S 分别登记仲裁与容量。
- **传输和外存。** 在途描述符／请求的身份、读写方向、地址、burst 和进度，源／目的端缓冲与信用，队列顺序和仲裁指针。已支持的 DDR 配置还要保留影响后续服务的 bank／行及读写切换状态。相同地址的读写依赖按实际控制器语义处理。
- **已排定和待仲裁的工作。** 区分已发生的握手、已被硬件保证的时隙、编译器计划发出的请求，以及尚未确定的预计返回。归档轨迹里的未来 ACK 只用于对账，试排根据状态和规则重新得出 ACK。

硬件清单登记的冷信息用来说明**资源怎么工作**。例如同一条 M 指令在操作数装齐后固定计算 4 拍，就把 4 拍保留为该阶段参数。若测到的 11 拍包含了一次端口等待和写确认，只有在能复用该测量边界时，才用 11 拍代表整条服务。换了竞争条件，应按阶段计算。缺失的硬件行为明确标成未校准，保守上界或近似值单独标记适用范围。

## 2. 一次 DP 或贪心扩展怎样重算

候选描述宏实例、分片、数据放置、路径和服务阶段。每个阶段声明前置事件、需要的资源、工作量，以及对输入／输出的可见性要求。资源的持有起止分别引用具体事件。发送缓冲、计算上下文、描述符槽和目标 S 窗口可以在不同拍释放。

1. **确定新增请求最早可能影响系统的时刻。** 根据依赖、允许的预取、提交顺序和不可撤销的动作，确定最早影响拍 τ。编译器刚处理到第 k 个节点，并不等于芯片运行到了第 k 拍。若候选能回填，就从 τ 或更早的状态检查点开始重放。保留该检查点前已发生的事件，保留到检查点仍在途的操作及进度。若新增静态连接会影响旧请求的路径或服务能力，检查点要早于首次受影响的事件，必要时从初态重放。
2. **把候选和旧计划交给同一套推进规则。** 旧计划里尚未发生的请求继续按其依赖与提交约束发出，和新候选争用同一套控制、链路、SRAM 和外存资源。根据真实仲裁顺序处理接纳、发出、传输、返回、提交和回传。阶段之间可等待，已接纳事务保持其身份。已承诺的时隙按合同保留，未承诺的预计完成拍由这次重放重新计算。输入不足或目的端背压时，只让实际能推进的阶段推进。
3. **按阶段结算。** 对确定性、连续占用的阶段，沿用 K 找最早空档。对共享仲裁的阶段，按授予的服务量推进。确认事件可能来自目标 S 写入、可见的外存提交或控制完成，按具体协议处理，不能用请求入队替代完成。逐项更新副本、在途操作、资源释放、等待原因、后继就绪拍及所需线束。
4. **形成可比较的后继。** 对同一分支所有已排工作，从重放事件重新得出 $T'$、$B_r'$、$B_w'$ 和 $E'$。如果新操作改变了旧操作的预测完成时间，T′ 要用更新后的旧事件和新事件共同计算。按唯一事务或 beat 统计已定义接口处的字节数，重放已有事务不重复收费。静态线束继续按并集统计。同一状态下能比较 $T'-T$、$B_r'-B_r$ 和 $B_w'-B_w$。计划不完整时，未完成事务仍留在状态中，作为后续候选的竞争者和依赖。
5. **检查，再评分。** 同一个扩展器供严格贪心和有界 DP 使用。独立检查器从事件重建资源、事务身份、数据可见性、生命周期和线束。容量、数值语义、覆盖和控制协议是合法性条件。评分初版保持基线的整份计划完成时间、DDR 总字节及静态网代价次序。输出每个候选的事件时间和主要等待原因，供定位排名反转。

若两个状态在未来仍可见的队列、地址、上下文、在途事务、等待和计划意图上不同，只有能证明任意合法后继的行为等价时才做精确合并。先保留必要信息。检查点、增量重放和粗模型筛选用于控制搜索成本。已证明的下界才用于安全剪枝，经验估计只用于排序或明确标注的启发式截断。进入最终对照的同一组候选要经过相同的详细评价。

### 一次试排的最小算例

假设输入已在 M，计算 4 拍，最后经 S 写回 1 拍。M 有既定预约 [14,20)，S 写口在 [8,12) 忙，候选最早第 8 拍可以开始。假设接口允许保留结果到写入，且结果保持槽和命令槽均符合约束。

- 全程同时占 M 与 S 的 5 拍服务，最早只能排到 [20,25)。
- 按接口分阶段，M 排 [8,12)，S 排 [12,13)。在第 13 拍提交后才放行消费者。若命令槽要等完成回传，还要继续保留该槽。
- 把 S 的占用延长到第 13 拍，并假设 M 要在算完时交付结果、没有保持槽。原来的 [8,12) 试排应被拒绝。若其他约束允许，可以改排 M [9,13)、S [13,14)。

再考虑一笔未被 DDR 接纳的 KV 写和候选的权重预取。若实际控制器允许预取改变接纳或服务顺序，重放需要同时产出两笔事务的新时刻。若控制器已经锁定原写的服务次序，则按该约束保留。两个分支可以搬完全相同的字节，仍有不同的 S 释放时刻、FFN 开工拍和总时间。

## 3. 实施顺序和交付

| 阶段 | 落地内容 | 通过条件 |
| --- | --- | --- |
| A. 冻结事件与静态基线 | 冻结 #257 现有事件模型、候选、硬件配置和 [#251](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/251) 回放。对照实际 RTL 定义接纳、出数、提交、可见、资源释放和退休。把可证实的固定阶段和跨阶段资源占用接入现有 K。 | 现有基线仍可复现。无争用及可手算争用场景逐事件一致，且能区分上例的第 13 拍和第 25 拍。未支持提前暂存的负例被拒绝。 |
| B. 从当前状态推进 | 在事件执行器接入检查点、共享资源的待处理请求、仲裁及背压。先重放完整受影响后缀作为参考，再优化复制状态和重放范围。独立验证器重建每项资源和事务。 | 同一候选从不同快照得到不同后果。新请求能按已声明规则影响旧预测。加速重放与参考重放对账，非法覆盖、过早释放、丢 ACK、重复计费和死锁均有诊断。 |
| C. 校准并做候选对照 | 对每个待比较候选，在模型和真实 RTL 或校准的周期后端上使用相同的控制镜像和数据。先测组件，再测多段串起来时的压力。固定候选池，分别运行旧代价＋贪心、旧代价＋DP、新代价＋贪心、新代价＋DP。 | 先对同一候选逐事件校准，再核对成对候选的真实排序。记录旧代价误判了什么、改进来自代价模型还是搜索宽度，以及编译时间与内存。 |
| D. 扩大回放范围 | 使用同样的事件语义覆盖支持范围内的跨层和跨 token，保留真实 KV 和未排空事务。复用 [#234](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/234) 的联合仿真与退休口径。 | 声明范围内实际程序、数值、事务和退休时间可对账。吞吐由完整运行的实际 token 退休时刻得出。未完成的执行链以缺口记录。 |

代码落点以当前 #257 为起点。事件执行和重放沿用 [event_execution.py](event_execution.py)，前沿及贪心沿用 [cover_frontier.py](cover_frontier.py)，合法性复核沿用 [verify_event_execution.py](verify_event_execution.py)。按需扩展硬件合同、快照及诊断输出，保留现有调用作为对照。程序和连接需求都从选中的合法计划生成。已有阶段行为与实际硬件不符时，先定位到接口或配方，再分别记录硬件变更和模型校准的收益。

## 4. 验收要看候选是否会选错

至少覆盖以下有区分力的成对场景。固定数据、时钟和硬件配置。先用同一候选测试不同竞争状态下的预测，再在相同初态和外部请求条件下比较不同候选的结果。模拟注入的场景与真实硬件回放分别记录。

| 场景 | 看什么 |
| --- | --- |
| 同一计算服务，不同局控命令槽或完成回传压力 | 宏算完、命令退休和后继放行能否分别对上。 |
| 相同容量和访问量，地址映射到同 bank／不同 bank | 仲裁、可重叠访问和真正可覆盖的时间是否正确。 |
| 相同 DDR 字节，改变 burst／bank 排布或在途读写竞争 | 请求顺序、行冲突、响应、目的写确认与旧事务被推迟的情况是否对上。 |
| RMSNorm 等多阶段服务与下一项操作重叠 | 统计上下文、结果保持及输出确认的寿命是否正确。 |
| 含 KV 的 Attention、FFN、下一层残差和下一 token | 局部交接及持续状态是否正确，允许重叠的资源是否仍能推进。 |
| 同一 FFN 的分片、驻留与并行候选 | 保留已有强对照，量出模型在已优化场景中的收益和回归。 |

每组报告独立检查失败项、关键阶段开始／结束误差、事务计数、候选排序一致性，以及模型选出的候选在参考执行中比同池最佳候选慢多少。对于参考差距小于测量波动的成对候选，单列为难以区分。误差报告覆盖空闲和拥塞，保留拟合时未使用的场景。整网结果同时给出绝对周期、相对变化和资源压力，便于识别两个大误差碰巧抵消的情况。

最终验收看两件事。**依赖、可见性和资源释放遵循实际硬件协议。** 在相同候选池里，使用更细状态计算的代价能解释选择差异，并在参考执行中改善或保持选择质量。
