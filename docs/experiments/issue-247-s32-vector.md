# S32 向量路径：实施、速度校准与面积评估

2026-11-11，Asia/Shanghai；负责人 Melodydt；[Issue247](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/247) / [PR243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)。本轮落实上一阶段第一项建议：补齐原图 S32 E 子集，再把两槽队列的真实收益纳入原评价体系。生产配置默认关闭，交付待审查，未合并。

## 1. 本轮结论

已增加四通道原生 signed32 E 核，接入串行/两槽/四槽前端。计算使用完整乘积和宽中间值，支持 signed7 位移量，末端统一饱和到 S32。原图中 shift=34/35 及负 shift 不再依赖截断后的 5 位字段；S32 数据也不截短为 S16。

真实 U 后端下，64 个 S32 值的一输入算子由 208 拍降为两槽 138 拍，吞吐提升 50.72%；二输入算子由 288 拍降为 198 拍，提升 45.45%。四槽分别为 131/198 拍，二输入没有额外收益。测量包含真实 S 读写、计算、写 ACK 与完成退休。

沿用原 8 场景，S32 两槽相对同口径串行的 prefill 提升 16.38%（shared）和 17.94%（idealdual）。两槽 prefill 为 2.940530/3.219458 token/s；四槽再提高 0.11%/0.12%。这是局部实测校准后的条件模型，不是完整模型 RTL 实测。

新数字可能低于上轮 4.184811/4.773362：这次把原先理想化的 S32 本地服务替换为完整 U 实测期，校准范围发生了变化。旧配置本身没有变慢，8 个完整历史控制全部复现。不能将局部队列加速倍率直接乘到整图，也不能把历史条件估计当作硬件已达到的速度。

## 2. 出发点：先解决原图位宽，再讨论扩宽

上一阶段队列主要测了 S16 算术，但三个原 trace 中可以直接按纯 S16 E 处理的算子为 0。原图有 S32 乘法、转换、加减和最大/最小；prefill 还有超过 31 的右移和负向左移。仅把 8 个 S16 通道当成 8 个 S32 通道，会同时误算精度、端口字节数和速度。

本轮选择先在既有 128bit 数据口放四个 S32 值，验证足够宽的数值合同和有限队列，再测瓶颈。保留共享池 32KiB、A32B/拍、DDR17.1GB/s、2P/1U 以及实际原本地 S 仲裁器，没有扩容或虚构每拍一个事务。

按位宽、元数、移位和等形状筛选：decode512/decode2048 各 108 个算子、543744 个值；prefill2 为 1909 个算子、24228352 个值。仅匹配一输入 Convert 或二输入 Add/Sub/Product/Maximum/Minimum，全部输入输出 S32，元素数为 4 的倍数，无广播。混合位宽、多输入、广播、未支持的 canonical 算子继续保留旧模型费用。

该筛选只是形状和算术合同的候选映射。trace 不含完整真实激活值和量化尺度；本轮不能证明完整模型精度，也未生成混合 S16/S32 图调度器。

## 3. RTL 方案与具体做法

### 3.1 数据通路与数值合同

新增 `block_v2_e_s32.sv`，每个 128bit 向量字含四个有符号 32 位 lane。乘法先得到 64 位积，FMA/RoPE 的合并中间量使用 65 位，舍入/移位使用 96 位；不在最终输出前截窄。核心采用两步执行：输入接受时锁存算术中间量，随后舍入、饱和并保持输出，等待 out_ready。它不是 II=1 的 S32 流水核。

| opcode | 操作 | shift 合同 |
| --- | --- | --- |
| 0/1 | 加/减 | 忽略 shift |
| 2/3 | 乘/乘加 | 正数 RNE 右移，负数饱和左移 |
| 4/5/6 | 最大/最小/按 C 非零选择 A | 忽略 shift |
| 7/8 | 饱和左移/算术右移 | 只接受非负 shift |
| 9/10 | 成对 RoPE/重定标 | 正数 RNE 右移，负数饱和左移 |
| 11 | 绝对值 | INT32_MIN 最终饱和 |
| 12..15 | 本 ABI 不支持 | 返回 error，不写 S |

