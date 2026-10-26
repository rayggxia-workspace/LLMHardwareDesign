# Issue117 全项目研究教程交接

- 仓库：https://github.com/rayggxia-workspace/LLMHardwareDesign
- 任务：https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/117
- 负责人/实际认证：Liangruizhi，182389313，2663955430@qq.com。
- 独立目录：`D:/Projects/liangruizhi/.worktrees/issue117-handbook`；分支 `task/117-research-handbook`。
- 主线基线：`2113afef4afc1f16391e0ed929158bdfc3f70b94`；本次文档源commit与PR发布后追加在下方。
- 临时来源快照：`D:/Projects/Codex/research-handbook-20261026`；轻量原文已归档入仓库，不依赖该本机目录即可核对文档来源。

## 成果和范围

[阅读入口](../research-handbook/README.md)、[全文](../research-handbook/FULL_REPORT.md)，11章。包含八模型逐项实验、版本/精度/校准评价、失败/限制、完整K/scale/状态发布的推理、M/V/A/R/S/D具体候选、P1–P15、后续电路/物理与团队映射成果、最小下一步。

164份来源原字节（105个Git文档/索引、59个Issue正文）、59Issue/58PR快照；新手例子说明attention、FFN/norm、递推/GDN、MoE和误差，均明确为教学而非模型实测。原模型/整数接收/RTL/门级/SAT/综合/物理均未在本次重跑，服务器新终态未查询。

不改原代码、实验输出、任务分支、服务器作业或他人进度；不改ref-project；避开成员116的docs/model-analysis/README图册归档。仅在ARCHITECTURE追加本报告导航/离线核对命令，建立自己的进度。原根工作区没有改文件/分支，新独立clone位于其`.worktrees`子目录，不应被其他任务加入提交。

## 实际验证

先运行 `python -B scripts/check_project.py`；初次因稀疏副本缺原.github而失败，补齐原文件后通过，没有放宽检查。再运行 `build_handbook.py` 和 `audit_handbook.py`；验证164成员SHA、105Git blob、11章全文一致、文档链接/锚点/表列、83组来源片段、12格原通信CSV汇总、13个正文原结果SHA及教学数例。最终准确数量/解释器/命令/输出见[validation.json](../../work/Liangruizhi/117/validation.json)。

上传前检查origin、作者/认证、任务分支、main base、暂存/未暂存/未跟踪路径和累计diff。远端固定commit的实际逐字节回读见[remote-readback.json](../../work/Liangruizhi/117/remote-readback.json)（发布后生成）。文档检查不能提升原实验资格。

## 未完成、责任人与恢复第一步

1. 文档PR要求的独立审查/合并，审查人待指定；未合并不done。本次不获自合并授权。
2. 登记management-hub PR5本次仍open/unmerged，pending。无board.json，实际GraphQL Project Items缺read:project，unverified/同步pending，管理员待指定；不增加token范围或改用别人的账号。
3. 原研究未完成项由各Issue继续：PR111固定来源的93最终完整门级/接收需主线读取真实终态；下游事务buffer、存储宏/driver/PVT、新共享top物理及制造固定层/产品图仍待验。本次只整理，不代为提交或停止这些任务。

恢复第一步：用Liangruizhi核最新Issue117/关联PR、main、成员116及主研究线进度；确认该目录无其他人使用，再运行上述离线检查。若只是审阅，不启动任何模型或服务器工作。修改手写章节后先build全文，再audit；新来源必须追加固定字节/索引，不覆盖旧证据。

## 发布记录

已上传[PR118](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/118)，base=main，未合并；正文/来源源commit `d31acfe62a35d54f2cd7ccdead8c00b4ea04d5ec`。该commit的27文件已从远端Git blob逐字节读回通过，含完整全文/来源索引/原文zip。创建PR的插件传输失败后，先查无重复，再由同一已核账号REST创建；没有换身份。最终metadata与CI由最后发布回执核验，不能据此标done。
