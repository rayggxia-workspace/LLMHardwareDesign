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

重放对每个绑定默认试算至多 32 组搬运组合，可通过硬件 JSON 的 `event_model.transport_limit` 调整，`null` 取消该上限。草拟一组方案时，先按声明的路由 READY 窗口和日历估计到达拍。完整后继按动态重放评分，评分也用于排列从该方案派生的未试组合。两层排序均为启发式。输出记录尝试数和发生截断的绑定扩展数。计划保存完整搬运选择序列，以便精确重放骨架。

原生服务通过 `window_phases.read`、`write`、`publish` 指定阶段名。读取占用以 `read` 阶段结束为边界，覆盖必须等到旧读取和活数据写回确认。延后写入须用 `window_phases.result_hold` 引用已声明的 `hold_claims`，以约束计算结果暂存。数据可在 `publish` 结束时供后继读取，命令槽保留到退休。未声明的窗口沿用整段服务的边界；任务显式 `after` 和同绑定的串行服务仍等待退休，输入搬运仍须在服务起点前确认。

`event_model.issue_rates` 在重放模式用于抽象端口的滑动发放上限。对 #251 逐 beat 读路由，在硬件清单的 `event_model.typed_dma` 配置 `addresses`（片段 ID 到 DDR 物理字节地址）、`return_latency`（两个通道的返回延迟）、可选的 `ddr_ready` 与 `client_ready`（按拍列出半开区间及 READY 掩码）。在 phased DDR LOAD 路由上声明 `typed_dma.client`、`typed_dma.record_beats`。每条记录以基地址位 11 决定通道；范围必须是完整的 2 beat 激活记录或 17／18 beat 权重记录。一个客户端按候选发起顺序提交完整记录。通用日历的路由吞吐仍用于草拟；重放从实际客户端回传结束和目的写 ACK 得到可读拍。

逐 beat 读分支从候选最早可影响时刻之前最近的可用检查点恢复。检查点保留正在执行的 DMA、记录进度、lane、队列、回传槽和仲裁指针。边界拍的事件按新分支重新计算，在途读沿用已发生的握手并重新预测余下的握手。早于首个检查点的候选从初态推进。选用 `typed_dma.ffn_provider` 时，填写 `mode`、`seed` 和可选的 `cycle_offset`，由 FFN provider 产生 DDR READY 和返回。读路由可用 `typed_dma.replica` 从 `addresses[片段]` 的具名地址中选择一份预置副本，未指定时查 `primary`。副本各自占用 DDR 容量，并检查物理区间互斥。DDR bank／行、读写切换、原生写路径和跨 token 的持续状态仍待补齐。普通读合同涵盖合法记录流，运行时模式切换、异常和长序号回卷的 flush 尚待接入。

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

### 从 scatter 到 G 激活和 Mid 目录发布

第 18 轮接入 `ffn_mid` 事件服务。两次 G 指令各处理半个 tile，跟踪两组输入／输出槽、四级可停顿流水线和两条按序 SRAM 所有权。量化按 RTL 的写优先规则推进，两个拼接槽保留到写 ACK，未能发放的请求保持原身份。最后一个写 ACK 之后至少两拍才发布，压力模式下还要等目录 READY，最多再等四拍。该服务按实际发放拍重算周期，IR 校验绑定实际 P.S 源地址、目的地址和占用端口。

- 把每条 stripe 的 scatter、G 和 Mid 放进同一份候选计划，未消费的环形字带入下一条 stripe。Mid 不再使用采样完成拍，模型的提交拍直接进入下一步放行检查。四组固定 102603 RTL 共核对 344 个 Mid tile、145,168 个 G／量化事件，地址、可见拍、请求和应答顺序一致。去掉新增探针行后，每份日志与第 17 轮逐行一致。
- 同一模式、seed 和权重下，用仅增加首条 G 指令放行条件的对照版 RTL，分别在第 15,025 和 15,026 拍启动。两次前驱 scatter 都在第 14,087 拍提交。首个 Mid 分别在第 15,399 和 15,389 拍发布，晚一拍启动的候选早十拍发布。事件服务复现两组全部 G／量化事件。两组的完整 FFN 周期和流量相同，原数值断言均通过。与该压力相位等价的小图里，严格贪心选择先发候选，计划用 385 拍。宽度 8 的 DP 保留后发候选，计划用 375 拍。
- 提前发布、错误的 G SRAM 字地址和错误的量化应答标签均被拒绝。独立计划检查还拒绝提前结束和错误的物理输入窗口。

```bash
# 复用第 17 轮运行参数，运行时增加 +TRACE_MID。
python -B project/experiments/block_synthesis/benchmark_ffn_control_trace.py check TRACE_LOG --mode 1 --seed 25001 --mid
```

Verilator 5.006。本机 `round18-mid-logs.sha256` 为 `c5a72d3986237d13db54481821b8dd74c69f2e68dfd4c19e343c10b89b290b45`，`round18-mid-verified.json` 为 `fe0c80db99e622331b13ed9cce1b923a6902456573fff2e2fcaa4155337e2ac7`。清单包含四组原 RTL、两组放行对照和私有探针源。Windows 351 项测试通过。固定控制序列保证 G／Mid 独占所声明的 SRAM 端口，本轮按服务保留这些端口。仍使用采样的 P DONE 和 Down 之前的 Mid 读回事件，后续继续接入 P 执行及全局候选重排。

### 从 P 写回到 Down 放行和程序结果

第 19 轮在固定 #251 FFN 中，从每条最终 K 记录首字写请求的接纳拍开始重放。两次 16 B 写入共用 P 的 SRAM 接口，每次写确认受当前拍的响应 READY 控制，第二字等第一字确认后才能发出。按描述符几何检查每个记录序号、K 进度、地址及双字票据。最后一笔确认后，guard 和 A 生命周期还要推进四拍才能完成末条记录，range iterator 再过两拍发出 DONE VALID。Gate/Up 各 P 单独确认，Down 每组三个 P 等到最慢的 VALID 后一起确认。模型的 P DONE 进入 scatter 和 LC→MC 回传重放，Down 组完成进入下一组放行。

读回以已经发布的 Mid 和 Down 物理字为输入，复用 SRAM 请求和响应 READY 门。Mid 最后一次发布后两拍确认 Gate/Up 结束，再过一拍发起第一笔读回。逐字等待响应再发下一笔，最后一个 Mid 读确认后两拍放行首组 Down。最后一组 Down 确认后开始读回 512 字，程序结果在最后一笔读确认后接受。四组 RTL 中，子命令均在末笔读确认前退休。

四组 Verilator 5.006 RTL 的数值和累计流量断言通过。每组检查 66,048 条 P 记录、6,016 次写请求及确认、192 个 scope DONE、1,376 字 Mid 和 512 字 Down 读回，逐拍一致。Down 单个 P 从 DONE VALID 到组确认最长等待 24 拍。去掉新增探针后，四组日志与第 18 轮逐行一致。七个负对照分别篡改写地址、写确认拍、K 进度、P DONE VALID 拍、Down 读地址、Mid 读回标签和程序接受拍，检查均拒绝。

| Seed／初始化 | 压力模式 | 最后 Mid 读确认拍 | 最后 Down 读确认拍 | 程序接受拍 |
| --- | --- | ---: | ---: | ---: |
| 25001／0 | 0 | 591,769 | 857,116 | 857,117 |
| 25001／0 | 1 | 666,040 | 952,010 | 952,011 |
| 25002／2 | 0 | 591,769 | 857,116 | 857,117 |
| 25002／2 | 1 | 666,095 | 951,933 | 951,934 |

```bash
# 复用第 18 轮运行参数，运行时增加 +TRACE_RESULT。
python -B project/experiments/block_synthesis/benchmark_ffn_control_trace.py check TRACE_LOG --mode 1 --seed 25001 --result
```

本机 `round19-result-logs.sha256` 为 `813dba7b4891e683578f06bb2bb9c81613c57576713ae62f6851d35f2a566317`，`round19-result-verified.json` 为 `4a2e7ecab072faaecb9750e40bd797668060c08235a8ff6e5734536037631a95`。Windows 352 项测试通过。102604 固定轨迹的旧基线仍为贪心与 DP 各 948,626 拍。本轮读回是 #251 验证程序的实际 SRAM 流量。P 首字写发起仍来自 RTL 采样，通用候选重排还需从 K 窗口、权重和 M 执行推导该拍，并把跨 scope 的未排空事务带进同一快照。

### 从 M EXEC 接纳到 P 记录退休

第 20 轮把 P 结果首字写回的发起拍前推到 M 接纳 EXEC。冻结的 K128 FFN 每条 EXEC 有八个连续的 K16 操作数拍，尾拍后三拍交付点积，再经三拍缩放和累加产生 RF 回包。INPUT 回包在尾拍后一拍就绪。两类回包和已就绪的分配、填充、上下文回包共用一条有优先级的链路。从各自就绪拍重放仲裁，包头在选择后一拍发送，收到 EOP 才可释放该链路。INPUT EOP 解除操作数占用，RF EOP 后结果仍由有序 guard 持有，末 K 还需等两笔真实 SRAM 写确认。成对命令首条从 guard 直接退休，A_LAST 另需关闭及释放 A。模型算出的首字发起和记录退休继续驱动第 19 轮的 P、Mid 和 Down 检查。

