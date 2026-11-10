# Issue250：联合底座实现入口

2026-11-10，Asia/Shanghai；负责人/实际GitHub身份 YUZE-LU。关联 [Issue250](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/250) / [PR251](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/251)。

用户已授权：先形成并验证不低于PR249同条件token/s的方案，再修改宏RTL及物理、五类控制分组/LC/MC/指令，完成紧凑利用率、接口与300 MHz验收，最终让通用DP适配新资源/费用；可并行agent，c96采用8×12、c64采用6×10。此工作不是仅提交研究计划。

用户2026-11-11补充：不得擅自停滞目标，遇到阻碍须持续定位、修改和重跑直到验收通过；子agent同样按解决/迭代执行。跨模块依赖由根agent协调，不把失败记录、局部测试通过或PR上传当作完整验收。

2026-11-11执行更新：R0已精确复现9.21564723269；有限命令准备队列的共享候选9.22603374894（约+0.113%）仍是条件模型，严格S内X顺序/预取尚未达到同门槛，继续验证同K tile有限复用以尝试省去共享池。未冻结最终资源。紧凑基线已整合14份源绑定回执和5宏实际口径；新M raw group/scale单元102060严格编译失败已修，102063、102065六seed全部通过并回收hash校验，见[m单元记录](m/README.md)。G和控制仍在各自分支迭代，不以单位算术/协议证明系统RTL或物理。

正式合同：[w8a16-next-base-contract.md](../../../docs/plans/w8a16-next-base-contract.md)。本轮把旧S128草稿改成共享X/S32候选与明确验收门；未宣称最终硬件冻结或性能已通过。

## 所有权与并行准备

| 工作 | 独占路径 | 分支/基底 | 当前范围 |
|---|---|---|---|
| 根合同/集成 | 本README、docs/plans合同、共同状态/个人进度 | task/250-contract-integration；原PR251 a237a6fa | 修订与集成，避免覆盖旧实验 |
| 联合性能 | performance/；project/experiments/stream_quant_synthesis/shared_x* | task/250-shared-x-evaluation；85fe7989b | 恢复原基线、真实有限共享服务与同条件对照 |
| 物理基线 | physical/；project/experiments/w8a16_physical/ | task/250-compact-physical-baseline；main c4d7b960 | 紧凑面积、pin/后端入口，未启动新宏长P&R |
| 控制准备 | control/；project/experiments/shared_x_control/ | task/250-shared-control-prep；85fe7989b | 有界对象/ACK/恢复合同与独立协议审计，不等于RTL |

每个分支的执行/归档commit、实际测试与作业在各子目录记录；尚未形成记录的交付不得写成已完成。由根agent依赖顺序整合，子agent不改共同状态、不更新在线Issue/PR、不合并PR。跨分支准备不意味着同一联合设计已验收。

## 当前门槛和未完成项

第一门为9.21564723269 token/s同条件四银行/S32/Mid32/RNE1/51.2GB/s基线。共享池三P端口、旧K8容器到新K16拼接及对象切换均须计费；X放既有S作为替代；不默认私有S扩容或LVT复制。未通过联合模型前不冻结最终资源或启动最终宏长P&R。

后续需完成真实记录数值映射、新M/G及其他所需服务、实际S/共享/权重前端、MC/LC程序和恢复、最终网表回放、完整物理门、RTL校准SystemC、通用DP/独立checker；长期整数质量、能耗与公平FPGA/ASIC对照仍未完成。原main叶宏的验收不能转移到新电路。

## 基础检查及发布限制

本地 `python scripts/check_project.py` PASS（仅管理结构）。Git直接HTTPS fetch两次因connection reset失败；使用已认证GitHub connector核验PR251原tree/commit，从本地main与原文件精确恢复同SHA对象后在隔离分支修改。没有改main、强推或自合并。

项目登记沿用management-hub PR5 pending；`config/board.json`不存在，Projects实际字段unverified/同步pending，沿用Issue7交接；审查人/管理员待指定。在线状态以更新后的Issue/PR读回为准。本工作未完成，不关闭Issue250。

## 2026-11-11 原生服务校准与继续实施

- [native-s](native-s/README.md)：公共S128诊断16条trace，同工作量7.595433尚未达旧9.215647；不将历史9.223当最终性能。
- [weights](weights/HANDOFF.md)：四1152B W记录银行、独立MC issue、34实际记录/head16，六seed三初态通过。
- [m](m/README.md)：追加24组实际历史raw通过，新Mid32端到端仍待验证。有限16×8 S32上下文已有Slurm102099六seed通过，回执回收中。
- [control](control/README.md)：有限A/copy及双结果槽初轮通过，真实S/MC/LC迭代中。G物理与S128流适配并行推进。

持续解决—迭代至完整验收。未完成保持Issue in_progress/PR draft；登记PR5 pending，缺board/Projects能力，状态unverified、同步pending；不自合并、不代独立审查。
