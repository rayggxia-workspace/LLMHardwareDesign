# Issue41资料及交付入口

负责人Liangruizhi（2663955430@qq.com，ID182389313），指定GitHub认证查询通过。
Issue https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/41。
task/41-block-candidate-v1，独立D:/Projects/LLMHardwareDesign-blockv1，base PR40@f2e55e08dad4e99b44d5532c6cc808e6537c2006。
临时/准备资料仅D:/Projects/Codex/block-candidate-20261023；不改其他worktree、他人进度或ref-project。

已读main0cc36f3最新README/AGENTS/project/协作/STATUS、Issue39/37及PR40/38/34评论，
Issue32仍in_progress、PR36@62e97da9继续Qwen；Issue31/PR35物理范围和PR26功能调研不接管。
未获用户兄方完成通知，仅核范围，不整合数值/状态成果。

正式方案docs/BLOCK_CANDIDATE_V1.md，最小实验docs/BLOCK_MINIMAL_EXPERIMENTS_V1.md；
project/experiments/block_candidate为解析库存/容量/打包下界复算，不是硬件实现或模型实验。
本轮不新跑模型/GPU/RTL，不下载权重、不启动任何其他机器。
analysis.json/checks.json及manifest记录实际复算、验证与SHA。
正式源码dfb12cddb81f6acdf44a2c1f64600aa37e121a3a，两次解析输出逐字节一致、三源码绑定、
8独立已知值/2容量反例、D1–D6覆盖和新文档相对链接通过；verify.py可重放交付核验。
PR44待审查/合并，交付commit以head读回为准。E1–E5未执行，没有模型/硬件通过结论。
checks/*.log保留原始CRLF字节；whitespace检查用
`git -c core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol diff --cached --check`，
只把CRLF末尾CR识别为换行，保留其他空白错误检查，不修改原始日志来通过检查。

登记沿用management-hub PR5 pending；无board.json/Projects条目工具，看板unverified/同步pending，管理员待指定。
审查人待指定，PR上传后仍待审查合并，Issue不done。GitHub分支创建曾超时，已读回404后才重试；
后续已成功创建分支及PR44；历史超时未当成功或重复盲写。任务期间新增Issue42/43互补范围已核，未接管。