四组 #251 Verilator 5.006 完整仿真逐拍对齐 264,192 条 EXEC 和 1,080,832 个回包的选择与 EOP。其间 8,729 条 EXEC 接纳时，前一条的 RF 回包还未传完。受控范围内 INPUT 和 RF 各最多等待两拍。去掉新增探针后，四组日志与第 19 轮逐行一致。篡改 EXEC 上下文、操作数拍、点积拍、控制就绪拍、回包身份、EOP 或 guard 退休拍的七个负例均被拒绝。

候选小图用同一套回包和写确认阶段重算两种 EXEC 接纳安排。空闲时，宽度 8 的 DP 选择第 8 拍接纳。加入第 18 和第 21 拍就绪的两条控制回包后，严格贪心仍选第 8 拍接纳，计划第 42 拍退休。宽度 8 的 DP 选第 9 拍接纳，计划第 39 拍退休。两份计划均经独立检查。该候选对照由事件 IR 注入，完整 RTL 对照使用固定程序。

```bash
# 复用第 19 轮运行参数，运行时增加 +TRACE_M。
python -B project/experiments/block_synthesis/benchmark_ffn_control_trace.py check TRACE_LOG --mode 1 --seed 25001 --m
```

本机 `round20-m-logs.sha256` 为 `eafb86e7a6a92bb6a321643c2cf77efecc877acf74386b726330ab3619db294d`，`round20-m-verified.json` 为 `91e9862778768b4edc9a0e2021a22fc4c3a727f9f7c40203c52500b16bc7b027`。Windows 353 项测试通过，102604 固定轨迹基线仍为 948,626 拍。M EXEC 接纳以及分配、填充和上下文回包的就绪仍来自 RTL 采样。下一步从命令仲裁及 A/W 准备重算这些入口，验证候选改变后跨 scope 的状态能否继续推进。

### 从 W/A 绑定到 M 命令接纳

第 21 轮从 W/A 绑定、侧带命令和权重 FILL 就绪开始，同时重放 P→M 命令与 M→P 回包。已发起的前瞻命令保持到 EOP，随后才能给 EXEC 分配 session。M 接收缓冲在命令 EOP 后仍要完成解码和接纳。BEGIN、上下文和 ALLOC 的回包就绪从命令重新推导。每个 W bank 记录物理编号、代次和所有者，分配接收槽要等 ALLOC 回包 EOP 释放，W bank 本身要等该记录的 INPUT 回包 EOP 释放。A 捕获证明与每次 W/A 绑定按 scope、K、slot、generation 及使用序号核对。重算出的 EXEC 接纳继续驱动第 20 轮的运算和回包、P 写确认及程序接受。

四组固定 RTL 各对齐 138,112 个命令、66,048 次 W 分配及 4,332 次 A 捕获证明。每组有 23,325 条 EXEC 因前瞻帧晚两拍入队，4,140 次 ALLOC 因前一个回包仍占用分配槽晚一拍接纳。这些 ALLOC 当时有可用 W bank。受控测试从第 31 拍复制四个 W bank 均在用、FILL 仍在传输的快照。改变首个 EXEC 的 W/A 绑定一拍后，待分配的第五个记录分别在第 51、52 拍接纳，并重新使用第 0 bank 的第 2 代。两份结果各自与从复位开始重放完全一致。

真实 RTL 成对对照保持程序、输入、数值断言和字节数相同。在私有插桩版的实际 early-exec 实例关闭前瞻后，两种压力下的程序结果接受拍从 857,117、952,011 变为 1,179,527、1,292,029。模型在各自采样入口下逐拍复现两种配置。单独改变测试台顶层同名参数的两次运行给出原轨迹，查明该参数没有传入 active early-exec 实例。四组固定轨迹移除新增探针后均与第 20 轮逐行一致。八个篡改负例分别覆盖 bank 可用掩码、bank 代次、A 证明及绑定代次、绑定 bank、命令 EOP、A 使用拍和 EXEC session。

```bash
# 复用第 20 轮运行参数，运行时增加 +TRACE_ISSUE。
python -B project/experiments/block_synthesis/benchmark_ffn_control_trace.py check TRACE_LOG --mode 1 --seed 25001 --issue
```

本机 `round21-admit-logs.sha256` 为 `dcef6d0ada817daf9c825a266bcf9b662d87d8f75ec71792ca2d352cc644746e`，`round21-admit-verified.json` 为 `d186058b7f7fdf4a5d7555f92d790b5486695619e916d5652da696bb25d321e1`。Verilator 5.006，Windows 355 项测试通过，102604 固定轨迹基线仍为 948,626 拍。A 捕获证明、W/A 绑定、侧带命令首次就绪和 FILL 首次就绪仍由 RTL 提供。两组下一段探针各已捕获 69,312 次 A 源字读回和同量 COPY 写确认。两组共 2,888 个 K 窗口的证明接纳拍等于 COPY 完成拍与最晚 A 读回后两拍的较大值。后续据此重算 A 捕获，再接入由 DDR beat 驱动的 FILL 和原生候选调度闭环。

### COPY 与 A 读取共用 SRAM

第 22 轮从 K header 释放拍和各 P 上一 K 的重放退休状态推出私有 A 加载。Gate/Up 从 U 取源字，Down 从保存 Mid 的 P 取源字。每个 P 的窄口按轮转接纳请求，保留两个按序返回的响应所有者。同一拍可以接收旧响应并接纳新请求。每个字的目的写确认推进可读前缀，A 加载按本地 slot 和代次请求，三个 P 在 COPY 完成且各自的读取证明均就绪时共同接纳证明。该模型按 #251 完整测试程序的串行 K 窗口重建，支持每个窗口内部的并行争用。

四组固定波形和三组候选波形均逐拍对齐，每组 1,444 个 K tile、69,312 次目的写及确认、69,312 次 A 读及返回、4,332 次共同证明接纳。四组固定波形移除新探针后与第 21 轮逐行一致。每组候选只把指定 K 的 COPY 晚启动一拍，分岔前的探针轨迹与 A 加载拍保持相同。候选与基线使用同一程序、输入和数值断言。表中以各自原启动时刻为基线。

| 压力及位置 | COPY 完成变化 | 共同证明接纳变化 | 完整 FFN 结果接纳变化 |
| --- | ---: | ---: | ---: |
| 有背压，Gate/Up scope 2，K=512 | +3 拍 | −4 拍 | 0 拍，952,011 |
| 有背压，Down scope 59，K=3200 | +3 拍 | −4 拍 | 0 拍，952,011 |
| 无外加背压，Gate/Up scope 2，K=512 | +2 拍 | −1 拍 | −1 拍，857,116 |

无外加背压时，共享窄口仍然要仲裁 COPY 和 A。按 COPY 完成拍单独比较，这三个候选都会被判为较慢。按 A 证明接纳拍比较，它们均更早放行，完整程序里只有第三组把提前量传到了程序结果。九个篡改负例分别覆盖 COPY 启动、Down 源地址、A tag、提前返回、提前写确认、加载拍、提前发布前缀、提前接纳证明和租约释放。

```bash
# 复用第 21 轮运行参数，运行时增加 +TRACE_AREAD。
python -B project/experiments/block_synthesis/benchmark_ffn_control_trace.py check TRACE_LOG --mode 1 --seed 25001 --aread
# 对照运行额外增加 +COPY_DELAY_EPOCH=21。
python -B project/experiments/block_synthesis/benchmark_ffn_control_trace.py check CANDIDATE_LOG --mode 1 --seed 25001 --copy-delay-epoch 21
```

本地仿真使用 Verilator 5.006。对构建用的 52 个直接源文件和两个头文件逐一对账，其中 51 个文件与 #251 的 `9abd46f5cbb4534bcfc614571ccd6d402ad11882` 一致。其余三个文件来自 #250 修订。M leaf 来自 `b78e24a93838c086d665c152fff392d2d6ddcb8b`，M native 来自 `21fac77b3bf80210cf3e484d26e9834bf0daf413`，测试台来自 `b7d420063d19a40d384ce16250a38e59b8d79c6b`。这两份 M 源码提供双执行所有者。测试台采用串行 K 准备。第 22、23 轮的逐拍结论适用于这套组合和记录的受控变体。102604 是独立的 #251 归档轨迹，回放仍为 948,626 拍。

原始记录和复现脚本保存在本机 Codex 实验目录。`round22-copy-source.json` 为 `83cdb535fb50de6ce312807c23adb209b9e57baf4e0ae5700f67abfa35b2a19d`，`round22-copy-logs.sha256` 为 `9e0088c065ae67f6d0f0e0aeb9ed55490204fb25028b51afc2cd078aaa3efd14`，`round22-copy-verified.json` 为 `8ed12589d1a596d749046dc783308f6195dd4542af9677d6a6e5886462d7a0be`。Windows 358 项测试通过。K header 释放、W/A 绑定、侧带命令首次就绪和 FILL 首次就绪继续由各自波形提供。下一步用预测的 A 证明和 W 填充重算绑定，并将可改变的 K 供给与后续执行纳入同一次候选重放。

### A 与 W 绑定的放行条件

