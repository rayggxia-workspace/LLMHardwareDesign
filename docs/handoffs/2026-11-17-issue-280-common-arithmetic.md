# 七模型算术缺项：公共 RMS/N 标定接续

2026-11-17，Asia/Shanghai。负责人 Melodydt。仓库 rayggxia-workspace/LLMHardwareDesign，[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280)，[PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281)，分支 `task/280-seven-model-energy`；本机导出工作区 `D:/Study_material/Study_material/LLMHardwareDesign` 无 `.git`，通过 Melodydt GitHub 连接向任务分支交付。未更改模型部署或冻结数值；无完整模型新能耗可发布，PDF v2.1 数值暂不变。

## Llama 三窗 N 完成（23:02 读回）

38828362 已 COMPLETED 0:0，耗时 33:36；decode 完整冻结重放、66 次 RMS 和四组真实输入定点校验通过。38828634 在 m3ca0301 自动运行 1:20，COMPLETED 0:0，四组 N RTL 因子全部一致，活动/空闲均 433 位标注。三窗累计 130 次 RMS、6 组样本。服务器 Python 为 3.10.12。

| 窗口 | 两样本的 N 增量 nJ/RMS | 未移位 N 因子 |
| --- | --- | --- |
| Prefill | 299.429079541 / 301.144850304 | 840227 / 850407 |
| 首个 decode token | 292.087531390 / 301.024649552 | 736705 / 616175 |
| 第二个 decode token | 292.835128683 / 300.202546407 | 813520 / 626623 |

样本极值不是误差/置信区间。N 核心已走通真实模型数据 → 定点验证 → RTL 因子 → 边界活动传播功耗；其他 RMS 子模块、驻留和实例积分仍待完成。Decode 捕获 SHA `54b80fceb6f3c867e237d9e7bb294f262d3066d55bcf95f096cc6fa8768b7beb`，小型回执在 `work/Melodydt/280/llama-arithmetic-decode/`；完整向量仍保留服务器及本机副本，不上传 Git。两阶段清单在 `llama-arithmetic-results.sha256`。其余六模型的采样/标定链见下一表，仍需等待实际验收。

## 后续推进：七模型采样及成功依赖链（22:59 快照）

Llama prefill 已通过完整冻结结果、逐层数值、DDR/SRAM/N 计数与定点复算：64 次 RMS 服务，512 个 S128 word（2048 元素），捕获 2 组完整真实输入。38828633 在该阶段独立验收后于 22:47 解除对整个双阶段采样作业的等待，48 秒内 COMPLETED 0:0（m3ca0905）。两个真实输入的 N 原始因子 840227/850407 与 RTL 一致，300 MHz 增量分别 299.429079541/301.144850304 nJ/次；每个等长窗 10,816,667 ps，活动 35.50054505/35.65916792 mW，空闲 7.818350568 mW。输入捕获 SHA 为 `2e3380e91b0495a7f888fe1b07c57f1cc82c0fc38a040569357bbd01a9147322`。这些结果仅是 N 算术动态增量，尚未添加其他 RMS 子模块或驻留，不能作为模型完整小计。

| 模型 | 采样作业 / 节点 | Prefill N | Decode N |
| --- | --- | --- | --- |
| Llama | 38828362 / m3ca1003，prefill 通过，decode 待最终退出 | 38828633 已通过 | 38828634 等待成功依赖 |
| Granite | 38828902 / m3ca1604，RUNNING | 38828998 等待 | 38828999 等待 |
| Phi | 38828903 / m3cd2608，RUNNING | 38829000 等待 | 38829001 等待 |
| Gemma | 38828904 / m3ce0402，RUNNING | 38829002 等待 | 38829003 等待 |
| Qwen3.5 | 38828905 / m3ce0506，RUNNING | 38829004 等待 | 38829005 等待 |
| Falcon | 38828906 / m3ce1203，RUNNING | 38829006 等待 | 38829007 等待 |
| Qwen3 | 38828968 / m3ca1907，RUNNING | 38829008 等待 | 38829009 等待 |

