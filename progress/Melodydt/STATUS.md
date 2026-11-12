# Melodydt 的进度

## 2026-11-12（Asia/Shanghai，UTC+08:00）

- 任务：[Issue #255](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/255)，负责人 Melodydt。交付分支 `task/255-dac-control-paper` 起自 [PR #251](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/251) 的 `9abd46f5cbb4534bcfc614571ccd6d402ad11882`，成果见 [草稿 PR #256](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/256)。
- 已完成：[英文控制正文、图注和逐图中文说明](../../docs/papers/dac-control/README.md)。三张 SVG 与三页 diagrams.net 源图保留独立图形、文字和连线。图 1(b) 按图 1(a) 的形式以橙色横带表示 C 内后制路径，G→E 接入横带，S/R 用断开的候选短线标示。图 2(a) 仅保留四类指令及其作用。图 2(b) 用 Llama 3.2-3B 和 Qwen3-4B 对照 Q/K 投影到 RoPE 的路径及额外逐头 RMSNorm。图 3 展示三 P FFN 的 17 条静态母控指令、三份相同局控镜像、192 次调用和独立 DDR 描述符区。
- 验证：管理结构检查通过。Python 3.12 核对可编辑对象、C 固定路径与后制旁路、四类指令及两段模型调度的调用顺序、依赖、等待掩码和 U0/U1 复用。基线 FFN 镜像及 192 次 CALL 回查通过，并核对图 3 的记录地址、等待掩码和可编辑对象。新增图已渲染并目视核验。本轮未新增 RTL、SystemC 或物理实验。
- 下一步：由 Melodydt 核对与论文全篇一致的术语，补充有日志支撑的控制时序证据。
- 阻塞与待同步：本地为独立文稿目录，CLI 无法解析 GitHub 域名。在线分支通过 Melodydt 的 GitHub 连接操作。看板条目待有权限的管理员核验，独立审查人待指定。
- [恢复与服务器交接](../../docs/handoffs/2026-11-11-issue-255-dac-control.md)。
