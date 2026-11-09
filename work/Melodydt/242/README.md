# Melodydt / Issue #242 轻量验证证据

[Issue #242](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/242)，用途：保存 R 原始 LOAD 边界修复的实际输入、日志、Slurm 终态和校验索引。正式代码在 `project/rtl/r_local_state`、回归在 `project/experiments/r_load_bounds`；[正式实验报告](../../../docs/experiments/issue-242-r-load-bounds.md)。

源码 commit `f034be2b7c87137b92f7bfce274a5485647e512d`，分支 `task/242-r-load-bounds`；基线 main `c4d7b960599b9d292f27eb4429d5f226a7156c95`。本目录后续仅补文档/证据，不改变已测源码。

| 文件 | 来源与用途 |
| --- | --- |
| inputs.json | 实际打包输入及源码 SHA-256 |
| verification.json | 输入/12 份输出日志独立核验汇总、证据文件 SHA、未执行范围 |
| raw256/、raw1024/ | 各三次原始端口回归的 result.json 与日志 |
| service256/ | 既有 C 适配器三次协议回归的 result.json 与日志 |
| negative/ | 原 main 源码三次预期失败记录，仿真 exit 1 表示旧缺陷被检出 |
| sacct.txt | 101572 数组四项真实终态 |
| allocation-*.txt | scontrol 原始资源、节点和 UNLIMITED 时限记录 |
| image.sha256 | 实际工具容器 SHA-256 |

原始完整输出保存在获授权的个人服务器目录 `/public/home/yuzelu/Melodydt/issue242-r-load-bounds/run01`；服务器登录目标 `yuzelu@10.129.166.172`。完整包 `evidence.tar.gz` SHA-256 为 `949031ef34ed9b2dc5cd841c67df6b9c82284128adb24d75d722c8e88eab348b`，本地副本在 `D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/242/r-load-bounds/run01/`。大包、二进制、编译对象不进入 Git。记录仅供本私有项目获授权成员访问。

九次修复版通过，三次旧源负控制检出预期缺陷；四个包装作业全部 COMPLETED 0:0。此结果仅覆盖 RTL/接口行为，未重新取得物理资格、未执行原 192 项最终网表回归，也未启动整模型仿真。

规则版本 rayggxia-project-collab 1.0.0。登记复用 [management-hub PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5) pending；看板 unverified / 同步 pending（无 board.json 和 Projects 条目工具；处理人待指定）。独立审查人待指定，任务提交 PR 后进入 in_review，不标 done。[交接入口](../../../docs/handoffs/2026-11-09-issue-242-r-load-bounds.md)。
