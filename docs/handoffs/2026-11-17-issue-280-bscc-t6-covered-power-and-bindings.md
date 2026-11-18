# Qwen3 三窗功耗小计与物理工件接续

2026-11-17（Asia/Shanghai），Melodydt。仓库 `rayggxia-workspace/LLMHardwareDesign`，分支 `task/280-seven-model-energy`，工作起点 `8b0a8783c5b165232f0e17653a71ac7d1d39aa69`。[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) · [草稿 PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281) · [旧版 M 标定](2026-11-17-issue-280-bscc-t6-m-baseline-power.md)

## 已覆盖功耗小计

对账旧 M 三窗结果和 `calibrated-coverage/windows.json` 的冻结 rollup 散列、窗口时长及 token 数。计入 DDR 器件、G32 活跃增量、旧 M 三路参考、真实载荷写 DMA 的活跃增量，以及独立的 U ADD2 字级控制、调度与 E32 算术增量。U 的 SRAM 读写事件保留在 SRAM 项下。PM 桥、局控 PM 的写入＋CRC 和已匹配位宽的 SRAM 增量作为独立参考，等待实际角色、物理实例和共享范围核对。读 DMA、G32 空闲及其余宏和全局控制／时钟／互连待补。

| 窗口 | 平均功耗（W） | 能耗（mJ/token） |
| --- | ---: | ---: |
| 短 Prefill（2 个输入 token） | 3.445843–3.448682 | 146.947624–147.068686 |
| 首 Decode token | 3.128330–3.129197 | 437.037286–437.158354 |
| 稳态 Decode | 3.126553–3.127419 | 437.197936–437.319004 |

样本范围保留旧版 M 的 TT 300 MHz setup `−1.121800 ns` 和 hold `−0.053419 ns` 违例。旧版 M 的开钟空闲为模型假设。窗口相加采用各自低、高样本端点。小计精度受物理覆盖及采样条件约束。BSCC-T6 现有 JSON 已通过各自结果清单。服务器目录 `covered-ledger-20261117/`，`results.sha256` 为 `29c3f6a77a6224d07ddfaaee29e360de9ebd5c4b3abed8e07cc23224eb0d2cf9`。[结果 JSON](../../work/Melodydt/280/qwen3_covered_power_windows.json) 与服务器 `windows.json` 的 SHA-256 均为 `99cf1e3953895578149c623de1bc65ce65c14a87d3fe9e4a38f63091e4e0d949`。

## 新增采样与准备

- **38812748** `mdt-280mholdidle` 使用旧版 M RTL 和同一个 116976 布线模型。发送合法八拍 `BEGIN_SCOPE`，校验成功回执，并断言 8,192 个采样周期中每个上升沿均保留非零 key、owner、bias 且没有握手或错误。两份 1,330 位边界活动传播的空载功耗均为 **248.092443 mW**。夹具覆盖已安装 scope 的等待状态。权重 RAM 驻留及门级内部翻转的差别仍未校准。作业在 `m3ca0401` 使用 8 核，用时 2:52，`COMPLETED 0:0`。结果清单 SHA-256 `cabd26adc38f1bb2fa82e9f8c6985abe7ce7c3214290475b9b603445a66a7951`。[对照 JSON](../../work/Melodydt/280/qwen3_m_retained_idle_comparison.json)
- **38812890** `mdt-280pmfetch` 在 `m3ca0201` 使用 4 核，用时 26 秒，`COMPLETED 0:0`。原六份 C639 波形的四路局控 PM 请求／返回和地址核验全部通过。正常／背压结果相同，Gate/Up 和 Down 窗口各为 **1／1／1／0** 次，写侧活跃窗为 **23／22／22／0** 次。24 个实例窗的请求与返回数一致，首尾在途均为零，未见错误。结果清单 SHA-256 `de3c55e6ded4d8d4092cb71a445937293c19b1e6f3af768776d2f7ba53921a29`。三窗全量取指次数另需从实跑获取。控制交换机、G32 空闲、本地和全局时钟的实例匹配及去重依据已归档。[审计 JSON](../../work/Melodydt/280/qwen3_c639_pm_runtime_audit.json) · [控制与时钟归属](../../work/Melodydt/280/qwen3_control_power_attribution.md)
- **38813039** `mdt-280pmlivepwr` 在 `m3ca0201` 使用 12 核，用时 36 秒，`COMPLETED 0:0`。冻结 C639 的 `lc_program_store_1k` 与物理作业 38794460 的同名 RTL SHA 一致，TT 300 MHz setup **+1.0965 ns**、hold **+6.8591 ps**，详细布线 DRC 文件为空。正常／背压代表窗覆盖三个站点，六个 8,192 周期后布线样本各实标 **533** 位。单阵列均值为 **30.7741–30.7766 mW**，即 **840.339–840.408 nJ/窗**，包含阵列时钟、内部、开关和漏电。范围保留为代表窗总功耗，真实模型的等长有状态静默参照和整窗驻留待绑定。结果清单 SHA-256 `4fb52469397d8b619dfa2296c12cb7407434fd7f141ae7ebf017f25906a8f53c`。[局控 PM 功耗 JSON](../../work/Melodydt/280/qwen3_c639_pm_live_window_power.json)

