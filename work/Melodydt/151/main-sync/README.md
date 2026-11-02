# Issue151 main同步资料

负责人Melodydt，PR152。本目录存本轮来源比较、树合并计划、当前八主线机器索引及实际静态验证；不存大型物理数据库、服务器构建或真实tensor。

- source-comparison.json：14历史源锁分为11合格叶依赖/1未合格R/2main未交付legacy；46runtime逐字节保持。
- merge-plan.json：固定main/研究/祖先、4自动树动作、8共享文件解决策略和本地API隔离目录。
- roadmap.json：当前L1–L8及下一L4-A-TSP退出门；旧索引作为历史不回写。
- verification.json：实际命令/输出摘要及SHA；未运行项明确列出。
- verify_main_sync.py：只读验证本轮文件/旧锁/来源与静态检查，不提交服务器作业。

正式说明见[主报告](../../../../docs/MAIN_SYNC_AND_RESEARCH_ROADMAP.md)。最终merge commit与线上状态见PR152回执；本目录内parents记录固定输入，不把旧仿真源改成merge提交。