第 23 轮用重算的 A 证明、ALLOC／FILL／INPUT 回包 EOP 和上一条 P 记录的退休拍重新推导 W/A 绑定。直接配对的首条记录还要等第二条记录的分配回包。前瞻队列中的配对要等两条已填充记录恢复到执行端及上一对退休。第二条记录在第一条 INPUT EOP 交接。若它的 FILL 同拍到达，下拍即可绑定。若 FILL 晚一拍，需经过填充等待状态，绑定再晚两拍。

四组固定和三组 COPY 候选每组重算 66,048 次绑定，均与上述本地组合的 RTL 波形对齐。另两组关闭 W 前瞻的完整波形也各重算 66,048 次绑定，使用采样的 A 证明。六个篡改负例分别覆盖 A 证明、首条 W 填充、第二条 W 分配、前瞻队列第二条填充、上一条 INPUT 和上一对退休。360 项测试通过。`round23-wa-verified.json` 的 SHA-256 为 `a85d93ccf59f39faaa2094e772cef84708c28cd9c69ad68112eaf2cea14a2d40`。

```bash
# --aread 和 --copy-delay-epoch 也会检查 W/A 绑定。
python -B project/experiments/block_synthesis/benchmark_ffn_control_trace.py check TRACE_LOG --mode 1 --seed 25001 --wa-join
python -B project/experiments/block_synthesis/benchmark_ffn_control_trace.py check NO_LOOKAHEAD_LOG --mode 1 --seed 25001 --no-lookahead
```

完整检查先从采样绑定重放 M，再用重放的时刻反查绑定。随后要把这条回路改成事件驱动，使候选引起的 W 与 A 就绪变化直接推进 P/M。K header、侧带首次就绪和 FILL 首次就绪仍是采样入口。

版本复核时，把三个替换文件恢复为 #251 固定提交中的原文件，以同一 seed、程序及输入重建仿真。两种压力均通过数值和字节断言。其 Gate/Up 加 Mid 与 Down 的原生阶段计数分别为 587,573／265,042 拍和 658,314／284,362 拍。双所有者组合在同样口径下为 586,103／263,811 拍和 658,258／283,649 拍。这是测试台的阶段计数。固定提交的 W/A 绑定尚未逐拍对账。`full-ffn-251-reference-0.log` 的 SHA-256 为 `9ca89ce3833699c0c250e6fedd0305cd4aacefd2161ba9e4ef829ad8a935e347`，`full-ffn-251-reference-1.log` 为 `478a3501647c9755061c41cb5ca08eae1efa503f7b689ab4b4038037176dc604`。

### 从 W beat 到 FILL 回包

第 24 轮在 DMA 客户端边界对账每个 W bank 的安装、请求和读回。每条记录按 bank、代次和 tag 收齐 17 个不同 beat 后成为待确认项。M 的 FILL 确认槽按 bank 编号选择，持有到 FILL 回包的 EOP。该确认仍与 INPUT、RF、ALLOC 等回包竞争同一条返回链路。命令模型由 beat 完成驱动 FILL 首次就绪，继续重放回包和执行。

带背压的基线和 COPY 晚一拍候选各对齐 1,122,816 个 W beat、66,048 次 FILL 和后续绑定。新增探针外的轨迹各与第 22 轮逐行一致。基线有 5,563 条记录收齐后仍等待 FILL 确认槽，最长 7 拍。候选有 5,555 条，两者的程序结果均在第 952,011 拍接纳。独立小例从第 31 拍已有一个确认占槽、另一个 bank 等待的快照开始。把第三个 bank 的完成从第 34 拍提到第 31 拍，使原有待确认 bank 的就绪从第 34 拍推迟到第 38 拍。两个快照后缀各与从复位开始的模型重放一致。

```bash
# 使用 instrument 生成测试台，运行时增加 +TRACE_WEIGHT。
python -B project/experiments/block_synthesis/benchmark_ffn_control_trace.py check TRACE_LOG.gz --mode 1 --seed 25001 --aread --wfill
python -B project/experiments/block_synthesis/benchmark_ffn_control_trace.py check CANDIDATE_LOG.gz --mode 1 --seed 25001 --copy-delay-epoch 21 --wfill
```

362 项测试通过。五个篡改负例覆盖 DMA 地址、过期 tag、完成代次、重复完成及错误的确认拍。两组原始轨迹及验证报告以本机 `round24-weight-verified.json` 索引，其 SHA-256 为 `62d87549789573f74a1329164b8f8647531928fa549c5379bc6f5acd88ab9125`。W 的 DMA 请求接纳和读回继续由波形提供。后续要把 W 的待发 bank、已锁定的 beat 和返回信用接入同一 DDR 仲裁，再让 K 供给、W/A 绑定和侧带发起随候选推进。

### W bank 与描述符共用 DDR

第 25 轮从 W bank 安装和控制器 CALL 重算 W 与描述符 DMA。每个 W 客户端保留四个 bank 的已发进度、轮转位置、已寄存的请求及剩余信用。当前拍返回的信用在下一拍可用。三个 W 客户端和描述符客户通过同一 `ReadFabric`。回放保留每个通道的请求表、两条物理发送通道、DDR 返回队列和响应暂存槽。重算的 W 读回驱动 FILL 回包，继而用于原有 M、A 和 P 轨迹校验。

带背压的基线及 COPY 延后候选、无外加背压的另一 seed，每组均逐拍对齐 1,122,816 个 W beat、384 个描述符 beat、1,123,200 次物理 DDR 请求和等量返回。核对包括 W 的首次 VALID 和接纳、DDR 的物理通道及全局 tag、客户端取回的时刻及本地 tag。带背压的两组结果均在第 952,011 拍接纳，无外加背压为第 857,117 拍。

同初态的缩小 RTL 对照在第 6 拍保留两个旧 W 客户端各四笔在途请求。把第三个 W bank 的安装从第 6 拍移到第 7 拍，第二条旧 W 记录的末拍从 49 提前到 46，后到的描述符从 27 提前到 24。新增 W 自己的末拍从 53 变为 54。两份从快照重算的结果均与从复位重算及独立 RTL 探针的 53 笔回执一致。六个篡改负例覆盖 CALL 拍、W tag 与接纳地址、后端物理通道、后端返回 tag、客户端返回 beat。

```bash
python -B project/experiments/block_synthesis/benchmark_ffn_control_trace.py check TRACE_LOG.gz --mode 1 --seed 25001 --aread --wdma
```

363 项测试通过。本机 `round25-dma-verified.json` 的 SHA-256 为 `a0ca8ae370091d3e67f87aff1e8a77c5a0cdd15bce6a0a119458bec79241a36b`，包含三组完整轨迹与小例的原始文件哈希。完整检查仍从采样的 W bank 安装和 CALL 推进。接下来让 M 的分配接纳直接安装 W bank，用 DDR 返回继续驱动同一个 M 命令链路。

### M 分配与 W DMA 双向推进

第 26 轮在 M 接纳 ALLOC 后，由模型选出可用 bank、更新代次并在下一拍安装。W 地址从 Gate、Up、Down 的 scope、列组与 K128 记录编号推导。三个 P/M 命令链路共用同一 DMA，读回再进入各自的 FILL 确认仲裁，随后按真实的回包竞争和 INPUT 释放条件回收 W bank。波形里的 W 安装拍、地址、代次和读回用于对账。

第 25 轮的三组完整轨迹每组均重算并逐拍对齐 66,048 次 bank 安装和 FILL、1,123,200 次物理 DDR 请求及等量返回，以及后续的执行和结果接纳。受控模型从第 13 拍的同一在途状态分岔。新 ALLOC 推迟 3 拍时，两条旧 W 的 FILL 就绪分别从第 47、50 拍提前到第 43、48 拍，新 W 的 FILL 从第 60 拍变为第 61 拍。每个分支均从复位重算核对，DMA 部分与独立 RTL 探针的 53 笔回执逐拍一致。该小例的 M 部分由模型驱动，完整 RTL 逐拍覆盖在三组实际程序上完成。

```bash
python -B project/experiments/block_synthesis/benchmark_ffn_control_trace.py check TRACE_LOG.gz --mode 1 --seed 25001 --aread --wlink
```

364 项测试通过。六个篡改负例覆盖安装地址、bank、代次、session、缺失安装和 ALLOC 意图拍。本机 `round26-linked-verified.json` 的 SHA-256 为 `7803b18fd708a4bd401aa6f8a2ff939c59696f2c8d1334c6f703a54a059006b2`。当前仍从采样的侧带意图、W/A 绑定、K header 和 CALL 推进完整程序。下一段要把重算的 A 证明、FILL 和 P 退休送回同一事件推进器，直接产生 W/A 绑定。

### W/A 绑定与 P 退休进入同一次重放

第 27 轮把重算的 COPY 和私有 A 读证明、M 回包 EOP、P 记录退休送入同一个绑定控制器。控制器确认 W/A 齐备后推进 M EXEC。W bank 仍在对应的 INPUT 回包后释放，RF 回包驱动顺序 guard 和必要的 SRAM 写回。每个 P 的上一片 K 末条记录退休后，下一片 K 才能计算 A 读取的最早时刻。

