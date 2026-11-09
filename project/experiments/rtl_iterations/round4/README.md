# R4：真实单 N/U 的四 lane stateless op12 验证

仅测试材料；未在本地运行 EDA。生产候选由 `feed/round4` 提供，正式目录为 `project/experiments/rtl_iterations/round4`。不改 R2/R3 证据，不扩 SRAM。NEXP_DIRECT_LANES 默认 2，仅 NEXP_BATCH && NEXP_DIRECT 时 U 内 op12 可选 4；普通统计、factor、replay、top 保持两 lane。非法 lane 参数在初始化时定向失败。

## 交付与源锁

本目录 `prepare.py/run.py/job.sh/make_prior.py`、六份 `r2_*.sv` 模板和本说明复制到正式 round4 根；生产候选的 `generate.py` 在该根命名 `generate_rtl.py`，保持 `baseline/` 相对位置，设计说明命名 `RTL_DESIGN.md`，源交付清单命名 `rtl-delivery.json`。本目录 `delivery.json` 可命名 `tests-delivery.json`。`preview/` 不交付。

模板逐字节来自实际 run18 `results/generated/`，prepare 强制六项固定 SHA。生产候选 native SHA `6efe29ed1121085d59bf072e2c3a062c9c18d67fa0f69a30da16f3b2b56f03ec`、U SHA `f5e30680ab32cc0a96e25e60268549265fac92373966a449e447cf28df33b413`；旧基线使用 generate_rtl 的 exact-R2 `baseline/`，shared/router 与 adapter 使用正式树中冻结的 R2 原件。EXP 查表头、E、N group、真实 local S 和仲裁器等依赖由 `run.py:RTL_PATHS` 明列，必须全部进入部署 `code_sha256`。

## 默认行为与实际执行证明

21 个顺序编译配置，各运行 reset mode/seed `(1,143),(2,143),(2,144)`，共 63 次。每次编译 `-j<=4`，不并发编译。

* `baseline_legacy/default_legacy/lanes4_legacy`：exact-R2 普通 U、R4 默认、R4 参数4但 DIRECT0；全部 COMPAT 数据/周期与物理 SRAM 事件精确相等。
* `baseline_batch/disabled_batch/direct_batch`：旧 four-command batch、参数4但 DIRECT0、启用四 lane；DIRECT0 全事件精确相等，启用后普通 N op0..14 的接受至完成间隔/元数据/结果精确相等。
* `baseline_compute/default_compute/baseline_disabled_compute/disabled_compute/compute`：新旧单 N compute；包含完整 65536 signed16 域、S32 low16 别名边界、n1..8、NX32 n1..4、尾 lane 清零、非法 count/payload、背压和在途 reset。
* `baseline_full_U/default_full_U/baseline_disabled_full_U/disabled_full_U/full_U`：同一真实 U/S 链；每条测量必须恰好一次 S 读和一次 S 写，完整 wall 等于 input/compute/output 分项。原有真实共享 S held response 阻塞输出 write/ACK 的断言保留，done 不得提前。
* `baseline_stateless/default_stateless/stateless`：统计、factor、softmax/RMS replay 与 top 全部持久字段在 op12 前后精确相等，普通命令继续执行；12 个 reset 点覆盖执行及 held completion。
* `group_gate`：LANES4 下四种 BATCH/DIRECT 组合，仅两 flag 同时开启才允许原生 op12。`illegal_lanes`：LANES3 实际运行必须以指定 `$fatal` 文本非零退出，单独列为预期拒绝，不能当一般失败放行。

`NEXP_LANE_PATH` 的 checked_commands 不来自参数或预计延迟。watcher 在每次真实 native op12 接受时保存 count，每个真实 CALC 边递增，成功响应消费时断言 `steps=ceil(count/LANES)`。非法请求不得执行 CALC；reset 取消在途记录，不计完成。逐 count 的 NEXP_LANE_COUNT 守恒并覆盖 n1..8。原 NEXP_NATIVE_PATH 保留 accepted 计数（可含 reset 取消），报告新增 `native_path.op12_lanes4_commands` 明确定义为已完成且 CALC 断言通过数，因此等于 lane_path.checked_commands，而不冒充全部 accepted。

