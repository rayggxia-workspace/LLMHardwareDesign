# 第一轮：校准驱动的 NExp 旧体系评估

此目录是新的独立实验扩展，建议正式位置 `project/experiments/iterative_speed/round01`。不修改 PR241/Issue247 旧生成器、source lock、矩阵调度、缓存和 DDR 代码。评价保持旧输入、300MHz、DDR总17.1GB/s、2P/1U、每块16KiB以及ctx8；shared 和 ideal-dual 分层。

主停止判据锁定本轮启动的旧最佳条件参考：W8/decode512、ctx8、16KiB、理想独立读写达到5 token/s，只能称“旧体系条件目标达到”；shared结果必须并列，不能称现四1RW硬件已到5。

## 运行接口

```sh
python3 -B project/experiments/iterative_speed/round01/run.py --root "$RUN"
```

要求真实 Slurm 作业，1至4核。`job.sh`采用既有容器、SystemC3.0.2和4核，不由本工具上传或提交作业。

运行目录：

```text
$RUN/
  source/                     # 父任务冻结的Git源码
  inputs.json                 # source_commit、code_sha256、input_sha256
  source-files.sha256
  input-files.sha256
  inputs/                     # run15使用的全部旧输入
  run15-result.json            # 固定原始回执 SHA31213ac8...6727cbc
  calibration-result.json     # 新U集成RTL的原始passed回执，禁止预填费用
  results/                    # runner新建，不能已存在
```

CLI模型参数继承旧11参数前缀，最后追加 `0` 或 `1`。例如：

```sh
model decode512.trace queued_pipe_w8 adaptive_prefix_pair_combine 8 1 1 16 0 4 0 1
```

省略新增参数相当于0。生成时可无profile供默认兼容性检查，但此binary使用flag1必须报错；正式run始终要求完整校准回执。费用编译入生成源码并携带原始校准文件SHA，不接受运行时自由填写一个速度倍率。

## 唯一计费变更

旧 NExp 的 `vector_region(i,i+1)` 完全保持，包含其原输入/输出字节宽度、E包服务、S读写、cache和DDR。只替换后续额外 `elements*16`：

- S32输入/S32输出：按1..8元素帧查校准表。NX32每个真实128b输入frame最多4个S32容器，因此n8必须两次真实n4服务。费用采用实际接受到下一次可接受的间隔，包含集成wrapper/control/返回握手；不拿standalone S16 n8响应延迟代替。
- S16输入/S32输出：本轮全部fallback旧 `16n`。当前prefill2恰属此类，所以flag1可以与旧结果全等，这是明确范围，不是测试失败。
- NX32数学合同只保留每个S32容器的有符号low16，N输出U16零扩至S32。这是继承旧packed假设的有损别名边界，不是任意S32指数值的数值证明。

`iteration_study`分开记录qualified/fallback操作、元素、帧数、旧费用、候选费用及实际选中费用；也保存校准结果SHA、RTL commit与费用表。保留的旧E/S费用不会被额外称作新收益。完整U含S的测试用于接入验证，计算profile只能取不含S的补充compute-wrapper服务。

## profile合同

直接读取原始 `calibration-result.json`：顶层 `passed=true`、`source_commit`、`rtl_source_sha256`；profile为：

```text
schema_version: 1
scope: NExp supplemental compute wrapper service only; old vector_region unchanged
payload_contract: signed low16 of each S32 container, U16 zeroextend to S32
rows: count1..8，每项包含count/charge_cycles/subcounts/mode/derivation
mode: legacy_s32_low16_zeroextend
subcounts: n<=4时[n]；n>4时[4,n-4]
```

`measurements.compute_s32`必须包含真实count1..4观察点及 `accepted_to_next_accept_cycles`；同count多seed须完全一致。每个 `charge_cycles` 独立重算为对应子frame间隔之和。不能仅凭profile自己声明一组费用。每项测量的 `passed/log/log_sha256/command/mode/seed` 必须对应顶层 `commands` 中exit0记录和 `runs` 中同一成功运行；compute来源同时要求至少65536个数值检查。`full_U` 必须覆盖S32 count1..4并满足读S、compute、写S分项守恒。

顶层六项gate `compute_s32/full_U/numeric/lifecycle/default_compatibility/enabled_ordinary` 均须为true；`profile.passed=true`、`fallback_input_bits=[16]`、单N资源及无物理资格声明也须一致。最终模型回执保留整个校准文件SHA以及所用日志SHA/命令映射，不将完整U含S费用再次加到旧S上。

## 测试与守恒

8个baseline先跑：W8/decode512、W16/decode512、W8/decode2048、W8/prefill2，各shared与idealdual。删除唯一新增metadata后完整RESULT逐字段等于run15。然后同样8个flag1候选。

独立audit从原trace重推NExp输入格式、元素及尾帧。M工作、非NExp算术、全部逻辑/总线字节、描述符、S服务/预约、cache状态、U/P数目、容量、端口、context工作与策略保持；等待和绝对时序可以变化。候选 `vector_work_ticks` 与旧值之差必须等于所替换的补充服务差额。没有合格格式时，候选也必须整份旧RESULT全等。

另跑既有225 kernels、validate、smoke；每case关键8项篡改拒绝、profile费用/模式/缺count/未通过/日志来源/生命周期gate六项拒绝、非法flag与实际无profile binary拒绝。完成后保存实际source/input/profile/generated/log SHA和完整命令。

## 状态与边界

当前只做Python AST、源文本生成、旧生成物五份SHA精确回归与独立trace解析；另用明确标记为合成数据的profile验证16份metadata合同、128项结果篡改拒绝，以及4项来源/费用拒绝。合成profile只用于Python审计自检，未生成性能结论或作为实际校准交付。未本机编译或仿真。真实profile与候选token/s尚待父任务服务器run16/run17。理想双端口层不表示四个1RW bank已实现独立64B读写，不转移300MHz物理资格，不声称完整大模型数值或真实生成速度。