RNE 为最近值、恰好中点取偶数；负数先按向下取整商和非负余数判定。shift 范围 -64..63。左移量达到 32 且值非零时直接判饱和方向，避免有限宽移位溢出后符号翻转。out_saturated 表示至少一个 lane 最终越界；非法指令返回 error。RoPE/FMA 合同只保证本 ABI，未声称与整图多算子中间饱和完全等价。

### 3.2 与现有 U、有限队列连接

`pu_u_group` 增加 E_S32 参数，默认 0；`block_v2_e_compact` 增加 S32 参数；串行及队列服务增加 SHIFT_WIDTH 参数，默认 5，S32 时为 7。只在选择 S32 的 U 实例改变 shift 接口宽度，默认 S16 路径保留原行为。E_S32 分支优先于 E_PIPELINE，不能把旧 S16 的流水开关当作 S32 II=1。

建议后续集成选择 E_S32=1、E_QUEUE_DEPTH=2。队列沿用按序读/发射/写回、RAW 等待写 ACK、WAR/WAW 保序及有限占用；没有新增跨客户端一致性。direct-A/abort、错误不写回、done 背压和 reset 合同保持。reset 清控制状态，已完成的 SRAM 写不回滚。

这是静态配置的 S32 实例，尚无运行时 S16/S32 混合分发、S16 输出 packing 或广播 lowering。部署完整图仍须补这些环节。共享容量和原 S 仲裁未变；备份分支 `task/247-before-s32-vector` 固定在 e22e60c6868795fb0f2e708c7e21358ce19a8b03，已在线读回。

## 4. 原生测试与周期结果

run49/job102642，c96/node15/4核，COMPLETED 0:0。共 186 次运行：旧参考/默认/两槽 S16 各 9 例×3，S32 深度 0/2/4 各 11 例×3，NExp 两种格式各 3 次。冻结旧 U 与默认配置的 27 对周期、流量、结果及覆盖观测完全一致。

Python 任意精度整数 oracle 与 RTL 独立实现；seed=2474701，含 S32 极值、正负舍入中点、所有 16 opcode×128 移位组合、相关/别名、direct/abort、IO 争用、完成背压及三个 reset 时点。每次运行检查每条命令的结果/error/saturation、读写数、写 ACK 先于完成、队列容量和全部 1024 个存储字。构造数据通过不等于真实激活推理质量通过。

下表固定同一 SRAM 后端和 S32 核。前四项各 64 条命令；mixed_edges 为 2048 条；hazards/direct 为 128 条；最后两个 tile 各 16 条，即 64 值。不同负载不能横向比较速度。

| 负载 | 串行 | 两槽 | 四槽 |
| --- | --- | --- | --- |
| unary_s32 | 832 | 546 | 515 |
| binary_s32 | 1152 | 774 | 774 |
| product_s32 | 1152 | 774 | 774 |
| convert_s32 | 832 | 546 | 515 |
| mixed_edges | 29024 | 19190 | 18149 |
| hazards | 2524 | 2115 | 2115 |
| direct | 1834 | 1076 | 901 |
| backpressure | 1207 | 918 | 774 |
| io_contention | 2114 | 2114 | 2114 |
| unary_tile | 208 | 138 | 131 |
| binary_tile | 288 | 198 | 198 |

两槽/四槽二输入 tile 都需 32 次读、16 次写和 16 次写 ACK，总计 48 次 S 事务，198 拍约为 4.125 拍/事务。四槽一输入 32 事务用 131 拍，约 4.094 拍/事务。这是完整服务比例，不能误写为 SRAM 宏延迟。现有仲裁采用 IDLE/SEND/RETURN 且仅容许一条在途事务，是接下来优先修改的协议瓶颈。

run47 在 sbatch 阶段因 DOS 换行被拒绝，没有作业号；修正 job.sh 为 LF 后使用新目录 run48。run48/job102637 的 168 次回归和 8 项面积也全部通过；run49 在相同生产 RTL 上补 64 值 tile 用例，全量重跑为 186 次。历史目录和 SHA 均保留。

## 5. 原评价体系的各场景结果

