# Issue143 六块交付与 R 未完成交接

> 2026-11-02 用户纠正：撤销助手此前写入的 R 禁止发射、禁用、不调度，以及失败后不再修复或重跑等额外限制；这些不是用户要求。R 纳入正常的计算宏实现、控制适配、互联接入及调度验证。已有失败和未完成状态继续如实记录，验收标准不变。

面向 main 的六块交付：[PR #161](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/161)；已提交待独立审查，尚未合并。R 仍未完成。

负责人 YUZE-LU，项目 llm-hardware-design，仓库 rayggxia-workspace/LLMHardwareDesign。

按用户要求先交付 M/N/E/G/S/T，将 R 标为未完成。整合分支 `task/143-six-block-main` 基于 main `a103da352b7e431cedc69f54b9f71c05371be1b3`；研究源码来自 `e836741d334429be7d991cdc260f1ba955a7562e`，历史在 PR144。所有选定 RTL 从 Git 对象取原字节，再与已实收物理包的 RTL SHA 核对。源和验收数据库不作修改。

查看 `docs/BLOCK_V2_RESULTS.md` 和 `work/YUZE-LU/143/release-six/index.json`。执行管理检查、仓库交付核验；有本地物理数据时额外执行 --local-artifacts。新 PR 面向 main，独立审查人待指定，不能将提交 PR 描述为已经合并。

R 不影响这次六块交付，原作业和失败证据保留；后续失败继续定位迭代，不限制修复或重跑。不得因单项通过自动加入合格清单。Issue143保持开放，六块待审、R未完成分别表述。

项目登记 management-hub PR5 未确认合并，仍 pending。缺 `config/board.json`，无法定位/验证实际看板，状态 unverified、同步 pending；由管理员配置看板后核验 Issue 卡片与字段。未向其他成员发消息或指定审查人。
