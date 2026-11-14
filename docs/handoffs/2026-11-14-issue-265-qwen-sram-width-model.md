# #265 SRAM 多位宽快评与 256-bit 对照交接

2026-11-14（Asia/Shanghai）。任务分支 `task/265-qwen3b-system-evaluation`，负责人 Melodydt，[Issue #265](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/265) 和 [PR #266](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/266)。已封存预测源码 `f435526317e75915feaea3297044881640f9a64a`，256-bit 基准源码 `affb579af39dab80faad3ec49170ba9b820b564b`。Windows 项目目录是文件副本，`.local` 缓存保留本地。结果和 SHA-256 见[机器回执](../../work/Melodydt/265/qwen-sram-width-estimate-20261114.json)。

以 107947 的 128-bit、八笔 KV 窗口的第一步校准。各页从母控页、局控镜像表和二进制描述符提取工作量。数据 SRAM 以 128-bit 字为单位，对齐的口组分别容纳 1、2、4 个字。模型按目标位宽重新计算 PM、Embedding、DMA、Q/K/V、Attention、O 投影、FFN、Down 和词表投影的 SRAM 拍数及确认等待。串行数据请求为两拍应答加一拍接续，PM 和 Embedding 以两拍计。FFN 取每个三 P WAIT 波次的最长 P 路径，加共享量化、Gate/Up 输出汇集、Mid 及激活搬运。DDR/其它残差使用校准页，Attention 残差按上下文缩放。SRAM 改宽造成的 DDR 行命中、仲裁和重叠变化属于残差。设置为非流水、核 3,334 ps、双通道 DDR 630 ps、每通道 32 credit。

| 位宽 | 第二步预测 | TLM 参考 | 吞吐相对误差 |
| --- | ---: | ---: | ---: |
| 128 | 1.206683342 tok/s | 1.206532241 tok/s，107947 | +0.01252% |
| 256 | 1.724335825 tok/s | 待 111693 第二次退休 | 待核验 |
| 512 | 2.077392362 tok/s | 2.090909630 tok/s，108284 | −0.64648% |

512-bit 预计退休间隔 481.372714424 ms，参考 478.260746356 ms，相差 3.111968068 ms。原 ATT1-only 结果低估吞吐 12.5773%。256-bit 预测在首次读取参考耗时前封存，首 150 页观测 251.407101366 ms、预测 252.735823724 ms，延迟误差 +0.52851%。该批尚未完成首次词表退休。111693 的参考从 108284 源副本只放宽位宽校验，两份改动散列已确认。

111738 在 c64/node11 单核 76 秒完成，估算计算 74 秒。127 个反馈间隔对应 C513–C639，128/256/512-bit 分别预测 1.126325、1.627322、1.974047 tok/s。长上下文误差尚缺同配置完整退休对照。固定延迟的四-bank 端口模型覆盖 128/256/512-bit。流水调度、不同端口延迟或不同 bank 拓扑需对应模型。#234 继续跟踪正式 P512/D128 联合数值与 RTL 验收。

```bash
ssh yuzelu@10.129.166.172
sacct -j 111631,111632,111633,111634,111635,111693,111738 -o JobID,NodeList,State,ExitCode,Elapsed
cd /public/home/yuzelu/Melodydt/runs/issue-265/qwen-sram-256-20261114-01
tail -n 20 slurm-111693.out
sha256sum -c output.sha256
python -B /path/to/estimate_qwen_sram.py compare /public/home/yuzelu/Melodydt/runs/issue-265/qwen-sram-estimate-20261114-01/prediction.json candidate/page-timing.jsonl --sram-bits 256 --execution candidate/execution.json
```

111693 在 c64/node2 单核运行。完成后由 Melodydt 按上述命令核验 582 页、两个实际 token 和延迟误差。上轮五档见[回放交接](../../docs/handoffs/2026-11-14-issue-265-qwen-sram-sweep.md)。111633 和 111635 已完成，各 578 页逐字段一致，吞吐误差 0；三个 Decode 复跑仍由 Slurm 独立执行。没有配置自动跟进。30 项既有和 3 项新位宽回归、项目结构检查通过。审查人待指定、Issue 进行中，登记 PR #5 待合并。Projects 缺 `config/board.json`，具权限维护者待核验。
