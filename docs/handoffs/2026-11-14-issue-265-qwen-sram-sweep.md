# #265 PR #260 SRAM 带宽核验交接

2026-11-14（Asia/Shanghai）。任务分支 `task/265-qwen3b-system-evaluation`，负责人 Melodydt。[Issue #265](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/265) · [PR #266](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/266)。PR #260 来源 `dd423e5a8010e7371ee1ccbd589df00bc0ff6478`，复跑源码 `560f637450fa016b76daa7749681c3c5351d8b2a`。Windows 工作区是任务文件副本，未上传本地缓存。运行目录由 [机器回执](../../work/Melodydt/265/qwen-sram-sweep-20261114.json) 记录。

五个新作业均使用 c96/node17，单核，状态截至 14:20 CST 为 RUNNING。Decode 为已有 512 位置代表性 KV 的两步、计时一个退休间隔，Prefill 为两个空 KV 起步的输入位置，计时到第二个末层残差。固定每通道 32 个 DDR 额度、KV 读窗口 8、核周期 3,334 ps、DDR 周期 630 ps。

| 归档 / 新作业 | 配置 | 参考耗时 | 参考吞吐 | 完整核对前缀 |
| --- | --- | ---: | ---: | ---: |
| 107947 / 111631 | 128-bit Decode | 828.821615 ms | 1.206532 tok/s | 70 / 582 |
| 108284 / 111632 | 512-bit Decode | 478.260746 ms | 2.090910 tok/s | 94 / 582 |
| 108359 / 111633 | 512-bit Prefill | 369.831191 ms | 5.407873 输入 tok/s | 142 / 578 |
| 110382 / 111634 | 512-bit 加 SRAM/DMA 流水 Decode | 427.533726 ms | 2.338997 tok/s | 92 / 582 |
| 110383 / 111635 | 512-bit 加 SRAM/DMA 流水 Prefill | 363.205987 ms | 5.506517 输入 tok/s | 142 / 578 |

使用每档冻结的 PR #260 服务代码，更换 #265 的批量 DDR 推进方式并独立执行。已检查前缀逐字段相同，最终比较器会记录逐页偏差、实际退休、DDR、完整吞吐和审计结果。整机仿真沿用同一类 TLM 服务模型。完整的硬件时序、数值验收仍由 #234 跟踪。

```bash
ssh yuzelu@10.129.166.172
cd /public/home/yuzelu/Melodydt/runs/issue-265/qwen-sram-sweep-20261114-01
squeue -j 111631,111632,111633,111634,111635
sacct -j 111631,111632,111633,111634,111635 -o JobID,NodeList,State,ExitCode,Elapsed
tail -n 15 107947/slurm-111631.out
for d in 107947 108284 108359 110382 110383; do
  (cd "$d" && sha256sum -c output.sha256 && cat comparison.json)
done
```

上述命令在各自新目录成功生成输出清单后核验。逐项确认退出码 0:0、应有 582/578 页、时长、吞吐、退休或输入位置、轨迹、DDR 及执行审计。由 Melodydt 负责下一次读回和结果登记。作业独立于聊天运行，未安排定时轮询。

独立估算检查只用 107947 的第一步校准，根据两个冻结 ATT1 描述符序列计算 SRAM 合并拍数。第二步 128-bit 为 1.206682 tok/s，相对参考 +0.01245%。把同一规则直接迁移到 512-bit，预测 547.067217 ms / 1.827929 tok/s，参考 478.260746 ms / 2.090910 tok/s，相对延迟误差 +14.3868%、吞吐误差 −12.5773%。ATT1 服务预测只多 1.685 ms，其它服务多 67.122 ms，占总误差 97.6%。模型固定了 128-bit 的非 ATT1 耗时，漏掉 FFN、词表投影、QKV 和 O 投影等加宽收益。流水配置的搬运与计算重叠超出该规则范围。此规则是在参考已发布后建立，拟合仅用 128-bit 首步，没有盲测预登记。既有单拍 KV 估算器保留原配置范围。

```bash
probe=work/Melodydt/265/audit_qwen_sram_width_transfer.py
python -B "$probe" predict PHASE1_DESCRIPTORS PHASE2_DESCRIPTORS TRACE_107947 > prediction.json
python -B "$probe" score prediction.json TRACE_107947 TRACE_108284 TRACE_110382
```

描述符分别在封存部署 `phase-1/descriptors.bin` 和 `phase-2/descriptors.bin`，以脚本内 SHA-256 核对。从[原始仿真档案](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/dd423e5a8010e7371ee1ccbd589df00bc0ff6478/work/YUZE-LU/234/native-sram-width/README.md)和[流水实验档案](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/dd423e5a8010e7371ee1ccbd589df00bc0ff6478/work/YUZE-LU/234/MEMORY_PIPELINE_EXPERIMENT.md)取得参考时间线。估算本地已复算一致，30 项现有测试、项目结构检查和服务器 `bash -n` 通过。项目登记待合并，`config/board.json` 缺失，待具权限维护者核验 #265。
