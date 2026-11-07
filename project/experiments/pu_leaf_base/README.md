# P/U 独立叶宏底座

既有合格交付记为 `P_128`/`U_128`，保持旧包和物理模块名称不变。`PU_INSTRUCTION_BITS=64` 生成独立的 `pu_p_controlled_64`/`pu_u_controlled_64`。64 位指令以 v2 镜像真正打包，PM 接口仍为 128 位；这是固定原生服务控制核的紧凑取指移植，支持范围和独立验收见[版本回执](../../../work/YUZE-LU/212/compact64-physical.md)。旧版资格不能转移给新版。

64 位版本仍逐条取指，同一 128 位 PM 字中的两个指令分别读取，没有新增取指缓存，不宣称取指吞吐翻倍。固定基线上的独立初始实现可用下面的命令启动；后续修复及最终验收以版本回执记录的不可变检查点为准。复跑依赖原工程存储中的固定叶宏视图和 #195 冻结源。

```sh
sbatch -p c64 -c 10 --export=ALL,PU_INSTRUCTION_BITS=64 --array=44-45%2 \
  "$task/source/project/experiments/pu_leaf_base/physical.sh" "$task"
sbatch -p c64 -c 10 --export=ALL,PU_INSTRUCTION_BITS=64 --array=2-3%2 \
  "$task/source/project/experiments/pu_leaf_base/control_replay.sh" "$task"
```

`PU_REPLAY_EVEN=1`、`PU_REPLAY_LEGACY=1`、`PU_E_COUNT_REPLAY=1` 分别选择偶数指令、旧 v1 镜像和 U 的两源 FMA 回归。每种回归使用独立目录，不能复用另一种变体的结果目录。最终网表作为 `control_replay.sh` 的第二个参数传入。

P 使用 M、紧凑 G 和 16 KiB S_P。U 使用 N、紧凑 E 和 16 KiB S_base。叶宏独立摆放，标准单元实现适配和仲裁。P 的 feeder 和两个组的 SRAM 回放路径为预连候选。P 的 M→G 预留 32 位数据、valid、反向 take。U 的 N→E 预留 128 位数据、valid、反向 ready。物理试验采用局部接入样片，顶层需使用叶宏或适配器的实际接点。

以下命令在获授权的服务器上运行。`$task/source` 为复跑源码。每个作业有独立输出目录及 CPU affinity。

```sh
sbatch -p c64 -c 10 --array=0-3%4 project/experiments/pu_leaf_base/smoke.sh "$task"
sbatch -p c64 -c 10 --array=0-3%4 project/experiments/pu_leaf_base/control_replay.sh "$task"
sbatch -p c96 -c 12 --array=0-7%8 project/experiments/pu_leaf_base/physical.sh "$task"
```

原生烟测使用固定 SHA-256 的 OpenRAM bank。控制回归复用 #195 母控、局控、镜像装载和原生描述符，C↔U 中的 C 沿用对照实现。物理脚本复用实际叶宏 GDS、Liberty 及最终 ODB。物理、电气和布线后网表有独立验收门。见 [Issue #212 回执](../../../work/YUZE-LU/212/README.md)。

物理数组 0–7 测服务接口样片，8–15 加入 #195 可编程局控和 PM 总线。P 的直连模式在矩阵读出描述符的 `native0[22]` 和门乘的 `native0[30]` 启用。U 使用 `0x104` 配对描述符。其 `native0` 为 N 的源操作数个数，`native1[19:0]` 为两个 S 槽，`native2` 和 `native3[7:0]` 构成 N 命令，`native4[8:0]` 为 E 的操作和移位，`native4[18:9]` 为写回槽，`native5[19:0]` 为 E 的 B/C 槽。剩余位为零。拓扑须把 `late_path_enable` 绑定到实际连通配置。

阶段 16–19 用于 P 的 M10 供电偏移和端点接入筛选。续跑工具 `resume.sh` 从固定 CTS 检查点复制参考网表和物理数据库。原生、研究上层、最终网表仿真分别使用 `audit.sh`、`overlay_sta.sh` 和 `smoke.sh` 的最终网表模式。完整原生规则集需在原生 GDS 上执行。上层 RC 以规则文件中的未标定几何模型为限。

阶段 20–23 筛选 P 的 S_P 真实同网接近段。两个下层回退可选的只是既有导体的抽象分类。叶宏 GDS、原端口和原底座验收边界均绑定。带可编程局控的样片使用异步断言、两拍同步释放，外部复位路径例外必须精确匹配两个同步触发器的 RN 脚。母控在 `release_ready_o` 置位后才发释放事务。