三组完整轨迹分别从 K header、侧带命令和 CALL 入口推进，每组逐拍对齐 4,332 次 A 证明接纳、66,048 次 W/A 绑定及 P 记录退休、1,123,200 次物理 DDR 请求及等量返回。带背压的基线和 COPY 晚一拍候选均在第 952,011 拍接纳程序结果，无外加背压的另一 seed 在第 857,117 拍接纳。

完整 COPY 候选只推迟第 21 个 K tile 的 COPY 发起。背压相位变化使这一片的 COPY 确认晚三拍，A 证明早四拍，三个 P 的首条绑定均从第 17,370 拍变为第 17,366 拍。全程有 576 次绑定及对应的 EXEC 接纳时刻改变。程序完成拍相同。

缩小模型对照从第 90 拍的共同快照分岔，W 已有在途请求。COPY 晚一拍使 A 证明从第 218 拍变为 219，W/A 绑定从第 220 拍变为 221，EXEC 接纳和 P 记录退休也各晚一拍。两份后缀均与从复位重算一致。另一对照推迟 W 分配，使绑定改为等待 FILL EOP 后两拍。

```bash
python -B project/experiments/block_synthesis/benchmark_ffn_control_trace.py check TRACE_LOG.gz --mode 1 --seed 25001 --wjoin
python -B project/experiments/block_synthesis/benchmark_ffn_control_trace.py check CANDIDATE_LOG.gz --mode 1 --seed 25001 --copy-delay-epoch 21 --wjoin
```

365 项测试通过。同时改动观测的 A 证明、W/A 绑定和 P 退休拍后，实时推进仍重算出与原始记录一致的时序，逐拍对账分别拒绝这些篡改。另三项负例覆盖丢失绑定、绑定记录号错误和 K header 推迟 128 拍后与固定侧带命令的 session 顺序冲突。本机 `round27-join-verified.json` 的 SHA-256 为 `eff5312fe631a410624c787a950ebeeb5e1c4236cd4cd683860f1812364fec40`。当前模型仍从采样的侧带命令、K header 和 CALL 推进。接下来用 P 的队列、回包和退休生成侧带命令，覆盖会改变其 session 顺序的候选。

### P 记录队列生成侧带命令

第 28 轮由 P 的状态生成 BEGIN、上下文和 ALLOC 首次 VALID。每个 P 的范围迭代器保留六个记录名额，前瞻队列最多容纳两条记录。直接配对先等第一条 ALLOC 回包，再接第二条记录。前瞻记录保留 bank 和 FILL，轮到队首才交给执行。侧带帧的实际 EOP 和 EXEC 入 guard 的时刻决定 session 号何时递增。W/A 绑定也由该状态机发出，进入已有的 M 和共享 DDR 重放。

三组已记录的完整 RTL 每组逐拍核对 72,064 条侧带命令、66,048 次 W/A 绑定和 P 退休、1,123,200 次物理 DDR 请求及等量返回。第 21 个 K tile 的 COPY 晚发一拍后，模型复现 564 次侧带命令时刻变化。三个 P 的第一条受影响 ALLOC 均从第 17,417 拍提前到第 17,413 拍。缩小模型在第 100 拍已有 BEGIN 帧在途时分岔，COPY 晚一拍把下一对记录的六条侧带命令各推迟一拍。两个分支均与从复位重算一致。

用相同输入、seed 和背压重新构建 RTL，只关闭 P 节点的 W 前瞻。新轨迹逐拍通过同样的核对，程序结果从第 952,011 拍变为第 1,292,029 拍，外部字节数相同。变体保留双 EXEC 所有者和四个 M bank。本机 `round28-side-verified.json` 包含四份原始轨迹哈希，文件 SHA-256 为 `838d5db6a852678014abbabcb6125c4964f7a4876e6832a7bb40d63adb36a00f`。

```bash
python -B project/experiments/block_synthesis/benchmark_ffn_control_trace.py check TRACE_LOG.gz --mode 1 --seed 25001 --wside
python -B project/experiments/block_synthesis/benchmark_ffn_control_trace.py check CANDIDATE_LOG.gz --mode 1 --seed 25001 --copy-delay-epoch 21 --wside
python -B project/experiments/block_synthesis/benchmark_ffn_control_trace.py check NO_LOOKAHEAD_LOG.gz --mode 1 --seed 25001 --no-lookahead --wside
```

366 项测试通过。五个观测篡改负例覆盖首次 VALID、丢失命令、session、ALLOC 记录号和长度。另把首个 K header 推迟 16 拍，对账在第 1,938 拍的三次 bank 安装处报出差异。删改多个侧带观测后，完整重放仍重算出原始 72,064 条侧带命令和 1,123,200 次 DDR 请求。本机 `round28-side-adversarial.json` 的 SHA-256 为 `c049c85ba31ad9a82bdae7380edf5e7af24aa7e5c20629b940a5d7257acb6ccb`。

推进仍以 scope dispatch、K header 和 CALL 波形为入口。已核对 1,444 个 K tile 的共同请求与 P 范围迭代器提供首条记录的时刻一致。首个 scope 的源量化耗时 97 拍，后续已有源数据的阶段耗时 1 拍，租约和 header 传输再耗时 8 拍。下一轮用这些接口时序和 P 的真实请求生成 header。

### P 请求驱动 K 窗口和 A 加载

第 29 轮从程序记录生成 K 窗口顺序。上一窗口的 COPY 与 A 读取证明接纳后释放租约。三个 P 都持有下一片 K 的首条范围记录时，发起该片的公共窗口。按测试台固定的源量化和 header 接口推进，三个 P 各在真正接纳首条记录后发出本地 A 加载。源量化阶段使用已核对的固定时序。测试台在此阶段独占 U SRAM。

带背压的基线、COPY 候选、关闭 W 前瞻的变体及无外加背压的基线，每组逐拍对齐 1,444 次共同请求、量化与 header 时刻，4,332 次本地 A 加载和证明接纳、72,064 条侧带命令及后续 M 与 DDR 握手。第 21 个 K tile 的 COPY 晚发一拍后，后续 11 个 K header 提前 6 至 19 拍，两组程序均在第 952,011 拍完成。

用同一 Verilator 构建与 mode 0 输入重新运行另一候选，只把第一个 K tile 的 COPY 晚发一拍。首个 A 证明晚一拍，之后 1,443 个 K header 均晚一拍。完整重放逐拍通过，程序结果从第 857,117 拍变为第 857,118 拍，数值及字节断言通过。五组原始轨迹和对账报告见本机 `round29-window-verified.json`，SHA-256 为 `49d1266bddf6cd23df5bc01859fe2495e944f10c132707d8eac50349234269b4`。

三 P 缩小模型在第 179 拍已有三个 BEGIN 帧在途时分岔。把第一片 COPY 晚发一拍，下一片 K 的共同请求由第 372 拍变为 373，header 由第 477 拍变为 478，证明接纳由第 595 拍变为 596。快照分支与从复位重算一致。

```bash
python -B project/experiments/block_synthesis/benchmark_ffn_control_trace.py check TRACE_LOG.gz --mode 1 --seed 25001 --wwindow
python -B project/experiments/block_synthesis/benchmark_ffn_control_trace.py check CANDIDATE_LOG.gz --mode 1 --seed 25001 --copy-delay-epoch 21 --wwindow
python -B project/experiments/block_synthesis/benchmark_ffn_control_trace.py check EARLY_COPY_LOG.gz --mode 0 --seed 25002 --copy-delay-epoch 1 --wwindow
```

367 项测试通过。请求、量化、header、K 身份和覆盖五个观测篡改均被拒绝。把一个 P 的真实 dispatch 推迟 16 拍，模型不再于第 1,938 拍安装这批 W bank。删改 K profile 的观测时刻后，完整重放仍能重算全部窗口、侧带和共享 DDR。负例报告 `round29-window-adversarial.json` 的 SHA-256 为 `abb24e0f11235a1cbb1620ee6df9b5e2f77d441b3a19ce078ebedd7d6cfbc820`。

当前的入口为 scope dispatch 和 CALL。四组既有轨迹的首个 CALL 均为程序启动后第 58 拍，同组 CALL 相隔 16 拍，组间最后一条终端回执到下一组首个 CALL 相隔 18 拍。下一步由已重算的 P 退休推动局控终端回执，再从该回执恢复母控等待和后续 CALL。

### P 退休驱动母控 CALL

第 30 轮从 P 最后一条记录的退休生成局控 DONE。Down 三个 P 等共同 DONE，Gate/Up 各自提交。局控终端帧争用同一母控接收口，保留帧占用和接收间隔。母控等待组内三个终端 EOP，随后发出下一组 CALL，CALL 实际时刻决定描述符 DMA 发起。

四组完整 RTL 各逐拍对齐 192 条 CALL、192 条终端回执、384 个描述符 beat 和 1,123,200 个物理 DDR 请求。无外加背压时首片 COPY 晚一拍，首组三条 CALL 保持原时刻，之后 189 条 CALL 和全部 192 条终端回执各晚一拍。缩小模型从已有终端帧在途的共同快照分岔。改变一个旧 P 的退休时刻，使两个待发终端帧交换接收顺序，下一组首个 CALL 从第 153 拍变为 156。快照和从复位重算一致。

