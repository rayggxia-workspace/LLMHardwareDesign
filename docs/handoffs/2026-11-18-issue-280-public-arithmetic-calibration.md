# 七模型公共算术标定接续

2026-11-18，Asia/Shanghai；负责人 Melodydt。[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280)、[草稿 PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281)，仓库 rayggxia-workspace/LLMHardwareDesign。分支 `task/280-seven-model-energy`，基分支 `task/274-seven-model-short-throughput`。本机 `D:/Study_material/Study_material/LLMHardwareDesign` 为无 `.git` 导出工作区；通过已核验的 Melodydt GitHub 连接、expected-SHA 更新任务分支。没有合并主干。新增本地文件限本任务；共享状态文档基于远端最新内容更新，保留其他成员记录。

## 已完成

27 份标定结果、262 组真实输入样本已在服务器核验数值、配对活动、结果 SHA，并下载小型回执再次核对 SHA。归档见 [index.json](../../work/Melodydt/280/arithmetic-calibration-results/index.json) 和同目录 `archive.sha256`；大波形、向量、综合网表留在服务器。七模型 N 66 样本、E32 66 样本、scan 66 样本全部通过；apply 36 样本通过、30 个大向量显式排除；Llama/Granite softmax 16、RoPE 12 样本通过。

| 模型 | E32 每次 RMS 元素数 | 样本数 | 两次乘法动态增量 µJ/次 |
| --- | ---: | ---: | ---: |
| Llama | 2048 | 6 | 26.032–26.265 |
| Granite | 1536 | 6 | 19.223–19.713 |
| Qwen3 | 128 / 1024 | 6 / 6 | 1.603–1.631 / 12.853–13.065 |
| Qwen3.5 | 256 / 2560 | 6 / 6 | 3.227–3.260 / 32.069–32.680 |
| Phi | 3072 | 6 | 38.157–38.874 |
| Gemma | 256 / 2560 | 6 / 12 | 3.182–3.241 / 32.407–33.050 |
| Falcon | 2560 | 6 | 31.818–32.313 |

长度不同，不构成模型效率排名；样本极值不是置信区间。E32 表仅算因子和 gamma 两次乘法，不包含 N、scan/apply 包装、访存、闲置或整模型驻留。

新增软算子结果：softmax 1/2 元素 87 周期、513/514 元素 2647 周期，16 样本动态增量 4.832–206.361 nJ/次；RoPE 64 元素的 16 个四路包共 976 周期，12 样本 1.248–1.312 µJ/次。scan 66 样本约 1.207–15.098 nJ/次。apply 36 样本约 1.681–27.455 µJ/次，随向量长度变化，包含包装和 E32。测试逐项检查中间/最终结果、错误标志和访问数量；这些周期来自理想单 outstanding S128 夹具，不等同实际系统 SRAM 延迟。

系统仍为 512-bit SRAM、三 P FFN、代表性 KV 位置、两步 decode/短 prefill；算术口宽度不改变 SRAM 配置。名义 300 MHz；E32/包装波形 3334 ps，N 按既有 300 MHz 重定时。Nangate45 typical、综合后 RTL 边界活动传播；没有 SPEF/布线寄生、内部门级回放或 300 MHz 时序签核。Verilator 5.042；OpenROAD 自报 unknown，精确版本待核实。冻结 RTL 原 commit 待核实，保留逐文件 SHA，不以脚本 commit 冒充。

`rms-e32-timing-ledger.json` 对齐七模型 30 个窗口/site 组合，2,665,472 个 PRODUCT 包：TLM 9 周期/包，连续无阻塞 RTL 18 周期/包。差额 23,989,248 是汇总算术资源周期，不能直接加到 token 墙钟时间，不能把速度乘二。尚未重写冻结时序或模型数值。

**尚未将这些算术增量填入整模型总值。** apply 已含 E32，禁止再叠加独立 E32；尚缺调用加权、共享资源去重、等待和 idle 驻留。PDF v2.1 片上/片上＋DDR 小计暂保持原值，后续积分完成再更新。

## 作业与版本

登录 `t6s011227@BSCC-T6@ssh.cn-zhongwei-1.paracloud.com`（SSH 实际参数用下方 `-l`），服务器根目录：

```bash
ssh -l 't6s011227@BSCC-T6' ssh.cn-zhongwei-1.paracloud.com
R=/public3/home/t6s011227/LLMHardware/zenanyan/issue-280-bscc-t6-01
```

工具位于 `~/LLMHardware/opt`。本轮新增作业均 v6_384、12 核、UNLIMITED；扩展采样为每作业两任务、各 12 核。任务/分支/本机目录对应关系见开头。

