已有模型、整数、RTL和物理成果分散在多条任务分支，读者很容易漏掉后续修订，或把局部通过误读为完整模型/制造验收。本PR新增一套从输入、运算、输出到划分依据的完整教程，逐模型保留失败与证据边界。

Refs #117；负责人 Liangruizhi（182389313），使用指定账号。基于 main 2113afef4afc1f16391e0ed929158bdfc3f70b94；正文/来源交付commit d31acfe62a35d54f2cd7ccdead8c00b4ea04d5ec。

[阅读入口](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/task/117-research-handbook/docs/research-handbook/README.md) · [完整全文](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/task/117-research-handbook/docs/research-handbook/FULL_REPORT.md)

## 内容

- 11章＋完整全文，前9章正文29,181汉字（另有证据目录和59任务总账，不重复计算全文副本）。
- 八模型逐项说明版本、真实范围、校准/评价、怎么执行、实际结果/失败、对边界的依据及下一步；保留Phi封存和未跑模型。
- 用手算attention、FFN/norm、GDN、MoE及整数例子解释完整K、scale/RQ、概率、状态、原子发布和端口/物理包。
- 具体M/V/A/R/S/D计算、状态、接口、预连线候选；后续电路/共享服务、物理/端点/H1/H2与团队通信优化完整串接。
- 164份冻结来源原文/索引/Issue快照（105 Git来源＋59 Issue）；约0.91MB证据包，无权重、封存数据或凭据。

## 实际验证

- python -B scripts/check_project.py：通过。初次稀疏副本缺原.github失败，补齐原检出后原规则通过。
- build_handbook.py / audit_handbook.py：11章与全文一致；164成员SHA、105 Git blob、430处本地链接/显式锚点、77张表（含全文重复）、83组来源片段、13个正文原结果SHA通过。
- 独立汇总原通信CSV的12个主配置，核fixed/greedy/beam/stronger-greedy和10胜2负；手算及关键派生数核对通过。
- 累计/暂存git diff --check及明确文件范围通过；正文源27文件已固定远端逐Git字节读回；最终metadata与CI见最后发布回执。

## 范围与限制

本次没有重新运行模型、原量化/接收器、RTL/gate、SAT/综合/STA或物理；没有连接服务器查新终态。PR111“91580运行中”明确作为2026-10-25来源快照，不猜今天结果。文档汇总不批准来源PR，也不宣告最终Block库/制造或端到端收益完成。

仅新增教程/本人work与进度/交接，ARCHITECTURE增加阅读及离线核对命令。避开Issue116的docs/model-analysis与README归档；不改原实验/代码/ref-project、他人进度或作业。

## 统一回执

规则rayggxia-project-collab1.0.0；project_id=llm-hardware-design；Issue117；分支task/117-research-handbook；PR base=main。成果/实际命令/读回见work/Liangruizhi/117及docs/handoffs/2026-10-26-issue-117-research-handbook.md。

登记：management-hub PR5本次open/unmerged，pending。看板：无board.json，实际Issue117 Project Items GraphQL缺read:project，unverified/同步pending，管理员待指定，不扩大权限或换账号。待指定审查人、待审查/合并，不自行merge/done。下一步为文档审查，原服务器/物理工作由各任务继续维护。