阶段 24–27 筛选紧凑 U。阶段 28–35 对独立 M/N 的低层障碍取保守包络，保留其 pin 和上层形状。上层线束由 overlay_geometry.sh 从生成的 GDS 回读检查，验证逐网几何连通和隔离。

阶段 36–43 用原生 GDS 定位结果给父层增加布线余量，检查叶宏切孔和父层 PG 过孔的间距，并复用真实 ANTENNA_X1 保护外部输入。验收仍运行原版完整规则集。局控的 Block ID 与拓扑 ID 从稳定的底座配置输入取得。给控制回归脚本传入同一实现的最终网表可重放原母控和程序镜像。

[端点合同](contract.json)登记固定的本地数据连接和可后制的两组数据及握手信号。物理验收按最终 ODB 导出 m10-bindings.tsv、m10-pins.tsv 和 leaf-instances.tsv。上层检查核对连接方向、每个落点所属 M10 几何连通体、跨网隔离与穿越上层连接的时序路径。

原生时序验收输出 hold-endpoints.tsv。物理续跑可按报告为实际接收分支加有源延迟。该步骤保留原始验收 SDC，重新做布线、提取和所有最终检查。

阶段 44–47 复用 36、41、37、42 的叶宏配置，在 tapcell 前给每个叶宏的行宽过渡留一行隔离。该步骤保留原叶宏、引脚和面积。GRT 检查点续跑支持读取独立提取的 SPEF 或违规端点，局部调整驱动和保持时间，再生成最终网表与 GDS。临时布线阻挡会在提取和供电检查前从 ODB 删除。定点同网 M10 缺口修复用 repair_notches.sh 单独复跑，记录精确导体、叶宏端口、修复区域和输入检查点哈希，重跑提取与完整原版规则。

对已详细布线的候选，repair_notches.sh 可接收额外的井区行窗口。它按站点裁切填充行，校验窗口内没有有源单元，重新填充后用原版规则和提取复核。check_native.py 可对已生成的完整原生回执独立复核，输出 DRC 数、setup/hold、电气与供电结果。

父层供电过孔与信号线间距可用同一续跑入口修复。只有与记录坐标及 VDD/VSS 匹配的完整 M7–M10 过孔栈可移除，条带保持，随后检查两条供电网连通并重新提取。

紧凑 E 的 `cmd_sources` 沿用普通描述符的 0–3 个操作数合同，缺项补零且不读 S。直连 A 计入总数；`0x104` 配对描述符由操作码生成总数。`tb_pu_compact_e` 使用真实旧 E 核做 257 组对照，检查数据、状态、准确 SRAM 读次数、直连和背压；`tb_pu_u_group` 另验证两源 FMA 的 SRAM 写回。修改适配器后须重新生成并验收 U 物理实现，旧 U 归档不能覆盖新的控制 RTL。

可编程控制回放对每个场景分别运行三种初态。U 设置 `PU_E_COUNT_REPLAY=1` 时，在同一母控／局控程序中追加两操作数 FMA，S[0] 为 5、A 为 2、B 为 3；结果通过实际 SRAM 写回和块间传输送到对端检查，必须为 6。该变体检查新增写入的确认字节数，仍覆盖正常、背压、故障、背压伴故障和复位。给 `control_replay.sh` 传入最终网表即可检查同一程序的布线后实现。

普通 U 服务入口和并发发送修复：`controlled.py` 为 U 生成独立的 128 位 TX 保持槽，S 读响应在锁存时释放，SEND 仍等远端真实写 ACK 才完成。只有 U E lane 0 开放普通描述符三源，N 和其他 LANES profile 的限制不变。控制回放必须使用同一份生成的普通服务适配器。

设置 `PU_U_NATIVE_REPLAY=fma-duplex`，两个实际 U（含母控、局控、原生描述符和 SRAM）各执行两源及三源 FMA，随后四轮双向预约／发送／接收，首轮等待双方都拿到发送数据才放行，后两轮把实际接收 SRAM 内容发回核对。`duplex` 变体独立检查双向发送；每种运行正常、背压和传输中复位，各三初态。该回归也用于 `_128` 和 `_64` 的最终物理网表。

`native_entry.sh` 单独走同一 U 原生服务和真实 SRAM，检查 FMA 0/1/2/3 个操作数的结果与精确读次数、延迟 ACK，以及 N 三源／非法 lane 在发宏命令前返回 status 5。该入口测试三初态通过；它补充控制程序回放，不替代最终网表验收。
