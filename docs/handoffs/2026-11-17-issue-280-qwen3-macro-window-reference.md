# Qwen3 三窗 SRAM 与母控 PM 参考小计

2026-11-17（Asia/Shanghai），Melodydt。任务分支 `task/280-seven-model-energy`，本轮起点 `32010d91bcf625e520929c442c8a7b73bde3632c`。[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) · [草稿 PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281) · [300 MHz 分项标定](2026-11-17-issue-280-sram-mother-pm-calibration.md)

## 对账及计算口径

冻结的活动源为 `rollup-38782605.json`。短 Prefill、首 Decode token 和两次退休间 Decode 时长为 **85.289804550／139.703051690／139.833834508 ms**，分母依次为 **2 个输入／1 个输出／1 个输出 token**。以已归档的 DDR 器件、G32 活跃增量、旧 M、写 DMA、U ADD2 逻辑小计为底数。对实际使用的 G32 #250、旧 M、写 DMA 38792114 和 U 三个叶的布线网表搜索同名 S128 宏，均无实例。母控 `program_store` 的四个宏有独立物理层级。先前 SRAM 位宽参考单列项由本次两种情景替代。

- **SRAM**。P、CONTEXT、MID、U 四个 TLM 站点均有 512-bit 读。逐窗验证各位宽事件和拍数、字节数、四 bank 总访问数守恒。当前工件中 `local_s_p` 有四 bank feeder，`local_s_base` 的 `wide_req` 接零。情景分别假定四个站点各部署一个 S_P 或 S_base，全程开钟。S_P 的 512-bit 读用测得的四 bank 同址系数，S_base 用四个普通 128-bit 读作串行估算。两种写侧都使用已测 128-bit 写及串行 256／512-bit 写组。稳态 P 站点的最少接受周期占原时间窗 **48.33%（S_P）／77.18%（S_base）**，只计端口接收基本需求。原时长固定，真实站点配置、时序调度和新增宽度拆拍对 tok/s 的影响待后续核验。
- **母控 PM**。由 **38794389** 的实际装载事件重新归窗，确认起止都落在窗口内、请求串行、有效长度和 128-bit 写拍一致，再与 **38782605** 的独立 PM 观察及 **38795749** 的页类别对账。三窗分别为 **58／30／30 次母控页装载**。240／272／1,616 B 的读回按原标定页的 15／17／101 次 128-bit 读折算。默认一组四宏全程开钟，在安装阶段采用对应静默基线和实际逐沿 Liberty 内部能量增量，其他时段取读就绪静默基线。母控的页载入与读回能量按此场景估算，运行时取指、宏外控制、装载桥及未覆盖的开关功耗均单列待补。

## 结果

| Qwen3 窗口 | 母控四宏（mJ/token） | S_P 情景 SRAM（mJ/token） | S_P 情景覆盖小计（W） | S_P 情景覆盖小计（mJ/token） | S_base 串行敏感性小计（mJ/token） |
| --- | ---: | ---: | ---: | ---: | ---: |
| 短 Prefill | 1.961 | 9.711 | 3.71954–3.72238 | 158.619–158.740 | 157.066–157.187 |
| 首 Decode token | 6.424 | 32.043 | 3.40368–3.40454 | 475.504–475.625 | 470.590–470.711 |
| 稳态 Decode | 6.430 | 32.073 | 3.40190–3.40277 | 475.701–475.822 | 470.783–470.904 |

新增能量主要来自整窗开钟的 SRAM 与母控宏。S_P 情景的静默功耗为约 **272.70 mW**（四组 SRAM＋一组母控四宏）。区间沿用已覆盖小计中各项的样本端点，SRAM 及母控 PM 的实际放置和门控不确定性未纳入该区间。旧版 M 的 300 MHz 时序违例沿用原回执。S_base 情景固定相同的三窗时长作为敏感性对照。数据内保留两种情景各站点操作数、最少接收周期、完整 W 与 mJ/token，以及三类 PM 页逐窗分项。[机器可读结果](../../work/Melodydt/280/qwen3_macro_window_reference.json)

## 复现

服务器 `ssh.cn-zhongwei-1.paracloud.com`，任务根 `~/LLMHardware/zenanyan/issue-280-bscc-t6-01`。本轮为既有结果的 Python 汇总，直接在任务目录运行，无新 Slurm 仿真。以 S_P **38814341**、S_base **38814342**、母控 **38814399** 的完成清单为输入。

```bash
cd ~/LLMHardware/zenanyan/issue-280-bscc-t6-01
dest=macro-window-reference-20261117
raw=real-activity/replay-38794389
sha256sum -c "$dest/inputs.sha256"
sha256sum -c "$dest/results.sha256"
PYTHONPATH="$PWD/covered-ledger-20261117" python3 -B "$dest/qwen3_macro_window_reference.py" \
  covered-ledger-20261117/windows.json independent-rollup/rollup-38782605.json \
  sram-macro-power/sram-38814341/s-p/calibration.json \
  sram-macro-power/sram-38814342/s-base/calibration.json \
  mother-pm-macro-retry/result-38814399/mother-pm-macro-power.json \
  pm-real-length/pm-38795749/pm-pages.json "$raw/dma-windows.json" \
  "$raw/prefill-w4-tile128-pr272-combined/real-activity.json" \
  "$raw/decode-live-w4-tile128-pr272-combined/real-activity.json" \
  "$dest/reproduced-$(date +%s).json"
```

`windows.json` 的 SHA-256 为 `e87a9a2097870bf0dabad1b1be0f486a78c6318af71b84abf7975136fc0e2541`，输入清单 `146d86349e7dee776075e6e4baacc51a31c2b42d2dc887f32cbd8d56e6cbe7c0`，结果清单 `6d46c4b0a822aa1abab781160e484a609092cd0e7f49ff2ea52cf425d74083b0`。实际验证输入清单、产物 SHA、TLM 三窗时长及访问计数。项目管理检查和 Python AST 均通过。

## 接续

Melodydt 下一步以全模型布局与时钟约束确认四个 SRAM 站点的实物配置和开钟驻留，补局控 PM 运行且保留数据的静默、母控运行取指以及剩余控制／互连和时钟。11:32 查验时原版读 DMA 38769386／38769388 已运行约 18:50，跳过 SHARE 的对照 38795299／38795300 已运行约 12:02；依赖功耗 38795516–38795519 仍在等待。通过读侧物理及波形对账后再出含 DMA 的三窗估算。正式 300 MHz 的 M 时序验收保持独立。PR #281 为草稿，Issue #280 进行中，登记 PR #5 待合并，Projects 条目待核验。
