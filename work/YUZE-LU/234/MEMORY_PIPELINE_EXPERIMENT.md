# SRAM 与 DMA 流水化对照

沿用 #260 的封存部署、双通道 DRAMsim3、八笔 KV 读窗口、512-bit 数据 SRAM 和 3,334 ps 核心周期。Decode 从代表性 512-position KV 连续执行两次，prefill 从空 KV 执行两个输入位置。以 108284 和 108359 为对应基线。

| 路径 | 实验变化 | 验证边界 |
| --- | --- | --- |
| Attention 搬运 | 两笔 S 写在途，DDR 回包窗口八笔，逐笔回收后释放分片 | 128-bit RTL 实现可选双写在途。DDR RTL 仍为单笔 |
| Attention 分片 | 在原 256-word 工作区切两个 128-word 槽。QK 由 8 行改 4 行，AV 由 128 行改 64 行 | TLM 分摊同一个 S 端口。QK 每次启动仍计 128 拍，包含缩小分片的额外开销 |
| Embedding、FFN 输入、回载 | 八笔 DDR 在途，每笔占用缓冲直至 S 确认，单段最多发两拍 S 请求 | TLM |
| KV / Down 写回 | 八笔端到端在途，组包后才交 DDR，收到全部提交回调才结束。Down 维持三 P 地址映射 | TLM |
| FFN 跨 S | 当前片写入和激活时最多预读下一片。独立保留一份 Gate/Up 返回，写确认由原路径回收 | TLM。RTL 的响应阻塞风险须另验 |
| PM 写入 | 同一 DDR 返回内按流水写计时，完整校验费用照计。在 512 bit 时单返回已是一笔，周期相同 | TLM |

远程工作目录为 `/public/home/yuzelu/project-circuit/issue260-sram-pipeline-qk3uTFl1`。110382 跑两步 decode，110383 跑短 prefill，110390 等两组完成再执行对照审计。每个运行目录留逐页时间线、摘要和审计，源码快照由 `source.sha256` 固定。入口是 `run_native_tlm_request.py --pipeline-memory`，基线默认关闭。

加载器专项 Verilator 作业 110389 通过连续发写、在途上限、回压和故障后排空。注意力外层用两槽顺序 FIFO 保存 SRAM 写标签，旧单笔模式默认保留。外层与真实 SRAM、母控、局控、DDR 的回归 110399 两种模式均通过，分别执行 227,431 和 436,458 拍，每种核对 15,200 个 KV 回调和 52,489 个 SRAM 应答，并逐字对照输出。其余流水化的整机结果属于 TLM 时序敏感性实验。

## 已执行的同页对照

| 范围 | 512 bit 基线 | 512 bit 加流水 |
| --- | ---: | ---: |
| Decode 首层 Attention 页 | 5.801 ms | 4.473 ms |
| Decode 首四层 | 43.540 ms | 37.797 ms |
| Prefill 首四层 | 20.425 ms | 20.109 ms |

首四层逐页核对 DDR 读写数和母控指令周期。Decode 以两次词表退休的时间差计算吞吐，短 prefill 以两个输入位置除以至第二个末层残差的时间计算。当前合并试验保留 V 重复读取，没有扩大计算阵列。可选的 128-bit RTL 双写在途尚未进物理验收。

| 128-bit Attention RTL 同夹具 | 单写在途 110405 | 双写在途 110399 |
| --- | ---: | ---: |
| mode 0 | 257,599 拍 | 227,431 拍 |
| mode 1 | 436,458 拍 | 436,458 拍 |

两种模式的输出逐字一致。mode 1 对应夹具施加的背压，保留这一零收益结果。两项 RTL 对照的源码和结果散列在远程各自的 `replay-JOB/proof.sha256`。

| 整段配置 | 512 bit 基线吞吐 | 512 bit 加流水 |
| --- | ---: | --- |
| Decode，已有 512-position KV，连续两步 | 2.0909 tok/s | 2.3390 tok/s（+11.87%） |
| Prefill，空 KV，两个输入位置 | 5.4079 tok/s | 5.5065 tok/s（+1.82%） |

两组均完成并通过 110390 对照审计。Decode 审计覆盖 582 页，两次词表退休间隔从 478.261 ms 降至 427.534 ms。Prefill 审计覆盖 578 页，两个位置总耗时从 369.831 ms 降至 363.206 ms。逐页核对母控指令周期、服务调用和 DDR 请求与回调，decode 还核对两次退休的 token ID 与跨步 KV。整段结果采用母控指令驱动的 TLM 回放，局部服务以模型执行。见 [decode 对照](memory-pipeline-receipts/decode-comparison.json) 和 [prefill 对照](memory-pipeline-receipts/prefill-comparison.json)。

基线回执见 [SRAM 位宽实验](native-sram-width/README.md)。用相同部署、同一组 DDR 参数和执行参数分别运行基线与流水模式。流水模式由 `--pipeline-memory` 打开。运行命令见 [decode](memory-pipeline-receipts/run.sbatch) 和 [prefill](memory-pipeline-receipts/prefill.sbatch)。结束后用 `python work/YUZE-LU/234/audit_memory_pipeline.py decode BASELINE_DIR CANDIDATE_DIR` 对照。Prefill 将子命令换成 `prefill`。输入目录须包含 `execution.json`、`timing-audit.json` 和 `page-timing.jsonl`。

RTL 的参考基线是原生集成分支上的 `9e190fd81` 搬运器。本 PR 分支尚未包含该原生集成的 RTL 依赖，随回执提供可在原生集成工作树应用的差异和验证命令。ATT1 程序和描述符沿用现有格式。

原生集成 RTL 可用 `git apply --check work/YUZE-LU/234/memory-pipeline-receipts/attention-rtl.patch` 检查基线兼容性，并在目标原生工作树应用该差异。专项夹具在 [test_s128_ddr_range_load_pipeline.sv](memory-pipeline-receipts/test_s128_ddr_range_load_pipeline.sv)，容器和 Verilator 命令见 [Slurm 配置](memory-pipeline-receipts/rtl.sbatch)。完整组件夹具用 `PIPELINE_KV_WRITES=0` 和 `PIPELINE_KV_WRITES=1` 各跑一次 `project/experiments/block_local_native/run_native_attention_core_scope.sh`。
