# Block 内部硬化与顶层集成 pilot

关联 [Issue #7](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7)。

本实验先硬化 llaccel v1 的完整 `vec_engine`，再将它作为一个真实宏放进直通端口的顶层工程 harness。原始 16 个 i16 lane、指令与存储接口、算术精度和握手协议均保留；harness 不插入寄存器、不增加周期。它不包含其余 llaccel core、SRAM bank 存储体，也不代表本项目的预制底座或受限金属定制实现。

## 固定输入与隔离

- 原 RTL commit：`f7db8a22791a1ce9dc13e7c90b0b9b9386169aa5`，只读源位于 `/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/llaccel-v1`。每次用 `git archive` 复制该 commit 到新 attempt，不修改原工程。
- 工具：`/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif`；镜像、实际工具二进制、Nangate45 输入、源码、生成配置与提交 runner 的 SHA-256 在计算节点记录。OpenROAD 版本字符串为 `unknown`；不能由该字符串推断版本。
- 输出全部位于 `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7/<attempt>/`。同名 attempt 禁止覆盖，失败记录保留。大数据库留在此处，仓库仅保留脚本和轻量索引。
- 代码快照 commit 见结果索引与 Issue/PR 回执；如在作业提交后生成，只能称为事后记录的代码快照。每次实际提交脚本的精确身份由 `runner-inputs.sha256` 表示，历史版本差异仍以这些哈希为准，不能将基线 `main` commit 充当 runner 版本。
- Slurm 仅使用 c64/c96 分区，每作业最多 16 CPU、最多 60 分钟。综合、编译、物理工具和大输出哈希均在计算节点运行。

## 流程与复跑

在有相同 SSH 权限的本地环境运行，使用全新 attempt 名称：

```powershell
python project/experiments/block_hierarchy/run_vec_pilot.py --attempt vec-screen-next --mode screening --cpus 8 --minutes 10
python project/experiments/block_hierarchy/run_vec_pilot.py --attempt vec-harden-next --mode pilot --cpus 16 --minutes 45
python project/experiments/block_hierarchy/run_vec_pilot.py --attempt vec-top-next --mode integration --block-attempt vec-harden-next --depends-on <hardening-job-id> --cpus 16 --minutes 30
python project/experiments/block_hierarchy/collect_results.py --attempt vec-screen-next:<screen-job-id> --attempt vec-harden-next:<hardening-job-id> --attempt vec-top-next:<integration-job-id>
```

`screening` 从容器实际脚本确认支持哪些流程选项，并完成原 VECTOR RTL elaboration。该容器支持 `SYNTH_HIERARCHICAL`、`SYNTH_KEEP_MODULES` 和 `BLOCKS`，未发现 `SYNTH_HIERARCHICAL_KEEP`。`SYNTH_KEEP_MODULES` 只保留综合层次，`BLOCKS` 才调用各块配置、生成宏抽象并向父级添加 LEF/Lib/GDS；不能仅设置层次保留就声称完成物理分块。原 llaccel elab 模板显式 `flatten`，需要从原 RTL 重新建立要保留的边界。

`pilot` 从原始 RTL生成完整 VECTOR 网表，再按原 v1 的 35% 利用率、0.55 放置密度、`-noshare` 和 16384-bit memory 上限执行 Nangate45 ORFS `finish`。此时 VECTOR 内部允许 flatten；它在父级以完整宏出现。

`integration` 依赖硬化成功，调用实际 ORFS `generate_abstract`。默认 `ABSTRACT_SOURCE=6_final`：记录最终 ODB/SDC/网表、SPEF 是否存在和 SHA；只有生成日志确认读入最终 SPEF 才称为使用路由后提取寄生。该脚本传播时钟，并将 source latency 归零后导出 Liberty；LEF 使用 `-bloat_occupied_layers` 输出占用层阻塞。

顶层输入只含生成的端口直通 wrapper 和宏 LEF/Lib/GDS，不再导入 VECTOR 实现 RTL。程序核验原始 26 个端口、2246 个信号 bit 与 LEF/Lib/wrapper一致；`u_vec` 固定在 `(80, 80) µm`、R0、FIRM。最终 ODB再检查宏 master、数量、位置、方向和无 `u_vec/` 内部标准单元。LEF含阻塞几何。顶层使用实际宏时钟 pin，CTS与顶层布线均由 ORFS执行；保存 check_setup、路径和电气检查，避免因缺少 timing arc产生表面良好时序。

## 验证口径和结果

实时轻量索引为 [results/issue-7.json](results/issue-7.json)，包含每次 attempt 的实际 `sacct` 状态、退出码、资源、输入身份、输出与日志路径。`collect_results.py` 默认采集本轮历史；新增 attempt 使用可重复的 `--attempt NAME:JOB_ID`。它只读取报告和计算节点已产生的哈希，不在登录节点运行物理工具。Slurm `COMPLETED` 仅表示命令执行结束；最终接口报告的布尔结果、额外信号 pin、未连接 pin和时序覆盖需要分别检查，不能以作业完成状态覆盖失败或缺失的验收证据。

时间约束为单时钟 3 ns、输入/输出 0.6 ns；数值沿用原 v1，只作为此次边界预算假设。导出块模型后只在父级端口施加父级约束，不将两个 0.6 ns简单相加推断系统频率。单角 WNS、DRC或 STA完成均不等于系统签核。

未执行形式等价性；顶层明确 `LEC_CHECK=0`。端口直通与结构检查不能代替 VECTOR 算术正确性或全 llaccel 软件回归。原项目已有独立功能结果是参考证据，本次未冒称重新完成这些回归。尚未验证多 Block 联通、统一底座、固定预埋轨道、允许定制层/通孔或制造成本优势。
