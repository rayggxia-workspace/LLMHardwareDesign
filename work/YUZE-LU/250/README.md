# Issue250：联合底座实现入口

2026-11-10，Asia/Shanghai；负责人/实际GitHub身份 YUZE-LU。关联 [Issue250](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/250) / [PR251](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/251)。

用户已授权：先形成并验证不低于PR249同条件token/s的方案，再修改宏RTL及物理、五类控制分组/LC/MC/指令，完成紧凑利用率、接口与300 MHz验收，最终让通用DP适配新资源/费用；可并行agent，c96采用8×12、c64采用6×10。此工作不是仅提交研究计划。

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