固定 300MHz 条件频率、2P/1U、P/U 私有容量基线、共享池 32KiB、A32、DDR17.1GB/s。shared 与 idealdual 含义沿用原模型：idealdual 是 P 读写端口条件场景，本轮 U 在两列都使用同一真实单事务服务测量，不能把它解释为所有实际 SRAM 都具备理想双端口吞吐。

单位 token/s。旧条件列是上轮完整 RESULT 重新复现；S32 三列使用同一新增校准范围，彼此才是本轮队列收益的直接比较。

| 场景 | 上轮条件复现 | S32串行校准 | S32两槽校准 | S32四槽校准 |
| --- | --- | --- | --- | --- |
| W8 decode512 shared | 3.449322 | 3.365489 | 3.394608 | 3.394608 |
| W8 decode512 idealdual | 3.700221 | 3.603919 | 3.637330 | 3.637330 |
| W16 decode512 shared | 1.932379 | 1.905784 | 1.915087 | 1.915087 |
| W16 decode512 idealdual | 2.192427 | 2.158256 | 2.170194 | 2.170194 |
| W8 decode2048 shared | 2.817071 | 2.760903 | 2.780469 | 2.780469 |
| W8 decode2048 idealdual | 2.994659 | 2.931267 | 2.953331 | 2.953331 |
| W8 prefill2 shared | 4.184811 | 2.526565 | 2.940530 | 2.943791 |
| W8 prefill2 idealdual | 4.773362 | 2.729773 | 3.219458 | 3.223368 |

模型冻结 run46 生成源码，8 个历史 RESULT 完全一致；32 次 SystemC 运行及 160 个篡改负控通过。每个可匹配 64 值 tile 保留原 cache/DDR 访问顺序，移除旧向量计算费与本地 S 读写费，改为一次实际 U 服务期。两槽一/二输入为 138/198 拍，不能再叠加理想 E pipeline 加速。不足 64 值但仍为 4 的倍数时保守按完整 tile 计费。

prefill 两槽校准覆盖 1909 个算子、378640 个 tile、24228352 个值，其中不满 64 值 tile 为 144 个；移除旧 E 费用 7950288 拍，新增包含 S/ACK 的完整 U 费用 73033200 拍。旧本地 S 费用单独移除，精确 subcycle ledger 见证据。

检查保持 DDR 读写字节、描述符、M 工作量、cache 事件完全一致；同时验证有限 32 credits、共享池峰值和生命周期、向量工作守恒、token/s 算式和原 trace 覆盖。该模型仍保留未匹配算子的条件假设，未包含完整混合图 dispatcher 的实际开销，因此不声明全图 RTL 校准。

历史 4.773362 是较窄校准范围的 prefill idealdual 条件值；更早 5.112600 还额外假设完整 U8 服务。本轮并未证明任何已部署完整 RTL 模型达到 5 token/s。

## 6. 面积及取舍

Nangate45 同库 Yosys/ABC 标准单元映射；库 SHA 及工具版本见证据。所有 8 项映射完成，没有未映射单元。仅比较本地 E 核/前端/序列器，未包含 SRAM 宏、S 仲裁、N 核、U 胶合逻辑、时钟树及布线；没有 STA/P&R 或 300MHz 物理验收。

| 模块 | 标准单元 µm² | 说明 |
| --- | --- | --- |
| 旧 E 核 | 56905.380 | S16 基准 |
| S32 E 核 | 84061.852 | 本轮四 lane、宽中间量 |
| 旧串行前端 | 2473.002 | shift5 |
| 旧两槽前端 | 9386.342 | shift5 |
| S32 两槽前端 | 9381.288 | shift7 |
| 旧四槽前端 | 18350.542 | shift5，不能当 S32 四槽精确面积 |
| 旧可选流水 E | 59758.230 | 独立比较项 |
| NExp 区域序列器 | 882.056 | 前阶段已有 |

S32 核比旧核增加 0.027156472 mm²（+47.72%）。S32 两槽“核＋前端”相比旧 S16 两槽增加 0.027151418 mm²；相比旧 S16 串行增加 0.034064758 mm²。这些不是全 U/芯片涨幅。前端 shift7 映射面积略小是综合优化结果，不能据几个门的差异推断物理优势。

