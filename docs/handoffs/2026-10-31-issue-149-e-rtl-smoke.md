# Issue149：E RTL 流程验证交接

- 仓库 rayggxia-workspace/LLMHardwareDesign；负责人 Melodydt；Issue149；任务分支 task/149-rtl-smoke。
- 已运行源码基线 `5e787714362d957b79c2997141cf05eeebb85afc`，服务器 `/public/home/yuzelu/Melodydt/LLMHardwareDesign-issue149`，原生Git状态clean。实验源HEAD固定；远端文档交付commit需另查任务PR，不能混为同一版本。
- 运行结果 `/public/home/yuzelu/Melodydt/runs/issue-149/e-smoke-20261031-01`；Slurm94188已自然COMPLETED/0:0，45秒，node1/16核，UNLIMITED，无活动仿真需要续跑。
- E严格lint/编译/三初态通过，每组107062检查。包SHA `d447a183f6108b7bdbf62a1de7ca1287489b925927318fc2dcd2203fdc77d06b`；17产物和3实际输入绑定已核验。
- 本地下载/复核位置 C:\Users\Administrator\Documents\ChatGPT\课题研究 大模型硬件化\rtl-smoke-preparation-20261031\；D:\Study_material\Study_material\LLMHardwareDesign 仍是管理参考副本，不是本次服务器Git副本。服务器传输/物化辅助材料位于 /public/home/yuzelu/Melodydt/issue-149-transfer-20261031-01/。
- 本任务没有修改原RTL、原测试、共享软件或其他成员目录/作业。服务器GitHub CLI认证尚未配置；原Git对象由Melodydt连接读取，物化期间Git网络被禁用。缺少非稀疏对象时先以本人连接补齐，不借用服务器其他GitHub凭据。
- 首次直接执行共享Verilator遇GLIBC错误；实际仿真应沿用现有Singularity ORFS容器。物化时遇过提交时区/末尾换行、Python3.6兼容和缺失目录元数据问题，均通过原始Git SHA/兼容API/必要目录元数据解决；最终Git状态返回0且clean。没有把这些准备失败记为RTL反例。
- 业务成果待独立审查/PR合并，不标done；审查人待指定。#147 / PR148的个人进度变更需在合并时保留，避免覆盖。
- 登记management-hub PR5仍open/pending；config无board.json、缺Projects条目工具，看板unverified/同步pending。具能力权限管理员待指定：核对适用看板和Issue149卡、Project ID=llm-hardware-design、Status=In review及实际assignee后读回；不猜Priority/日期/条目ID。
- 恢复第一步：读取最新AGENTS/Skill、本Issue及PR、本人STATUS和本交接；按work/Melodydt/149/README.md用sacct和receipt核对94188，不重复提交已封存输出目录。需要新增实验时使用全新attempt并明确任务范围。