```bash
python -B project/experiments/block_synthesis/benchmark_ffn_control_trace.py check TRACE_LOG.gz --mode 1 --seed 25001 --wcall
```

六个负例覆盖 CALL 时刻、缺失 CALL、目标、终端时刻、重复终端和程序起点。更改所有 scope 元数据里的 CALL 和终端时刻后，模型仍能生成与原始物理波形一致的结果。证据 `round30-call-adversarial.json` 的 SHA-256 为 `1063d534ae1fb6036f39da87b2ec366e3d3b4d911ab2b1795d90fe933042e0b8`。scope dispatch 在此模式继续由波形提供。

### DP 前沿恢复在途 DMA

第 32 轮在 `run.py --event-ir` 的重放分支接入 DMA 检查点。初始间距为 64 拍，每分支最多保留 16 个检查点，达到上限后保留隔点并加大间距。不同候选共享既有检查点，恢复后各自推进 DMA 状态。预测的整份计划周期继续用于评分。

一条旧 LOAD 已发放且被回传反压时，DP 在第 64 拍的快照上试排后续 LOAD，选择另一客户端。两个候选的完整轨迹分别与从复位重放一致。并行对照包含同一快照分出的同通道／异通道、空闲后保留仲裁状态，以及 48 组混合压力下 672 次候选追加。已有 #251 回执中，旧请求在通道 0 时主副本为 38 拍、另一副本为 31 拍，旧请求在通道 1 时分别为 31、39 拍，两种搜索宽度均选中更快的副本。

服务器 Python 3.12.7，Slurm `105458`。管理结构检查通过，372 项回归通过。验证脚本 `run/r32-reviewed.sbatch`，全量日志 `run/snapshot-105458_0.log` 的 SHA-256 为 `e1accdfe5b78c627841509ff7bd911e5468bf4346a158b0354bf18457e2a1449`，归档 RTL 的候选排序对照 `run/snapshot-105458_2.log` 的 SHA-256 为 `a7147099f70c3fdd5206186a31f983eda29132150cba8647f71c234e44c53c33`。文件在项目远程 `issue-219-block-search/chip-state-replay-20261113/` 下。

### 有界搬运枚举使用实时评分

第 33 轮让已试组合的实际分支评分决定后续搬运组合的探索顺序。用同一候选池对比第 32 轮代码，测试两段串行搬运都需要改路、各路 READY 关闭时长不同、资源争用与 ACK 等待、骨架复现。8 个逐步增大候选池的对照中，旧 32 次预算均选出 116 拍的计划，新版均选出 10 拍，穷举也为 10 拍。穷举规模为 484–1,369 组。另有 36 组固定随机种子的混合竞争对照，新旧版均达到各自同池穷举的完成拍。已有 FFN 权重副本对照保留原排序反转。

服务器 Python 3.12.7。Slurm `105506` 管理检查及 373 项回归通过。`run/transport-105506_0.log` 的 SHA-256 为 `cb535aadab258ab0dc670d3cf98e3a4025ec1345ff95a4f55e3c01d538a0db88`。旧版对照 `run/transport-105481.log` 的 SHA-256 为 `b1335a4ee7da84d1e09a1f1c812c1ea9a090a3ad5fdee22109add35a34423b87`。混合对照作业 `105517` 的两份输出 SHA-256 均为 `2ca91412164223c0236e83a42c5488138c67cc2f416e00fbef1cf51fc05f57c4`。

### 用在途 DMA 快照试排搬运路线

第 34 轮在有界搬运枚举中，先合并物理读请求、事件阶段、窗口和静态连接完全相同的路线。前沿用当前分支和已草拟的操作试排不同的物理读请求，再探查同一物理请求的时序变体。试排以数据送达拍排序，完整候选仍按整份计划重放评分。每次扩展的探查上限与完整候选上限各为 `transport_limit`，计划分别记录探查次数和预算耗尽后按估计排序的次数。无界模式仍枚举所有路线，骨架仍按原始索引恢复。

旧 LOAD 从第 64 拍快照恢复后仍有请求在途。客户端 0 受背压时，36 个等价路线占满旧版的 32 次预算，旧版完成于 214 拍。新版用两次局部探查和四次完整扩展得到 206 拍，与同池穷举的 40 次扩展一致。改为客户端 1 受背压后，新版与穷举均在第 87 拍完成并选客户端 0。再把 36 个别名改成不同仲裁优先级，两个物理客户端仍各获得一次探查，最终为 206 拍。24 组九客户端随机压力对照中，旧新版在预算为 4 时均达到各自的穷举完成拍。

服务器 Python 3.12.7。Slurm `105545` 管理结构检查和 374 项回归通过，旧权重副本硬件回执仍复核通过。`run/dma-pool-105545_0.log` 的 SHA-256 为 `25d6bbdbaca87256f9c97478ea26cdd057408b77669013bbf969a8fe3dd95524`。成对场景旧版 `105534` 的输出 SHA-256 为 `c47fa7c3c1fb72d34a5f44d972b9a6b6b80ebbfe722c895eedb6421fc97fa295`，新版 `105545_2` 为 `b079a50a1a2851eba17dc15c5b83a19709886e8232940cccdedd2629cda8e3c9`。随机对照 `105555` 的两份输出 SHA-256 均为 `ad388ed81787e3cc3e3300b5d0ad422f24dad320a0a8bb5da95b2024c77f940c`。

### DP 候选与片上 SRAM 的回传槽

第 35 轮让实际前沿从绑定的物理窗口生成 #251 四 bank feeder 请求。硬件清单用 `event_model.sram_feeders` 按站点启用，可通过 `ready` 声明两个回传口的 READY 半开区间，掩码的位 0 和位 1 分别对应窄口和宽口。服务用 `sram_access` 声明 `read-narrow`、`read-wide` 或 `write-narrow`，绑定对应单个窗口。窄口请求使用 16 B 对齐物理字，宽口每次读同一行的四个 bank，要求 64 B 对齐。每站点每拍接纳一路，宽口优先，各口两个回传槽。快照保留未发请求、已占用的响应槽及已确认的 beat。计划记录地址、bank、接纳拍与 ACK 拍。最终 ACK 在下一拍对事件后继可见。

远程复用原有 8 组 SRAM 硬件记录，实际 DP 入口重建 86 次握手。两种候选读取同一份 64 B，宽口畅通时计划最后一次 ACK 为宽读第 5 拍、窄读第 8 拍。宽口受阻时为第 9 和第 8 拍。搜索宽度 1 和 8 均选中对应的更快候选。宽读插入时，旧窄写的最后一次 ACK 由第 4 拍移至第 5 拍。另有 40 组 SRAM 和 DMA 混合压力，640 次追加与从复位重放一致。独立检查拒绝篡改 bank 和提早或推迟复用响应槽。

当前在已声明的 feeder 服务上核算时序。完整 FFN 的 COPY、消费端 READY 反馈及跨任务 SRAM 共享流仍待映射到该入口。

服务器 Python 3.12.7，Slurm `105580` 管理检查和 376 项回归通过。`run/sram-dp-105580_0.log` 的 SHA-256 为 `d7e0b9340c9c2032b849c6784d85e058da1e4fa20aa1601ee51a7db037151615`，归档握手及候选排序对照 `run/sram-dp-105580_2.log` 为 `cd28215490cd500bbc20e8394af15d4cb662e8e4dc2fe936bb960ea607e8da8d`。混合快照对照 `run/sram-dp-105583.log` 为 `a6a9acc0c4e297b0e5971f9c135b9e7fe56f307a478ad36b31bba22be3689a47`。

### FFN 激活候选按 A 证明放行计价

第 36 轮将已校准的 #251 COPY 与私有 A 读取联合模型接入事件 DP。服务以分支中实际发放拍为 header，`ffn_activation` 声明压力模式、COPY 延迟及三路 A 加载相对时刻。绑定提供一个 16 字源和三个 P 的 A 窗口。模型从物理地址派生源读取及三路目的写，重算按字写确认、前缀可读、轮转仲裁、两份回传所有者和 A 证明。阶段持有对应的私有 S 端口，后继在共同证明接纳的下一拍获得数据。验证器核对回执与后继依赖，并拒绝与通用 feeder 共用同一端口的配置。

三个已有硬件成对用例中，强制两个候选分别通过普通 DP 入口，核对每份轨迹的 48 次写、48 次读及各自的 ACK、三路加载和共同证明。打开压力时，Gate/Up 与 Down 的 COPY 均晚 3 拍完成，A 证明均早 4 拍。关闭压力时，Gate/Up 的 COPY 晚 2 拍，A 证明早 1 拍。宽度 1 和 8 均选择实际更早放行消费者的方案。篡改写确认、把消费者提前一拍、漏掉任一私有端口的配置均被拒绝。

这些对照使用归档的窗口入口和 A 加载相对时刻。当前验证的是 K 窗口内的候选排序。完整 FFN 的跨 K 退休、A 加载放行和整网候选排序仍须在常规 DP 入口联合计价。

服务器 Python 3.12.7，Slurm `105588` 管理检查和 377 项回归通过。`run/ffn-act-105588_0.log` 的 SHA-256 为 `6d39aac124e9a7faeb36359583bb964f0103319d1e88963deb3362a6c78e2bc9`。三个成对用例使用同作业的 `_1`、`_2`、`_3` 日志及 `run/r36-review.sbatch`，输入为既有第 22 轮记录。

