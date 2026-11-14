# Algo1 特征交接和块级投影对照

Issue #219，基于 PR #273 的 dfcdb0d870f28d055839177801ca7a11ba79a973。评估使用 Qwen2.5-3B 首个 decoder layer 的真实整数图和权重，batch 1、序列长 2，束宽 8，分块深度 3。各方案沿用同一份 Block V2 归档资源、线束预算 10 和 PR182 逐记录 DDR 模型。输入分别为 [1, 2] 和 [42, 43]。两组输入的每档输出均与整算子逐位一致，块级候选走独立 C++ 有限 SRAM 解释器并核对命令与搬运计数。

| 方案 | 模型拍 | DDR 总字节 | 静态 Dot 权重读取字节 | DP 展开状态 |
| --- | ---: | ---: | ---: | ---: |
| 整算子 | 93,582,477,980 | 50,583,128,704 | 7,398,752,256 | 1,224 |
| 原整行驻留 | 93,582,456,220 | 50,583,123,584 | 7,398,752,256 | 3,080 |
| 特征分块及驻留 | 93,580,981,660 | 50,582,742,656 | 7,398,752,256 | 24,788 |
| 特征分块驻留加块级 Dot | 63,073,102,364 | 34,057,648,768 | 5,620,367,360 | 28,510 |
| 整行驻留加块级 Dot | 8,815,456,028 | 4,663,600,256 | 2,466,250,752 | 3,556 |

特征分块根据张量形状和真实整数依赖发现，宽度由最小本地 SRAM 字数的四分之一得出，归档上为 256 项。每块带绝对输出记录地址，边界确认后才能消费。特征版本共用有限窗口，淘汰仍有消费者的唯一副本必须写回。特征分块相对原整行驻留少读 380,928 B，整层 DDR 写入仍为 7,601,955,200 B。

块级配方用已测 P/E 边界、实际站点绑定和同一 DDR 描述符模型计价。静态 S16 权重与 S32 激活按多个输出复用。准备命令、固定 SRAM 暂存、转换、散写和外部确认均入账。常数及临时区有实际分配范围。只有整 K 完成后才舍入，部分和 DDR 流量为零。固定输出窗口的配方要求 canonical DDR 提交，所以遇到命名的 SRAM 输入或输出时保留标量配方。DP 在特征分块版本中为 92 次派发选了块级配方，整行版本为 14 次派发选用了它，覆盖 7 个静态权重投影，包括 Gate、Up、Down。块级配方最大 P0.S 暂存 8,320 B。SRAM 交接峰值另列 P0.S、U0.S 各 8,192 B，二者的时间区间应以窗口和命令事件为准。

Down 仍执行完整 K 归约。Gated 激活在该评估中仍经过 DDR，其唯一 canonical 数据为 352,256 B，实际搬运包含重复读取。现有归档仍无 P0.S→U0.S 的通用 SRAM 直传，QK 缩放保持既有路径。Block V2 原生范围及块级目标指令编码、硬件 ACK、系统时延和吞吐待验证。

## 复现

远端目录 `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/qwen-feature-7hxru8`。沿用本页上方的 TILE_FRONTIER.md 对应源模型、权重和参考整数原语入口。给 benchmark_event_layer.py 增加 `--depth 0 3 --width 8 --modes sram features block-tile row-block-tile`。带 `--tile-profile` 传 algorithm-fix-261-tile-plan-replay/proof/probes 下的 column-v3-profile、probe-v5-profile 和 local-round8-tile-inputs-20261109-v1/instance-services.json，带 `--tile-worker` 传 algorithm-fix-268-corrected-tile-numeric/native-tile-host。两组输入用独立 Slurm 作业并行验证。Python 3.12，计算结果单位为现有 PR182 代价模型拍。

- 114233 为 [1,2]，report-114233.log 的 SHA-256 为 2f09f14f8681012cc0dad3f1b66365a342631ca254f64133a59711135e8769d6。
- 114234 为 [42,43]，report-114234.log 的 SHA-256 为 86cde1176204b442710bb4c0a5a05a3a3add1b3b938dd6e1d34bf8bdd29ea1e2。
- 114232 的 unittest discover 收集 422 项，416 项通过、6 项跳过，regression-114232.log 的 SHA-256 为 1593d5ca0b12d11aac7d7c8888ae287bf5c382e3574f6fc801fc9661c22782b6。仓库结构核验通过。