新增 SRAM 宏为 0。四槽二输入无收益、一输入只再改善 5.34%，不值得在本阶段默认采用更深队列。新 S32 核不是免费优化，但它补上原图位宽支撑；维持默认关闭及备份，等待完整调度与面积/时序审查。

## 7. 下一步具体实施顺序

优先推进 U 本地 S 连续请求协议：在有限请求/响应队列下分离请求接受与响应返回，保证返回路由、读后写/写后读顺序、写 ACK 和 reset；与当前单在途模式做默认逐项对照。先在两槽 S32 上验证每拍请求条件及实际 SRAM 接受能力，再考虑 1R1W，不把端口宽度直接等同吞吐。

随后补混合位宽调度与明确的 Convert packing、广播和多输入 lowering，用真实图中可重放的数据验证。只有具备实际激活/尺度及逐算子一致性证据后，才能扩大校准范围和部署完整模型。

S32 lane 扩到 8/16、更多 M、48/96KiB 共享池和外存提速继续保留为独立方向；本轮结果显示单纯把队列加深到 4 槽已难以改善二输入服务，应先消除本地 S 事务气泡。

## 8. 版本、复现及交付状态

| 运行 | 源码 commit | 作业与状态 |
| --- | --- | --- |
| run48 原生/面积 | 532745f61ddf28af3c722daa99a5621f49e7a43c | 102637，COMPLETED 0:0 |
| run49 正式原生/面积 | a49537ee55dae2003c19fa3d44b5817f9d616db8 | 102642，COMPLETED 0:0 |
| run50 原体系模型 | 68ed552f6291e2d5023ac032e6607ed56aae3222 | 102656，COMPLETED 0:0 |

服务器 yuzelu@10.129.166.172，根目录 `/public/home/yuzelu/Melodydt/issue247-area-speed`；run48/49 为 c96/node15/4核，run50 为 c64/node10/4核。各目录 source/ 保存锁定源码，slurm-作业号.log 为启动日志，results/result.json 为结果。实际启动命令在各根目录执行 sbatch --parsable job.sh；脚本通过 srun 和固定容器运行。

```bash
cd /public/home/yuzelu/Melodydt/issue247-area-speed/run50
squeue -j 102656
sacct -j 102656 -X --format=JobID,State,ExitCode,Elapsed,NodeList
tail -n 30 slurm-102656.log
cat results/result.json
```

原生入口 project/experiments/s32_vector_native/run.py；模型入口 project/experiments/s32_vector_model/run.py；复核入口同目录 analyze.py。每次新建目录，固定 source/input SHA 清单，不覆盖结果。run49 和 run50 的 371 份回收文件 SHA、原生 summary、模型日志 RESULT 均重新核验。

原生 result SHA：0e0d499eb5eddc29cd5cc68da17f644768c898782970c6a3774fe24641633f56。模型 result SHA：9898c1a7181180a3cc00574cf440d078876bad00a9b51f2e29ade6891ea8a742。模型输入 run46 result SHA 固定为 4be10c512c8d28e7e41eaaedab4a4f6803adbc4450458f0ec59f33c49b20c1cc。所有原始构建、全日志、网表留在服务器，以 output-files.sha256 索引；仓库提交有界回执，详见[证据索引](../../work/Melodydt/247/s32-vector-native/evidence-index.json)和[分析](../../work/Melodydt/247/s32-vector-native/analysis.json)。

python scripts/check_project.py 管理结构检查通过，不能替代功能验收。源码 CI42953113735 completed/failure，validate 返回 steps/logs=null，原因待管理员核实，未绕过检查。正式审查人待指定；PR 未合并，Issue 保持 in_review，不标 done。登记 management-hub PR5 open/unmerged，pending；无 board 配置及 Projects 工具，看板 unverified、同步 pending，处理人待指定。遵守 rayggxia-project-collab 1.0.0；全部本轮作业已结束，没有自动监测。恢复从[交接](../handoffs/2026-11-11-issue-247-s32-vector.md)开始。
