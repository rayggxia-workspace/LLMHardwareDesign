# Attention V 复用与投影权重取数对照

沿用 #260 的封存 Algo1 程序和描述符。Attention RTL 的 `V_READS_PER_16` 可选 4、2、1，默认 4。模式 2 只请求包含当前输出组的 64 B。模式 1 在既有工作区保留 32 行完整 64 B，复用一套 Dot 分两次计算，通过两份七字 S80 快照切换累加上下文。硬件源码差异见 [原生集成补丁](av-weight-receipts/att1-v-reuse.patch)。该补丁面向原生 RTL 集成工作树，局部提交为 d3177e6c9。

## 原生 Attention RTL

实际 C380 回放。各组逐地址核对 K 读一次及 V 的 4、2、1 次，输出逐字一致。三组均启用前一轮的 SRAM 双写在途。数字包含 QK、Softmax、AV 和服务交接。

| V 每地址读次数 | K/V DDR 回调 | 常规周期 | 加背压周期 |
| ---: | ---: | ---: | ---: |
| 4 | 15,200 | 227,431 | 436,458 |
| 2 | 9,120 | 176,169 | 372,533 |
| 1 | 6,080 | 143,977 | 357,118 |

[逐地址审计](av-weight-receipts/independent-address-audit-c380.json) · [Slurm 回执与散列](av-weight-receipts/)

在封存的 C639 末步用例上，111867、111868、111869 也逐字通过。常规周期为 380,934、295,370、242,964，施加背压后为 730,433、625,278、598,293。三组的 K/V 回调为 25,560、15,336 和 10,224。

## 母控指令驱动的 TLM 回放

`--av-value-fetch selected` 每组只取有用的一笔。`--av-value-fetch paired` 每笔用于两组，以两个顺序 Dot 过程和显式 SRAM 上下文读写计时。两次 Dot 的乘加量不变。窗口容量、访存数量和等待因果均显式建模，S80 命令开销仍用模型时序。`--rtl-weight-fetch` 模拟 M 的有限 W 缓冲、请求入队、回包和在途额度。见 [取数实现和原生轨迹](NATIVE_TLM_WEIGHT_FETCH.md)。

首层 decode 的 Attention 页用时基线 4.473 ms，selected 3.914 ms，paired 5.483 ms。paired 少发 196,992 笔的重复读，但在该 TLM 里放弃了双窗口流水，并增加了逐行 S 读取和上下文保存开销。C380 原生 RTL 的三组使用同一串行分片装载结构，两个结果需要各按其执行方式解释。首层短 prefill 的 FFN 从 3.378 ms 降至 2.767 ms，仅打开权重取数修改。

| 对照配置 | 两步 decode | 两 token prefill |
| --- | ---: | ---: |
| 512-bit 流水基线 | 110382 | 110383 |
| 仅去掉无用 V 读 | 111841 | |
| 仅复用 V | 111855 | |
| 仅更新权重取数 | 111856 | 111857 |
| V 复用和权重取数 | 111858 | 111859 |
| 只取必要 V 地址和权重取数 | 111875 | |

远程目录为 `/public/home/yuzelu/project-circuit/issue260-av-weight-GEwVA0Bi`。完整回放结束后由相应 Slurm 依赖任务执行 [对照审计](audit_av_weight.py)。审计逐页核对母控指令、服务调用、DDR 读写和 KV 结果，DDR 读数差额必须全部来自 AV。整段吞吐待完整回放。物理时序仍待验收。

## 28 行双窗口对照

`--pipeline-memory --av-value-fetch paired-ping-pong` 使用两个连续的 V 窗口，每个为 112 个 S128 字。两份七字快照紧接在第二个窗口后面。总共占用 238 字（3,808 B），均在描述符既有的 256 字工作区中。算当前片与加载下一片同时发起，两条路径共用一个带仲裁的 S 端口。当前片的两组计算和快照操作、下一片写确认均完成后才换窗口。单窗口 `paired` 保留用于对照。

逐页新增 `av_refill_compute_overlap_ps` 与 `av_checkpoint_elapsed_ps`。前者计两条路径同时在执行的墙钟区间，后者包含快照命令计费、共享端口等待及 S 应答，两个计数可以互相重叠。局部测试用 69 个位置跨过两个分片边界，验证 V 各地址只读一次、K 不变、与原方式输出逐字一致，以及非零重叠。

