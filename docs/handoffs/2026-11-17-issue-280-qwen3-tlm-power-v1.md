# Qwen3 TLM 分项能耗估算 v1

2026-11-17 13:10（Asia/Shanghai），Melodydt。项目 `llm-hardware-design`，仓库 `rayggxia-workspace/LLMHardwareDesign`，任务分支 `task/280-seven-model-energy`，输入源码快照 `dc977453d61d62be77c4873cff7bff9b356a4bc0`。模型回放复用 #274 的 `fbff1bd0e455739f28d9b7dd00b97216fe7bb847`、冻结 DDR 回放 116481 和窗口计数 38782605。[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) · [草稿 PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281)

## 结果

Qwen3-0.6B W8A16，全 28 层，三 P、512-bit SRAM、300 MHz 分项标定。短 Prefill 的分母是两个输入 token。Decode 从真实 512 位置 KV 历史开始，分别报告开始到首个输出及两次输出退休之间的窗口。均值用各自整窗能量除以实际 TLM 时间。两端沿用分项样本，不包含时钟驻留、拓扑或标定转用的建模误差。

| 窗口 | TLM 时长（ms） | tok/s | 片上已覆盖（mJ/token） | 片上已覆盖＋DDR 芯片（W） | 片上已覆盖＋DDR 芯片（mJ/token） |
| --- | ---: | ---: | ---: | ---: | ---: |
| 短 Prefill | 85.289805 | 23.4495 | 50.004–50.127 | 3.8679–3.8707 | 164.944–165.067 |
| 首 Decode token | 139.703052 | 7.1580 | 163.433–163.558 | 3.5520–3.5529 | 496.224–496.350 |
| 稳态 Decode | 139.833835 | 7.1513 | 163.586–163.711 | 3.5502–3.5511 | 496.440–496.566 |

| 窗口 | DDR 芯片 | 旧版 M 三路 | S_P 四站点 | 母控 PM 四宏 | 局控 PM 四份静默 | 局控描述符四份静默 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 短 Prefill | 114.940 | 31.951–32.071 | 9.711 | 1.961 | 5.246–5.247 | 0.962 |
| 首 Decode token | 332.791 | 104.189–104.310 | 32.043 | 6.424 | 17.186–17.190 | 3.150 |
| 稳态 Decode | 332.855 | 104.286–104.407 | 32.073 | 6.430 | 17.202–17.206 | 3.153 |

分项表单位均为 mJ/token。G32 空闲和活跃增量、局部交换机空闲、U ADD2 及写 DMA 活跃增量见 [机器可读结果](../../work/Melodydt/280/qwen3_tlm_power_v1.json)。每个叶的整窗开钟基线按驻留积分，已有配对的活动项按事件数乘单次增量。旧版 M 使用每路忙时间和实测活动／静默功耗，原 300 MHz setup **−1.121800 ns**、hold **−0.053419 ns**。512-bit 数据 SRAM 使用四站点各一个 S_P 的布置情景。局控描述符使用 38815974 每站点零事务窗口的实测功耗，四站点合计约 **22.55 mW**，只积分这项开钟基线。母控 PM 只计已标定四宏和页装载／读回。[SRAM 与 PM 分项来源](2026-11-17-issue-280-qwen3-macro-window-reference.md) · [控制与时钟来源](2026-11-17-issue-280-qwen3-control-power-progress.md)

## 读 DMA 动态敏感性

实测写 DMA 活跃增量按三窗 17,920／8,960／8,960 笔算出每 64 B 单价的样本范围。读侧以对应写侧中点的 0.5、1、2 倍作为显式敏感性假设。两通道的读提交、接受和完成数逐窗相同，三窗分别为 14,782,150／13,794,813／13,801,957 笔。DDR 芯片能耗已计，上列假设只加到片上 DMA。

| 窗口 | 假定同写单价（pJ/64 B） | 同单价读动态增量（mJ/token） | 加同单价读动态后（W） | 加同单价读动态后（mJ/token） | 0.5–2 倍假设敏感性（mJ/token） |
| --- | ---: | ---: | ---: | ---: | ---: |
| 短 Prefill | 23.645 | 0.175 | 3.8720–3.8748 | 165.119–165.241 | 165.032–165.416 |
| 首 Decode token | 23.632 | 0.326 | 3.5543–3.5552 | 496.550–496.676 | 496.387–497.002 |
| 稳态 Decode | 23.580 | 0.325 | 3.5525–3.5534 | 496.766–496.891 | 496.603–497.217 |

