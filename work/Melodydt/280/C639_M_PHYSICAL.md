# C639 M 握手验证与同源物理实现

2026-11-15（Asia/Shanghai），`llm-hardware-design`，任务分支 `task/280-seven-model-energy`，负责人 Melodydt。C639 来源为 `116937` 的冻结模型和波形，上一阶段的 G32 结果见 [G32 功耗](C639_G32_POWER.md)。 [Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) · [PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281)

## 实际 M60 来源和可达差异

M60 的交付网表来自 `issue250-m-physical-20261111-60/tasks/delivery/6_final.v`。#47 原始 Yosys 映射清单与 #60 的验收源码在六个 M 文件上逐字节一致，实体验收的源自该清单。之前观察的双执行槽变更来自 P 集成回归的另一份源码副本。实际送布线的 M60 与 C639 冻结 M 都用单执行槽。

比较闭包后，`m_group_s32` 和 `scale_group_s32` 完全相同。`m_native_leaf_s32`、`m_native_s32`、`weight_records`、`projection_context_s32` 存在差异，涉及命令条件、RF STEP／控制就绪、权重 ALLOC／START 优先级、CANCEL 与返回仲裁。C639 原有的 `$test$plusargs` 观测探针位于 `ifndef SYNTHESIS`。

`116953` 在 c64/node12 用 4 核、5 秒 `COMPLETED 0:0`。两个 `weight_records` 实例接受完全相同的合法 17 拍权重记录。随后给已就绪的记录发 `START`，同时在另一空闲 bank 请求一笔独立 `ALLOC`。两版都接受 `START` 且没有 fault。M60 同拍接受 `ALLOC` 并确认分配 bank 1，当前 C639 同拍不给 `ALLOC` 就绪，bank 1 保持空闲。由此可证组件接口在这组合法事务下存在周期差异。此次对照直接使用经原始映射清单确认的两个 RTL 版本。首轮 `116952` 用了非法零比例因子，修订夹具改用四个合法 FP16 1.0 比例因子后通过。

## 真实 C639 窗口中的条件覆盖

`116958` 在 c64/node12 用 2 核、5 秒 `COMPLETED 0:0`，逐拍解析 `116937` 四份 FFN 波形及 `116950` 两份 G32 计算波形。每个窗口和每路 P 检查 8,192 个完整上升沿，共 147,456 个 lane-cycle。观测到 3,472 次 `ALLOC` 与 3,423 次 `START` 接受，`START` 和 `ALLOC` 的 valid 从未同拍。模块对照的反例在这六窗中未触发。当前 M 同源物理实现用于后续门级功耗。

| 证据 | SHA-256 |
| --- | --- |
| M60 原始 Yosys 映射 `receipt.json` | `e7bf99bce08b841c381524c65e658695a1eba1ec24b4f52822b46f336c46ec47` |
| M60 最终信号网表 | `01293f481a1100c95106afa76f7792b4fff32dac9b3da2dc3c9f9bbae4f3bed5` |
| `contract-116953/contract-results.sha256` | `b2e0f1091a266ac6cbb936ed0036a6f3f1915345c2bad98a70362d4a076a8dd6` |
| `wave-116958/wave-results.sha256` | `c3982240a2abc49a78bae0db37f199f0f42b3cb9859f6ad76205161415cc7e34` |

## 当前 M 同源映射与布线

从 C639 冻结版本逐字节复制六个 M 源文件。沿用 #250 的向量、六个种子和三种初态，18 个叶块功能回归已全部通过。修订前的 `116954` 因旧 C++ 驱动没有为 Verilator 注册参数、遇到冻结 RTL 的探针时退出，依赖 `116955` 随后取消。修订只为测试驱动注册 `commandArgs`，并使生成模板在测试目录重现带探针的原始叶块，六个 M 设计文件、向量和断言均按原样使用。