### 上一片 K 的退休驱动下一片 A 加载

第 37 轮给事件 IR 的 `event_after` 增加可选 `load` 字段，分别引用三个 P 上一片 K 的退休阶段。目标必须是 FFN 激活阶段，每路恰好一个依赖。COPY 仍按 header 发出。每路 A 加载取该路退休后两拍与 header 相对下限的较晚值。若窗口开始时某路尚未确定退休拍，快照保留已发放的窗口与端口归属，并在候选重放中重新求得该路退休和共同证明。独立计划检查从前驱阶段的实际结束拍还原加载时刻。

三组已有硬件成对用例从上一片 K 的末条记录 pop 加 3 拍建立退休边界，从三路退休和 header 重建加载。三路加载、写与读握手和共同证明逐拍一致。模型对照逐个扫描 P0 退休延迟 0–64 拍。原场景选择 COPY 晚发一拍，仅把 P0 的退休推迟 4 拍，选择翻回准时发。另有在窗口已发放、P0 未取得退休资源时追加竞争者的分岔检查，从快照恢复与从复位重放一致。

上述成对对照从归档退休边界开始。完整 FFN 里决定这些边界的执行及回传仲裁仍需与常规 DP 端到端联合计价。

服务器 Python 3.12.7。Slurm `105617` 管理检查及 379 项回归通过，全量日志 `run/retire-105617_0.log` 的 SHA-256 为 `ecec80404bf341ccec805924daff33523ce8254481f0ab35894b25e926dd77fc`。三组成对回执是同作业的 `_1` 至 `_3`。延迟扫描为 `run/retire-105609.log`，SHA-256 为 `b416e407aceb12dc0508edc2b52a5e8880815e3d4143fa5c583c68444d8bf646`。

### 完整 FFN 的结果接纳进入 DP 评分

第 38 轮将 #251 三 P FFN 作为 `run.py --event-ir` 的原生候选。实际发放拍启动母控、描述符、权重读、三路执行、片间生产和退休。下游在程序结果接纳后的下一拍读取三个结果窗口。候选用重算的完成拍计价。模型记录 71,884,800 B 外部读取和 96,256 B 片上写确认，外部写量为零。阶段暂时独占母控、DDR 和私有站点端口。

使用既有作业 `105339` 的五份结果回执核对三组成对场景。开启压力时，延后第 21 个 COPY 的方案与基线均在第 952,011 拍完成。无外加压力时，延后首个 COPY 将完成拍从 857,117 推至 857,118。关闭权重预取将第 952,011 拍推至第 1,292,029 拍。宽度 1 和 8 均选中对应的最早候选。篡改结果接纳拍、外部读量或片上写量均被拒绝。

服务器 Python 3.12.7。Slurm `105647` 管理结构检查及 379 项回归通过。三个场景的命令在 `run/r38-program.sh`，日志依次为 `run/ffn-program-105647_1.log`、`_2.log`、`_3.log`，SHA-256 依次为 `2ac8735ce421f6c88cf14f243eaa8ad3e134291d9eca1cd987748f7d62438085`、`ed00c088803b2843fe3f8ef307d89eedc6514c479029ce4f16d3f56bd076375b`、`584c94c889868851feabaf0bf44b234428376e4ff33c191e5022dcbd446bc630`。

母控有旧请求先占一拍时，同一 FFN 改在第 1,538 拍启动，仍于第 952,011 拍接纳结果。Slurm `105693`，`run/ffn-shift-105693.log` 的 SHA-256 为 `da984c45b6b04fe16a01bb18d98ef7b58f465e12088a724630e8e32599b45653`。

### 完整 FFN 与普通 LOAD 共用逐拍读仲裁

第 39 轮在 `typed_dma.ffn_provider` 与 FFN 的压力模式、种子匹配时，普通 LOAD 和 FFN 描述符、权重共用同一个读仲裁器。普通 LOAD 使用客户端 3–8，写入 FFN 私有站点以外的窗口。重放同时推进各客户端在途请求，控制器、P 和私有 SRAM 继续由 FFN 持有。审计按计划的实际发放拍重建联合读队列，并核对两边的回执与结果可见性。普通 LOAD 需避开 FFN 的描述符和权重后备区，这些区间计入外存容量。

候选能影响运行中的 FFN 时，从程序启动前的共享队列快照恢复，保留当时已经在途的 LOAD。FFN 退休后恢复建立常规快照。缩小模型验证了运行中追加候选时，两种分支的轨迹分别与从复位重算一致，旧 LOAD 的握手和 FFN 结果都能随候选变化。独立的共享状态仍未覆盖 DDR 写、DRAM 行时序、片上私有 SRAM 跨任务共用，以及整网、跨 token 执行。

普通 DP 入口的 32 KiB LOAD 单独于第 2,122 拍完成。将读基址偏移 0 或 2,048 B 后与 FFN 同跑，LOAD 分别在第 2,137 和 2,138 拍完成，FFN 均保持第 952,011 拍。两笔请求的物理记录跨两个通道，首个记录分别在通道 0 和 1。将压力扩大到六路 128 KiB LOAD，若第 1,580 拍发起，FFN 推至第 954,398 拍。若第 940,000 拍发起，FFN 推至第 954,528 拍。两种情况下六笔旧 LOAD 全部推迟。联合竞争是模型对照，FFN 单跑完成拍继续与既有硬件回执一致。

Slurm `105763` 管理结构检查和 380 项回归通过。完整 DP 三组场景是 `105750_0` 至 `_2`。负例 `105774` 拒绝四个 FFN 后备区的地址重叠、外存容量少 1 B 和误用描述符客户端。六路压力对照 `105770_0`、`_1` 的日志 SHA-256 分别为 `13ccc67209347bca123bd3149b15a6a8de8d74c88c99a0610f98be3d22939c49` 和 `d06fdf748335ccccc67eae4b8aa016d9ed2029791adba35770a6fe8657b655f5`。

### 运行中 FFN 与 DDR 共享快照

第 40 轮在重放检查点保存执行中的 FFN。模型共同复制程序和 DDR 仲裁器，使尚未返回的权重记录仍与原有 bank、在途队列和信用关联。候选从最早影响拍之前最近的快照恢复，重新仲裁其后的请求。活跃 FFN 快照至少相隔 131,072 拍。检查点总数仍限制在 16 个。

六路 LOAD 在第 940,000 拍到来时，恢复第 919,041 拍的快照。FFN 结果接纳和六笔 LOAD 的每个 beat 都与从复位重算一致。这一分支用 10.94 秒，完整重算用 87.57 秒。早到的候选从第 1,537 拍启动快照恢复，结果同样一致。恢复并继续建立快照用 127.34 秒，完整重算且关闭快照用 86.26 秒。两个对照的作业峰值内存分别约 0.77 GiB 和 1.25 GiB。快照复制的内存及启动附近的额外耗时仍需降低。

服务器 Python 3.12.7。Slurm `105793` 管理结构检查与 380 项回归通过。`105792` 验证从同一有在途读和权重记录的快照分出两个不同候选，重复首个候选得到完全相同的轨迹。完整对照脚本为 `run/r40-live.sh`。`run/ffn-live-105786_0.log` 和 `_1.log` 的 SHA-256 分别为 `ed1416640b77e933d7c0f2e1ea16f4b7ec3473ef50ce58d458d3c1017768dba9` 和 `31dfdcd18878cfefdb97c160130da72a454c78d7cd0d4690f20ab5e638e6788a`。

### 写回、读写切换和 KV 片段接续

第 41 轮在 `typed_dma.mixed` 声明后端队列深度 `queue` 和写延迟 `write_latency`，沿用 #251 的 64 B beat、客户端队列及在途信用。读写共用每通道的后端队列。快照保留各 bank 当前行、最早命令拍、读写方向、切换等待及已占用的返回槽。四 bank、64 B 交错、1 KiB 行、2 拍命令间隔、6 拍换行和 4 拍读写切换采用 PR #182 提供器的规则。组合配置由模型选择，时钟单位为当前事件调度拍，队列仲裁为可复现的确定性模型。PR #182 的 16 B 接口、异步时钟、随机停顿和错误响应不作为该配置的校准结果。未声明 `mixed` 的 #251 配置保留原有规则。

STORE 从私有窗口发出，DMA 阶段在最后写响应接纳后一拍结束，再完成路由 ACK。源 SRAM 保持到 ACK，DDR 的同一值随后可供 LOAD。混合模式要求已登记物理地址，禁止不同值覆盖同一地址区间。阶段的 `persist` 可列出要落外存的输入窗口，使 KV 即使留在 SRAM 也能显式发布。当前使用不同物理片段标识历史 token 的版本。

相同的权重读候选在无额外写入时，两个副本为 33 和 34 拍。写入与主副本共用通道时，两者为 57 和 34 拍。把写入移到另一通道后为 33 和 57 拍。宽度 1 和 8 均选出同候选池的较短计划。96 组混合压力对照的 288 次快照续算逐 beat 等于从复位重放。

混合模型下完整 FFN 单跑于第 1,054,099 拍完成。加入三读三写各 64 KiB 后，早发和晚发的模型结果分别为第 1,061,491 拍和 1,062,569 拍。六笔旧事务均比单跑推迟。该混合压力的参考来自模型对照，#251 硬件回执用于旧读配置的校准。

