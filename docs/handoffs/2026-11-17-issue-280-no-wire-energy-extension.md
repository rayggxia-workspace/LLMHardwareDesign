# Issue #280 七模型无布线寄生分项扩展

2026-11-17（Asia/Shanghai）。负责人 Melodydt；仓库 `rayggxia-workspace/LLMHardwareDesign`，Issue [#280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280)，草稿 PR [#281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281)，任务分支 `task/280-seven-model-energy`，基分支 `task/274-seven-model-short-throughput`。本地导出工作目录 `D:/Study_material/Study_material/LLMHardwareDesign`；使用 Melodydt GitHub 连接在已有任务分支提交，不覆盖其他会话或本地未同步内容。没有修改主干或合并 PR。

## 本次范围与结果

用户要求在不考虑布局布线寄生时补入每模型缺项。新增九类：普通投影 M 活跃项；写 DMA、U ADD2 链、PM 传输桥驻留；PM 传输装载；局控 PM 启动/CRC、运行读取；描述符取指活动；九目标母控核心。既有分项重新去除线网 RC，DDR 器件项保持原计数和结果。已补入能匹配本轮证据的项目，仍未得到完整芯片功耗，未支持的项目保持未知。

三个窗口为短 Prefill（2 输入 token）、开始到首 Decode 输出、第二步 Decode（各 1 输出 token）。512-bit 数据 SRAM、三 P、代表性真实 512 位置历史、固定 3334 ps TLM 核周期与名义 300 MHz 标定不变。第2步不是长序列稳态统计。

| 模型 | 第2步片上已覆盖 mJ/token | 第2步片上＋DDR mJ/token | 本轮新增片上分项 mJ/token |
| --- | ---: | ---: | ---: |
| Qwen3-0.6B | 158.395–158.745 | 491.250–491.600 | 4.703–4.972 |
| Granite | 163.216–163.568 | 517.193–517.545 | 4.651–4.825 |
| Llama-3.2-1B | 199.902–200.548 | 653.387–654.034 | 6.055–6.464 |
| Falcon-H1-3B | 375.475–376.552 | 1273.719–1274.796 | 11.120–11.752 |
| Gemma-3-4B | 516.407–518.264 | 1728.003–1729.860 | 15.667–16.744 |
| Qwen3.5-4B | 517.359–519.275 | 1761.294–1763.210 | 16.017–17.268 |
| Phi-4-mini | 559.342–561.135 | 1861.728–1863.521 | 16.826–17.911 |

新增项是与**同口径去寄生后的原分项**比较；不能直接相加到 v1.6 含寄生总数。单 M 开钟静默由 248.092443 mW 降至 229.954869 mW。区间是样本端点，不是整体误差界。完整三窗、平均 W、每项细数及原范围对照在 `work/Melodydt/280/*_tlm_power_v2_no_wire.json`，旧版 `*_tlm_power_v1.json` 保留。

## 实验方法和边界

1. 对 M、SRAM、局控 PM/取指、U、写 DMA、PM 桥、G32、交换机的 133 个原活动窗，复用同一单元网络和 VCD，不加载 `read_spef`，也不执行寄生估计。另重算母控 PM 三种页长、每页四种状态的四宏功耗。输入 SHA、活动标注数和输出 SHA 有回执。
2. 这些网络保留原有缓冲器/时钟单元及引脚电容，不能称为全新纯综合拓扑。活动仍有零延迟、端口传播及模型间载荷迁移限制，不计延迟毛刺。库沿用 Nangate45 typical 和既有 #155 SRAM 宏 Liberty；没有用 129-bit SRAM 取代 512-bit 数据接口。
3. 母控使用实际 `mc_native_controller` 九目标核心，STALL_LIMIT=4096、SERVICE_STALL_LIMIT=4096。仅在私有实验副本拆开一个前向 net 声明和原驱动表达式，以适配 Slang；没有改变该表达式或时序状态更新。Yosys 技术映射后加载标准单元定义并要求 `check -assert`，再用六个 C639 边界 VCD 在 300 MHz 无寄生功耗分析。母控 PM、传输和局控不在核心内，不重复计入。全窗使用六样本功耗范围，是状态迁移参考，尚非逐模型母控占空比实测。
4. 六模型普通 M 忙时间来自已验收观察；Qwen3 新增观测用 38825995，核对计划迁移后的内容、全部 result 字段（路径引起的 plan SHA 单独验证）、逐层和输出二进制、DDR 终态，并断言普通 M 与 FFN M 忙区间不重叠。本轮没有重跑 FP32，继承原同输入/历史验收。
5. 局控正常顶层服务按 RTL 的 20 次元数据读取加 3 次指令读取及一次描述符抓取计数，使用原 `services` 分位置统计；嵌套算术不重复算 CALL。PM 启动只在 Prefill/首 Decode 的四次实际装载计入，第二步为零。匹配页长用原样本，其他页长保留按字迁移范围。
6. 驻留假设为三 M、四 S_P、四局控 PM/取指、一份 G32、交换机、写侧、U ADD2 链和 PM 传输桥，以及四母控 PM 宏和一份九目标核心。真实模型部署、实例数和门控仍待验证。旧 M 300 MHz setup WNS=-1.121800 ns、hold WNS=-0.053419 ns；去掉 RC 不构成时序闭合或整模型物理验收。

## 服务器与作业回执

登录 `t6s011227@BSCC-T6@ssh.cn-zhongwei-1.paracloud.com`，工作根目录 `R=/public3/home/t6s011227/LLMHardware/zenanyan/issue-280-bscc-t6-01`，工具根 `~/LLMHardware/opt`。均用 `sbatch --parsable --time=0`，分区 v6_384，全部 UNLIMITED；未取消原作业。

| 作业 | 名称/目录（相对 R） | 源码 commit | 核数 | 结果 |
| --- | --- | --- | ---: | --- |
| 38825938 | mdt-280nw-m / no-wire-power-01 | 736c346b18009540cce0886c29d9a654a2afd363 | 12 | COMPLETED 0:0，4:56，m3ca0707，19 窗 |
| 38825939 | mdt-280nw-control / no-wire-power-01 | 同上 | 12 | COMPLETED 0:0，0:49，m3ca0907，40 窗 |
| 38825940 | mdt-280nw-write_u / no-wire-power-01 | 同上 | 12 | COMPLETED 0:0，0:44，m3ca1202，58 窗 |
| 38825941 | mdt-280nw-sram / no-wire-power-01 | 同上 | 12 | COMPLETED 0:0，0:13，m3ca1908，6 窗 |
| 38825995 | mdt-280qwen-m / no-wire-extension-01 | 9920979287dabbf11c4c9d686645d4ee87c85c79 | 24（2×12） | COMPLETED 0:0，24:55，m3ca0305 |
| 38826075 | mdt-280nw-legacy / no-wire-legacy-power-01 | 44c42a96e7bfcca80039c941bafcb2d7f9123695 | 12 | COMPLETED 0:0，0:22，m3ca1202，10 窗及 PM 宏 |
| 38826201 | mdt-280mc-nowire / native-mother-nowire-01 | 7105a177d92ff43b96ba7f0ba0681ebe026c701f | 12 | 严格连接检查和六窗功耗通过，终态见 no-wire-jobs.json |

原生母控失败/未采用过程保留：38826026 因前向声明被 Slang 拒绝；38826074 因本版 Yosys 不支持 `abc -fast` 失败；38826139 进程 COMPLETED，但其连接检查未加载库定义，1253 个驱动警告未消解，因此不采纳该回执，改用 38826201 严格检查版本。

日志均为对应目录 `slurm-<job>.log`。前四项结果 `no-wire-power-01/run-<job>-<m|control|write_u|sram>/`；Qwen3 `no-wire-extension-01/qwen3-38825995/`；另两项为各自目录 `run-<job>/`。每目录有 `results.sha256`，小型校验与聚合结果保存于 `work/Melodydt/280/no-wire-results/` 和 `qwen3-ordinary-results/`。G32/交换机工件从授权旧服务器直接流式转移至 BSCC，未把大型工件存入本机，14 个输入的来源、大小、SHA 在 `legacy-transfer.json`。

```bash
R=/public3/home/t6s011227/LLMHardware/zenanyan/issue-280-bscc-t6-01
cd "$R/native-mother-nowire-01"
sbatch --parsable --time=0 run_native_mother_power.sbatch
# 前四项实际依次执行：
cd "$R/no-wire-power-01"
for family in m control write_u sram; do
  sbatch --parsable --time=0 --job-name=mdt-280nw-$family run_no_wire_power.sbatch "$family"
done
squeue -j 38769386,38769388,38795299,38795300,38795516,38795517,38795518,38795519
sacct -j 38825938,38825939,38825940,38825941,38825995,38826075,38826201 --format=JobID,State,ExitCode,Elapsed,NodeList
tail -n 30 "$R/native-mother-nowire-01/slurm-38826201.log"
cat "$R/native-mother-nowire-01/run-38826201/calibration.json"
(cd "$R/native-mother-nowire-01/run-38826201" && sha256sum -c results.sha256)
```

上面 sbatch 命令会产生新作业；仅检查进度时从 squeue 开始。复跑仍需核验 bundle 输入、工具版本和源码提交。原读 DMA 四项仍为 RUNNING，四项依赖功耗为 PENDING；最新快照在 `no-wire-jobs.json`，不推测结束时间。

## 验证、复算和剩余工作

```powershell
python scripts/check_project.py
python work/Melodydt/280/verify_six_model_energy.py
python work/Melodydt/280/seven_model_no_wire_power.py
python work/Melodydt/280/verify_no_wire_energy.py
python work/Melodydt/280/build_energy_report.py --output output/pdf/seven-model-energy-evaluation-current.pdf
```

管理结构、六模型原回执复算、七模型 21 窗输入 SHA/分项守恒/单位/DDR 分离/新增覆盖归属检查通过。PDF 使用既有 ReportLab/中文字体流程；本地复算不等同于再跑整模型 RTL 或物理签核。正式报告沿用 `docs/experiments/seven-model-energy-evaluation.pdf`，PDF 版本及视觉检查回执在发布文件和验证记录中。

仍缺的项目不能填零：

- 等已有作业：读 DMA 的匹配映射网表、真实活动、静默及漏电；当前读价代理只做敏感性，不进入基础小计。获得网表即可直接无 SPEF 标定，不等布局布线。
- 可另行准备但尚无齐备标定：母控运行取指/启动、局控外壳与分发、交换机流量、RMS/softmax/RoPE/额外缩放；需明确硬件边界、操作计数及匹配活动后加入，不能把已有叶块功耗重复相加。
- 模型特有且缺匹配硬件/活动：Gemma GELU；Granite router、专家加权/缩放；Qwen3.5 sigmoid、GDN/卷积；Falcon Mamba2/卷积；Phi LongRoPE。SiLU 的 G32 系数没有用于替代 GELU/sigmoid。
- 尚未绑定的时钟/互连单元、各模型实际实例/门控、DDR PHY 与板级 I/O；主动排除的线网寄生与缺少硬件数据是两回事。

恢复第一步：读本交接、PR 最新 head、`no-wire-jobs.json`，检查四项 DMA 映射是否输出；无结果时按以上未标定范围选定真实 RTL/活动，不修改旧实验输出。负责人 Melodydt；需要硬件部署决定时交由项目维护者确认。没有配置聊天结束后的自动监控，需再次唤起检查。

规则版本 rayggxia-project-collab 1.0.0。登记 management-hub PR #5 仍 open/未合并，pending；任务分支 `config/board.json` 读取失败且缺 Projects 工具，条目 unverified、同步 pending，待有权限维护者处理。Issue in_progress；PR 草稿/未合并，独立审查人待指定。文件上传、登记、看板和验收分别记录，不标 done。