## SRAM／母控 PM 工件

10:52 已恢复旧服务器访问，完成 11 个原件的 BSCC 上传和校验，另核对了 6 个母控物理文件。以下保留本轮早些时候的归档路径和旧访问状态。[恢复回执与可读路径](2026-11-17-issue-280-macro-views-recovered.md)

归档服务器 `yuzelu@10.129.166.172`，项目共用根 `/public/home/yuzelu/project-circuit/LLMHardwareDesign`。已用保存的公共主机指纹核对，现有 SSH 身份被服务器拒绝，尚未取回工件。当前 BSCC 任务材料中只有匹配宏的功能 Verilog。恢复已授权身份后，由 Melodydt 在项目根按下列位置读取并比对 SHA-256。

| 范围 | 归档位置（相对共同项目根） | 用于恢复的 SHA-256 |
| --- | --- | --- |
| #155 S128 bank | `issue-155/bank-views-011/generation/bank/` 的 `s_sram_256x128_freepdk45.lef` 和 `s_sram_256x128_freepdk45_TT_1p1V_25C.lib` | LEF `d18426af718292b9d88e7ebd88b5002f238bfa0b295a5102b24814d1c4bed2eb`，Liberty `47f8de1c22d27beb51982c73ab745e1f3f2b5a7819e53bcb6da73980ce077189` |
| #200 S_P 后布线 | `issue-200-compact-local-s/run10-delay1/results/4/flow/results/nangate45/local_s_p/base/6_final.{v,odb,sdc,spef}` | V `b93d064cb07d3978efe280cbddec91fb2c24d74c932078a808680705ca01e32d`，ODB `fc80d8c2a59ac1851b233907afff0ba0e2eccf60b03761a58cae9d4722b54e72`，SDC `1a0b433f47ae75972349338a82c78f2ad03da1b5de1ea63630cd8bf158c10556`，SPEF `203a54e7b931355909f19c5bf6847429573ae105c351af42cf463b9fe9a1ac9a` |
| #200 S_base 后布线 | `issue-200-compact-local-s/run08-base0/results/0/flow/results/nangate45/local_s_base/base/6_final.{v,odb,sdc,spef}` | V `add5e99b97b471d35ef6c1eb3161821968172a96af4feb130fd4ca45217254fc`，ODB `634b808ec827ca17fc5be66a6d109ee4ba181f8ddc288a0fc731156fcf1974af`，SDC `e40d8eb6dfe9bbc5027b03cafb81a02233f56f4350eac1199e91f7c6f9a0fefc`，SPEF `7e611b64686e05d0981641daca71f40e9912b94cf3d4fcbbfe79c67b08c5a726` |
| #223 母控及 16 KiB `program_store` | `issue-223-mother-backend/receipt-mother128-01/mother128-accepted.tar.gz`；物理原目录 `issue-223-mother-backend/eco04/candidate0` | 归档 `55eab9f6d3c6d2510e3875552d61e18357cd99608bc39e5c3fffa5d0d8a8ba2c` |