从 #234 连续整数序列的两条已审计样本提取前三个 decode 步的层 0 K/V 形状和量化格式。每 token 的 K 和 V 各占 1,024 B，三个 token 的新片段共写入 6,144 B，两次读取上一步追加的片段共读 4,096 B。宽度 1 和 8 均验证四次读取等到对应片段的确认，末次持久化于第 362 拍完成。这项对照将实际形状和版本用于搬运模型，周期只覆盖六个追加片段与四次回读。全历史读取、Attention 数值/周期联动与跨层执行还需接入。

服务器 Python 3.12.7。Slurm `105895` 管理检查和 383 项回归通过，`run/mixed-reg-105895_0.log` 的 SHA-256 为 `801e4ce145fb7cb0a6b0e322a98cfa32b510400bbe249905f63e4afb0d515950`。选路对照 `105860`，`run/mixed-dp-105860.log` 的 SHA-256 为 `984ba53387ea870901e1308e265378909ceea9445bab26d769ec8f883588b22d`。混合快照检查为 `105847_0` 至 `_3`，完整 FFN 负载对照为 `105842_0` 至 `_2`。

`105894` 手算对照核验换行加 6 拍、写转读加 4 拍。两条 KV 形状与搬运对照为 `105880_0`、`_1`，日志 SHA-256 分别为 `c30d77a4a939956209ebfab180a458f549e62b3cf3e466cef8a926025b2ca076`、`ca0453c07e2ea8782a6ae7929eb5a3b59ec33e2e2f53d331f6d6bd6e67744cab`。

实际事件编译入口另验证完整 FFN 与两个 token 间的单片段 KV 写回／读回共跑。在两种通道放置下，写回分别于第 1,640 和 1,641 拍确认，读回分别于第 1,680 和 1,676 拍结束，FFN 均保持第 1,054,099 拍接纳结果。审计从各自发放拍独立重放，外存写 1,024 B，额外读 1,024 B。Slurm `105869` 两项通过，日志 SHA-256 为 `da178adc6d1da023ad916c29da175a71802d5cf4337dc1b01a248c557ae1ae00`、`1ce1b3e5a086600e4a309b94c96e267e0493052311c797dec07577a639d8f064`。每个作业约 9 分钟，含候选重放和最后审计。

### 完整历史 KV 分块与有界预取

第 42 轮在 replay 绑定的第二段起允许 `prefetch` 列出输入窗口。指定窗口从已发布的 DDR 副本走 typed LOAD，最早可与前一段原生服务重叠。重放仍等待对应的 STORE 确认、窗口上一位写者和所有旧读者释放，以及搬运自身的目的 ACK。预取和串行方案使用同一仲裁、同一代价和同一检查器。日历模式仍支持原有绑定。

`benchmark_attention_kv.py` 读入 #234 的 `program.json` 与 `receipt.json`，校验程序哈希和历史 K/V 到两次 Dot 的依赖，确认 QK、行最大值、行归约和 PV 的依赖次序。层 0 的 16 个 query head 按 2 个 KV head 分组。每组对完整历史逐块生成 K、V 读取，保留当前 token 的片上 K/V，PV 按原历史次序累加后统一收窄。DDR 回执逐块核对 64 B 地址，独立按张量形状计算总字节数。

本对照采用 16 KiB 私有 S，给 QK/PV 划出独立捕获、计算及写入阶段，使用显式的 96 位 PV 累加缓冲和两个 4 KiB 历史窗口。DDR LOAD 与相应 SRAM 端口共享模型资源。两种方案的计算及数据布局相同。#234 只为该对照提供程序形状、数值格式和依赖。地址放置、操作数暂存、64 B/拍的本地搬运、算术和 Softmax 服务时间均是模型输入，Attention 候选还需要用原生控制和数值回放校准。投影、RoPE 和本 token 写回接入实际图的工作仍在后续。

两个序列各前三步的历史为 512、513 和 514 个 token。两种方案分别读取 1,048,576、1,050,624 和 1,052,672 B，包含尾块。无旧写时，512 历史的串行与预取计划分别在第 135,533 和 114,074 拍结束。加上第 92 拍可发出的 2,048 B 旧写，在 513 历史对照中，预取让旧任务从第 242 拍延至第 378 拍完成。两个序列、两个通道都得到同一反例。旧写后没有长后继时，宽度 1 和 8 都选预取。为旧写接上 138,000 拍的合成后继后，贪心仍选预取，整份计划用 138,378 拍。宽度 8 保留并选择串行，整份计划用 138,242 拍，等于同池强制候选的最优结果。该用例隔离旧工作的关键路径，使用模拟负载和预测周期。

服务器 Python 3.12.7。Slurm `106177` 管理检查和 385 项回归通过。两项新增测试验证空闲窗口可提前载入、旧读者占用时必须等待、跨任务 STORE 发布前不得读取，且篡改预取标记会被拒绝。最终完整历史与压力对照分别为 `106230_0` 至 `_5` 和 `106229_0` 至 `_7`，使用远程脚本 `run/r42-attention.sh` 和 `run/r42-attention-critical-final.sh`。回归日志 `run/kv-reg-106177_0.log` SHA-256 为 `45da68453f0a62d884a01f161256f94d0d03c388ceabc38311eb365e7c641b44`。无压力 512 历史的 `run/kv-ports-final-106230_0.log` 为 `1553cab399f033e78adbfad0c4950e46a654f90fe7ff3178c64e026a1b3068e8`，关键路径反例 `run/kv-critical-final-106229_2.log` 为 `6d3e3a1f89c5c144c9c7ba7d55da89f805faa3bcc1115d961d90a577003870b4`。

### 跨 token 的 KV 发布、FFN 与算术对照

第 43 轮把 #234 的相邻两份 decode 程序形状接成一个事件图。第一步 Attention 写入 FFN 输入，三 P FFN 按 #251 的完整程序推进，KV 追加使用同一 typed DMA fabric。四个 K/V 片段用与下一步历史一致的物理地址，等待各自 STORE ACK 后才可读回。下一步的早读候选在上一 token 的 FFN 期间只搬一块与新输入无关的旧 K。下一步的 Q/K/V 准备有显式 FFN 完成依赖。断言逐 beat 检查两个历史版本及总流量。投影、残差、归一化、采样和跨层流转仍是模型边界，不能从此切片外推整 token 周期。九实例按已声明的库存分配有限 SRAM，Attention 映射和端口时间仍是模型候选。

Slurm `106380_0` 至 `_3` 用同一事件编译入口分别强制串行与早读候选。每份读取 73,984,000 B，写入 2,048 B。早读候选的 64 个 K beat 在 FFN 期间发出，串行候选为 0。mode 0 下 FFN 从第 1,093,059 拍推迟至第 1,093,066 拍，整段由 1,216,121 降至 1,201,005 拍。mode 1 下 FFN 均于第 1,159,898 拍结束，整段由 1,283,069 降至 1,267,935 拍。两个模式分别使用 case 2、3 的 #234 回执，同一模式内数据与硬件设定固定。最终 JSON 归档在 `run/decode-final-106303_*.log` 末段。mode 0 两份纯回执 SHA-256 为 `da88eb71212da698101ac589d891963ce1593ce950a2f108a44eab91bde12907` 和 `2ccced0d78867cb4252fd76888542393e069124e41802e9e1723f98a8566b680`。复现输入见 `run/r43-handoff-final.sh`，最终作业将同版 Python 源内嵌至 Slurm 脚本，日志先写计算节点 `/tmp`。

分块算术对照读取 #234 两条序列三个 decode 步的归档 S32 K/V，前缀和追加后的字节分别与相邻整数回执的 SHA-256 对齐。读取真实算术指令和校验过的 ONNX 常量，Q 使用六个确定性输入，Softmax 沿用原指令及归档 NFactor oracle。1、7、8、16、33 的五种分块，每份逐位核对 QK、概率和 PV 的 18,464–18,528 个元素。PV 保留宽和，最后只收窄一次。六份缺失当前 V 行的负例使 2,042–2,048 个 PV 元素变化。Slurm `106402` 六项通过。共享盘当时拒绝新建文件，原回执在 node5 的 `/tmp/yzl-i219-kv-exact-106402_*.log`，最终 JSON 已保存在共享的 `run/kv-exact-106332_*.log` 最后一段。首末两份纯回执 SHA-256 为 `24433f7cd4b080f02060849763872370979fc38c470cb74b553488ff16426a9e` 和 `3d64f99b45f92bb5c3bf1839d28ca1b88e8b0e011a4aa300374d53c798909c2d`。

修正有界搬运探查的排序依据。只比较探查的最后一条搬运实际完成拍，避免重叠的长计算把早完成的两条路线都抹成相同分数。完整候选依旧按整个分支的完成拍与流量评分。定向测试的两条 DMA 路线都能在计算结束前交付，实际 ACK 仍不同，探查须保留该区别。Slurm `106447_0` 管理检查及 386 项回归通过，纯日志 SHA-256 为 `2b024d251118b7497a101db9982289dfb15c16fe7c0f7fcfcc498be405462756`。定向及重放相关 52 项为 `106447_1`。最终回执追加在 `run/decode-reg-106292_*.log`。

