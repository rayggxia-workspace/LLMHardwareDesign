# Block 内部硬化与顶层集成 pilot

关联 [Issue #7](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7)。

本实验先硬化 llaccel v1 的完整 `vec_engine`，再将它作为一个真实宏放进直通端口的顶层工程 harness。原始 16 个 i16 lane、指令与存储接口、算术精度和握手协议均保留；harness 不插入寄存器、不增加周期。它不包含其余 llaccel core、SRAM bank 存储体，也不代表本项目的预制底座或受限金属定制实现。

## 固定输入与隔离

- 原 RTL commit：`f7db8a22791a1ce9dc13e7c90b0b9b9386169aa5`，只读源位于 `/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/llaccel-v1`。每次用 `git archive` 复制该 commit 到新 attempt，不修改原工程。
- 工具：`/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif`；该路径是可变文件名。当前 runner 在计算节点开始物理工具前断言已确认的 SHA-256 `49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a`；如要改变镜像必须显式修改受审查配置。本轮已提交的早期版本只记录镜像哈希，各已运行 attempt 的实际值相同，不冒称当时已有断言。实际工具二进制、Nangate45 输入、源码、生成配置与提交 runner 的 SHA-256 也在计算节点记录。OpenROAD 版本字符串为 `unknown`；不能由该字符串推断版本。
- 输出全部位于 `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7/<attempt>/`。同名 attempt 禁止覆盖，失败记录保留。大数据库留在此处，仓库仅保留脚本和轻量索引。
- 代码快照 commit 见结果索引与 Issue/PR 回执；如在作业提交后生成，只能称为事后记录的代码快照。每次实际提交脚本的精确身份由 `runner-inputs.sha256` 表示，历史版本差异仍以这些哈希为准，不能将基线 `main` commit 充当 runner 版本。
- Slurm 仅使用 c64/c96 分区，每作业最多 16 CPU。按用户要求，当前 runner 使用 `--time=0` 请求无限时，不设置人为运行时限；2026-10-21 实读两分区均 `DefaultTime=NONE`、`MaxTime=UNLIMITED`，安装的 sbatch 手册明确零表示无时间限制。提交回执记录 `scontrol` 读回的实际 `TimeLimit`，若不是 `UNLIMITED` 就取消新作业并保留回执。综合、编译、物理工具和大输出哈希均在计算节点运行。历史 89443 的 45 分钟 TIMEOUT 和 89447 的 60 分钟配置仍按当时事实保留，后续已撤销此类人工上限。
- 新提交遵守新主干远程规则，以本人缩写 `yzl-vec-<mode>` 命名。89448/89449 只更新任务名，前后调度回执见 `slurm-name-update-20261021/`；时间上限和作业输入均不改，历史 submission 保留原名。

## 流程与复跑

在有相同 SSH 权限的本地环境运行，使用全新 attempt 名称：

```powershell
python project/experiments/block_hierarchy/run_vec_pilot.py --attempt vec-screen-next --mode screening --cpus 8
python project/experiments/block_hierarchy/run_vec_pilot.py --attempt vec-harden-next --mode pilot --cpus 16
python project/experiments/block_hierarchy/run_vec_pilot.py --attempt vec-top-next --mode integration --block-attempt vec-harden-next --depends-on <hardening-job-id> --cpus 16
python project/experiments/block_hierarchy/run_vec_pilot.py --attempt vec-regression-next --mode regression --cpus 8
python project/experiments/block_hierarchy/collect_results.py --attempt vec-screen-next:<screen-job-id> --attempt vec-harden-next:<hardening-job-id> --attempt vec-top-next:<integration-job-id>
```

`screening` 从容器实际脚本确认支持哪些流程选项，并完成原 VECTOR RTL elaboration。该容器支持 `SYNTH_HIERARCHICAL`、`SYNTH_KEEP_MODULES` 和 `BLOCKS`，未发现 `SYNTH_HIERARCHICAL_KEEP`。`SYNTH_KEEP_MODULES` 只保留综合层次，`BLOCKS` 才调用各块配置、生成宏抽象并向父级添加 LEF/Lib/GDS；不能仅设置层次保留就声称完成物理分块。原 llaccel elab 模板显式 `flatten`，需要从原 RTL 重新建立要保留的边界。

`pilot` 从原始 RTL生成完整 VECTOR 网表，再按原 v1 的 35% 利用率、0.55 放置密度、`-noshare` 和 16384-bit memory 上限执行 Nangate45 ORFS `finish`。此时 VECTOR 内部允许 flatten；它在父级以完整宏出现。

`regression` 固定 `SEED=1` 运行原 `tb/vec` Makefile 的 math/vector benches，保持 RTL、数值、用例和比较断言。89452 在编译原 `tb_math.cpp` 时因 uint32_t 初始化中的 `1 << 31` narrowing 失败，未完成运行测试；失败日志保留。当前 runner 在全新 attempt 中复制出独立 `regression-source`，仅将这一处改为 `1u << 31`，仍为 uint32_t 的 `0x80000000`。脚本断言唯一替换、比较全文件集合与内容，强制其它文件（含 RTL/reference头）逐字节不变，原 archive 不改；`compat-patch.diff` 和前后哈希记录兼容修改，未增加全局 warning 抑制。编译、缓存和临时文件分别位于该 attempt 的独立目录。使用镜像内 GCC 11.4 与绑定目录中的 Verilator 5.042，记录工具/源文件哈希、日志与 `regression-result.json`。它验证原 RTL 的数值/协议回归，不能代替物理网表等价性或 STA。

恢复模式可显式指定 `--skip-phase-lec`，启动另一条独立物理工程路线。它仅在 `make` 命令中附加 `LEC_CHECK=0`，保留同一终态 checkpoint、原 RTL、3 ns/0.6 ns约束、放置和优化配置。receipt、容器环境、runner哈希及 `phase-lec-policy.txt` 均记录这一选择；此路线只检验物理流程、抽象和接口，不主张门级等价。89448 的默认完整检查和89449的依赖保持运行；不得将它的未完成或后续证明套用到另一份网表，除非另行核验实际网表身份及证明范围。复制父目录留下的旧 LEC 日志在索引中标为继承，不能算新作业执行的检查。

如果某次作业在完成综合后中断，可在它到达终态后使用 `--mode resume --resume-from <旧attempt>` 和全新 `--attempt`。该入口在计算节点复制完整 ORFS 阶段目录，保持文件时间、配置和3 ns/0.6 ns约束不变；旧路径仅保留为只读网表/SDC输入。实际执行前对首个缺失阶段保存 `make -n`，发现需要重新综合就停止并保留诊断，再正常执行全流程 `finish`。首轮恢复 89447 通过身份校验，但全流程 dry-run 因尚未生成的后续 SDC 副产物失败；修正为首个缺失阶段的 dry-run 后新建 attempt，不掩盖该失败。恢复逻辑以本轮阶段实测为限，不声称通用 checkpoint 恢复能力；实际恢复是否成功以索引为准。既有旧 attempt、失败日志和部分阶段均保留。

`integration` 依赖硬化成功，调用实际 ORFS `generate_abstract`。默认 `ABSTRACT_SOURCE=6_final`：记录最终 ODB/SDC/网表、SPEF 是否存在和 SHA；只有生成日志确认读入最终 SPEF 才称为使用路由后提取寄生。该脚本传播时钟，并将 source latency 归零后导出 Liberty；LEF 使用 `-bloat_occupied_layers` 输出占用层阻塞。

89454 的默认顶层在 PDN 阶段失败：既有宏的 PG pin 只在 M7、未伸至边界，原抽象将 M1–M9 整层阻塞；Nangate45 默认宏供电网无法跨越这些阻塞。失败视图和日志保留。89456 使用独立的 `detailed-m10` 视图（bloat factor 0）完成了顶层详细路由、路由 DRC 为 0，但最终 PSM 检出 43 处 VDD 与宏 M8/M9 OBS 的实际重叠，报 PSM-0069，作业 FAILED；它未通过供电/最终顶层验收。一个实读 via 中心在 OBS 外，M8 landing 为中心 ±0.62 µm，仍切入 OBS；证据位于 `pdn-geometry-diagnostic-01/probe-02.log` 及失败 top 的 `VDD.rpt`，不能忽略。

89457 用 `guarded-m10` 请求 `-bloat_factor 1` 并在真实 `POST_PDN_TCL` hook（写出 2_4 ODB 之前）执行严格双网检查。实测关键 M8/M9 routed OBS 外边界没有扩大，不能将 API 参数视为普遍 padding；VDD/VSS 均 catch=1 / PSM-0069，提前终止。89459 对 89456 最终 ODB 的独立只读负向审计也复现双网失败，PG ITerm net 归属本身正确。失败输入、几何、日志和输出哈希均保留。除 M8 landing 切入外，另一处 M9 via 中心本身位于 OBS 内；不能将全部短路归为 enclosure 扩张。

下一候选为 `--macro-pdn legal-m10`，尚待实际验收。它从同一最终 ODB 在新 `macro-view/` 导出 bloat factor 0 的详细 OBS、复制字节一致的原 Liberty 并引用原 GDS；原块输出只读。验证宏尺寸和全部 2248 pin 的方向/use/几何不变、全部占用 OBS 层留存。父级新增 M10 供电竖条，不在宏上新铺 M5/M6。`POST_PDN_TCL` 从实际导入的 macro master 读取 OBS、原 PG pin 和 R0@(80,80) 坐标，从真实 via master 取全套 landing。对所有父级 PG via（也可能包含 lower-parent via）按同网/同 XY 整组选择，不修改 master 几何。M8/M9 landing 与实际 OBS 保持 L∞ 2 µm guard；实际固定镜像 M7–M9 spacing table 最大值为 1.5 µm。M7 landing 只有完全包含在同网原 PG pin 内才豁免，否则同样检查 OBS；M10 已检查无宏 OBS。原文与 SHA 在 `pdn-spacing-evidence-01/`。这不覆盖完整工艺 spacing 签核。

发现任一 landing 不满足 guard 时删除整个父级同站 via 组；遇到非完整 7–8/8–9/9–10 栈或独立 M8/M9 PG patch 则 fail closed。随后重新枚举所有剩余 landing，输出实际 OBS/PG pin/删除原因/残余形状 TSV 和 `pg-access-selection.json`，并执行严格 VDD/VSS native 连通检查。要求 Tcl catch=0 且原生返回严格 true；失连即失败，最终 PSM 也保留。该方案属于 H1 新增供电资源与接入选择，不能称为 H2 冻结底座。

先运行独立 `pdn-filter-audit`：只读终态 89456 ODB，在内存选择父级 via，只把通过检查的数据库写到自身新目录。独立审查者再根据导出的实际 OBS/landing 复算残余站。它是工程修复试验，不是对原失败 ODB 的验收。经实际复核后才运行完整 legal 顶层：

```powershell
python project/experiments/block_hierarchy/run_vec_pilot.py --attempt vec-pdn-filter-next --mode pdn-filter-audit --block-attempt vec-physical-top-02 --cpus 1
python project/experiments/block_hierarchy/run_vec_pilot.py --attempt vec-physical-top-next --mode integration --block-attempt vec-physical-01 --macro-pdn legal-m10 --cpus 16
python project/experiments/block_hierarchy/collect_results.py --attempt vec-pdn-filter-next:<audit-job-id> --attempt vec-physical-top-next:<integration-job-id>
```

自定义视图要求源 Block 已有同一最终实现生成的 LEF/Lib/SPEF；不能借用另一条物理路线的模型。89448 的最终匹配视图需在其自身流程完成后另行生成；当前 89449 的旧默认 PDN 配置尚未替代。

镜像默认 `pdn.tcl` 注释了 `check_power_grid`。`pdn-audit` 对终态顶层 ODB 只读检查 VDD/VSS、宏 PG ITerm 实际 net 归属，并单列原 failed-via 清单和 PDN 警告。最终 legal 顶层另用 `pdn-site-audit`：同样读取终态 ODB，同时以 check-only 模式重新枚举实际 PG landing，禁止删除 via、禁止写 DB，发现 unsafe 站即失败；不能在验收中默默修复。审计保存工具、ODB、脚本哈希、每网 catch code/原生返回值及日志。

```powershell
python project/experiments/block_hierarchy/run_vec_pilot.py --attempt vec-pdn-final-next --mode pdn-site-audit --block-attempt vec-physical-top-next --depends-on <completed-top-job-id> --cpus 1
python project/experiments/block_hierarchy/collect_results.py --attempt vec-pdn-final-next:<audit-job-id>
```

零 failed-via 与 PG 全连通需要分别成立。导出的宏 Liberty 没有 internal_power/leakage/活动电流模型，因此即便顶层工具能报告功耗/压降，也不能代表包含原宏真实电流的 PI 验收。

顶层输入只含生成的端口直通 wrapper 和宏 LEF/Lib/GDS，不再导入 VECTOR 实现 RTL。程序核验原始 26 个端口、2246 个信号 bit 与 LEF/Lib/wrapper一致；`u_vec` 固定在 `(80, 80) µm`、R0、FIRM。最终 ODB再检查宏 master、数量、位置、方向和无 `u_vec/` 内部标准单元。LEF含阻塞几何。顶层使用实际宏时钟 pin，CTS与顶层布线均由 ORFS执行；保存 check_setup、路径和电气检查，避免因缺少 timing arc产生表面良好时序。

## 验证口径和结果

`test_pdn_hook_scope.tcl` 用 mock OpenDB／原生 PG API 检查实际 hook 脚本的 Tcl 过程加载上下文，覆盖整站删除、只读安全／不安全及原生返回 false 四条路径；它不产生 EDA 结论。已有 `pdn-hook-scope-diagnostic-01/` 保存输入哈希、日志及 exit=0；独立 `pdn-hook-scope-negative-01/` 仅换回旧 filter，实际 exit=1、复现变量不可读，证明该测试能捕获原缺陷。在已有 Tcl 环境中可用以下命令复跑，输出目录必须全新：

```bash
tclsh project/experiments/block_hierarchy/test_pdn_hook_scope.tcl <new-output-directory>
```

实时轻量索引为 [results/issue-7.json](results/issue-7.json)，包含每次 attempt 的实际 `sacct` 状态、退出码、资源、输入身份、输出与日志路径。`collect_results.py` 默认采集本轮历史；新增 attempt 使用可重复的 `--attempt NAME:JOB_ID`。它只读取报告和计算节点已产生的哈希，不在登录节点运行物理工具。Slurm `COMPLETED` 仅表示命令执行结束；最终接口报告的布尔结果、额外信号 pin、未连接 pin和时序覆盖需要分别检查，不能以作业完成状态覆盖失败或缺失的验收证据。

阶段状态要求对应 ODB 与收尾 metrics 同时存在。索引按父拷贝的大小/mtime（小日志另比内容）及本作业开始时间区分 `current`、`inherited`、`mixed`、`unknown`，时间同秒或证据不足保守记未知。LEC 按每个日志的来源分别判定，只用本轮日志形成本轮结论；复制的旧 `identical` 不算新检查，本轮相互冲突的结论也不判通过。这些来源标签不替代计算节点保存的输入/输出哈希或功能验收。

时间约束为单时钟 3 ns、输入/输出 0.6 ns；数值沿用原 v1，只作为此次边界预算假设。导出块模型后只在父级端口施加父级约束，不将两个 0.6 ns简单相加推断系统频率。单角 WNS、DRC或 STA完成均不等于系统签核。

手写边界 SDC 未显式设置外部 driving cell/input transition 或输出 load，因此这些预算不能充当完整系统边界电气模型。综合 ABC 的技术映射负载假设与顶层 STA 的外部负载需要区别；若 ORFS导出约束含工具默认模型，应在实际结果中记录其值及来源。

89453 已完成全 VECTOR 物理流程（33:03，无限时；本路线显式跳过阶段 LEC）。详细路由 DRC 为 0、天线 net/pin 为 0；最终单角 setup WS −4.16659 ns、TNS −1056.05 ns，287 条 setup 违例，max-cap 59，hold WS +0.0253833 ns/TNS 0。最差路径是 `u_f0.rp[0]` 到 `wr_data_r[187]` 的 FF→FF 数据 setup，不是 reset recovery；3 ns 未闭合。宏 footprint 为 1148.52×1148.52 µm；最终非 filler 标准单元面积约 524749 µm²（含时钟、repair、tap），另有 411821 个 filler/约 787959 µm²，不能将含 filler 的 733546 总实例当作活跃逻辑数。

同次 ORFS 自动 PSM 报 VDD worst drop 0.688493 V、VSS worst rise 0.629844 V，未通过 PI 验收。来源是 Nangate45 默认 1.1/0 V、电源入口 `BUMPS` 和 Liberty 静态活动传播；未提供应用 VCD/SAIF、显式 bump 布局或外部供电模型。工具默认输入 activity 为每最短时钟周期 0.1 次转换、duty 0.5，日志总功耗约 22.7 W。两个最差位置未配对，不能直接相加，也不能当作真实应用的供电结果。只读策略/帮助证据在 `vec-physical-01/psm-policy-observation.txt`，未重跑或更改该分析。

未执行原始 RTL 到物理网表的完整形式比较；Block 会按镜像默认配置调用 Kepler 的阶段前后门级 LEC，是否实际执行、结果及范围以各阶段日志为准，不能与源 RTL 算术验证混同。顶层明确 `LEC_CHECK=0`。89455 已通过上述原 VECTOR 源 RTL 的 1203 例和 math/rounding 回归；端口直通与结构检查仍不能代替物理网表等价性或全 llaccel 软件回归。尚未验证多 Block 联通、统一底座、固定预埋轨道、允许定制层/通孔或制造成本优势。
