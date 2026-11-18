# 算术缺项 2–4：E32 实测与六模型扩展采样

2026-11-17，Asia/Shanghai；负责人 Melodydt。[仓库](https://github.com/rayggxia-workspace/LLMHardwareDesign)、[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280)、[草稿 PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281)。分支 `task/280-seven-model-energy`，基分支 `task/274-seven-model-short-throughput`。本机 `D:/Study_material/Study_material/LLMHardwareDesign` 是无 `.git` 导出工作区；使用已核验的 Melodydt GitHub 连接创建树/提交并以 expected-SHA 更新任务分支，未合并主干。

## 已完成及证据边界

- 38830027：六模型观察点补丁预检查全部通过，10 秒，m3ca0705，COMPLETED 0:0。
- 38830028：Llama 三窗 6 组真实 RMS 输入、6,144 个两阶段 PRODUCT 包逐项匹配 `e_s32_ap64`；15 秒，m3ca1905，COMPLETED 0:0。源码 `358ba0c6c49f73c13778710b92fc9c8a603244a6`。
- 38830195：Granite 6 组、Qwen3 12 组真实 RMS 输入，新增 8,064 个 PRODUCT 包逐项通过；10 秒，COMPLETED 0:0。上述三模型累计 14,208 包。源码 `67e0d9afb58301a919d8e0fc37ec5650e71839e4`。
- 连续输入、输出不阻塞时，E32 PRODUCT 实测 18 周期/四个 S32 元素，TLM 两个乘法叶节点各记 9 周期；完整调度周期尚待校准。未改写原冻结模型速度，不直接把整体时延乘二。
- 38830194：4:01，m3ca0705，COMPLETED 0:0；E32 核心 23,900 cells，RMS scan 3,301，RMS apply wrapper 2,713，RoPE wrapper 4,430。Yosys 0.68+post，Nangate45 typical，所有 mapped/unmapped 检查及 SHA 通过。wrapper 单独映射不包含外接 E32 或 SRAM，不把相互重叠的模块重复相加。
- 38830436：Llama E32 配对功耗，1:40，m3ca1604，COMPLETED 0:0，6 组真实输入全部通过；158 位边界活动均标注，等长窗口 61,452,288 ps。源码 `8c801bf3cf55815d72e00c7f75ee35bcf677a4fd`，Verilator 5.042。OpenROAD 精确版本待核实；标准单元库 SHA、RTL、网表、输入/输出 SHA 已记录。
- 原有 Granite 捕获 38828902 和 N 标定 38828998/99、Qwen3 捕获 38828968 和 N 标定 38829008/09 均已 COMPLETED 0:0，日志分别报告 2/4 与 4/8 样本 PASS；其完整 N 回执归档/统一积分仍待接续。

| Llama 窗口 | 两组样本的 E32 动态增量，µJ/次 RMS | 说明 |
| --- | --- | --- |
| Prefill | 26.215774 / 26.032136 | 两次 E32 乘法，不含其他 RMS 项 |
| 第一个 decode token | 26.265105 / 26.215126 | 同上 |
| 第二个 decode token | 26.153788 / 26.188460 | 同上 |

活跃功率约 427.149–430.940 mW，配对空闲约 3.53333 mW；计算为 `(Pactive−Pidle)×同长窗口`。这是 RTL 边界 VCD 传播到综合网表的无布线寄生估计，不是内部门级波形、物理签核或整模型功耗；样本极值不是置信区间。波形 3334 ps，与冻结 TLM 一致，名义 300 MHz；未宣称时序闭合。SRAM 仍是 512-bit 系统配置，E32 的 64-bit 是算术接口。

本地小型回执：`work/Melodydt/280/llama-rms-e32-receipt.json`、`qwen3-granite-rms-e32-receipt.json`、`e32-wrapper-map-summary.json`、`llama-rms-e32-power.json` 及对应 `*-results.sha256`。功耗汇总文件 SHA256：`1eafa435f238a01dbb3f1380f33eb32adfa4d23616408f611b148d11991d042c`。大型网表/向量/VCD 留服务器；原 RTL 来自冻结 C639 源码副本，每文件 SHA 已核验，原源码 commit 仍待核实，不将本轮运行脚本 commit 冒充 RTL 原始 commit。

## 11 月 18 日 00:02：Granite / Qwen3 E32 功耗完成

Granite `38830711 / mdt-e32pwr-granite`：1:06，m3ca0108，COMPLETED 0:0；Qwen3 `38830712 / mdt-e32pwr-qwen3`：1:47，m3ca1507，COMPLETED 0:0。各 12 核、UNLIMITED，源码、网表与 Llama 功耗作业相同；6/12 样本、158 位活动、配对窗口及 SHA 均通过。本地结果分别为 `granite-rms-e32-power.json`、`qwen3-rms-e32-power.json` 及对应 SHA 清单。三模型合计 24 个真实 RMS 样本，仍只是 E32 两阶段乘法增量。

| 模型 / RMS 元素数 | Prefill µJ/次 | 首 token µJ/次 | 第二 token µJ/次 |
| --- | --- | --- | --- |
| Granite / 1536 | 19.584071 / 19.429667 | 19.713490 / 19.527781 | 19.637170 / 19.223397 |
| Qwen3 / 1024 | 12.875443 / 12.853254 | 13.065309 / 12.909808 | 12.930761 / 13.040342 |
| Qwen3 / 128 | 1.630872 / 1.624917 | 1.618622 / 1.624333 | 1.623566 / 1.602508 |

不同向量长度不能直接作为模型效率排名。上述采样范围/物理边界与 Llama 相同，尚未进入完整模型小计。目录 `R/rms-e32-power-01`，日志 `slurm-<job>.log`，输出 `power-<job>/calibration.json`。完整启动命令与下文 Llama 相同，分别替换为 `common-arithmetic-capture-01/run-38828902/{prefill,decode}/arithmetic-observation.json` 和 `common-arithmetic-qwen3-01/qwen3-38828968/{prefill,decode-live}-w4-tile128-pr272-combined/arithmetic-observation.json`；使用对应 job name。

## 正在运行的本轮作业

登录目标：`t6s011227@BSCC-T6`，主机 `ssh.cn-zhongwei-1.paracloud.com`。所有下列作业均 `v6_384`、UNLIMITED，每个采样作业 2 tasks × 12 cores，prefill/decode 各 12 核；运行代码/结果均在授权工作根目录下，开源工具在 `~/LLMHardware/opt`。

```bash
R=$HOME/LLMHardware/zenanyan/issue-280-bscc-t6-01
B=$R/operator-capture-02
```

| 模型 / job name | 作业号 | RUNNING 节点 | 已验收来源目录（相对 R） | 本轮结果（相对 B） |
| --- | --- | --- | --- | --- |
| Llama / mdt-op-llama | 38830188 | m3ca0405 | six-model-energy-01/run-38820601-llama | run-38830188 |
| Granite / mdt-op-granite | 38830189 | m3ca1506 | six-model-energy-01/run-38820602-granite | run-38830189 |
| Phi / mdt-op-phi | 38830190 | m3ca2103 | six-model-energy-01/run-38820798-phi | run-38830190 |
| Gemma / mdt-op-gemma | 38830191 | m3ca2208 | six-model-energy-01/run-38821513-gemma | run-38830191 |
| Qwen3.5 / mdt-op-qwen35 | 38830192 | m3cd0505 | six-model-energy-01/run-38821601-qwen35 | run-38830192 |
| Falcon / mdt-op-falcon | 38830193 | m3cd0608 | six-model-energy-01/run-38821511-falcon | run-38830193 |

六项已实际进入模型重放阶段，不能写成已验收。运行脚本版本 `67e0d9afb58301a919d8e0fc37ec5650e71839e4`，探针输入清单 `operator-capture-02-inputs.sha256`。模型/输入版本由每项 `capture-provenance.json`、`operator-provenance.json`、`transfer-verified.json` 和 `instrumented-source.json` 给出。

实际提交命令（仅作追溯；勿重复提交正在运行的作业）：

```bash
cd "$B"
for model in 38820601-llama 38820602-granite 38820798-phi 38821513-gemma 38821601-qwen35 38821511-falcon; do
  sbatch --parsable --time=0 --job-name="mdt-op-${model#*-}" run_operator_capture.sbatch "$R/six-model-energy-01/run-$model"
done
sbatch --parsable --time=0 run_e32_wrapper_map.sbatch
sbatch --parsable --time=0 --job-name=mdt-e32-q3-granite run_rms_e32_check.sbatch \
  "$R/common-arithmetic-capture-01/run-38828902/prefill/arithmetic-observation.json" \
  "$R/common-arithmetic-capture-01/run-38828902/decode/arithmetic-observation.json" \
  "$R/common-arithmetic-qwen3-01/qwen3-38828968/prefill-w4-tile128-pr272-combined/arithmetic-observation.json" \
  "$R/common-arithmetic-qwen3-01/qwen3-38828968/decode-live-w4-tile128-pr272-combined/arithmetic-observation.json"
cd "$R/operator-capture-01"
sbatch --time=0 run_operator_preflight.sbatch
sbatch --time=0 run_rms_e32_check.sbatch \
  "$R/common-arithmetic-capture-01/run-38828362/prefill/arithmetic-observation.json" \
  "$R/common-arithmetic-capture-01/run-38828362/decode/arithmetic-observation.json"
cd "$R/rms-e32-power-01"
sbatch --parsable --time=0 run_rms_e32_power.sbatch "$B/map-38830194/e_s32_ap64" \
  "$R/common-arithmetic-capture-01/run-38828362/prefill/arithmetic-observation.json" \
  "$R/common-arithmetic-capture-01/run-38828362/decode/arithmetic-observation.json"
```

第一次带 `afterok:38830194` 的功耗提交被 Slurm 以 `Job dependency problem` 拒绝，未生成作业号；随后读回该综合 COMPLETED 0:0 且核验输出 SHA，再无依赖提交 38830436。没有重复功耗作业。

恢复检查的第一步（只查本任务）：

```bash
R=$HOME/LLMHardware/zenanyan/issue-280-bscc-t6-01
B=$R/operator-capture-02
squeue -j 38830188,38830189,38830190,38830191,38830192,38830193
sacct -j 38830188,38830189,38830190,38830191,38830192,38830193,38830194,38830195,38830436 -X --format=JobID,State,Elapsed,ExitCode,NodeList
tail -n 30 "$B/slurm-38830189.log"
tail -n 20 "$B/run-38830189/prefill.log" "$B/run-38830189/decode.log"
cat "$B/run-38830189/prefill/operator-capture-check.json"
cat "$B/run-38830189/prefill/operator-binding-audit.json"
cd "$B/run-38830189" && sha256sum -c results.sha256
cat "$R/rms-e32-power-01/power-38830436/calibration.json"
```

成功判据：Slurm 0:0 + 冻结 `acceptance.json` + RMS 和 operator capture check + 完整 SHA；格式审计生成并不代表候选 RTL 已通过。每个窗口/算子/site/形状前两样本，完整调用计数不抽样。PDF v2.1 整模型小计不变，防止尚未完成实例/调度绑定的分项被误计。

## 接下来全部步骤及依赖

1. **等待六项采样完成，随后可验收**：逐模型核对冻结输出、周期、算子复算、SHA 和范围/误差审计；归档小回执，必要时修复观察器，不改冻结模型来掩盖差异。原四模型 RMS/N 链 38828903–06 / 38829000–07 也需结束后验收。
2. **公共算术可接续推进**：Llama/Qwen3/Granite E32 标定已完成，后续推广到其余四模型；补 scan/apply、softmax、各种 RoPE 和 scaling 的 RTL 数值/周期/真实活动。映射已具备，真实非 RMS 操作数仍待本轮采样。核对 9/18 周期差异以及跨 bank/大向量调度，决定重新测量范围。
3. **GELU/路由可继续实现，数据验证待采样**：Gemma S32 GELU 与 S16 G、Granite S32 score 与 S16 top-k 并非直接等价；明确格式与近似误差、实现或适配 RTL，再验证 top-k/tie、路由概率和加权和，最后综合/活动标定。不能把当前 Python 候选审计算作数值正确性已解决。
4. **GDN/Mamba2 可继续 RTL 指令工件准备，误差/活动依赖真实采样**：先检查 Q14 系数可表示性、逐阶段 RNE、卷积历史顺序和注入项；按八路真实 R 生成 load/execute/read/commit 流，补 Softplus/EXP、gate/norm；验证状态/输出与模型误差并实测周期，然后做无寄生标定。32 路 TLM 不能直接当作八路 RTL 周期。
5. **依赖上述标定与周期绑定**：统一实例驻留、等待、共享资源复用及动态增量，避免与现有 E/G/U、SRAM、DMA 小计重复；重新积分各模型三个窗口。
6. **依赖新积分验收**：更新片上及片上+DDR 两类结果、每模型覆盖/未覆盖项目、PDF、分支交付包和 Issue/PR，保留无布局布线寄生和未闭合时序的边界。

详细对应关系见 [OPERATOR_BINDINGS.md](../../work/Melodydt/280/OPERATOR_BINDINGS.md)。本地管理结构检查、Python AST、服务器 Bash 检查、上述 RTL/映射/功耗及 SHA 已实际执行；完整六模型新增捕获未结束，整模型新能耗和物理签核未执行。

规则版本 rayggxia-project-collab 1.0.0。成果上传任务分支，不代表合并/验收；Issue 仍 in_progress，PR 草稿，审查人待指定。登记 management-hub PR #5 pending；缺少本项目 board.json 和 Projects 能力，看板 unverified、同步 pending，处理人待指定。本机/服务器/远端分支/主干状态分别如上，未覆盖无关改动。Slurm 独立于聊天持久运行；未配置聊天自动监测，下一次由用户唤起读取以上作业。