搜索与硬件实测的对照方法参考 [Ansor](https://www.usenix.org/conference/osdi20/presentation/zheng)。内存控制器的地址解码、队列、仲裁和完成回调的分层参考 [Ramulator 2.0](https://arxiv.org/abs/2308.11030)。当前实现使用项目自有合同。

### 两个相邻层在同一 DDR 状态上连续计价

第 44 轮允许完整 FFN 将描述符和权重镜像重定位到 4 KiB 对齐的 DDR 地址，保留原通道选择位。多个候选复用同一镜像时只占一份容量。两个镜像物理重叠、KV 落入描述符或权重范围，以及后备容量少一字节均被拒绝。两层使用不同数据版本及 DDR 范围，复用有限的 SRAM 窗口、母控和同一个 typed DMA fabric。早读可以与前层 KV 写竞争，后层 Q/K/V 仍等待前层 FFN 结果可见和写回释放当前 K/V 的 SRAM 窗口。两层完成边界还要求最后一层 FFN 结果和两次 KV 追加都可见。

`benchmark_decode_handoff.py CASE --layer-pair --candidate serial|lookahead|both --mode 0|1 --width 1|8` 从 #234 归档的同一个程序校验层 0/1 的 QK、PV、FFN 投影尺寸及残差到后层 Q/K/V 的依赖。模型使用 #251 同一三 P 程序的两份物理镜像。Q/K/V 准备、残差、投影和归一化仍以模型服务接续。逐 beat 核对两层 KV 的地址及读写量。

允许早读与前层 KV 写回争用的完整 Slurm 对照 `106615` 中，mode 0 的前层 KV 可见拍从 107,324 变为 107,406，前层 FFN 从 1,093,059 变为 1,093,067，两层完成从 2,201,048 提前到 2,186,015。mode 1 的前层 KV 从 107,424 变为 107,506，前层 FFN 同为 1,159,898，两层完成从 2,334,764 提前到 2,319,749。四份回放的 DDR 读写都是 145,866,752 B 和 4,096 B。Slurm `106616` 的同池宽度 1 在两种压力下都选择早读并达到强制候选的较早完成拍，宽度 8 待收取。强制对照回执保存在共享目录 `run/decode-final-106303_0.log` 的 `R44 complete shared KV and FFN candidate comparison` 段。

较早的完整对照 `106572` 让后层早读先等待前层 KV 写回，用于隔离与 FFN 的争用。mode 0 前层结果由第 1,093,059 拍推至 1,093,066，后层结果与两层完成边界由第 2,201,048 拍提前至 2,186,014。mode 1 前层结果同为 1,159,898 拍，两层完成从 2,334,764 提前至 2,319,749。每份共读 145,866,752 B、写 4,096 B。四份回执已保存于 `run/decode-final-106303_0.log` 的 `R44 complete two-program control comparison` 段。

Slurm `106654` 在 16 行历史和定长 FFN 的隔离用例中，早读把前层 KV 可见拍从 4,326 推至 4,408，两层边界从 13,602 提前至 13,103，字节数相同。宽度 1 和 8 都选早读，Q/K/V 开始或两层完成提前一拍均被独立检查拒绝。Slurm `106659` 的 24 个地址和发放拍分岔使用缩短的 FFN 权重流，每个快照恢复与从复位重放相同。mode 1 第 24 拍发出 4,096 B 时，两个等量地址使前层 FFN 分别在第 159 或 97 拍可见、旧 KV 写在第 84 或 60 拍可见、后层 FFN 在第 218 或 182 拍可见。共同前缀的三个原时刻为 95、60、152。

Slurm `106664` 管理结构检查和 387 项回归通过，`/tmp/yzl-i219-r44reg-106664_0.log` 在 node8，SHA-256 为 `aff75842d15628a90f6fc3d7bec192ff58ab06a9adc7d45f833a03a95b217b2a`。Slurm `106695` 复用已归档的数值 oracle 和两条序列各三个 step 的层 1 KV。五种分块逐位核对每份 18,464–18,528 个元素，漏掉当前 V 的负例各改变 2,048 个 PV 元素。首末日志 `/tmp/yzl-i219-r44bits-106695_{0,5}.log` 在 node8，SHA-256 分别为 `937ae6cefc01e6ebc458f17867dd3121d4fee84b6742094e2ac7c02d945e5e0b` 和 `71809f39fe2442f2e27b9b01a1eea43a791450b5a535a8050507e5e6b7a05645`。数值对照使用归档 KV 和确定性 Q，覆盖 Attention 子图。精简回执与哈希保存在共享项目目录的 `run/decode-final-106303_0.log` 末段。

### 按输入分别核算首次读取和最后一次读取

第 45 轮给多阶段事件服务增加可选的 `window_phases.input_reads`，从窗口名映射到首次和最后读取阶段。新增候选使输入交付改变时，只有对应的首次读取阶段等待其 ACK。窗口须持有原版本至最后读取结束。跨两次读取的间隔也保留该版本，允许独立端口或窗口继续推进。检查器从回执重建每个输入的区间。已有单一 `read` 及整服务读取合同仍有效。负例覆盖首次读取早于搬运 ACK、第二次读取之前覆盖原窗口、颠倒阶段顺序。

`benchmark_norm_event.py` 复用 `algorithm-fix-17-rows` 三初态已归档的 2048 元素 S16 RMSNorm。原生命令分为 BEGIN 8、STATS 4,096、FACTOR 170、SCALE 8,192 拍，常驻对照通过独立检查并复现原总长 12,466 拍。显式声明 N 端口优先、FACTOR 不占 S 端口和 64 B/拍的模型搬运时，非驻留 4,096 B gamma 放在 [4104,4168) 完成，结果仍在第 12,466 拍可见。将同样的 gamma 设为入口依赖则需 12,530 拍。分段长度源自归档原生命令，重叠采用模型端口合同。#234 层间归一化的数据格式为 S32，仍需独立接续和校准。

Slurm `106785` 管理结构和 388 项回归通过，回归日志 SHA-256 为 `73d491d44a5be0d531e91c9be0ffb2b373e5d2e40e064c2b1e64c4d291f3d5d7`。Slurm `106801` 的非驻留与驻留对照通过。Slurm `106811` 扫描了 80 组系数计算时长与搬运速率，每组核对入口读取与晚读，合计 160 份计划与手算一致。40 组非驻留均缩短，40 组驻留均持平。回执及哈希保存在共享项目目录 `run/decode-final-106303_0.log` 的 `R45 phase-specific input custody receipts` 和 `R45 normalization timing sweep` 段。

Slurm `106817` 固定两个模型候选，分别使用原 16 KiB 窗口内的 DDR gamma，和扩大 SRAM 容量后额外驻留且需 32 拍准备的 gamma。四个格子使用相同扩大容量与副本，改变计价方式及搜索宽度。入口计价下宽度 1、8 均选驻留候选，12,498 拍。按实际读取阶段计价时，两者均改选 DDR 候选，12,466 拍。此对照把选择变化归因于输入等待模型。回执在同一日志的 `R45 normalization same-pool matrix` 段。

### 有限 SRAM 内的 S32 原址更新

第 46 轮给分阶段服务增加显式的 `window_phases.in_place`。指定输入和输出使用同一个物理窗口、同样的字节数和不同的数据版本。内核合同须保证更新阶段逐字先读旧值再写新值。调度器从该阶段开始独占窗口，等全窗口提交后才放行新版本。若以后还要用旧版本，覆写前须保留副本。检查器拒绝缺失原址合同、抢读部分写入的结果及覆盖仍有其他读者的窗口。

`benchmark_s32_norm_event.py` 从 #234 两条已归档序列的程序校验层 1 NFactorAdaptive、2048 元素归约和 S32 gamma 投影，从常量镜像校验实际 gamma 地址和 SHA-256。窗口按已有原址 S32 路径放在 16 KiB 的两半，各 8,192 B。周期对照使用显式模型参数 SCAN/STATS/APPLY 每个 S128 字 3/8/28 拍，DDR 用 typed 路由和 8／16 队列。Slurm `106826` 的四对计划中，按阶段读取允许扫描第 0 拍启动，但扫描及统计和 gamma 写回仍竞争同一个端口。四对均只提前一拍，体现了端口竞争对可重叠空间的限制。旧版本后续有消费者时，保存和恢复各增加 8,192 B，独立核对通过。

S32 原址路径依据 #234 归档 `native-rms-gamma-JIkJyf7C` 的接口定义。该组件 fixture 按 LOAD X → LOAD gamma → FACTOR → APPLY 顺序驱动，源文件 SHA-256 为 `2a7d5b3df3ef076116d5019e8bff8a00723769a65fba6ceda73664eb902b5950`。早读与原址更新的对照是事件模型，归档 fixture 没有提供交叠时序或当前层整段的数值证据。Slurm `106824` 管理结构及 389 项回归通过，完整回归日志 SHA-256 为 `70a02d07714064e3f85e0f77798203512214dd2d1ef3fb32115aa8851d412b49`。摘要及四份回执在共享项目目录 `run/decode-final-106303_0.log` 的 `R46 in-place S32 SRAM contract` 段。

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
