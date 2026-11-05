# Issue #184 五类组合 Block v1 执行交接

- 项目为 `llm-hardware-design`，仓库为 [LLMHardwareDesign](https://github.com/rayggxia-workspace/LLMHardwareDesign)。
- 方案提交人为 YUZE-LU，2026-11-05 中国标准时间（UTC+08:00）。YUZE-LU / Codex 认领 P16、J16 的 RTL 至独立物理验收，见 [Issue #187](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/187)。U/C/F 负责人和独立审查人待指定。
- [Issue #184](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/184) · [方案 PR #185](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/185) · 分支 `task/184-five-block-v1`。PR 当前提交为交付锚点，初始远端提交 `2235295e569cbfabc79b11e5205c8bcc0b5991d4` 之后补入最新 SRAM 验收。基于 `main@10ea8a736d5b34f494010f0ffdad0fe20975b129`。
- [实施计划](../local-blocks/FIVE_BLOCK_V1_PLAN.md) · [设计取舍](../decisions/0007-five-block-v1-synthesis.md)。本轮提交方案，实施和各项联合验收留在 Issue #184。

## 开始执行

1. 先读根目录 `AGENTS.md` 和协作 Skill，核对 PR #185 最新 head、Issue 状态及实施授权。打开计划的基线与证据表，锁定将使用的叶宏、控制 ABI 和实际模型切片。依赖 PR 各自审查。
2. 先用下表摘要核对 P4/N4/N5 包。给五类封装及九实例共同登记私有 S 类型、地址宽度、MEM 路径、M10 端点、完成事件和临时未接边。三颗 P 共用一个 P16 物理版图。核对单颗 P4 的 feeder、ACK、端点和载荷预算，以及 Qwen 和 Granite 分片在 16 KiB 下的峰值占用。
3. 按计划并行启动五类 RTL、SystemC、映射器及物理工作。首批共用工件为实例与服务表、固定/候选逐位端点表、实际 SRAM 绑定和三个模型的可执行测试范围。先完成五种 Block 的独立物理验收，再放置九实例。P16、J16 每轮按[迭代索引](../../work/YUZE-LU/187/README.md)记录诊断、变更和结果。
4. 运行任何远程物理作业前读取 `docs/REMOTE_RULES.md`，仅使用获授权的资源与目录。模型和物理工件记录版本、复跑命令、输出位置及 SHA-256。

## 2026-11-05 私有 SRAM 验收输入

下列文件由用户提供，位于 `D:/Data/电路实验/LLMHardwareDesign-worktrees/local-s-sram-rtl-verification/physical-acceptance-01/`。本轮读取报告，复算三个文件的 SHA-256，核对包内每个配置的六文件和验收回执条目。大型包留在来源目录。若换机器，需从原交付者或经授权的项目存储获取相同摘要。

| 工件 | SHA-256 |
| --- | --- |
| `验收报告.md` | `948879b4d3aeadf522b4789b1bb300d7d4c7834bbbd0b5767557be42561bc6b6` |
| `accepted-p4.tar.gz` | `f3ef828391b82f1d0d3169a141557cebe554e6757a764f1c5de4e361ef5878c5` |
| `accepted-v2-n4-n5.tar.gz` | `30cfc286b12c4e29d52e17eeee04c242dda8309bec0c387928009a6d417d9d55` |

对应 P4/N4/N5 汇合作业 97462/97451/97456。包内为每个配置的最终 V、SDC、DEF、ODB、SPEF、GDS，附版图、验收回执、执行源及来源清单。父层所需 LEF/时序抽象另按匹配视图验收。#178 线上快照仍为原仲裁与标准单元 S 的来源，本表索引另行验收的真 SRAM 包。

## 验证和未完成项

- 计划交付验证见 PR #185 回执。三份 SRAM 源摘要和文档量化值复核，本轮未执行 RTL、SystemC、模型或 EDA。
- 后续仍需验收实际五类硬化封装、16 KiB 分片调度、MEM 与九实例部署、联合后制互联及三模型切片。当前登记 [管理中心 PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5) 为 pending。仓库缺少 `config/board.json`，候选组织看板读取缺少 `read:project`，条目状态 unverified，同步 pending，由具备权限的管理员待处理。
