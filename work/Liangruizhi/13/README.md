# Issue13 工作记录

- 负责人Liangruizhi／2663955430@qq.com；[Issue13](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/13)。审查人待指定。
- 主工作树D:/Projects/LLMHardwareDesign-endpoints，分支task/13-endpoint-ablation，起点47d134411775e25a0c43f9818bfbd95e69e69734（PR12当前head）。PR以task/11-frozen-routing-pilot为基分支，依赖PR12审查/合并；没有自行合并。
- 并行微例实现/审查目录D:/Projects/LLMHardwareDesign-endpoint-review，分支task/13-endpoint-fixture-review；只新增tiny_cases.py/test_tiny_cases.py，经读取后复制入主任务树，无远端分支或重复PR。主树和Issue7/他人目录不并发修改。
- 先核对main/Issue7/11/PR6/8/10/12、评论、进度与交接。PR10更新到2b76f692，其他成员继续处理宏资格/电容；本轮只读核对指定9个视图，不运行服务器任务。
- 本机已有D:/APP/Python/python.exe；创建项目内system-site-packages venv，不安装/升级解释器、EDA或全局包。数据、源码与环境在D盘。
- 用户新全局规则到达后，TEMP/TMP/TMPDIR/PYTHONPYCACHEPREFIX/MPLCONFIGDIR均按进程设置到D:/Projects/Codex/issue-13-endpoint-ablation对应子目录，不改系统环境变量。完成后清理无用缓存，保留项目结果与必要开发尝试。
- 方法合同和配置在正式结果之前建立；已有图已被观察，不称新盲测。开发试运行local_runs/development-01显式allow-dirty，保留为开发记录，不提升正式证据。开发后只补合同断言与来源/验收，无结果导向库存或参数调优。
- 开始时管理中心PR5仍OPEN，默认registry仅有team-workspace；登记pending。当前插件无Projects工具，本项目无board.json，条目/本人权限unverified，同步pending，管理员待指定；不可套用其他会话缺read:project的结论。
