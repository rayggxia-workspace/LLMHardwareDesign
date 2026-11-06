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