全部 `v6_384`、UNLIMITED；采样作业各 2×12 核，N 标定每项 12 核，等待中的标定节点均未分配。采样 job 名为 `mdt-280arith-cap`，Qwen3 为 `mdt-280q3arith`；后续标定名为 `mdt-rms-<model>-<phase>`。五个新增模型复用采样 commit `91fd33eeed6b3b40ec4254970aace879392983a9`；N 标定均复用 `f6aa5c96916ecc0712d531c2f3b20e81935c0a8b`。Qwen3 适配 commit `308921b5ef6dce6efafc5000acbe6a1bb308277a`，已核对其原 RMS 与 Llama 冻结版本 SHA 均为 `78961329f7393134ee2878e675e89e88b81a8548c8ba02ecb99f13b1f38e7c2d`，保留其普通/FFN M 不重叠检查及冻结数值/DDR 验收。

真实 Llama prefill 小型回执在 `work/Melodydt/280/llama-arithmetic-prefill/`（acceptance、arithmetic-capture-check、n-calibration、n-results.sha256）。完整输入保留服务器 `common-arithmetic-capture-01/run-38828362/prefill/arithmetic-observation.json`，本机亦下载同名文件但未上传该大段向量；其 SHA 可与 n-calibration 回执交叉核验。本地默认 Python 3.7 缺 `math.isqrt`，3.12 启动器不可运行，因此本地定点校验未成功执行；容器中同一校验器和 RTL 实测均已通过，不把本地 AST 检查称为数值验收。

```bash
# 实际已执行的五模型采样提交
R=/public3/home/t6s011227/LLMHardware/zenanyan/issue-280-bscc-t6-01
cd "$R/common-arithmetic-capture-01"
for spec in 38820602-granite 38820798-phi 38821513-gemma 38821601-qwen35 38821511-falcon; do
  sbatch --parsable --time=0 run_arithmetic_capture.sbatch "$R/six-model-energy-01/run-$spec"
done
cd "$R/common-arithmetic-qwen3-01"
sbatch --parsable --time=0 run_qwen3_arithmetic_capture.sbatch

# 已受理的成功依赖链，接续时不要重复提交
cd "$R/common-arithmetic-n-01"
for spec in granite:38828902 phi:38828903 gemma:38828904 qwen35:38828905 falcon:38828906; do
  model=${spec%:*}; parent=${spec#*:}
  for phase in prefill decode; do
    sbatch --parsable --time=0 --dependency=afterok:$parent --kill-on-invalid-dep=yes \
      --job-name=mdt-rms-$model-$phase run_rms_n_calibration.sbatch \
      --capture "$R/common-arithmetic-capture-01/run-$parent/$phase/arithmetic-observation.json"
  done
done
for phase in prefill decode-live; do
  sbatch --parsable --time=0 --dependency=afterok:38828968 --kill-on-invalid-dep=yes \
    --job-name=mdt-rms-qwen3-$phase run_rms_n_calibration.sbatch \
    --capture "$R/common-arithmetic-qwen3-01/qwen3-38828968/$phase-w4-tile128-pr272-combined/arithmetic-observation.json"
done

squeue -j 38828362,38828634,38828902,38828903,38828904,38828905,38828906,38828968,38828998,38828999,38829000,38829001,38829002,38829003,38829004,38829005,38829006,38829007,38829008,38829009
# 任意上表 JOB 可用以下命令；N 日志/结果为：
sacct -j JOB --format=JobID,JobName,State,ExitCode,Elapsed,NodeList,Timelimit
tail -n 30 "$R/common-arithmetic-n-01/slurm-JOB.log"
cat "$R/common-arithmetic-n-01/n-JOB/calibration.json"
# 六模型采样日志/结果为 common-arithmetic-capture-01/run-JOB/{prefill,decode}/
# Qwen3 采样日志/结果为 common-arithmetic-qwen3-01/qwen3-38828968/{prefill,decode-live}-w4-tile128-pr272-combined/
```

## 首批作业记录（原快照，最新状态以上表为准）

