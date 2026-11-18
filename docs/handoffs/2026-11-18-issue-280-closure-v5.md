# #280：控制部署、读 DMA 与特殊算子校准 v5

更新时间：2026-11-18 21:30（Asia/Shanghai）。负责人 Melodydt；仓库 rayggxia-workspace/LLMHardwareDesign；[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) / [草稿 PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281)。分支 `task/280-seven-model-energy`，PR 基分支 `task/274-seven-model-short-throughput`。引脚标定源码 `30b6095c6cf75b9c6dafe0108972b3eed46b8f01`；积分源码已上传至 `03cc4e99b907491333f5c734f026672109dbcbd3`，本文件后的数据/文档提交以 PR 最新回执为准。没有合并或物理验收。

本机目录 `D:/Study_material/Study_material/LLMHardwareDesign` 是无 `.git` 的导出工作区；本轮仅在 `work/Melodydt/280/closure-v5` 新增实验脚本和小回执，并更新相关进度/报告。使用 Melodydt 本人连接及 expected_sha 租约发布。`recurrent-step1` / #293 的 200 MHz 分支单独进行，本轮只读取并引用其引脚别名方法，不覆盖其文件或采用其频率。

## 本次新增五窗积分

新增 Phi、Gemma、Qwen3.5 短 prefill 及 Falcon 两步 decode 共 5 窗；已完成七模型全部 prefill、Qwen3/Llama/Granite/Falcon 的两步 decode，共 15/21 窗。Falcon 38852034 于 21:24:07 COMPLETED 0:0，第二步 2.988568 tok/s。新增窗的数值、DDR/SRAM、输入输出 SHA、资源区间及功耗单位/去重/守恒均通过。四版读 DMA 的条件场景和特殊候选替换场景均同步积分，片上与片上＋DDR分开。

管理结构检查、25 份已验收阶段工件 SHA、部署/资源审计、15 窗三类账本独立对账通过。PDF 为 36 页（11 页更新＋25 页保留历史），316 组数值检查和新增页目检通过；每模型页面列 W 与 mJ/token、四种互斥 DMA 场景及未覆盖项。

Phi/Gemma/Qwen3.5 decode 作业 38852028/38852030/38852032 仍 RUNNING，12 核、UNLIMITED；剩余 6 窗等待其验收。每模型真实物理部署、provider/原生 ABI、路由/门控、完整 RTL 控制驻留以及特殊算子转换/复合运算/递推状态/候选周期仍需实现验证。旧布局布线不作前提，M 时序闭合不作前提。

本轮更新前远端任务分支为 bfe691ce626d6dac5d02a6a26a4c11047bb6cc18；当前本机仍为无 `.git` 的导出工作区，只修改本任务脚本、账本、报告与进度。本次提交完成与否以 PR 回执/分支读回为准，不把本地成果当作已上传。

## 口径与当前验收状态

用户要求的三项仍是进行中，不把局部标定写成全部完成。M 时序闭合明确排除；采用 300 MHz、TLM 3334 ps、512-bit 数据 SRAM、三 P、代表性历史起点、短 prefill 和两步 decode。无 SPEF、无布局布线前置条件。

