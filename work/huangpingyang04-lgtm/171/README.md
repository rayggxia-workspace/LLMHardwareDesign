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
