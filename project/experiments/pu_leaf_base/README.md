# P/U 独立叶宏底座

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