1. **控制与部署**：已记录真实执行的 provider 注册键、调用路由、PM 安装、母控指令数、四个 LC/服务回调驻留以及共享 E32/M 区间。已通过窗口无 E32/M/同一 local target 重叠，区间守恒。完整每模型物理顶层、provider-to-port 适配、实际路由 RTL 参数和真正时钟门控仍未验收；精确 TLM 区间不等于完整 RTL 状态驻留。未计入无证据的门控节能。
2. **母控外围**：38850581 COMPLETED 0:0，1m11。25,880 单元，切除已计入的母控、4 LC、4 router 和 switch 共 10 实例；外围 C639 启动/运行参考为 10.553–11.762 mW。C639 内状态驻留有记录；转移到模型仍是条件估算。
3. **BSCC / DMA**：登录已恢复，四份原综合网表 SHA、标准单元链接和综合结构检查均通过。四版配对引脚标定 38855808–11 全部 COMPLETED 0:0；结果 SHA、空闲 fence/模式/owner 和活动标注通过。这一项已完成到综合后直接估算口径。仍为观测 RTL 位向连接引脚映射及未观测活动传播，不是完整门级回放。布局布线状态不决定本轮功耗。旧 38769386/38795299 物理作业未取消；phase 旧物理流程在引脚放置失败，综合网表仍可用。
4. **特殊算子**：EXP/sigmoid/softplus/GELU 的 S40/Q24 插值候选共 50,693 条指令逐字通过定点参考；8 路 Conv4 的捕获通道全部通过定点参考。对冻结 Q16 输出，卷积 Qwen3.5 最大差 0，Falcon prefill/decode 最大 2/4 LSB。复合运算和完整 FP32/provider 接入仍待校准，不能替换为“整模型 RTL 数值通过”。
5. **E32**：实际调度从 9 修正为 18 周期，重算共享资源、DDR 等待及其设备能耗；逐层输出和数值文件保持一致。已经受理七模型双阶段链。`deployments-current.tar.json` 区分 accepted 与尚无成功清单，不能按结果文件存在推断通过。

## 关键修正与不采用的临时结果

- 原 DMA idle 没有完成自动 reset fence，会停在 F_OFFER；旧 `dma-shared-state-calibration.json` 的 96.38 mW **不可作为正常空闲值**。新 idle 驱动完成 fence、切换模式、确认 generation、无请求/响应/fence/故障后再测 8192 周期。
- 较早 C639 FST 缺 6144-bit response data。新标定仅使用已验收的扩展 VCD，并检查 preflight SHA，不补造活动。
- SystemVerilog `$var logic` 已纳入解析，位宽冲突的内部数组名不作猜测绑定。
- 当前 BSCC OpenSTA 实测仅按内部网名读取时未标注内部引脚。`calibrate_retained_pins.py` 重新读取**确切 STA 结构网表**，用连接图将已观测位映射到实际单元引脚；只改表示/别名，不改事件时间。每对窗要求相同引脚集合，工具实际标注数必须与生成清单严格相等。未观测内部网络仍为传播估计，不是全门级回放。
- Conv4 38855639 / special 38855640 均 COMPLETED 0:0，分别 1m02 / 1m00。实际标注分别 44,258/247,897、5,724/140,975 个总连接引脚；**匹配集合全部标注，不代表全部电路活动已直接观测**。旧 boundary-only 系数不用于新候选结果。
- 修正后 Conv4 动态约 0.475–0.789 nJ/通道；EXP 0.693、sigmoid 0.912、softplus 0.895、GELU 0.554 nJ/调用。仅对应该候选、样本和无寄生映射；数值范围不是置信区间，不含完整转换/provider/存储历史链路。

## 已通过的 E32 重测

| 模型 | 短 prefill tok/s | 第二步 decode tok/s | 已积分窗口 |
|---|---:|---:|---:|
| Qwen3 | 21.564769 | 6.964554 | 3/3 |
| Llama | 15.296032 | 5.643081 | 3/3 |
| Granite | 15.689335 | 6.867212 | 3/3 |
| Phi | 4.892059 | 运行中，未验收 | 1/3 |
| Gemma | 4.891126 | 运行中，未验收 | 1/3 |
| Qwen3.5 | 3.961885 | 运行中，未验收 | 1/3 |
| Falcon | 4.234239 | 2.988568 | 3/3 |

`integrate_calibrated_timing.py` 已为通过的窗口重算分项：固定驻留项按新时间，M 按真实新区间并集，计数项仅在逐窗 SRAM/PM/服务/DDR 等量核验后复用，DDR 使用新运行的设备结果。不会按总延迟比例放大全部动态能耗。`timing-ledger` 仍未加入 DMA / 新特殊算子候选，不能当成最终 v5 全覆盖小计。