`116956` 在 c64/node9 用 12 核运行 9 分 55 秒，`COMPLETED 0:0`。沿用 #250 的 Yosys／ABC Nangate45 流程，当前 M 映射面积 723,919.532 µm²、单元 406,959 个。原 M60 映射为 722,942.248 µm²、407,125 个单元。两版 1,330 位公开端口的名称、方向及宽度完全一致。映射面积只计映射后的标准单元。`mapping-results.sha256` 的 SHA-256 为 `0fc17d5e1c00eb1b3d5e5c73f6ade85723f556bc9472e24dd12825fc3b63ac95`，`mapped.v` 的 SHA-256 为 `a83e06a0b0dabe498f92348e31443d3149d2cfec76d745c92fdc758264b6970c`。

首个布线 `116957` 在映射验收后启动，因调用传入 `mapping/m_native_leaf_s32`、而布线入口需要 `mapping` 父目录而退出。修订布线 `116976` 已在 c64/node9 用 12 核运行，映射清单校验通过，OpenROAD 已生成网表结构工件。按 #47 edge1390 配置复用 1,390 µm 尺寸、14 µm 边距、0.55 放置密度、300 MHz 约束与相同余量。后续验收实际布线、时序、电气、DRC、寄生、门级功能和真实工作负载功耗。

## 服务器和复跑

登录 `yuzelu@10.129.166.172`，实验根 `/public/home/yuzelu/Melodydt/runs/issue-280`。

| 作业 | 目录 | 脚本 | 源 commit |
| --- | --- | --- | --- |
| 116953 | `c639-m-contract-02` | `run_c639_m_contract.sbatch` | `87fb5bcd6a8d4413f991abf1d8c588b37303e693` |
| 116958 | `c639-m-wave-audit-01` | `run_c639_m_wave_audit.sbatch` | `9569071418e87d400902108dcf4aa5e90a532af7` |
| 116956、116957 | `c639-m-physical-02` | `run_c639_m_physical.sbatch` | `e0bee1338fb214bc53bbeee8806aef415c17e333` |
| 116976 | `c639-m-physical-03` | `run_c639_m_physical.sbatch` | `4d3f3535e5989d00242b7485c89962a9993f698c` |

前三个作业以 `sbatch --parsable <脚本>` 启动。取消或失败的旧作业分别保留日志。目录中的 `source-commit.txt` 与 `bundle.sha256` 固定实际提交脚本。

```bash
cd /public/home/yuzelu/Melodydt/runs/issue-280
squeue -j 116976 -o '%i|%j|%P|%T|%C|%N|%R'
sacct -j 116953,116956,116957,116958,116976 -o JobID,State,ExitCode,Elapsed,NodeList
tail -n 30 c639-m-physical-02/slurm-116956.log
tail -n 30 c639-m-physical-03/slurm-116976.log
tail -n 30 c639-m-physical-03/route-116976/route.log
sha256sum -c c639-m-contract-02/contract-116953/contract-results.sha256
sha256sum -c c639-m-wave-audit-01/wave-116958/wave-results.sha256
(cd c639-m-physical-02/map-116956 && sha256sum -c mapping-results.sha256)
sha256sum -c c639-m-physical-03/route-116976/route-results.sha256
```

修订布线的实际启动命令如下。

```bash
cd /public/home/yuzelu/Melodydt/runs/issue-280/c639-m-physical-03
sbatch --parsable --job-name=mdt-280mroute --time=04:30:00 run_c639_m_physical.sbatch route /public/home/yuzelu/Melodydt/runs/issue-280/c639-m-physical-02/map-116956
```

后续先验收同源 M 布线和门级功能，按 C639 各 P 的实际握手采样 M 功耗，再补真实 512-bit SRAM／PM 写入、母控、局控、DMA、互连、时钟等物理分项。之后完成 Granite／Phi／Falcon 专项 A/B、七模型和 Qwen2.5-3B 同口径扩测与系统能耗、误差汇总。#280 进行中，PR #281 草稿，登记待合并，Projects 缺配置待维护者核验。
