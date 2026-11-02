# Issue143：六块成果整合

面向 main 的六块交付：[PR #161](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/161)；已提交待独立审查，尚未合并。R 仍未完成。

任务：[Issue #143](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/143)。研究过程和失败证据仍在 [PR #144](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/144) 的原分支。

本分支 `task/143-six-block-main` 从 main `a103da352b7e431cedc69f54b9f71c05371be1b3` 建立，只整合选定的六块源码、必要运行依赖和源绑定交付证据；没有引入原 637 个研究提交，不修改 #121/#130 工作树或作业。

- 正式入口：[实施合同](../../../docs/BLOCK_V2.md)、[结果与限制](../../../docs/BLOCK_V2_RESULTS.md)。
- 合格选择：M、N-q14、E-wide、G-v2、S、T；[机器可读索引](release-six/index.json)。
- R：未完成，不在合格选择中；已有研究源码及原验收限制保留。
- 原始轻量回执在 `release-six/<宏>/`；大体积数据库只留授权存储路径和 SHA。
- 审查人待指定；登记沿用 management-hub PR5 pending。当前仓库无 `config/board.json`，看板 unverified、同步 pending，待管理员补配置后核验。本次不关闭整个七块 Issue。
