# 第二轮：无持久状态的单命令 relative-exp

Issue247 / PR243。独立目录 `project/experiments/iterative_speed/round02`；不改R1冻结文件。本轮仅把S32→S32 NExp补充compute-wrapper服务替换为新op12实际校准费用。原vector_region、S读写、cache、DDR、E服务、P调度与16KiB容量全部保留。S16→S32继续原费用，因此prefill2明确fallback。

## 运行

```sh
python3 -B project/experiments/iterative_speed/round02/run.py --root "$RUN"
```

要求真实Slurm 1至4核；job不自行提交。目录：

```text
$RUN/source/                     # 含冻结R1/R2与旧模型依赖
$RUN/inputs.json                 # source_commit/code_sha256/input_sha256
$RUN/source-files.sha256
$RUN/input-files.sha256
$RUN/inputs/                     # 原run17八份输入
$RUN/run15-result.json           # 原始SHA31213ac8...6727cbc
$RUN/run17-result.json           # 原始SHAbc27f6b6...95d076
$RUN/r1-calibration-result.json  # run16原始SHA78c57feb...3d4ef7
$RUN/calibration-result.json     # 新R2完整passed RTL回执，未测不得预填
$RUN/results/                   # 必须由runner新建
```

模型保留旧参数前缀，追加R2flag：

```sh
model decode512.trace queued_pipe_w8 adaptive_prefix_pair_combine 8 1 1 16 0 4 0 1 1
```

倒数第二个1启用R1基础，最后一个0/1关闭/启用R2。R2on但R1off、缺新profile、非严格0/1均拒绝。生成无新profile可用于负例，但不能启用R2。

## 来源与默认兼容

生成器用独立Python进程执行冻结R1生成器，避免同名audit模块污染导入。R1生成出的全部源码SHA必须等于run17回执。新模型只增加R2选择及metadata；原iteration1.hpp、matrix/context/detail源码保持字节不变。

R2off（R1on）删除唯一新增`iteration2_study`后完整RESULT等于run17相应候选。R2on时`iteration_study`明确显示实际采用的新profile SHA、费用表及收费，不把新费用伪装为旧profile；`iteration2_study`同时给出R1来源、新来源、真实implementation/mode及配对差额。若全trace没有合格S32输入，仍选择R1实际ledger，删除R2metadata后也必须完整等于run17。

两个候选费用账本仅是主机侧统计，实际只选择一次费用；不复制N硬件，也不把旧费用再次执行。旧CLI未启用R1时仍采用原scalar服务，metadata明确标记`legacy_scalar`。

## 新校准合同

原始RTL回执沿R1结构保留顶层passed/source_commit/rtl_source_sha256、commands、runs、measurements.compute_s32/full_U。scope与payload保持相同补充服务和S32 low16合同，新增：

```text
profile.implementation: native_stateless_relative_exp_op12
profile.rows[].mode: legacy_s32_low16_zeroextend_stateless_op12
gates.stateless_context_preservation: true
gates.old_batch_compatibility: true
```

R1的六项gate也必须全部通过。每个测量的日志SHA、命令、seed、mode必须对应exit0的实际commands和passed runs，且测量及run都需`direct_mode=1`；run的`native_path`必须观察到op12，compute来源还须`other_commands=0`。compute计费采用真实accept到next-accept；n1..4来自真实NX32，n5..8必须分成[4,n-4]，不直接采用packed S16 n8速度。full_U仍验证1读/1写与三阶段守恒，S费用不再加到旧vector_region。

新gate必须来自实际验证：op12不能修改普通N持久统计、factor、replay或top状态。`stateless`的三seed运行必须有至少10个状态case、正检查数与12个reset case；三个`disabled_*`对照各三seed必须`exact_old_batch_match=true`并绑定日志/命令，回执的prior SHA必须是实际run16。默认DIRECT0四命令路径须完整对照R1。不得把尚未测试的假设II9写进profile。

## 审计与案例

16次完整模型：W8/decode512、W16/decode512、W8/decode2048、W8/prefill2，各shared/idealdual，各R2off/on；始终ctx8、16KiB、switch1、reuse1、policy0。8个默认先完整回归run17，随后跑候选。

新audit按真实trace资格选择实际profile，再调用冻结R1 audit对run15核对M/S/cache/DDR及算术守恒；另对run17核对R2差额、实际profile身份和default/fallback完整一致。允许等待和时序变化，但绝不隐藏额外流量或硬件。每case8项篡改拒绝；新profile8项拒绝；实际CLI、R1off、新profile缺失拒绝；保留原kernel/validate/smoke。

主停止判据仍为W8 decode512理想端口ctx8达到5，只能称旧体系条件目标。shared必须并列；不代表当前四1RW硬件达5。新RTL、全模型数值、物理频率资格独立；NX32仍是signed low16容器别名，不是任意S32指数数值证明。

当前本地验证：3份Python AST、16case计划、纯生成得到的7份R1源码SHA与run17精确一致，其中6份保持字节不变；16项合成metadata合同、128项结果篡改和6项来源/新gate拒绝通过。合成R2 profile仅在临时目录用于审计自检，已清除，没有作为真实校准或性能结果保留。真实R2校准与性能尚未执行，未本地编译/仿真，服务器执行由父任务统一安排。
