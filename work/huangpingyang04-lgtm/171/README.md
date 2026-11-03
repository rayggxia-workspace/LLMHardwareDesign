# Issue171：DRAM→S→M 异步 FIFO 方案文档

- [Issue #171](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/171)；[方案正文](../../../docs/DRAM_S_ASYNC_FIFO.md)。
- 执行账号及负责人：**huangpingyang04-lgtm**；优先级和独立审查人待指定。
- 日期：2026-11-03（Asia/Shanghai）；分支 `task/171-dram-s-async-fifo-docs`；main 基线 `4b1df2c7cbdaa0fa6f9f468f2b5b854cec875609`。
- 用户要求纠正此前错误使用 YUZE-LU 创建的 PR170/Issue169。使用本账号重新创建文档提交，个人进度放在本账号目录；旧 PR/Issue 关闭并链接到新任务，旧专用分支按用户要求清理，实际结果记录在本 Issue。GitHub 不支持删除已有 PR 记录。

## 修改与验证

仅修改方案正文、ARCHITECTURE 入口、本账号个人进度及本记录，共四个 Markdown 文件。没有 FIFO RTL、服务器或运行作业变更。

从精确 main 基线取得原 `scripts/check_project.py` 和管理输入，在独立本地最小快照中叠加本次四个文档后运行：

```powershell
python -X utf8 scripts/check_project.py
```

另核对新本地引用、500/300 MHz 和带宽算例、AMD 官方 URL 保留、四个远端文件与预期内容、commit 和 PR 的实际作者。最小快照不等于完整代码检出；具体实际结果记录在 PR 回执。未执行 RTL 仿真、形式/CDC、综合或物理流程。

## 依据与后续

[AMD PG327：Independent Clocks: Block RAM and Distributed RAM](https://docs.amd.com/r/en-US/pg327-emb-fifo-gen/Independent-Clocks-Block-RAM-and-Distributed-RAM)说明独立读写时钟、Gray 指针同步及空满判断，支持该方案已有产品级实现；本项目 ASIC 的参数和物理结果仍待验证。原技术正文保持，仅调整关联任务。

规则 rayggxia-project-collab1.0.0。登记沿用 management-hub PR5 pending 证据；缺 `config/board.json`、无 Projects 条目工具，看板 unverified/同步 pending；需管理员提供配置并加入/核验本 Issue，处理人待指定。PR/commit 实际链接见 Issue 回执。待独立审查，不自合并或提前标 done。

## 三聊天合并补充：完整流程（2026-11-03）

用户要求合并本聊天、“评估 S宏 改用 SRAM 方案”、“分析DRAM与片上时钟域跨越方案”，并一并上传PR。已只读核对两个指定聊天的本地历史及公开到本仓库的固定来源，未上传原始聊天内容。原PR170已撤销，继续正式PR172，不重开重复PR；执行账号沿用明确纠正后的huangpingyang04-lgtm。

- 正文：[DRAM → FIFO → D → SRAM S → M](../../../docs/DRAM_SRAM_S_M_FLOW.md)。
- 同步澄清原FIFO专题和ARCHITECTURE入口，更新本账号进度。
- 记录控制器用户接口时钟、完整AXI跨域、D与异步FIFO的区别、C逐阶段完成条件、SRAM替换/延迟、结果回写、多S候选及实际物理归属。
- 源版本：[来源索引](sources-flow.json)。来源为PR158、PR159、PR163、main六宏和PR172现有方案；不合并它们的代码或历史。现有main状态文档有过时描述，以线上PR和固定验收报告为事实依据。
- 本次PR-head基线 `f5f9edb2af9074ed96bb085366ccdf534aa46261`。后续commit实际SHA和读回结果见PR提交回执。

### 本次实际验证范围

在从上述PR-head取得的29项管理/文档输入最小快照中运行原 `python -X utf8 scripts/check_project.py`，补充前后通过。该快照不是完整工程检出，不用它证明业务或硬件通过。

文档检查：六个交付文件的非空/UTF-8/空白、Markdown代码围栏成对、新增相对链接可解析、固定来源可追溯，以及16KiB/64B/128B/8GB/s/4.8GB/s/3200B算例通过。完整流程与两个指定聊天和固定接口逐项核对；Mermaid图做文本结构和人工阅读检查，未执行图形渲染。GitHub文件/分支头/作者读回结果在PR最终回执报告。

未执行FIFO RTL、仿真、形式/CDC、综合、PEX或布局布线；没有操作服务器、现有作业、其他成员进度或RTL。工程完成与方案提交分开。

### 协作交接

规则rayggxia-project-collab1.0.0；project_id=llm-hardware-design；Issue171/PR172；负责人huangpingyang04-lgtm。登记沿用management-hub PR5 pending证据，未改管理中心；PR-head树无config/board.json，已读status-mapping且无Projects条目能力，看板unverified/同步pending，管理员待指定。保持open/in_review与待独立审查，不自合并、不标done；下一步由待指定审查人审查完整流程，硬件实现另行落实。