| 作业 | 任务/版本 | 实际状态 | 资源与结果 |
| --- | --- | --- | --- |
| 38828028 | `83a3333b0b3d39af76dbddf6ae03f044bc8b0b53`，N/E/softmax 候选综合 | COMPLETED 0:0，43 秒 | m3ca1208，12 核，三个映射进程；N 43,411、E compact 49,343、S32 softmax 19,649 cells；无未映射单元，`check -assert` 通过 |
| 38828362 | `91fd33eeed6b3b40ec4254970aace879392983a9`，Llama prefill/decode RMS 输入采样 | RUNNING，m3ca1003 | 2×12 核；冻结运行器已逐文件 SHA 校验，两个阶段均已进入逐层重放；最终输出一致性尚待结束验收 |
| 38828546 | `795bb57bb8d4f5da08c91399e74b5a3587d9123b`，N 合成样例 | FAILED 1:0，37 秒 | RTL 因子通过；VCD 总线缺下标导致只标注 9 位，被完整覆盖检查拒绝，结果不得使用 |
| 38828612 | `f6aa5c96916ecc0712d531c2f3b20e81935c0a8b`，修正 VCD 总线声明后重跑 | COMPLETED 0:0，21 秒 | m3ce0901，12 核；因子一致，活动/空闲各 433 位标注，SHA 校验通过 |
| 38828633 | 同 f6aa5c9，Llama prefill 真实输入 N 标定 | 已提交，依赖 38828362 afterok | 12 核，节点待分配；未开始执行 |
| 38828634 | 同 f6aa5c9，Llama decode 真实输入 N 标定 | 已提交，依赖 38828362 afterok | 12 核，节点待分配；未开始执行 |

以上均为 `v6_384`，`--time=0`，Slurm 读回 `UNLIMITED`。依赖任务使用 `--kill-on-invalid-dep=yes`，输入采样失败时不得继续标定。

## 已验证的边界

- 综合采用 Yosys 0.68+post、Nangate45 typical，源文件从冻结 C639 包复制并逐文件记录 SHA。冻结包的原始代码 commit 对应关系仍待核实，不能以本轮运行脚本 commit 代替它。三个候选网表不是七模型整设计，也没有证明 300 MHz 时序闭合。
- 捕获器只向各模型自己已验收的运行器副本加入观测钩子。记录全部 N leaf 次数/周期，按窗口、site、长度、epsilon、移位签名保留前两个完整 RMS 输入/gamma/输出；采样偏差尚未量化。
- 每阶段结束后要求冻结 result、逐层数值文件、DDR/SRAM 与 N 计数全部对账；另按捕获值复算 RMS 定点结果。此项不是重新进行全模型 FP32 验收。
- N RTL 夹具按真实输入缩放后发送 BEGIN/STATS/FINALIZE/READ_FACTOR，逐例核对未移位原始因子。E 的 S32 乘法、范围扫描和应用 wrapper、SRAM 不在本 N 标定范围，不能重复计入已有 U ADD2 或 SRAM。
- 功耗为 300 MHz、无 SPEF/无估计布线寄生，RTL 边界 VCD 传播到同一综合网表，等长活动/空闲配对。尚无内部门级活动校准或物理时序签核。
- 38828612 仅为 64 元素合成数据的流程验证：活动 32.85606205 mW、空闲 7.818350568 mW，等长窗 896,667 ps，增量 22.45048964 nJ。**不是 Llama 或任何模型的能耗结果，不得纳入模型 PDF 小计。**

小型证据在 `work/Melodydt/280/common-arithmetic-map-summary.json`、`common-arithmetic-{inputs,results}.sha256`、`common-arithmetic-yosys.txt`、`rms-n-smoke-calibration.json`、`rms-n-smoke-results.sha256`、`rms-n-calibration-inputs.sha256`。原始网表、日志、VCD 保留以下授权服务器目录。

## 服务器、命令与结果

登录：主机 `ssh.cn-zhongwei-1.paracloud.com`，用户名 `t6s011227@BSCC-T6`。不保存凭据。工具位于 `~/LLMHardware/opt`。