## 作业与可复制追踪

登录目标：`t6s011227@BSCC-T6@ssh.cn-zhongwei-1.paracloud.com`（SSH user 字段为 `t6s011227@BSCC-T6`；不要把双 @ 字符串当 shell 命令）。实际核验 .6 地址，主机密钥严格校验。凭据不写入仓库。

服务器根目录：`/public3/home/t6s011227/LLMHardware/zenanyan/issue-280-bscc-t6-01`；工具 `~/LLMHardware/opt`。所有新作业 v6_384、12 核、UNLIMITED。

| 路线 | 作业 | 源码目录 / commit | 结果目录 |
|---|---|---|---|
| 新 DMA 操作空闲/活动 | 38854351 shared、38854356 shared-noshare、38854358 phase、38854359 phase-noshare | closure-v5-cal-278fbf5c / 278fbf5c | dma-state-ID-VARIANT |
| 特殊函数 / Conv4 数值与映射 | 38854360 / 38854361 | 同上 | special-ID / conv4-ID |
| 引脚覆盖修正 Conv4 / special | 38855639 / 38855640 | closure-v5-pins-30b6095c / 30b6095c | pins-ID-conv4 / pins-ID-special |
| 引脚覆盖修正 DMA | 38855808 shared、38855809 shared-noshare、38855810 phase、38855811 phase-noshare | 同上 | pins-ID-dma |
| E32 全量后继 | 38852023–38852036；逐模型映射见 e32-retry-jobs.json | closure-v5-e32-9a2f2d23 / 9a2f2d23 | deployment-ID-e32-18-PHASE |

20:18 历史快照（当前以首节和逐行时间戳为准）：引脚 Conv4/special 与四版 DMA 全完成。DMA 38855808/09/10/11 分别用时 11m52、11m51、27m54、23m51，节点 m3ca0206/m3ca0801/m3ca0405/m3ca1101。Qwen3/Llama/Granite 的 E32 双阶段通过；Falcon prefill 已通过（1h03m56）；Phi/Gemma/Qwen3.5 prefill 和四模型 decode 共 7 项仍在运行。七模型基线观察全部通过。具体状态和旧物理作业以同目录 job-status-current.json 为准，恢复时必须读回。

## 已完成的 DMA 积分与候选场景

| 单实例版本 | 操作空闲 W | 动态增量 nJ/64 B | Qwen3 第二步 DMA mJ/token |
|---|---:|---:|---:|
| shared-noshare | 0.086118–0.086118 | 1.233155–1.354252 | 29.385148–31.056521 |
| shared | 0.096348–0.096348 | 1.742491–1.942310 | 37.883859–40.641791 |
| phase | 0.083165–0.083195 | 1.591845–1.758743 | 33.911824–36.219654 |
| phase-noshare | 0.093769–0.093826 | 2.175221–2.279289 | 43.486075–44.930603 |

每个场景只加一个 fabric；phase 自带 shared，禁止叠加。动态窗口仅直接覆盖 owner 0；其余 owner 动态迁移为假设，四个空闲 owner/mode 状态已测。事务分母由真实请求/回包握手数量与最多一个初始沿的 12 客户端差异形成；范围不是置信区间。不得把未观测内部活动标为完整门级活动。

已完成七模型 prefill 及 Qwen3/Llama/Granite/Falcon 两步 decode 共 15 窗的分项积分和独立守恒核对，`dma-ledger` 给四版的片上/片上＋DDR。Qwen3 第二步四场景片上 199.053–223.493、片上＋DDR 538.644–563.085 mJ/token，范围跨越四种部署，尚未唯一绑定实际物理版本。

`special-candidate-ledger` 单独将匹配函数/卷积从旧代理中删去，再加候选标定成本和仍需代理的乘除/归一化。每个实际调用站点一个开钟单元是候选实例假设，0.5–2 倍迁移敏感性沿用原方案，不是测得误差界。完整 provider、FP32 转换、复合运算和新候选周期尚未安装到模型；该场景不改变已验收 E32 吞吐。已有 G32/RMS/E32/RoPE/softmax/SRAM 不重复增加。

