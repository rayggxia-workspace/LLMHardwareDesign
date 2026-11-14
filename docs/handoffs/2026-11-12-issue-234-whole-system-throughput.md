# Qwen2.5-3B 整机吞吐实施与验收交接

- 日期与交接人：2026-11-12（CST），YUZE-LU。
- 任务：[LLMHardwareDesign Issue #234](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/234)。当前负责人为 YUZE-LU，接手人由项目负责人指定。
- 分支：`task/234-whole-system-throughput-handoff`，基于 `main` 的 `c4d7b960599b9d292f27eb4429d5f226a7156c95`。本次提交号见交接 PR。独立工作树，已有实现和远程作业保留原状。
- 当前状态：已补入[指令驱动事务级评估代码](../../project/experiments/systemc_benchmark/README.md)，可运行两步 decode 和短 prefill。正式 P512/D128 联合仿真和物理验收仍在进行。

## 目标

在远程服务器用项目实际硬件配置，执行完整 Qwen2.5-3B 的 **B1、512 token prefill、连续生成 128 token**。沿用已冻结的真实 checkpoint、prompt、质量门和对照基线。按项目合同补做 128 和 2048 输入场景。模型执行使用编译产物和上一步实际生成的 token、KV，参考模型用于独立核对数值。 [现有基准合同](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/eaf3008868982e5ac6c2f70878250c148ec6d009/work/YUZE-LU/234/BENCHMARK_CONTRACT.md)

## 实施原则

1. **缺什么就在产生实际行为的层补什么。** 缺算子就补算子到原生指令的 lowering，缺服务就补相应 RTL 和接口，缺仲裁就补真实请求队列与仲裁，缺 DMA 或存储响应就补相应控制和时序接口。每个修复先验证真实数据与握手，再接回联合仿真。硬件自身的改动单开关联 PR，记录版本与适用的验收结果。
2. **一次运行走完整链路。** 图、权重和资源清单经编译生成母控／局控镜像及连接需求。联合仿真装载对应镜像和拓扑，由实际控制、互联、宏和存储接口推进 36 层以及词表投影和 token 选择。覆盖 Attention（含 RoPE、Softmax、KV 读写）、FFN、归一化、残差及其他运行路径。时序依赖按真实完成事件释放，背压可一直传回请求端。
3. **存储调度纳入同一时间轴。** 绑定实际 SRAM 的容量、分银行、端口和冲突，覆盖局部／共享存储中实际用到的路径。DDR 请求由运行中的 DMA 发出，逐笔跟踪事务身份、物理地址、读写方向、burst、接受、响应和依赖。覆盖同地址反复访问、RAW/WAR/WAW、请求排队、存储竞争、KV 分配和写回。按实现的内存可见性与写入完成合同推进消费者，保留 DDR 接收、转发、写命令和实际完成的区别。SystemC 可以驱动联合仿真，外存器件可用已绑定配置的逐命令周期后端。当前型号、通道、位宽、频率和仲裁全部列入运行清单。
4. **禁止用估计、近似或替代执行补中间缺口。** 旧 DP makespan 换算、单层乘 36、FFN 时序拼接、查表时延、主机算出中间张量后注入、离线请求表预先喂给 DDR、理想 SRAM、无代价拷贝、等价软件算子代替实际硬件，以及改短上下文、绕过 KV、弱化质量门或对照配置，均不得用于整机验收。组件级实验可帮助定位故障，验收证据须来自完整联合运行。发现缺口后保留失败证据、修复真实路径、复跑验收。

## 恢复执行的入口

| 证据 | 已验证范围与下一步 |
| --- | --- |
| [PR #235](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/235)，`eaf3008868982e5ac6c2f70878250c148ec6d009` | 有真实控制及算子组件的 SystemC/RTL 对照、独立 DDR 桥和完整形状的主机整数参考。联合运行先把实际 DMA 端口接到 DDR，按事务 ID 对账，覆盖同址混合读写与写尾排空。 |
| [PR #251](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/251)，`9abd46f5cbb4534bcfc614571ccd6d402ad11882` | 有原生 FFN 组件和控制证据；已有系统表仍含估算的服务周期。复用已实测的 RTL 与握手入口，逐项消除完整执行路径中的替代服务。 |
| [PR #257](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/257)，`461f533a813cf5bc08974ee84968b2f731f4a2cf` | 已验证事件 IR 和固定 FFN 的回放。需要把完整模型 lowering、部署镜像、实际连接与 RTL 退休事件接成一条执行链。 |
| Slurm `101602`，`FAILED 1:0` | 两个 P512 样本分别在连续生成第 51 个 token 与首次 prefill 超出原数值门。修复实际产生异常数值的算子、格式或状态路径，保留原失败 prompt 和原门槛。 |
| Slurm `103217`，`COMPLETED 0:0` | 对两条失败样本复核了 36 层 K/V。Decode 的五项超限张量中，新增位置贡献均超过 99.7% 的平方误差，最早超限为第 30 层 K/V。Prefill 的误差分散在多个位置，第 34 层 V 相对 L2 为 4.01%。 |
| Slurm `103220`，`COMPLETED 0:0` | 隔离的 DDR 桥组件改版支持重复读。三次同址读得到三次回调，器件模型发出两条读命令。原配置的负例仍为 64 次写回调、60 条实际写命令。同址混合读写和实际 DMA 仍需接入，组件改版尚未进仓。 |

远程目录为项目服务器上的 `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-234-systemc-benchmark/`。原始失败在 `sequence-recipe-001/case-2` 和 `case-3`。`strict-kv-localize-OhtHd3pH/result.json` 的 SHA-256 为 `882f1e7b77086368fab694f77b162bca001738ea9e088546a56dfa857e77ac92`，`strict-dram-repeat-ZyprDHdt/receipt.json` 为 `0e80372f6dfc79c29d07bf6bd06555da90d5544f010f64d868f2706071c876f0`。两个组件报告均已校验。接手先复核报告与当前分支状态，再从实际 DMA 到存储的链路开始联调，同时补齐 Attention/KV 等尚未接通的原生服务。小规模回归用于定位和验证修复，随后必须跑完整验收。

## 完成门槛

- [ ] **数值与状态**：全模型执行，连续生成 128 个 token，全部步骤通过原定质量门；实际生成的 KV 跨步延续。核对关键算子边界、数值、地址与写回，保存失败轨迹。
- [ ] **整机执行**：同一次联合仿真覆盖编译产物、母控、局控、算子 RTL、互联、有限 SRAM 和 DDR。退休 token、指令及必要存储事务可对账。没有假完成事件、遗漏服务、未清的应完成事务或绕过背压的请求。
- [ ] **吞吐**：保存请求开始、首 token 及其余各 token 的仿真退休时间。报告 TTFT、prefill 时间、整请求吞吐和 decode 吞吐。按冻结口径计算，decode 为 `127 / (t128 - t1)`，整请求为 `128 / (t128 - t_start)`，时间单位为秒。频率和时钟域必须对应已核实的硬件配置，报告可重算的周期和时标。
- [ ] **能耗和最优适配对照**：按已验证的活动与能耗边界报告 J/token，缺失能耗记录为待验收。采用面向 3–4B 充分优化的 ASIC／FPGA 配置，记录模型、精度、输入长度、批量、带宽与硬件边界。保持原 FPGA 性能和能效门槛。若落后，保留原结果，区分算法、硬件和存储瓶颈，修复后重新实跑。算法 20% 指标用相同硬件和数值合同的对照来验证，配方及硬件收益分别记录。
- [ ] **复现**：保存代码、程序、硬件、权重、输入和工具版本，Slurm 作业号、退出状态、运行命令、仿真日志、数值与事务检查和结果 SHA-256。数值、吞吐及对应验收项达标后再关闭任务。

本 PR 包含短程评估代码、服务回归与已有远程回执。项目登记沿用[管理中心 PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5)。项目看板按[现有接入交接](2026-10-21-issue-7-projects.md)处理。
