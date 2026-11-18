# #280：控制部署、读 DMA 与特殊算子校准 v5

更新时间：2026-11-18 19:30（Asia/Shanghai）。负责人 Melodydt；仓库 rayggxia-workspace/LLMHardwareDesign；[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) / [草稿 PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281)。分支 `task/280-seven-model-energy`，PR 基分支 `task/274-seven-model-short-throughput`。源码当前已上传至 `30b6095c6cf75b9c6dafe0108972b3eed46b8f01`，本文件后的数据/文档提交以 PR 最新回执为准。没有合并或物理验收。

本机目录 `D:/Study_material/Study_material/LLMHardwareDesign` 是无 `.git` 的导出工作区；本轮仅在 `work/Melodydt/280/closure-v5` 新增实验脚本和小回执，并更新相关进度/报告。使用 Melodydt 本人连接及 expected_sha 租约发布。`recurrent-step1` / #293 的 200 MHz 分支单独进行，本轮只读取并引用其引脚别名方法，不覆盖其文件或采用其频率。

## 口径与当前验收状态

用户要求的三项仍是进行中，不把局部标定写成全部完成。M 时序闭合明确排除；采用 300 MHz、TLM 3334 ps、512-bit 数据 SRAM、三 P、代表性历史起点、短 prefill 和两步 decode。无 SPEF、无布局布线前置条件。

1. **控制与部署**：已记录真实执行的 provider 注册键、调用路由、PM 安装、母控指令数、四个 LC/服务回调驻留以及共享 E32/M 区间。已通过窗口无 E32/M/同一 local target 重叠，区间守恒。完整每模型物理顶层、provider-to-port 适配、实际路由 RTL 参数和真正时钟门控仍未验收；精确 TLM 区间不等于完整 RTL 状态驻留。未计入无证据的门控节能。
2. **母控外围**：38850581 COMPLETED 0:0，1m11。25,880 单元，切除已计入的母控、4 LC、4 router 和 switch 共 10 实例；外围 C639 启动/运行参考为 10.553–11.762 mW。C639 内状态驻留有记录；转移到模型仍是条件估算。
3. **BSCC / DMA**：登录已恢复，四份原综合网表 SHA、标准单元链接和综合结构检查均通过。布局布线状态不决定本轮功耗。旧 38769386/38795299 物理作业未取消；phase 旧物理流程在引脚放置失败，综合网表仍可用。
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

| 模型 | 短 prefill tok/s | 第二步 decode tok/s |
|---|---:|---:|
| Qwen3 | 21.564769 | 6.964554 |
| Granite | 15.689335 | 6.867212 |
| Llama | 15.296032 | 等待本轮验收 |
| Phi / Gemma / Qwen3.5 / Falcon | 部分基线与后继运行中 | 部分基线与后继运行中 |

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

19:28 快照：引脚 Conv4/special 已完成；DMA shared 两项在 m3ca0206/m3ca0801 RUNNING，phase 两项等 38854358/59 成功依赖（节点待分配）。状态会变化，恢复时必须读回。

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

1. 验收四版 DMA 修正引脚标定，按 64B 请求/返回数量与边界在途差给系数范围；phase 已包含 shared，四版作独立场景，绝不相加。然后按每模型真实读量与驻留积分。
2. 收齐七模型 observe / E32-18，逐模型公布结果并保存 SHA；复算 21 窗的片上与片上＋DDR。
3. 将特殊候选与捕获输入格式、ABI、复合运算和实例数量逐一绑定；GDN/Mamba 的侧边 200 MHz 结果需要 300 MHz 对应标定及接口/转换，不能直接挪用。
4. 完成每模型真实物理控制/router/provider 配置与全模型 RTL 状态记录。当前 TLM 部署审计明确列出了未验收项，不能把它替换为完整硬件证据。
5. 更新滚动 PDF、JSON 和复现包，验证数值、分项去重、未覆盖说明与视觉排版；同步 PR 回执及本人进度。审查人待指定，不自行合并。

已执行管理检查、资源区间守恒、SV 活动解析及引脚别名/总线/常量/未观测网络的测试；这些不代表整模型 RTL 或物理验收。Issue 保持 in_progress，PR 草稿未合并；登记 management-hub PR #5 pending，config/board.json 缺失且无 Projects 能力，看板 unverified、同步 pending，交由有权限维护者。未配置聊天自动监测。