对 exact-R2 与 R4 同时加入被动 `R4_TRACE`，比较所有接受的 native 命令/响应的数据与 global cycle，不改变刺激或 delay。默认2四类完整 trace 均须精确相等；参数4但 DIRECT0 的 compute/U 也精确相等。

## 实际 run18 原可观察事件

输入 `run18-result.json` SHA `fb0b4d0d1251140655feea5bd671c196e5ae13b1fd47066dc22d6e1e1a2eac78`。

`run18-observed.json` 是小型独立部署输入，SHA `cc5e13093dd5269e8fcd473e56a524e7a3b4e21d426e064b48ed0fab1f080296`，由 `make_prior.py` 只读提取 run18 七类×三 seed 的全部原可观察 COMPAT、带时间物理 SRAM、NEXP 测量、native path 和 PASS 行，排除工具尾注。每个原 log SHA 同时对照 run18 result 中成功 command 与原 output-files 清单。runner 固定该投影 SHA，再将每项 log SHA 接回原 result，比较 fresh exact-R2/default2/相应 DIRECT0 的全部旧可观察行。原 run18 没有被动 R4_TRACE；该新增握手 trace 只声称与本轮 fresh exact-R2 源重跑相等，不倒称原日志已包含未记录字段。

可重复整理输入（纯 Python，无 EDA）：

```text
python -B make_prior.py --receipts /path/to/run18/receipts --out run18-observed.json
```

## 运行入口与费用

root 由父任务部署到 Melodydt 自己的服务器目录。root/source 为已提交任务源码，root/inputs.json 的 source_commit 必须真实，code_sha256/input_sha256 不得为空；必须包含上述依赖、本目录、候选 baseline 及两个 run18 输入。job.sh 先核对 source-files/input-files 清单，记录实际 Slurm allocation、SIF/Verilator/bank SHA，再进入原容器执行：

```text
python3 -B ROOT/source/project/experiments/rtl_iterations/round4/run.py --root ROOT
```

仅 Slurm c64/c96、1 task 4 CPU；有效分配和作业号是 runner 硬门。固定 Verilator 为 `/public/home/yuzelu/opt/eda/verilator-5-042-repro02/bin/verilator`。真实 SRAM bank SHA `6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7`；没有虚构多端口。完整旧源沿 run18 保留已有 warning 范式；未改 router 额外严格 lint。失败保留 result.json error/traceback、退出码及原 log SHA。

profile 仅在所有实际 gates 通过后由实际 compute_s32 的接受至下一次接受间隔生成。NX32 一个 128bit 帧最多四个 S32 容器，n5..8 仍显式拆成 `[4,n-4]` 两次真实 wrapper 费用，不能把 packedS16 的 n8 单次费用冒作 S32。scope/payload 与 R2 相同，implementation 为 `native_stateless_relative_exp_op12_lanes4`，row.mode 为 `legacy_s32_low16_zeroextend_stateless_op12_lanes4`；所有 active runs/measurements 标记 direct_mode1/direct_lanes4，并由实际 CALC 路径证明绑定成功 command/log SHA。

旧模型只可替换原 NExp 附加 compute 服务；原 S/cache/DDR/E 和 vector_region 保留。full_U 费用用于核对 S 生命周期，不可再与原 vector_region 重复收费。S32 low16 extraction/U16 zeroextend 别名合同未变，不是任意 S32 EXP 数值证明。没有物理面积、STA、300MHz 或端到端 LLM RTL 资格；额外两 EXP 单元及控制寄存器成本见独立生产设计账本。

## 本地实际检查

已执行：Python AST、固定模板/源 SHA、纯生成、run18 实际测量解析、CALC 直方图正例与篡改拒绝、21份原 log SHA 同 result/manifest 交叉核对。未执行：本地/服务器 RTL 编译或仿真；真实周期和新费用等待父任务 Slurm 作业。