| 作业 | 内容 | 结果/耗时 | 节点 | 目录 |
| --- | --- | --- | --- | --- |
| 38831450 | Falcon E32 | COMPLETED 0:0 / 1:11 | m3ca0506 | rms-e32-power-01/power-38831450 |
| 38831451 | Qwen3.5 E32 | COMPLETED 0:0 / 2:06 | m3ca1601 | rms-e32-power-01/power-38831451 |
| 38831452 | Phi E32 | COMPLETED 0:0 / 1:02 | m3ca2305 | rms-e32-power-01/power-38831452 |
| 38831453 | Gemma E32 | COMPLETED 0:0 / 3:30 | m3ca1905 | rms-e32-power-01/power-38831453 |
| 38831680 | Llama/Granite softmax | COMPLETED 0:0 / 1:39 | m3ca0301 | public-operator-power-01/operator-38831680 |
| 38831681 | Llama/Granite RoPE | COMPLETED 0:0 / 3:02 | m3ca0907 | public-operator-power-01/operator-38831681 |
| 38831748 | Llama/Granite/Qwen3 scan | COMPLETED 0:0 / 0:45 | m3ca0108 | public-operator-power-02/operator-38831748 |
| 38831749 | 同三模型 apply | COMPLETED 0:0 / 4:50 | m3ca0301 | public-operator-power-02/operator-38831749 |
| 38831838 | 其余四模型 scan | COMPLETED 0:0 / 1:16 | m3ca0108 | public-operator-power-02/operator-38831838 |
| 38831839 | 其余四模型 apply | COMPLETED 0:0 / 2:01，12通过/30排除 | m3ca0301 | public-operator-power-02/operator-38831839 |
| 38832101 | 其余模型 softmax | 已受理；等四项采样 afterok | 待分配 | public-operator-power-02/operator-38832101 |
| 38832112 | 其余模型 RoPE | 已受理；等四项采样 afterok | 待分配 | public-operator-power-02/operator-38832112 |

运行脚本版本：E32 `8c801bf3cf55815d72e00c7f75ee35bcf677a4fd`；public-operator-power-01 `a632159d3bf5cf5bdc049a9338e6140c615d6105`；public-operator-power-02 `b94d221baaee5e1218aca795846fc891b756255f`。源码脚本在 `work/Melodydt/280/`。bundle 内 `inputs.sha256` 固定脚本、测试和 source-commit；结果内 `results.sha256` 固定 calibration/build/receipt。实际脚本验证映射源、网表及 Liberty SHA 后才运行。

所有 RMS N 作业已完成：Llama 38828633/34，Granite 38828998/99，Qwen3 38829008/09，Phi 38829000/01，Gemma 38829002/03，Qwen3.5 38829004/05，Falcon 38829006/07；结果在 `R/common-arithmetic-n-01/n-<job>/`，全部纳入归档。既有 E32 Llama 38830436、Granite 38830711、Qwen3 38830712 也纳入本次核验。

00:50 快照：扩展采样 Phi 38830190/m3ca2103、Gemma 38830191/m3ca2208、Qwen3.5 38830192/m3cd0505、Falcon 38830193/m3cd0608 均 RUNNING，已运行约 1:06；Llama 38830188 和 Granite 38830189 已通过。采样 bundle `R/operator-capture-02`、版本 `67e0d9afb58301a919d8e0fc37ec5650e71839e4`；结果 `run-<job>/{prefill,decode}`，日志 `slurm-<job>.log`。后续更晚的状态以归档 `job-status.json` 为准。

既有 DMA 综合 38769386/88、38795299/300 仍独立运行，四项后继 38795516–19 等依赖；未取消或更改。其精确 RTL 增量不阻塞当前算术标定，但仍是后续替代近似项的来源。不要混入同账号下非本任务的作业。

## 可复制启动及追踪命令

softmax/RoPE 首批实际命令模式如下，kind 分别取 softmax/rope；目录决定源码版本：

```bash
cd "$R/public-operator-power-01"
sbatch --parsable --time=0 --job-name="mdt-pwr-$kind" run_public_operator_power.sbatch "$kind" \
 "$R/operator-capture-02/run-3883018"{8,9}/{prefill,decode}/operator-observation.json
```

三模型 scan/apply 实际命令（kind 取 scan/apply）：

```bash
cd "$R/public-operator-power-02"
sbatch --parsable --time=0 --job-name="mdt-rms-$kind" run_public_operator_power.sbatch "$kind" \
 "$R/common-arithmetic-capture-01/run-38828362/"{prefill,decode}/arithmetic-observation.json \
 "$R/common-arithmetic-capture-01/run-38828902/"{prefill,decode}/arithmetic-observation.json \
 "$R/common-arithmetic-qwen3-01/qwen3-38828968/prefill-w4-tile128-pr272-combined/arithmetic-observation.json" \
 "$R/common-arithmetic-qwen3-01/qwen3-38828968/decode-live-w4-tile128-pr272-combined/arithmetic-observation.json"
sbatch --parsable --time=0 --job-name="mdt-rms-$kind-rest" run_public_operator_power.sbatch "$kind" \
 "$R/common-arithmetic-capture-01/run-3882890"{3,4,5,6}/{prefill,decode}/arithmetic-observation.json
```

