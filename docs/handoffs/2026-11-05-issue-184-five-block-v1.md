# Issue #184 五类逻辑 Block v1 执行交接

- 当前修订：2026-11-13，YUZE-LU / Codex。合同版本 `five-block-v1/2026-11-13`。
- [Issue #184](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/184) · [PR #185](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/185) · 远端分支 `task/184-five-block-v1`。
- 统一入口为[共同底座实施清单](../local-blocks/PRODUCT_BASE_V1.md)、[实施与验收合同](../local-blocks/FIVE_BLOCK_V1_PLAN.md)和[决策 0007](../decisions/0007-five-block-v1-synthesis.md)。合同修订不构成 RTL/EDA 验收。旧 P/J 任务 #187 与组合硬宏包作为历史结果保留。
- 当前续作从 #185 的 4aa8206a2 与已合并独立交付的 main c4d7b9605 对齐。

## 执行前必须确认

1. 读取 `AGENTS.md`、协作 Skill 及本合同。五类各一份实现，九组是控制归属；全局直接摆独立叶宏和标准单元局控，组合验证夹具的硬框/LEF 不得成为顶层单元。
2. 叶宏按[候选库存](../local-blocks/product-base-v1-inventory.json)选定，逐项核对匹配视图、ABI、六文件与摘要。P 的原生 S_P 普通口保留，A256 由父层拼拍，真实 W512 由 DDR 传输供应。
3. #213/#214/#221/#224 的独立交付已进 main。联合接入新 P/U/C/F/J 与 MC06 时核对 E 源数量、双向发送前进、PM/描述符 ABI 和真实 LC 身份。旧版资格与新版本分别登记。
4. 对齐 model/arch/base schema，列出 30 个独立功能叶实例、九个 LC 身份、实际 PM/MEM、S 外部仲裁和辅助资源。端点从真实联合布局导出。
5. 五类服务、SystemC、映射器、RTL 与全局物理并行工作，共用上述输入与事件合同。逐位登记真实叶宏/适配端点；主要组内/组间数据边默认后制，有限预连逐项确认。同步修订映射、程序和布线需求，禁止只换端口名而保持旧封装几何模型。
6. 比较紧凑全局布局，解释每处保留区和大块空白；锁定共同底座前试至少两份产品连接。按合同完成五类局部路径、九实例与同底座不同产品的联合验收。运行远程作业前读取 `docs/REMOTE_RULES.md`，记录输入/工具/命令、输出和摘要。

## 本次交付与待办

本次固定候选宏清单和端点准入。P 的 RTL 与 S_P 最终映射网表替换对照各六组通过。继续执行 P 父层接入和紧凑布局、U/C/F/J 端点归属、64 B DMA 及联合底座与产品验收。

项目登记 [management-hub PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5) 为 pending；缺少 `config/board.json`，Projects 条目 unverified、同步 pending，待具备权限的管理员核验。此项不改变技术合同。

## 历史：2026-11-05 私有 SRAM 验收输入（已被 #203 选型替代）

下列文件由用户提供，位于 `D:/Data/电路实验/LLMHardwareDesign-worktrees/local-s-sram-rtl-verification/physical-acceptance-01/`。本轮读取报告，复算三个文件的 SHA-256，核对包内每个配置的六文件和验收回执条目。大型包留在来源目录。若换机器，需从原交付者或经授权的项目存储获取相同摘要。

| 工件 | SHA-256 |
| --- | --- |
| `验收报告.md` | `948879b4d3aeadf522b4789b1bb300d7d4c7834bbbd0b5767557be42561bc6b6` |
| `accepted-p4.tar.gz` | `f3ef828391b82f1d0d3169a141557cebe554e6757a764f1c5de4e361ef5878c5` |
| `accepted-v2-n4-n5.tar.gz` | `30cfc286b12c4e29d52e17eeee04c242dda8309bec0c387928009a6d417d9d55` |

对应 P4/N4/N5 汇合作业 97462/97451/97456。包内为每个配置的最终 V、SDC、DEF、ODB、SPEF、GDS，附版图、验收回执、执行源及来源清单。父层所需 LEF/时序抽象另按匹配视图验收。#178 线上快照仍为原仲裁与标准单元 S 的来源，本表索引另行验收的真 SRAM 包。
