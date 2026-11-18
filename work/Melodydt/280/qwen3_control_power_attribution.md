# Qwen3 控制、取指、时钟和互连的功耗归属

2026-11-17（Asia/Shanghai），Melodydt。BSCC 上的 `wave-audit/audit-38782228/mode-0-down/signal-table.tsv` 在 FFN 作用域记录一个 `feed_forward/dut/G` 实例的时钟，与原 117749 绑定的 C639 G 相符。整模型的物理实例驻留和时钟门控仍需核对。[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) · [草稿 PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281)

## 已对照的分项与工件

| 分项 | 已有证据 | 纳入三窗前的检查 |
| --- | --- | --- |
| G32 本地时钟、开钟空闲与动态 | `117749` 以 TT 300 MHz 重算 116943 的四个零握手窗和 116950 的两窗，每窗实标 77,423 引脚。四个零握手窗约 2.660–2.703 mW/已测叶，功耗报告的 `Clock` 组约 0.867 mW，已包含于叶块总值。 | 用 `c380-g32-power-300-03/result-117749/summary.json` 的同工况空闲参考，核对实际 G32 物理实例、开钟时间和门控状态，再折算空闲基线。现有三窗已含 G32 活跃减空闲的增量，新增开钟基线时不再折入全活动窗功耗。 |
| C639 四端点控制交换机 | `117841` 的 `mdt_c639_switch` 使用 `cohort/transport`，`REBIND_TARGET=4'b0001`、`LOCAL_TARGET=32'b0`，TT setup/hold +746.803/+23.705 ps，DRC 0，后端等价通过。零握手 78.328–78.398 µW，`117856` 的正常／背压各 20 个握手周期约 78.550 µW。 | 比较冻结 RTL、参数和交付目标拓扑，核对交换机实际实例与三窗握手。20 握手的结果供现有抽样参考。`cohort/mother/transport` 是另一个 RTL 层级，按物理范围明确归属。 |
| 局控 PM 阵列 | `38794460/38794931/38795055` 对 `lc_program_store_1k` 给出 352 B（22 个 128-bit 字）的启动写入＋CRC、同初态的读回，而 `38795749` 提供按真实页类别的 PM 桥能量。 | `local_controller/pm` 的阵列端口与外部装载桥分开归属。运行读口按实际 `pm_valid/pm_ready`、`pm_rsp_valid/pm_rsp_ready` 和地址分类；`0.187457 nJ/22 字` 仅作同类阵列读吞吐参考。 |
| 局控描述符 fetch | 旧入口 `run_c639_control_component_power_300.sbatch fetch` 对 `lc_scope_fetch128` 四站点的 `start`、`fetch`、`mc_req`、`mc_rsp` 接口计数。`117940` 止于 CTS hold 缓冲上限，功耗缺失。 | 可先复核当前 C639 的完整握手和端口数据，之后用已验证的 BSCC 物理流程取得匹配的网表、SDC、SPEF 和 STA／DRC。对应 `local_controller/scope_fetch`，与程序阵列本体、DDR 传输和 DMA fabric 分开计。 |
| 母控核和其余局控／调度 | `38796363` 记录 11 个逻辑作用域、六窗的位宽、信号翻转和 VCD 别名。包括产品边界、母控核、母控 transport、四局控和四 dispatch。 | 匹配物理实现前保留逻辑活动。产品边界是抽样入口，各子域只对同一物理单元计一次。已完成的 U 字级控制、U ADD2 调度和 E32 逻辑从读数入口逐一标注。`#223 mother_control_64` 与 `#250 packet` 的候选号需做同源或等价确认后再绑定。 |
| 上层互连和时钟树 | `117841/117856` 是单块交换机，G32 和其他叶块的报告可包含本地时钟。冻结整机的上层寄生和全局时钟树仍待匹配。 | 建立以物理实例路径、clock root 至 leaf 入口、SPEF net 为键的覆盖清单。叶块已计本地驱动与时钟组。上层分项只收相邻块之间的网、顶层时钟网和未计入的缓冲；叶端 pin capacitance 的充放电归属结合对应 SPEF/Liberty。 |

参考结果路径、校验和及工具输入见 [117749 300 MHz 标定](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/80fec96d68fb991f4a79b9acfc5fb49199192dd9/docs/handoffs/2026-11-16-issue-280-power-calibration-300.md)、[117841／117856 交换机](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/8b0a8783c5b165232f0e17653a71ac7d1d39aa69/docs/handoffs/2026-11-16-issue-280-m-eco-switch-300.md) 和 [BSCC-T6 分项标定回执](../../docs/handoffs/2026-11-16-issue-280-bscc-t6-actual-payload-and-leaf-calibration.md)。

## 用现有六份 FST 复核运行时 PM 阵列活动

`38796363` 的 JSON 只记录部分接口的逐位翻转，临时 VCD 已删。以下使用冻结的 `38792112` FST 和原有转换工具。脚本读取 `local_controller/pm` 的 128-bit 运行读接口，按工况、相位、站点保存采样窗内的请求、返回、错误和窗口两端待返回计数。验证 8,192 个上升沿和请求守恒。两端待返回用于处理跨采样边界的事务，程序装载和 CRC 走独立的配置接口。

在 BSCC-T6 的 `~/LLMHardware/zenanyan/issue-280-bscc-t6-01/pm-runtime` 放置同目录的 [`qwen3_c639_pm_runtime_audit.py`](qwen3_c639_pm_runtime_audit.py) 和 [`run_bscc_t6_qwen3_c639_pm_runtime.sbatch`](run_bscc_t6_qwen3_c639_pm_runtime.sbatch)。脚本在同一容器运行，使用 `v6_384` 分区、4 核和无限时限。生成的 JSON 还保存每个有效读地址的次数。

```bash
cd ~/LLMHardware/zenanyan/issue-280-bscc-t6-01/pm-runtime
sha256sum qwen3_c639_pm_runtime_audit.py run_bscc_t6_qwen3_c639_pm_runtime.sbatch > inputs.sha256
job=$(sbatch --parsable --time=0 run_bscc_t6_qwen3_c639_pm_runtime.sbatch)
squeue -j "$job" -o '%i|%j|%T|%M|%N|%C|%l|%R'
sacct -X -j "$job" -o JobID,State,ExitCode,Elapsed,NodeList,Timelimit
tail -n 30 "slurm-$job.log"
(cd "pm-runtime-$job" && sha256sum -c results.sha256 && cat pm-runtime-audit.json)
```

三窗已有 TLM 装载事件按页记录，`qwen3_component_observation.py` 的 `wrap_pm` 只观察 `install_pm`。全窗运行读需再确认 Qwen3 实跑中实际发出的元数据／指令读，按物理站点、页地址和退休边界计数。地址、返回数据、错误、停顿和控制器 `pm_trace_valid` 要在同源全窗或代表波形交叉核对。窗口内的载荷敏感性以保留程序的空闲对照和读窗评估；六个 C639 短窗只能核对覆盖。