E32 四模型实际使用 `R/rms-e32-power-01/run_rms_e32_power.sbatch`、job name `mdt-e32pwr-<model>`，传入 `R/common-arithmetic-capture-01/run-<capture>/{prefill,decode}/arithmetic-observation.json`；Falcon/Qwen3.5 输入分别 38828906/905，已核验成功后直接提交；Phi/Gemma 分别 38828903/904，以 `--dependency=afterok:<capture>` 提交。均 `sbatch --parsable --time=0`。

已提交的后继命令（不要重复提交）：

```bash
cd "$R/public-operator-power-02"
for kind in softmax rope; do
 sbatch --parsable --time=0 --dependency=afterok:38830190:38830191:38830192:38830193 \
  --job-name="mdt-op-$kind-rest" run_public_operator_power.sbatch "$kind" \
  "$R/operator-capture-02/run-3883019"{0,1,2,3}/{prefill,decode}/operator-observation.json
done
```

**恢复的第一步是查询现有作业，不是重新提交。**

```bash
squeue -u "$USER" -o '%.18i %.30j %.10T %.12M %.12l %.30R'
sacct -X -j 38830190,38830191,38830192,38830193,38832101,38832112 \
 --format=JobID,JobName,State,ExitCode,Elapsed,NodeList,Timelimit,AllocCPUS -P
tail -n 30 "$R/operator-capture-02/slurm-38830193.log"
tail -n 30 "$R/public-operator-power-02/slurm-38832101.log"
cat "$R/public-operator-power-02/operator-38832101/calibration.json"
(cd "$R/public-operator-power-02/operator-38832101" && sha256sum -c results.sha256)
python3 "$R/collect_arithmetic_calibration.py" "$R" "$R/arithmetic-calibration-index-20261118.json"
```

后继输出目录在运行后才产生。成功判据：COMPLETED 0:0、`PUBLIC_OPERATOR_PASS`、所有数值/计数/错误位检查通过、边界活动完整、结果及源 SHA 一致；不能把排队、退出或候选 Python 审计算作 RTL/模型验收。collector 当前固定验收 27 份已完成结果，后继完成后需显式增加条目，不能以旧索引冒充覆盖新作业。

## 全部剩余步骤

1. 等待并验收四模型扩展采样及已提交的 softmax/RoPE 后继；检查冻结输出/时序不变、输入/结果 SHA、采样复算、binding audit。后继预计自身几分钟级；采样没有可靠剩余时间估计。
2. 可立即继续准备：30 个大 RMS 向量的跨 bank 或分块 staging，验证完整结果与实际访存/包装周期；Qwen3 非 RMS 公共算子的专用捕获入口也待补齐。
3. 可继续编写、实际验收需真实样本：缩放/专家加权和 E32 指令；Granite router 的 S32→S16 排序/tie/EXP/归一化；Gemma S32 GELU 近似与范围；Qwen3.5 GDN、Falcon Mamba2/Conv4 的 R 指令加载、状态、执行和提交，以及 Softplus/EXP/norm-gate。候选定点审计不等于 RTL 等价，FP32 差异和溢出需单列。
4. 将真实调用数按窗口/site/形状加权，处理 E32/apply/RoPE 重复归属，补 SRAM 请求、访存等待和每个实例仅一次的 idle/驻留；校准 9/18 周期差与并行重叠后再解释吞吐。不得把 standalone 能耗和全量模块功耗重复相加。
5. 结合既有 M、控制、互连、512-bit SRAM/PM、DMA 近似及 DDR 分项，更新七模型的片上与片上＋DDR 小计、平均功率、缺项清单、误差边界及 PDF；精确 DMA 综合回执完成后替换对应近似，不等待 P&R。
6. 分项守恒、单位、输入 SHA、冻结性能和数值回归；更新 PR、Issue、个人进度，审查/合并另行验收。原 RTL commit、OpenROAD 准确版本仍待追溯。

本轮实际验证：项目管理结构 PASS（不代表业务验收）；脚本 AST；上述 262 样本数值/端口活动/配对功耗；服务器 SHA 清单和本地归档 SHA；时序账本 30 组计数守恒。未执行整模型 RTL、物理时序签核、内部门级活动或新增整模型 FP32 回归。

规则 rayggxia-project-collab 1.0.0。Issue in_progress、PR 草稿未合并，审查人待指定；管理中心登记 PR #5 仍 pending。缺 `config/board.json` 及 Projects 能力，看板 unverified/同步 pending，待有权限维护者处理。作业通过 Slurm 独立持续保存日志和结果；未配置聊天自动监测，下一次由用户唤起按上述入口核验。
