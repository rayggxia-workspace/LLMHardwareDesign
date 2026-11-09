# Melodydt / Issue #245：P/DMA 研究证据

用途：[Issue #245](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/245) / [PR #243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243) 的本人实验回执；来源为冻结PR241和本人Slurm实验，不是他人工作目录副本。规则rayggxia-project-collab1.0.0；Asia/Shanghai，2026-11-09。

[中文研究报告](../../../docs/experiments/issue-245-p-dma-study.md) · [正式代码/复跑](../../../project/experiments/p_dma_study/README.md) · [交接/追踪](../../../docs/handoffs/2026-11-09-issue-245-p-dma-study.md)

- `index.json`：每轮源码commit、实际工具版本、输入/生成源码/完整结果SHA，44份轻量证据SHA及最终15个功能源码SHA。索引不自签名，说明/verify脚本不在其不可变证据范围。
- `summary.json`：三轮56份观测/候选记录的轻量汇总，含重复基线，不伪称56个不同配置。连同六次未加仪表原版基线共62次完整trace执行。每条保留run/source_commit。
- `run02/03/04`：真实Slurm allocation（启动时RUNNING快照）与`sacct.txt`终态、作业脚本/输入及源码SHA清单、运行时容器/库SHA、日志和输出索引。26/18/18次均COMPLETED0:0。
- 原版/仪表全部原指标及上游W8/W16精确一致；每轮225 kernels、4 validation、5 smoke、软件oracle通过。run03/04另各通过7项篡改拒绝。保留run02/04检查日志和四份原始完整case JSON（基线、最终W8策略/组合、W16策略）。
- `run01`：101611在-Werror编译阶段失败1:0的原始日志/终态/SHA，修正统计缩进后独立新目录重跑；没有弱化编译选项。

原始trace、完整result.json、所有case日志/生成源码和二进制留在获授权服务器 `yuzelu@10.129.166.172:/public/home/yuzelu/Melodydt/issue245-pdma/run0{1,2,3,4}/`；未上传大包。三成功轮回收91个由原输出清单覆盖的文件并核对SHA，68个清单项仅留服务器。清单中未收进Git的路径是“服务器保留”，不是已下载或缺失；输入trace的上游原始CRLF和实际LF SHA分别记录。

```bash
python -B work/Melodydt/245/verify.py
```

该命令只核对回执/源码一致性，不能代替仿真；仿真须Slurm/实际SystemC环境。源码试验727f297c与交付功能源码15文件保持一致；README补入实际结果不改变已测功能源。无活动作业、无自动监测。

研究成果待审查/合并；登记PR5 pending，看板unverified/同步pending、管理员待指定。当前分支是非Git本地源快照的在线交付，不宣称本地pull/暂存/HEAD。性能是条件候选架构，不是真实LLM生成、RTL或物理签核。
