# Algo1 多输出组与全宽激活复用

2026-11-15 CST · [Issue #219](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/219) · [草稿 PR #273](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/273)

## 原生硬件合同

[DOWN_NATIVE_CAPABILITIES.json](DOWN_NATIVE_CAPABILITIES.json) 记录本轮静态核对的边界。归档的 Down 原生 P 投影每个 scope 有 16 组八路 S32 上下文，最多覆盖 128 列。U 可以分批供 K，P 在同一 scope 期间保留归约进度。P 流式描述符在 `p_scope128_decode.sv` 明确拒绝部分 K scope。该命令接口因此没有可用于跨 Down scope 交错的 checkpoint 动作。独立的 Attention 内部模块含 S80 checkpoint，单个八路图像占 7 个 S128 字，其中 2 字是元数据。这条路径的 `REUSE_V` 模式与 Down 的流式描述符分开，归档的 resident Attention 绑定也未选该模式。

U0/U1→P0 的 projection feed 合同涉及范围搬运和窗口 lease。固定 FFN Mid ring 还可选一个 P.S 写入，等对应的 16 次写确认才发布。已知连接支持分发到指定目的端，当前合同缺少让多个暂停的 Down scope 消费同一份活跃 tile 的接口、端口可用性和费率。原生代码与归档路径见 JSON。

对 `native-ffn-candidates-114185` 的 U0+P0 和 U1+P0 命令 DAG 独立解码，结果一致。Qwen 首层两个 token 行，K=11,008，每行 16 个完整 K scope，每个 scope 计算 128 列。Mid 以 S32 表示，两个 token 行合计写 88,064 B，192 条 Down load 读 1,409,024 B，同一段被 16 个输出组各读一次。交接总量为 1,497,088 B，即每 token 行 748,544 B（731 KiB）。这是静态命令清单的字节数。该清单的已有证据是候选编译及部分服务检测，范围截至全局选择和联合执行之前。审计代码为 `audit_tile_frontier_native.py`。

## 通用范围 DP

每个算子状态记录已分配的输出前沿、已发布的输出位图以及若干有序的活动组 `(输出起点, 输出终点, 已归约前缀)`。每步既可开新输出组，也可推进已有组。分几组、组宽和 K 步长由相同搜索选择。组允许乱序完成，消费者只读自己所需的已发布范围。若存在尚未打开的输出组，旧 K 片段仍可能被读，需要保留本地版本或已落实的 DDR 副本。全部组已分配后，最慢的活动组决定哪个 K 前缀可释放。剩余读者、工作区和部分和共同参与容量判定。独立部分和 bank 也可作为输入资源，容量和带宽均明计。beam 限定的搜索保留整算子、整 K 与单组方案作为候选回退。

## 同图对照

沿用 Qwen2.5-3B 首层的 `v288 Product → v289 Dot`，一个 token、全部 2,048 输出列、完整 K=11,008，权重流量固定 45,088,768 B。下表每行采用 16 KiB 数据 SRAM、2 KiB 工作区、基线 DDR 和数据 SRAM 分别 16 和 64 B/拍。整数原型默认激活 16 B/项，各行使用有界 beam。单组在各组硬件参数下均回退到整 K 路径。所有最终计划均与同输入的整段整数结果逐位一致。

| 选择 | 额外部分和能力 | 交接 DDR | 估算工期 | 部分和片上读写 |
| --- | --- | ---: | ---: | ---: |
| 整算子 | 无 | 352,256 B | 3,217,792 | 0 B |
| 整 K、允许驻留 | 无 | 327,680 B | 3,216,672 | 0 B |
| 多组候选 | 与数据共用 16 KiB，S64 | 327,680 B | 3,216,672 | 0 B |
| 多组候选 | 独立 8 KiB、256 B/拍，S64，DDR 优先 | 327,680 B | 3,216,672 | 0 B |
| 多组候选 | 独立 16 KiB、64 B/拍，S64 | 0 B | 3,215,248 | 655,360 B |
| 多组候选 | 独立 32 KiB、64 B/拍，按 S80 参考镜像密度计价 | 327,680 B | 3,216,672 | 0 B |
| 多组候选 | 独立 32 KiB、192 B/拍，按 S80 参考镜像密度计价 | 0 B | 3,211,008 | 1,146,880 B |

16 KiB 独立 bank 的成功路径使用两组 1,024 列。这同时需要服务在模型层允许一个 1,024 列的可续接 dispatch，超出当前 P scope 的 128 列。DP 给两组交替喂同一个 512 项激活 tile，直到最慢的组用完再释放。DDR 少 327,680 B，总 DDR 降约 0.72%。工期只比相同池的整 K 路径少 1,424 拍，约 0.044%。S80 行采用 112/8=14 B/列的计价密度，仍是原整数运算的模型，不能作为 S80 物理实现的吞吐测量。

另以每项 4 B 的打包激活口径做敏感性对照。独立 S64 bank 16 KiB、256 B/拍时，交接从 59,392 B 降至 0，模型工期从 3,181,936 降至 3,180,672（约 0.04%）。抽象模型里完整 K 动作只为该读取范围计一次激活服务，所以该结果不可与原生命令清单的 16 次读取直接相减。

## 复现与接入条件

独立远端工作目录为 `issue-219-block-search/multi-output-O8GNpG`。仓库内的汇总在 [TILE_FRONTIER_MULTI_OUTPUT_RESULTS.json](TILE_FRONTIER_MULTI_OUTPUT_RESULTS.json)。字节审计结果在 `evidence/native-U*.json`，模型表和逐动作计划在同目录。Slurm 114413–114418 与 114426–114429 完成；114421 验证六个范围 DP 用例，包括多组共享、容量受限和乱序发布。114441 通过 32 项相关回归。没有启动 RTL 或完整首层 token 作业。

```sh
python -B -m unittest -v test_tile_frontier
python -B audit_tile_frontier_native.py U0-ffn-candidate.json
python -B benchmark_tile_frontier.py ARCHIVED_HARDWARE.json --columns 2048 --width 32 --sram-rate 64 --ddr-rate 16 --bank-bytes 16384 --bank-rate 64 --accumulator-bytes 8 --max-group-outputs 1024 --multi-groups 4 --output report.json
```

当前能力下打开多组搜索没有收益，原型继续保留在独立评估入口。后续先对现有编译器重复读取的 16 份 Mid 逐次记账，优先核对现有固定 Mid 环路和缓存路径能覆盖哪些绑定。只有能表达实际范围发布、独立上下文和端口约束的能力可以接入普通图 lowering 与原生指令生成。
