# G 与 E 紧凑独立宏

[Issue #201](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/201)

G 使用已验收的运算 RTL。E 保留原八路数值核心，将输入改为同一组 128 位数据端口。首拍带操作码和 shift，后续按操作需要送 B、C。握手接受最终操作数时才启动运算。复位丢弃未完成的操作数组。结果仍由原 128 位输出握手返回。适配器应在收到 S 的写响应之后再发布要求写回的局控完成。

两排配置复用原来每侧的错列接点。三、四排配置把同一侧接点分配到宏内相距数十微米的不同带。原 4 µm 轨道和 2.2 µm via 间距沿用。所有信号要同时有合法逃线才进入原生实现。独立 KLayout 回读记录在每个候选的 P&R 目录。该结果覆盖本候选的统一逃线，父层仍需按真实端点和负载核验。

在项目服务器上把快照解到专用目录，预先创建各轮的结果目录。每项只分配 10 核。保持同一候选的原始输入和输出可读。

```bash
sbatch --output="$results/slurm-%A_%a.log" project/experiments/block_v2/remote_compact_ge.sh "$source" "$results"
sbatch --output="$next/slurm-%A_%a.log" project/experiments/block_v2/remote_compact_ge.sh "$source" "$next" followup
sbatch --dependency="afterany:$producer" --output="$audit/slurm-%A_%a.log" project/experiments/block_v2/remote_compact_ge_audit.sh "$source" "$results" "$audit"
```

面积使用实际 ODB 中有功能的单元，分别除以宏外框和 core 面积。Filler、tap 和纯天线保护单元单独排除。记录 10 µm 网格中的最大连续空区。80% 是优化目标，优先保留原功能、原规则和 300 MHz 预算。
