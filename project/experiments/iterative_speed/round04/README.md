# R4：从最佳 R2 继续的四 lane op12 评价

Issue247 / PR243。本轮从实际 run19 的最佳配置出发，不启用 run21 的有限 M 候选。R3 BUF2 主 ideal 为 3.66041657326 token/s，未超过 R2 的 3.66958239533；shared 也保留 R2 的 3.37834376557。R3 源码、正负结果和原生资格证据完整保留。

本目录仅改变 NExp 的补充计算服务，费用来自真实四 lane op12/NX32 wrapper 校准。旧 vector_region 的 E/S/cache/DDR、NExp 输入/输出读写、16KiB/P、16KiB/U、2P、300MHz、17.1GB/s、8 context、端口层、调度、M 工作和 R1/R2 格式回退全部保留。新增 lane 是 N 的组合/寄存器面积，不扩容 SRAM，不把裸运算器吞吐当完整服务。

## 原生合同与来源

新 profile implementation 必须为 `native_stateless_relative_exp_op12_lanes4`，row mode 必须为 `legacy_s32_low16_zeroextend_stateless_op12_lanes4`。保留旧 S32 容器的 signed low16 / U16 零扩语义，不能将它称为任意 full-S32 指数数值资格。真实 NX32 一帧最多 4 个值；旧模型 n8 始终收取两帧 n4 的实际接受间隔，不用 packedS16 n8 的费用代替。

费用从通过的实际回执 `/profile/rows` 读取，校验 compute/full_U/stateless 三种运行的 command、log SHA、direct_mode=1、direct_lanes=4、原生 op12 实际执行与 `lane_path`。每个 op12 返回前，RTL bench 必须已核对实际 CALC 次数等于 ceil(count/4)，并把 checked_commands、completed、CALC 总步数和同日志来源绑定。新 lane2 默认相对旧 R2、DIRECT0 在 lane4 下相对旧四命令路径、原统计 context 保留、复位/错误/普通命令、数值与完整 U 存储门均需通过。

provenance parser 复用冻结 R2 审计文件的相同证据语法，先核对该文件 SHA，再显式传入新的 implementation、mode、run18 prior 身份和新增 gates，随后独立检查四 lane 执行与默认兼容明细。不改或重新标记真实回执，不伪装成旧费用表。实际 fees 未出前，只能纯生成缺 profile 的拒绝路径，不能填入预计 7 拍或其他猜测数值。

## 模型与 ledger

生成器在独立 Python 进程调用冻结 R2 generator，保存全部旧生成 SHA，除了 `model.cpp` 之外的旧 C++/header/inc 字节完全不变。新计算项只有 `NExp` 原来的补充 service 调用，完整原 vector_region 仍执行。

R4 关闭或整个 trace 没有合法 S32→S32 NExp 时，去掉唯一新增 `iteration4_study` 后，完整 RESULT 必须等于 run19 对应 R2 已启用结果。prefill 的 S16→S32 NExp 仍收完整旧 16n 补充费用，不借 lane4 扩大 ABI。

R4 真启用时，通用 `iteration_study` 绑定实际四 lane profile；原 R2 ledger 改名为 `iteration2_baseline_study`，其内容必须完整等于 run19 的 `iteration2_study`。新 `iteration4_study` 明确旧/新费用、实际选择、default lane2/CALC 执行验证和来源，避免把基线费用当当前收费。

## 执行

正式目录 `project/experiments/iterative_speed/round04`：

```sh
python3 -B project/experiments/iterative_speed/round04/run.py --root /path/to/run
```

运行根目录提供冻结 `source/`、旧八份 `inputs/`、`inputs.json` 源码/输入 SHA、run15-result.json、run19-result.json、r1-calibration-result.json（run16）、r2-calibration-result.json（run18）、calibration-result.json（本轮真实四 lane 回执）。所有旧结果 SHA 在 runner 中固定，新校准 SHA 通过实际输入锁及生成 header 绑定。

四个场景 W8 decode512 / W16 decode512 / W8 decode2048 / W8 prefill2 × shared/idealdual × R4 off/on，共 16 个实际 SystemC case；先 8 个关闭回归，再 8 个候选。旧 kernel/validate/smoke 使用同一实际 binary 执行。还验证非法 flag、未启用 R2、缺 profile 和关键来源/CALC/费用篡改拒绝。脚本必须在真实 Slurm 1–4 核分配中运行，不能用本地模拟结果充服务器测量。

停止判据仍是旧体系条件主场景 W8 decode512、16KiB、ctx8、idealdual 达到 5 token/s 或完成四轮；shared 实测层同表。达标也不等于现有四个 1RW 宏的整机 RTL 或物理吞吐。每轮配对比较使用同层相同 workload，不叠加局部百分比；新候选若退化则保留旧最佳。

## 本地检查状态

本地只执行 AST、纯 Python 生成、冻结源 SHA 和独立审计；不运行 RTL、C++、SystemC。实际 run22（源码 `7048c35ed2912e80e62bd7827deaec480d4a7e1a`，结果 SHA `5abb31227f0c7b2c7ac9ff7eb8f80687569fab0b64bf74eb1a9ea6ccb54b518d`）已通过：63 runs、11 gates，n1..8 实测费用为 `[7,7,7,7,14,14,14,14]`。新 profile 已经独立核验实际 lane CALC 直方图、默认兼容来源、精确 RTL SHA 和真实测量费用，并用于纯生成；R2 的 9 份生成源 SHA 仍完全对应 run19，8 个非 model 文件保持字节不变。本目录新整图 SystemC 结果仍待服务器作业。完整数值、物理时钟、功耗和全 P/U/DMA 联合 RTL 资格仍未授予。
