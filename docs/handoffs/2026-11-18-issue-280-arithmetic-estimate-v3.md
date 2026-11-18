# 七模型算术补项能耗 v3 交付与接续

更新时间：2026-11-18，Asia/Shanghai。规则 rayggxia-project-collab 1.0.0。

- 仓库：rayggxia-workspace/LLMHardwareDesign；project_id：llm-hardware-design。
- Issue：https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280；负责人 Melodydt。
- PR：https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281，草稿未合并，独立审查人待指定。
- 分支：`task/280-seven-model-energy`；基分支 `task/274-seven-model-short-throughput`。
- 数据/估算代码提交：`0d84209e10e898f17998e959157a760a80c2afaf`。本交接及最终报告的提交另见 PR head；该数据提交不是所有远程仿真的源版本。
- 本机：`D:/Study_material/Study_material/LLMHardwareDesign` 是无 `.git` 的文件副本；通过 Melodydt GitHub 连接创建 tree/commit，并以 expected_sha 更新任务分支。仅本任务清单上传；本地无关改动没有纳入。

## 本轮目标和完成口径

用户明确选择“完成能耗估算：允许特殊算子采用明确标注的运算级近似和误差范围，不宣称 RTL 数值验收”。本版已完成七模型三窗算术成本估算、两类能耗/平均功率和 PDF。公共算术使用真实输入活动标定，特殊算子使用运算计数与显式敏感性场景。范围不是概率置信区间、已校准误差界或保证上下界；真实能耗可能落在范围外。

系统仍为 512-bit SRAM、三 P FFN、名义 300 MHz；冻结短 Prefill、真实 512 位置历史起点及两步 Decode 时间不变。没有等待或补做布局布线，没有把 TLM 调度等同于已验收的整模型 RTL。Issue 还包含更广的物理/部署与对照实验范围，因此不标 done。

## 第 2 步 Decode 结果

单位 mJ/输出 token，默认小计含已覆盖写 DMA；读 DMA 动态代理另列于每模型页和 JSON，未混入下表。

| 模型 | 片上条件估算 | 片上＋DDR 条件估算 |
| --- | ---: | ---: |
| Qwen3-0.6B | 162.175–170.487 | 495.029–503.342 |
| Llama-3.2-1B | 201.743–212.362 | 655.229–665.847 |
| Granite | 167.428–180.426 | 521.406–534.403 |
| Phi-4-mini | 564.155–593.889 | 1866.541–1896.275 |
| Gemma-3-4B | 537.480–646.122 | 1749.076–1857.717 |
| Qwen3.5-4B | 702.234–1340.473 | 1946.169–2584.409 |
| Falcon-H1-3B | 728.201–1885.552 | 1626.445–2783.796 |

GDN/Mamba 的标量状态更新量很大，其成本迁移假设主导 Qwen3.5/Falcon 范围；Gemma 的 GELU 代理也是主要不确定项。其余模型主要新增公共算术及实例驻留场景。不能以此表直接进行已实现硬件的效率排名。

## 成果和复现

- 正式报告：`docs/experiments/seven-model-energy-evaluation.pdf`，18 页；本地交付 `output/pdf/seven-model-energy-evaluation.pdf`。
- 持续维护索引：`work/Melodydt/280/energy_report_models.json`，format=arithmetic-v3；v2.1 索引另存 `energy_report_models_v2_1.json`。
- 七份 `*_tlm_power_v3_arithmetic.json` 包含三窗两类能耗、两类平均功率、逐签名运算数、原小计、新增分项和读 DMA 0.5/1/2 倍场景。
- `ARITHMETIC_ESTIMATION_METHOD.md` 给出公式、代理与去重边界；`arithmetic-model-counts/` 保存已核验调用数及原始文件 SHA。
- `arithmetic-calibration-results/v3-evidence-index.json` 保存全部 32 份标定回执散列和四项新作业的实际 SubmitLine、节点、源 commit、工作/日志/结果目录；历史 index 保留。
- N/E32/scan 各 66 样本；96 个 apply 分块完整覆盖 66 个原 RMS 向量，零容量排除。softmax 56、RoPE 54。旧 36 个 apply 样本不重复计入。
- `arithmetic-report-validation.json`：462 组格式化数值核对；`arithmetic-report-visual-review.json`：18 页 PNG 目检通过。

在仓库根目录运行（PDF 两个命令需要带 reportlab/pypdf 的 Python；本轮采用 Codex bundled Python，报告字体 Deng.ttf/Dengb.ttf）：

```text
python scripts/check_project.py
python work/Melodydt/280/seven_model_arithmetic_estimate.py
python work/Melodydt/280/verify_arithmetic_estimate.py
python work/Melodydt/280/build_energy_report.py
python work/Melodydt/280/verify_energy_report_pdf.py output/pdf/seven-model-energy-evaluation.pdf
```

本轮以上检查实际通过；PDF 先全部 18 页目检，添加片上平均功率后重新渲染并复查全部 7 个变更页，其余 11 页像素一致。管理检查仅覆盖管理结构。未执行新增整模型 FP32 回归、整模型门级活动、特殊算子匹配 RTL 数值验收或 300 MHz 物理签核。

## 已完成作业和服务器入口

登录 `ssh.cn-zhongwei-1.paracloud.com`，用户 `t6s011227@BSCC-T6`。工作根目录：
`/public3/home/t6s011227/LLMHardware/zenanyan/issue-280-bscc-t6-01`（下称 R）。工具仍在 `~/LLMHardware/opt`。下列全部 v6_384、TimeLimit=UNLIMITED、COMPLETED 0:0。