控制部署的具体差距：C639 控制参考使用 4 LC、每站点 1 个统一 provider 端口和 9 项路由，不能仅凭 Python provider 注册键就宣称各模型匹配此 RTL 参数。需要实际 128 B 原生 descriptor/ABI 适配、可综合 provider 接口、路由参数及整模型运行状态回放。当前不计无证据的门控节能；此项需要实现工作，不是等待队列即可解决。

实际提交入口（在对应 bundle 目录执行；以下是已有作业的复现形式，**检查后再决定是否重交，避免重复任务**）：

```bash
sbatch --job-name=mdt-280state-shared run_dma_state_power.sbatch shared
sbatch --job-name=mdt-280special-int run_special_lut.sbatch
sbatch --job-name=mdt-280conv4-int run_conv4.sbatch
sbatch --job-name=mdt-280pin-conv run_retained_pins.sbatch ../closure-v5-cal-278fbf5c/conv4-38854361 conv4
sbatch --job-name=mdt-280pin-shared run_retained_pins.sbatch ../closure-v5-cal-278fbf5c/dma-state-38854351-shared dma
```

上述启动时实际传入 source 为绝对路径；完整 source、SHA 和输出路径随 calibration.json 记录。日志均为对应目录 `slurm-ID.log`。

恢复执行第一步：

```bash
cd ~/LLMHardware/zenanyan/issue-280-bscc-t6-01
squeue -u t6s011227 -o '%.12i %.30j %.9T %.12M %.12l %.18R'
sacct -j 38855808,38855809,38855810,38855811,38855639,38855640 --format=JobID,State,ExitCode,Elapsed,Timelimit,NodeList -X
tail -40 closure-v5-pins-30b6095c/slurm-38855808.log
cat closure-v5-pins-30b6095c/pins-38855808-dma/calibration.json
cd closure-v5-20261118
python3 -B collect_deployments.py .. deployments-current.tar.gz closure-v5-e32-9a2f2d23
```

每项成功判据：Slurm COMPLETED 0:0，预期 PASS 标志，结果清单 SHA 全通过，活跃/空闲同覆盖集合且工具标注数量相等；E32 还需 acceptance 的数值文件、流量守恒和资源区间审计。进程退出或提交受理不代替这些判据。

## 剩余工作顺序

1. 收齐 Phi/Gemma/Qwen3.5 的 E32-18 decode 作业 38852028/38852030/38852032，逐模型验收并保存 SHA；将当前 15 窗补至全部 21 窗，复用四版 DMA 标定。
2. 用每模型真实物理实例/端口绑定选择 DMA 场景；如使用 phase owner 1，还需其活跃窗口直接标定。当前四种替代场景已可复算，不能自动决定实际部署。
3. 将特殊候选与捕获输入格式、ABI、复合运算和实例数量逐一绑定；GDN/Mamba 的侧边 200 MHz 结果需要 300 MHz 对应标定及接口/转换，不能直接挪用。
4. 完成每模型真实物理控制/router/provider 配置与全模型 RTL 状态记录。当前 TLM 部署审计明确列出了未验收项，不能把它替换为完整硬件证据。
5. 持续更新滚动 PDF、JSON 和复现包，验证数值、分项去重、未覆盖说明与视觉排版；同步 PR 回执及本人进度。当前 v5 补充报告保留原 v4 的 25 页历史快照。审查人待指定，不自行合并。

已执行管理检查、资源区间守恒、SV 活动解析及引脚别名/总线/常量/未观测网络的测试；这些不代表整模型 RTL 或物理验收。Issue 保持 in_progress，PR 草稿未合并；登记 management-hub PR #5 pending，config/board.json 缺失且无 Projects 能力，看板 unverified、同步 pending，交由有权限维护者。未配置聊天自动监测。