远程目录 `/public/home/yuzelu/project-circuit/issue260-av-weight-GEwVA0Bi/paired28`，两步 decode 作业 111910，两 token prefill 作业 111911，对照审计 111913/111914。配置保持 512-bit 数据 S、相同程序和 DDR 参数，关闭权重取数新模式以隔离 V 改动。已有的串行 V1 RTL 仍是硬件证据。28 行双窗口是 TLM 实验，待原生 RTL 实现与物理验收。

## 独立 KV 回包槽

`--kv-response-slots 16` 为候选 ATT1 路径加入 16 个回包槽，保留 8 个读请求额度。发请求时预留槽位，DDR 返回即归还请求额度，S 写确认后才归还槽位。S 写入器可先写已返回的位置，Dot 仍等整片写确认。单通道绑定和 S 端口配置使用原设置。局部测试用乱序回包核对全部 V 地址、输出、读额度和回包槽上限。

沿用 selected V、512-bit S、修订后的权重取数。两步 decode 作业 111977，与 111875 的唯一区别为回包槽模式。两 token prefill 作业 111978，对应无回包槽的短 prefill 权重对照 111857，另含 selected V。两组远程路径为 `/public/home/yuzelu/project-circuit/issue260-av-weight-GEwVA0Bi/kv-slots16`，源文件由 [散列](av-weight-receipts/kv-slots16-source.sha256) 固定。作业 111981 和 111982 负责完成后对照审计。回包槽为候选系统 TLM 改动，硬件实现待验证。

## ATT1 的 SRAM 请求流水

`--attn-sram-pipeline` 允许 ATT1 最多同时跟踪四份回填数据从提交写请求到写确认，读取一段连续数据时最多保持两拍请求未应答。读写和上一版共用同一个 512-bit S 端口，每拍最多接受一次访问，响应延迟仍为两拍。回填窗口写齐后才放行对应的计算。两组使用同一部署、母控指令、局控调用和描述符，保留 8 笔 KV DDR 读额度和 16 个回包槽，DDR 频道绑定和 S 容量相同。

| 已完成且逐页匹配的范围 | 原配置 | 开启 ATT1 SRAM 流水 |
| --- | ---: | ---: |
| C512 decode 前七层，总耗时 | 56.187 ms | 47.919 ms |
| C512 decode 前七层，仅 Attention 页 | 27.367 ms | 19.104 ms |
| 空 KV 两 token prefill，第一个位置前九层 | 37.606 ms | 37.580 ms |

表中各层计入从第一条层内指令到本层结束的时间，独立的 embedding 页及 decode 词表头由整次作业计入。完成的对照页中，母控指令周期数、局控调用绑定和次数、DDR 事务数以及各 S 读写次数和字节数一致。首层 Attention 页的 DDR 读为 197,060 笔、写为 128 笔。七层平均约少 1.18 ms，其余层节省相近时，36 层约少 42.5 ms/token。若沿用前一版约 376 ms/token 的临时估值（111875 的 289.204 ms 前缀加 110382 的 86.828 ms 词表页），得到约 3.0 tok/s 的规划值。完整吞吐使用实际退休时间计算。 [逐页对照](attn-critical-path-receipts/matched-prefix.json)

| 作业 | 两步 decode | 空 KV 两 token prefill |
| --- | ---: | ---: |
| 同配置基线 | 111977 | 111978 |
| ATT1 SRAM 流水 | 112069 | 112070 |
| 等两边完成后逐页审计 | 112116 | 112117 |

流水组远程目录为 `/public/home/yuzelu/project-circuit/issue260-av-weight-GEwVA0Bi/sram-rw-pipeline`。启动方式与该目录的 `decode.sbatch` 和 `prefill.sbatch` 一致，参数为 `512 --av-value-fetch selected --rtl-weight-fetch --kv-response-slots 16 --attn-sram-pipeline`。结果写入各 `run-<job>/sram-pipeline-comparison.json`。 [执行源 SHA-256](attn-critical-path-receipts/sram-pipeline-source.sha256) · [对照审计](audit_av_weight.py)

`python scripts/check_project.py` 通过。运行 `python project/experiments/systemc_benchmark/test_native_tlm_services.py` 通过 10 项，其中 Attention 用 69 个位置和乱序返回，在 128/512-bit 下验证输出逐字一致、逐地址 DDR 事务及有限队列。512-bit 端口与新的 ATT1 供数时序属于 #260 候选 TLM，硬件 RTL、物理时序及当前两次完整吞吐回执仍待验证。Issue #234 保持开放，审查人待指定。看板配置缺失，当前 Issue 未返回已关联的 Projects 条目。协作规则版本为 rayggxia-project-collab 1.0.0，登记沿用待核验状态。
