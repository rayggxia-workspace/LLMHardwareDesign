# Issue #184 五类逻辑 Block v1 执行交接

- 当前修订：2026-11-07，YUZE-LU / Codex。合同版本 `five-block-v1/2026-11-07`。
- [Issue #184](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/184) · [PR #185](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/185) · 远端分支 `task/184-five-block-v1`。
- 统一入口为[实施与验收合同](../local-blocks/FIVE_BLOCK_V1_PLAN.md)和[决策 0007](../decisions/0007-five-block-v1-synthesis.md)。合同修订不构成 RTL/EDA 验收。旧 P/J 任务 #187 与组合硬宏包作为历史结果保留。
- 本次从远端 `c60dd412caa1d2a01c7275ed07b788060d321769` 修订。旧工作树同内容但历史不同，保留原分支，在本地 `task/184-five-block-contract-v2` 工作，再将提交正常推进 PR #185 原分支。

## 执行前必须确认

1. 读取 `AGENTS.md`、协作 Skill 及本合同。五类各一份实现，九组是控制归属；全局直接摆独立叶宏和标准单元局控，组合验证夹具的硬框/LEF 不得成为顶层单元。
2. 叶宏选型使用 #203 的 S_base/S_P、#205 的紧凑 G/E，锁定每颗 master 的合格源码、ABI、六文件/集成视图和 SHA。旧 P4/N4/N5 包只保留历史记录，不得按旧面积或客户端数实施新版。
3. P/U 由 [Issue #212](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/212) / [PR #214](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/214) 跟踪，C/F/J 由 [Issue #211](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/211) / [PR #213](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/213) 跟踪。用户正在修改两份 PR，集成前读取其最终合格回执，核对 E 源数量、双向发送前进、PM/描述符 ABI 和实际 LC 身份。最新源码与旧版物理资格分别登记。
4. 对齐 `model/arch/base` schema 和合同版本，列出完整五类资源、28 个功能叶实例、九个 LC 身份、实际 PM/MEM、S 外部仲裁、保持/选择/驱动及额外算术。独立夹具的 ID0 或外部 PM 代理不得直接视为已完成顶层部署。
5. 五类服务、SystemC、映射器、RTL 与全局物理并行工作，共用上述输入与事件合同。逐位登记真实叶宏/适配端点；主要组内/组间数据边默认后制，有限预连逐项确认。同步修订映射、程序和布线需求，禁止只换端口名而保持旧封装几何模型。
6. 比较紧凑全局布局，解释每处保留区和大块空白；锁定共同底座前试至少两份产品连接。按合同完成五类局部路径、九实例与同底座不同产品的联合验收。运行远程作业前读取 `docs/REMOTE_RULES.md`，记录输入/工具/命令、输出和摘要。

## 本次交付与待办

本次仅修订合同、决策、交接和状态，并同步 Issue/PR 入口。实际检查以 PR #185 当前回执为准；未执行 RTL、SystemC、模型或 EDA。#184 继续开放，五类实现、PM/MEM、DP 和完整底座/产品验收仍按证据推进，不据此标 done。

项目登记 [management-hub PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5) 为 pending；缺少 `config/board.json`，Projects 条目 unverified、同步 pending，待具备权限的管理员核验。此项不改变技术合同。

## 历史：2026-11-05 私有 SRAM 验收输入（已被 #203 选型替代）

下列文件由用户提供，位于 `D:/Data/电路实验/LLMHardwareDesign-worktrees/local-s-sram-rtl-verification/physical-acceptance-01/`。本轮读取报告，复算三个文件的 SHA-256，核对包内每个配置的六文件和验收回执条目。大型包留在来源目录。若换机器，需从原交付者或经授权的项目存储获取相同摘要。

| 工件 | SHA-256 |
| --- | --- |
| `验收报告.md` | `948879b4d3aeadf522b4789b1bb300d7d4c7834bbbd0b5767557be42561bc6b6` |
| `accepted-p4.tar.gz` | `f3ef828391b82f1d0d3169a141557cebe554e6757a764f1c5de4e361ef5878c5` |
| `accepted-v2-n4-n5.tar.gz` | `30cfc286b12c4e29d52e17eeee04c242dda8309bec0c387928009a6d417d9d55` |

对应 P4/N4/N5 汇合作业 97462/97451/97456。包内为每个配置的最终 V、SDC、DEF、ODB、SPEF、GDS，附版图、验收回执、执行源及来源清单。父层所需 LEF/时序抽象另按匹配视图验收。#178 线上快照仍为原仲裁与标准单元 S 的来源，本表索引另行验收的真 SRAM 包。
