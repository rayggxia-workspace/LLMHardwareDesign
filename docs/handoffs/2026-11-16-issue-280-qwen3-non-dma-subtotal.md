# Issue #280 Qwen3 三窗非 DMA 已覆盖功耗小计

2026-11-16（Asia/Shanghai）。项目 `llm-hardware-design`，仓库 `rayggxia-workspace/LLMHardwareDesign`，负责人 Melodydt。任务分支 `task/280-seven-model-energy` 的线上 HEAD 已读回为 `91812f2891ba9ec563fb5a41aff71920129fe761`。本轮脚本与回执存于本地管理目录 `D:/Study_material/Study_material/LLMHardwareDesign`，以及服务器本人目录。 [Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) · [草稿 PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281)

## 已覆盖结果

沿用 #274 的三 P、512-bit SRAM、全 28 层以及 Decode 真实 512 位置历史。整窗边界和退休数与 DDR 探针逐项核对。两输入 token 的短 Prefill 计 1,344 次 FFN 激活服务，两个 Decode 窗各计 672 次。由冻结 TLM 的 `ACT/VECTOR/op1`（11/8/1）实现，每次服务对应 32 个 SRAM 字，每字计算两个 G32 packet，故分别为 86,016、43,008 和 43,008 个模型 G32 输入包。 [冻结 DDR 窗口](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/049bd82218920e0b3786dfc9dfc7a0ed3534d3b5/work/Melodydt/280/QWEN3_DDR_PILOT.md)

| 窗口 | 时长（ms） | DDR（W） | G32 活跃增量平均值（µW） | 已覆盖小计（W） | 已覆盖小计（mJ/token） |
| --- | ---: | ---: | ---: | ---: | ---: |
| 短 Prefill，两输入 token | 85.289805 | 2.695278 | 43.73–48.64 | 2.695322–2.695327 | 114.9417–114.9420（输入） |
| 开始到首个 Decode token | 139.703052 | 2.382134 | 13.35–14.85 | 2.382147–2.382149 | 332.7932–332.7934（首 token） |
| 两次退休间 Decode | 139.833835 | 2.380359 | 13.34–14.83 | 2.380372–2.380373 | 332.8565–332.8567（输出） |

小计 = 双通道 DDR 器件 + G32 FFN 活跃增量。G32 使用 117749 的 300 MHz 结果。各工况下，从接受 64 个输入的 C639 活跃窗减去等长、零握手的 Down 参考窗，得 2.77524–3.08680 nJ/64 输入。两端是正常和背压的参考差异，范围未覆盖状态差异或从 C639 向 Qwen3 TLM 转标的误差。G32 各窗实标 77,423 个引脚。G32 空闲基线等明确留在待补分项。表中小数位便于追溯增量，系统精度待验证。 [G32 标定](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/80fec96d68fb991f4a79b9acfc5fb49199192dd9/docs/handoffs/2026-11-16-issue-280-power-calibration-300.md)

## 尚未计入

- **片上功耗**：G32 常驻空闲、三路 M、SRAM、PM、控制交换机及其他控制、计算、互连和全局时钟。局部样本留待逐实例的整窗时间或事件计数对齐。特别是 M 的 268.51–272.19 mW/路是局部端口活动估值。已归档的 TLM 服务耗时包含等待，共享资源活动无法从服务总耗时直接反推。同一个 SRAM 宏、片上模块的空闲基线、本地时钟和漏电各计一次。
- **片上 DMA**：保留原运行流量、等待和背压，DMA 电功耗按本轮评估口径留空。
- **外部**：DDR PHY、板级 I/O 与终端能耗留空。已覆盖的 DRAMsim3 数值为 DDR 芯片器件模型。

下一步由 Melodydt 从原 TLM 回放获取每路 M 的活动与空闲驻留，并把 SRAM/PM 计数按真实模块、位宽、bank 掩码和三窗对齐。随后补完整母控与局控、其他计算、互连及时钟。DMA 综合独立推进。当前完成的是第一版局部覆盖小计。

## 复现

本轮仅执行已有 JSON 的轻量积分。使用服务器 Python 3.6.8，未提交新的 Slurm 仿真。DDR 原回执、两份全层回放 `result.json`、G32 活跃和空闲源清单、以及 117749 全套清单均复核。生成的 `summary.json` 记录 8 个输入与脚本 SHA-256。脚本散列 `5683956cd8b43d0d8cce8afa6f7edac75297b1f445c8f7b238243f34186687b2`，服务器结果清单文件散列 `b10c2a79af24f6712a61ba4ceb394a7c3716d4ef069015e68aca75e1a6643cb1`。

```bash
ssh yuzelu@10.129.166.172
r=/public/home/yuzelu/Melodydt/runs/issue-280
p=$r/ddr-pilot-02/pilot-116481
replay=$p/staged/replay/run-116481
cd "$r/qwen3-non-dma-subtotal-01"
sha256sum -c replay-inputs.sha256
sha256sum -c results.sha256
cat summary.json
python3 -B qwen3_non_dma_subtotal.py \
  --prefill "$replay/prefill-w4-tile128-pr272-combined/result.json" \
  --decode "$replay/decode-live-w4-tile128-pr272-combined/result.json" \
  --ddr-prefill "$p/ddr-prefill.json" --ddr-decode "$p/ddr-decode.json" \
  --g32-power "$r/c380-g32-power-300-03/result-117749/summary.json" \
  --g32-active-counts "$r/c639-g32-active-01/power-116950/summary.json" \
  --g32-mode0-idle "$r/c639-g32-power-03/power-116943/mode-0-down/functional.json" \
  --g32-mode1-idle "$r/c639-g32-power-03/power-116943/mode-1-down/functional.json" \
  --output "reproduced-$(date +%s).json"
```

项目检查 `python scripts/check_project.py` 通过。规则 rayggxia-project-collab 1.0.0。同步前复核服务器结果清单，仓库中的 [结果 JSON](../../work/Melodydt/280/qwen3_non_dma_subtotal.json) 对应服务器 `summary.json`，SHA-256 `b678fa91b600df44e2f16ee676dcc6afe6ba55a391427472551bdae05913bd15`。#280 进行中，PR #281 草稿，登记 PR #5 待合并。项目未配置专属 Projects 看板，组织总览的 #280 条目待管理员核验。