读侧的请求队列、返回路径、6,144-bit 扇出和空闲／漏电需独立标定。倍数情景没有读侧误差上界。每漏计 100 mW 整窗常驻功耗，三窗结果分别少 **4.264／13.970／13.983 mJ/token**。其他缺项为母／局控运行取指、九目标母控外围、其余计算控制、跨块互连与全局时钟。DDR PHY 和板级 I/O 另计。

## 复算

BSCC-T6 `ssh.cn-zhongwei-1.paracloud.com`，项目目录 `~/LLMHardware/zenanyan/issue-280-bscc-t6-01`。远端 Python 3.6.6 和本地 Python 3.7.0 均执行积分，JSON 字节一致。来源 SHA、时间与 token 对齐、DMA 三项计数、分项去重、单位转换及错误输入拒绝均通过验证。执行 `python scripts/check_project.py` 通过。本轮未提交仿真，真实读侧综合网表估功耗尚未执行。

```bash
cd ~/LLMHardware/zenanyan/issue-280-bscc-t6-01
out=tlm-power-v1-20261117
sha256sum -c "$out/inputs.sha256"
sha256sum -c "$out/results.sha256"
PYTHONPATH=covered-ledger-20261117 python3 -B "$out/qwen3_tlm_power_v1.py" \
  independent-rollup/rollup-38782605.json "$out/qwen3_non_dma_subtotal.json" \
  covered-ledger-20261117/windows.json m-baseline-power/scenario-38809915/qwen3-m-reference.json \
  macro-window-reference-20261117/windows.json "$out/qwen3_control_idle_reference.json" \
  "$out/qwen3_lc_fetch_power.json" "$out/reproduced-$(date +%s).json"
```

- [计算脚本](../../work/Melodydt/280/qwen3_tlm_power_v1.py) SHA-256 `9ddbb9191f47345ff7b0ba5a06a9cb127d0bb56dc74c7a7bcf97fa774400553c`
- [结果 JSON](../../work/Melodydt/280/qwen3_tlm_power_v1.json) SHA-256 `d7d3a6bd0cff54f99e0343921f636b52db74b25b268300a65a0743ee06c85c17`
- 服务器输入／结果清单 SHA-256 `bad7dcae4fca26eaa75e88ec3b526fc2f75a9b3937d46fca29ea99944740a695`／`0bfbf94e52d2dfd20d4e66995d9f27e8ebad29b3611461d615735b4ca6913415`

## 综合后直接估功耗

1. Melodydt 按下面的路径检查任一读 DMA 的完整技术映射网表及对应的 300 MHz SDC。13:10 读回原版 38769386／38769388 和跳过 SHARE 的 38795299／38795300 均运行中，此时没有非空读 DMA `1_2_yosys.v`。使用跳过 SHARE 的结果前核验功能等价。原后布线功耗链 38795516–38795519 继续等待其原有依赖。
2. 有映射网表后，直接在 OpenSTA 载入 Nangate45 TT Liberty、该网表和 300 MHz SDC，复用 `read-port-preflight/stage-38793408/{mc_dma_fabric_typed_p,c639_dma_phase_ports}/*/ports.vcd` 的六个端口窗口和现有 `gate_power_300` 时标转换。用端口名和宽度核对后读 VCD，记录标注覆盖率、传播活动、漏电、内部及开关能耗。无 SPEF 的首版明确为单元和 pin load 估算，布局布线无需完成即可执行这一步。
3. 配对开钟静默、正常、背压及读写并发活动，将读 DMA 空闲和活跃增量折算回这三窗，替换代理单价。阶段包装含共享 fabric，对同一逻辑只计一次。保留 M 时序和其余缺项，后续补齐九目标母控、运行取指和跨块互连，再扩至另外六个模型。

```bash
cd ~/LLMHardware/zenanyan/issue-280-bscc-t6-01
squeue -j 38769386,38769388,38795299,38795300,38795516,38795517,38795518,38795519 -o '%i|%T|%M|%N|%l|%R'
sacct -X -j 38769386,38769388,38795299,38795300 -o JobID,State,ExitCode,Elapsed,NodeList,Timelimit
find . -path '*/results/nangate45/*/base/1_2_yosys.v' -size +0c | grep -E '(mc_dma_fabric_typed_p|c639_dma_phase_ports)'
(cd read-port-preflight/stage-38793408 && sha256sum -c results.sha256)
```

规则 rayggxia-project-collab 1.0.0。#280 继续进行，PR #281 草稿待审查，独立审查人待指定。登记 [PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5) 待合并。任务分支缺 `config/board.json`，组织 Projects 条目待有权限维护者核验。
