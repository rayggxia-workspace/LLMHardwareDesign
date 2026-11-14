# FFN 三路 P 到母控 WAIT 的周期归因

2026-11-14（Asia/Shanghai）。[Issue #270](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/270) · [草稿 PR #272](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/272)，Melodydt，任务基点 `a7ff9e5b06405f518300bc90e18490635b854e62`。本轮在隔离的 PR #260 C639 源归档加仿真探针，原生功能用例为两次 FFN/FDS 与自产残差。设备、指令、权重、时钟、随机种子与 113199 一致。探针适用于 Verilator 5.042 和该夹具的层级及纳秒时标。

## 周期归因

逐条以 `P/owner/record/M bank/generation/EXEC ticket` 对齐。每次 FFN 有 58 组三路 Gate/Up、6 组 Down。用真实母控 opcode 0x11 退休和每组的三路结果配对。每种模式应有 2 页、128 个 WAIT、384 个 scope 和每类 44,032 条权重记录。三路 P 可同时执行，每组选最后交回局控结果的一路。表中等待只统计和该路 M 的 EXEC 到结果区间不重叠的周期，单位是每组平均夹具拍，1 拍 10 ns。

| 指标 | 正常 Gate/Up | 正常 Down | 背压 Gate/Up | 背压 Down |
| --- | ---: | ---: | ---: | ---: |
| 有效组数 | 116 | 12 | 116 | 12 |
| 最慢一路本地总长 | 9,600 | 45,573 | 9,826 | 47,081 |
| 本地配对准备 | 1,204 | 4,398 | 1,043 | 4,480 |
| 权重和激活都未就绪 | 694 | 3,990 | 765 | 4,304 |
| 单独等权重 | 268 | 1,257 | 105 | 178 |
| 单独等激活 | 253 | 715 | 738 | 3,298 |
| 权重就绪后的连接、EXEC 提交和操作数发出合计 | 1,073 | 5,281 | 1,070 | 5,210 |
| 最后一路交回结果至母控 WAIT（中位数） | 11 | 16 | 15 | 13.5 |

正常模式下 P2 单独最后完成 81/116 组 Gate/Up。背压为 P2 37、P1 35、P0 30，另有 14 组并列。平均时延来自两个 C639 FFN 调用，不要求不同层、两步 TLM 和其他工况都由同一路决定。113287 两模式各 384 个 scope 和 128 个 WAIT 严格对账，退出 0:0。数值、页终态、FFN/FDS 和三份 DDR 事务轨迹与 113199 对齐。局控的其他状态仍有时钟开销，尤其是 Down。这里的等待是直接观测到的时间，实际可缩短的周期需用下一轮 A/B 验证。

优先试验 `p_native_weight_overlap_candidate.sv` 中的 `FILL_WAIT / PAIR_ACCEPT_SECOND → W_JOIN`。拆掉已满足资格的老记录 EXEC 对后续配对准备的不必要阻塞是首个假设。先保持四 bank、两侧 DMA credit、固定字节量、真实 A 和 FILL 确认以及 retire 顺序，验证取消、迟到回包和 drain。若该改动缩短配对准备却增加执行空泡，则比较整组 WAIT 和整段时钟后选择。背压下再独立量化激活搬运和 operand 交接。

## 同配置速度

| 场景 | 第四轮 ATT1 完整基线 | FFN 前四层外推 | FFN 完整 TLM |
| --- | ---: | ---: | ---: |
| 两步 Decode，初始 KV 512 | 2.739056 tok/s | 2.926561 tok/s | 待 113165 |
| 两位置短 Prefill，初始 KV 空 | 5.511216 输入 tok/s | 6.316319 输入 tok/s | 6.316164 输入 tok/s |

短 Prefill 为 113166/113167，578 页、72 个 Down 散列、程序和 DDR/SRAM 流量对账通过。同比提高 14.61%，前四层外推比完整结果高 0.0025%。Decode 使用 113070 和 113164 的真实退休间隔以及第二步前四层，外推提高 6.85%。第四轮 ATT1 相对第三轮完整 Decode 从 2.609346 到 2.739056 tok/s，短 Prefill 从 5.511880 到 5.511216 输入 tok/s。

第二个 Decode 的词表页耗时 86.827619 ms，占 ATT1 基线退休间隔 23.78%，1187 次调用覆盖 151,936 列。当前页级计数包含描述符和整个 provider 的累计时间。后续应为 SRAM 输出读回、归约及 retirement 添加单独时间戳。分析可用 [词表页脚本](audit_head16_baseline.py) 复跑。

## 证据与复现

- 源归档、探针、启动命令和工具版本见 [源码清单](source.sha256)、[工具清单](tools.sha256) 和 [Slurm 脚本](run_ffn_wait.sbatch)。同一源码生成流程复用 [prepare_native_probe.py](../ffn-weight-05/prepare_native_probe.py)。
- [正常模式摘要](mode-0-summary.json) · [背压模式摘要](mode-1-summary.json) · [原生探针散列](ffn-wait.sha256) · [短 Prefill 完整对账](prefill-full.json) · [Decode 预测](decode-rebased.json) · [词表页事务收据](head16-baseline.json)。
- 本地项目结构、Python 和 Bash 语法、Verilator 构建、原生两模式功能输出及探针散列、已完成短 Prefill 及第三/四轮 ATT1 短程校验已执行。FFN 新功能、原生端口故障注入、300 MHz STA 和正式 P512/D128 待执行。
- 后续全部步骤与服务器恢复命令见 [交接](../../../../docs/handoffs/2026-11-14-issue-270-ffn-wait.md)。