```bash
R=/public3/home/t6s011227/LLMHardware/zenanyan/issue-280-bscc-t6-01
MAP=$R/common-arithmetic-01
CAP=$R/common-arithmetic-capture-01
N=$R/common-arithmetic-n-01

# 已执行的提交；接手时先查已有作业，不要重复提交。
cd "$MAP"
sbatch --parsable --time=0 run_common_arithmetic_map.sbatch
cd "$CAP"
sbatch --parsable --time=0 run_arithmetic_capture.sbatch "$R/six-model-energy-01/run-38820601-llama"
cd "$N"
sbatch --parsable --time=0 run_rms_n_calibration.sbatch --smoke
sbatch --parsable --time=0 --dependency=afterok:38828362 --kill-on-invalid-dep=yes --job-name=mdt-280rms-pre run_rms_n_calibration.sbatch --capture "$CAP/run-38828362/prefill/arithmetic-observation.json"
sbatch --parsable --time=0 --dependency=afterok:38828362 --kill-on-invalid-dep=yes --job-name=mdt-280rms-dec run_rms_n_calibration.sbatch --capture "$CAP/run-38828362/decode/arithmetic-observation.json"

squeue -j 38828362,38828633,38828634
sacct -j 38828028,38828362,38828546,38828612,38828633,38828634 --format=JobID,State,ExitCode,Elapsed,NodeList,Timelimit
tail -n 30 "$CAP/slurm-38828362.log" "$CAP/run-38828362/"{prefill,decode}.log
tail -n 30 "$N/slurm-38828633.log" "$N/slurm-38828634.log"
cat "$CAP/run-38828362/"{prefill,decode}/{acceptance,arithmetic-capture-check}.json
cat "$N/n-38828633/calibration.json" "$N/n-38828634/calibration.json"
cd "$MAP/run-38828028" && sha256sum -c results.sha256
cd "$N/n-38828612" && sha256sum -c results.sha256
```

成功判据：作业 `COMPLETED 0:0`、阶段完整验收、N RTL 因子逐例一致、活动解析无错误、全部边界位标注、等长窗、输入/输出 SHA 完整。任何单项失败均不得回填模型。吞吐时间继续使用冻结的三 P/512-bit TLM，不用这些微测试的墙钟时间替代。

## 接下来所有步骤（依顺序）

1. Llama 38828362 与 N 标定 38828633/34 已全部通过；保留原始输入、三窗计数/采样策略、因子、活动覆盖与 SHA 回执。不要重复提交。
2. 等待并逐个验收其余六模型的采样/标定成功依赖链；失败则修观测器副本或输入/RTL 绑定并重跑，不改冻结基线。Slurm 依赖不是自动聊天监测。
3. Qwen3、Granite、Phi、Gemma、Qwen3.5、Falcon 的冻结运行器扩展及采样/依赖标定均已提交；依次核验数值、计数、N 因子、活动和 SHA。Qwen3 已独立适配，不直接套六模型 launcher。
4. 完成公共 softmax、RoPE、缩放以及 RMS E/scan/apply 部分的真实输入捕获、数值合同/RTL 匹配、无布线寄生标定。初次映射的 E compact 仅为候选，不代表已匹配 S32 E。
5. 按模型实际签名计数、驻留与并行实例积分；去掉重复 U/时钟/漏电归属。更新片上与片上＋DDR 两类分项、覆盖和剩余缺项，重新生成并逐页验收 PDF。
6. 公共算术完成后，补 GELU，以及 Granite router/top-k、路由 softmax 和专家加权和；已有 M 投影不重复计费。
7. 再补 Qwen3.5 GDN、Falcon Mamba2、卷积、Softplus/EXP/门控和归一化。先解决 32-lane TLM 与现有 8-lane R RTL 的部署/周期对应；必要时同步重新测速度与数值，不能直接套单元功耗。
8. 最后汇总剩余非算术缺项：读 DMA 实测替代代理、控制/传输外壳、实例与门控、互连/DDR PHY/板级边界。布线寄生仍按用户要求主动排除；旧 M 300 MHz 时序未闭合限制继续保留。本轮未查询旧 DMA 作业，不能把历史运行状态当成当前状态。

现有长作业可独立于 SSH/聊天持续；没有配置定时监测或自动通知，后续需再次唤起读取结果。仍可准备其他公共算术的数据与绑定，不能声称所有剩余工作都必须等待。

## 交付状态

规则 rayggxia-project-collab 1.0.0；project_id `llm-hardware-design`。本轮 Python AST、Bash 语法、管理结构检查、综合检查、SHA 与短样例通过；真实模型新增标定尚未验收。代码/回执通过既有任务分支和 PR #281 交付，不合并、不关闭 Issue。Issue `in_progress`，PR 草稿，审查人待指定。登记 management-hub PR #5 pending；`config/board.json` 缺失且无 Projects 工具，看板 unverified/同步 pending，待具权限维护者处理。

恢复第一步：读取本交接、Issue/PR 最新状态，然后执行上述 squeue/sacct 和日志命令；先验收已有作业，再决定重跑或扩展。
