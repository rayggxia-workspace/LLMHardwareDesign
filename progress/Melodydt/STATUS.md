# Melodydt 的进度

## 2026-11-11（Asia/Shanghai，UTC+08:00）

- 任务：[Issue #255](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/255)，负责人 Melodydt。交付分支 `task/255-dac-control-paper` 起自 [PR #251](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/251) 的 `9abd46f5cbb4534bcfc614571ccd6d402ad11882`，成果见 [草稿 PR #256](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/256)。
- 已完成：[英文控制正文、图注和逐图中文说明](../../docs/papers/dac-control/README.md)。两张 SVG 与双页 diagrams.net 源图保留独立图形、文字和连线。图 1(b) 用 C Block 展开 S/R/G/E，突出母控和局控，统一蓝色接口交换并用橙色虚线标出 G→E 产品直送。图 2 保留五类 Block 的公共局控指令，对照 Qwen2.5-3B-Instruct 门控 FFN 与 GPT-2 GELU MLP 的候选数据路由和母控调度。
- 验证：管理结构检查通过。Python 3.12 核对可编辑对象、控制器层级、连线规则和五类 Block 公共局控指令。两段模型算子调度以基线汇编器核对，检查调用顺序、掩码与目标复用，算子公式对照固定版本官方模型源码和配置。基线 FFN 镜像及 192 次 CALL 回查通过。两图已渲染并目视核验。本轮未新增 RTL、SystemC 或物理实验。
- 下一步：由 Melodydt 核对与论文全篇一致的术语，补充有日志支撑的控制时序证据。
- 阻塞与待同步：本地为独立文稿目录，CLI 无法解析 GitHub 域名。在线分支通过 Melodydt 的 GitHub 连接操作。看板条目待有权限的管理员核验，独立审查人待指定。
- [恢复与服务器交接](../../docs/handoffs/2026-11-11-issue-255-dac-control.md)。