| 作业 | 名称 | 节点 | 核数 | 耗时 | 源码 commit |
| --- | --- | --- | --- | --- | --- |
| 38837942 | mdt-rms-chunked | m3ca0606 | 12 | 25:36 | 1ebcc49a4afe198a82a0031d91aaf70b823bbe0f |
| 38838045 | mdt-280q3op | m3ca0706 | 2×12 | 24:02 | 0a4f3386d99e3005ad029378a52294057ce5d8b3 |
| 38838116 | mdt-q3-softmax | m3ca0305 | 12 | 1:03 | 1ebcc49a4afe198a82a0031d91aaf70b823bbe0f |
| 38838117 | mdt-q3-rope | m3ca1301 | 12 | 3:08 | 1ebcc49a4afe198a82a0031d91aaf70b823bbe0f |

Qwen3 capture 工作/日志位于 `R/qwen3-operator-capture-01`，结果 `qwen3-38838045`；另三项工作/日志位于 `R/public-operator-power-03`，结果各 `operator-JOBID`，日志各 `slurm-JOBID.log`。SubmitLine 从 sacct 实际读回，完整保存于证据索引；例如 Qwen3 为 `sbatch --parsable --time=0 run_qwen3_operator_capture.sbatch`，两项后继实际附加 `--dependency=afterok:38838045`。

Qwen3 完整冻结数值/时间和 DDR/SRAM 对账通过，新算子捕获 20 样本（softmax 8、RoPE 12）复算通过。四项服务器 results.sha256 校验通过，小型原始回执已归档，大体积向量、VCD 和构建日志继续保存在上述授权任务目录。Verilator 5.042、Nangate45 typical；OpenROAD 精确版本和冻结 RTL 原始 commit 待核实，不能拿运行脚本 commit 代替；源 RTL/Liberty SHA 保存在回执中。

服务器可直接执行：

```bash
R=/public3/home/t6s011227/LLMHardware/zenanyan/issue-280-bscc-t6-01
squeue -j 38769386,38795299,38795516,38795518 -o '%.18i %.24j %.10T %.12M %.20R'
sacct -X -j 38837942,38838045,38838116,38838117 --format=JobID,JobName,State,ExitCode,Elapsed,NodeList,Timelimit
tail -n 40 "$R/public-operator-power-03/slurm-38837942.log"
cat "$R/public-operator-power-03/operator-38838116/calibration.json"
(cd "$R/public-operator-power-03/operator-38838116" && sha256sum -c results.sha256)
(cd "$R/qwen3-operator-capture-01/qwen3-38838045" && sha256sum -c results.sha256)
```

## 既有长作业状态与完整剩余范围

2026-11-18 11:27:49 +08 实际快照：38769386 RUNNING 42:44:59（m3ca0405）；38795299 RUNNING 35:57:10（m3ca0608）。38769388 FAILED 2:0，39:41:52；38795300 FAILED 2:0，29:44:51。38795516/18 仍 PENDING，38795517/19 CANCELLED。均无六小时时限。没有因为本轮结束取消任何作业，也没有配置聊天结束后的自动监测。

两项失败发生在综合网表生成之后的 IO pin placement：26,307 pins 超过 17,128 可用位置（PPL-0024），当前周长 9,600 µm，要求约 14,731.92 µm。因此不能笼统称为综合失败。现存候选网表：`R/read-phase-noshare/physical-38795300/flow/results/nangate45/c639_dma_phase_ports/base/1_synth_lec.v`；还没有以该网表完成读 DMA 功耗验收。

本轮已选估算目标没有等待项。后续提升准确性/扩大覆盖需要：

1. 检查现存读 DMA 网表和 Liberty，改成综合后直接活动标定，替代写侧成本代理并补读侧静默/漏电；可以独立准备，不必等布局布线。原 route 依赖脚本要求 6_final.v，不能原样重提冒充无寄生标定。
2. 为 GELU、浮点 EXP/Softplus、GDN/Mamba 等实现匹配数据格式/指令的 RTL，解决 Falcon S16 Q14 系数越界；逐算子数值和活动验收后替代代理。这是提高准确性的新增实现工作，不是本轮已完成。
3. 固定实际算术实例数、门控和分块 staging，校准 E32 9/18 周期及并行重叠，再重跑新的整模型时间与数值；当前 PDF 沿用冻结时间。
4. 补母控未覆盖运行取指/启动、局控外壳/分发、交换机活跃流量、全局时钟/跨块互连、DDR PHY/封装/板级 I/O。两类小计均注明这些项目。
5. 若以后要求正式 300 MHz 物理验收，再修复 M 时序、部署/布线、寄生及毛刺功耗；当前不以此阻塞研究估算。
6. PR 独立审查和后续合并；项目登记 management-hub PR #5 仍 open/unmerged，记 pending。config/board.json 返回 404，当前无 Projects 工具，条目状态 unverified、同步 pending，由有权限维护者处理；审查人待指定。Issue 保持真实 in_progress，不标 done。

恢复第一步：读回 PR #281 最新 head、Issue #280 和本交接，运行算术对账脚本；仅在用户继续提高准确性时按上列顺序推进。完成项以本交接覆盖旧记录的“等待算术采样/积分/PDF”描述，历史日志保留。