#223 与冻结 C639 的母控顶层和 16 KiB 四 bank 子层 RTL 散列相同。`control_pm` 的已见差异是小容量单 bank 分支，当前 16 KiB 参数不选中该分支。取回后核对实际 `program_store` 网表层级、物理视图和时钟，按该实例分解，文档同时保留 S_P 和 S_base 的独立物理范围。[#155 银行视图](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/ac29d11ed5728861689046d04a0f03060de2439c/work/YUZE-LU/155/final-033/source-binding-index.json) · [#234 路由工件索引](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/eaf3008868982e5ac6c2f70878250c148ec6d009/work/YUZE-LU/234/s-activity-result-002.json) · [#223 母控验收](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/main/docs/experiments/mother-control-dual-format.md)

## 复现与追踪

服务器 `ssh.cn-zhongwei-1.paracloud.com`，工作根 `~/LLMHardware/zenanyan/issue-280-bscc-t6-01`，工具 `~/LLMHardware/opt`。仿真用 Verilator 5.042 和现有 ORFS/OpenROAD/OpenSTA 容器。三个新增作业分区为 `v6_384`、时限 `UNLIMITED`，各子目录 `inputs.sha256` 或 `live-inputs.sha256` 标识本次输入。

```bash
cd ~/LLMHardware/zenanyan/issue-280-bscc-t6-01
sha256sum -c calibrated-coverage/results.sha256
(cd m-baseline-power && sha256sum -c scenario-38809915/results.sha256)
python3 -B covered-ledger-20261117/qwen3_covered_power_ledger.py \
  m-baseline-power/scenario-38809915/qwen3-m-reference.json \
  calibrated-coverage/windows.json covered-ledger-20261117/reproduced.json
sha256sum -c covered-ledger-20261117/results.sha256
cat covered-ledger-20261117/windows.json
(cd m-retained-idle && sbatch --parsable --time=0 run_bscc_t6_m_retained_idle.sbatch)
(cd pm-runtime && sbatch --parsable --time=0 run_bscc_t6_qwen3_c639_pm_runtime.sbatch)
(cd pm-runtime && sbatch --parsable --time=0 run_bscc_t6_qwen3_c639_pm_live_power.sbatch 38812890)
squeue -j 38812748,38812890,38813039 -o '%i|%j|%T|%M|%N|%C|%l|%R'
sacct -X -j 38812748,38812890,38813039 -o JobID,State,ExitCode,Elapsed,NodeList,Timelimit
tail -n 12 m-retained-idle/slurm-38812748.log pm-runtime/slurm-{38812890,38813039}.log
(cd m-retained-idle/hold-38812748 && sha256sum -c results.sha256 && cat comparison.json)
(cd pm-runtime/pm-runtime-38812890 && sha256sum -c results.sha256 && cat pm-runtime-audit.json)
(cd pm-runtime/pm-live-power-38813039 && sha256sum -c results.sha256 && cat pm-live-window-power.json)
```

## 接下来

- 对已标定的局控代表窗补有状态静默对照，补采完整三窗的运行时取指请求。核对 G32／交换机实际物理实例、开钟驻留及共享时钟范围，按 [归属表](../../work/Melodydt/280/qwen3_control_power_attribution.md) 补测。
- 旧归档访问恢复后核对物理视图和散列，再标定 S128 多拍宽及母控 PM 本体。已有局控 PM 和 PM 桥先按实例与事件匹配，可单列将来要补的运行时读与空闲功耗。
- BSCC-T6 10:25 查验时，读侧原版 `38769386/38769388` 已运行 17 小时 42 分，跳过 SHARE 的对照 `38795299/38795300` 已运行 10 小时 54 分。四项仍处 ABC，尚无映射网表，四条 `38795516–38795519` 功耗作业待依赖。待合格网表和寄生后验证时序、DRC、端口活动，并按物理范围去重。正式 300 MHz 的 M 时序仍从 `38792357` 的 `3_place.odb` 独立接续。
- 三窗整模型 W、mJ/token 与误差按实际范围汇报，随后沿用口径扩至其余模型。DDR PHY 和板级在三窗器件能耗之外。

项目管理检查、Python AST、已运行 Slurm 作业和结果散列按实际回执核对。任务继续进行，PR #281 保持草稿。登记 PR #5 待合并，Projects 条目待有权限维护者核验。
