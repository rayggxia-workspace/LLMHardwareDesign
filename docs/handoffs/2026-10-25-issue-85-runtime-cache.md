# Issue85运行时缓存交接

更新时间2026-10-25T12:16:13.088516+08:00。仓库https://github.com/rayggxia-workspace/LLMHardwareDesign，负责人Liangruizhi；Issue https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/85。分支task/85-runtime-cache；工作目录D:/Projects/LLMHardwareDesign-runtime-cache；临时D:/Projects/Codex/runtime-cache-20261025-01。主会话负责push/PR/Issue和看板，本实现代理未推送或创建PR。

执行RTL commit 588f61c781ecf3be7fca626c8aae4819b775adfd（phase2），最终遥测驱动/接收源码af634db7ba2712edeae6dee315181e01e666fa94（phase5）；完整phase1–5源码绑定/命令见work/Liangruizhi/85/execution.json。最终文档/精选提交以本文件所在Git提交和主会话PR回执为准；提交前只含本任务文件。不得借用其他GitHub账号。

## 结果与位置

正式两路60完整真实命令、94次接受、22次soft-abort、12个错误条件及2个迟到响应丢弃已实际通过。一个可执行文件混合两cache模式，实际全部acc/down/join/norm逐位一致；外部测试FIFO峰各2。核心cycles与84静态shared对应模式相同，logic-only52415.566um²，对84cached/shared增加1.52715%；generic FF4309（+97bit），仍8S8+1S32、16KiB单1RW。

服务器根/public/home/yuzelu/RuizhiLiang/issue85-runtime-cache-20261025，正式rtl-s002/102早期结果保留，最终rtl-s003/103、receipt-s004/104.json、analysis03/report.json、map02（相同RTL字节）为当前证据。inputs在input01；完整输入引用只读/public/home/yuzelu/RuizhiLiang/issue84-cache-share-20261025/input01，全部artifact SHA在接收阶段核验。报告docs/experiments/issue-85-runtime-cache.md，设计决定docs/decisions/2026-10-25-runtime-cache-and-epoch.md。

|成果|大小/成员|SHA256|
|---|---:|---|
|/public/home/yuzelu/RuizhiLiang/issue85-runtime-cache-20261025/delivery02/full-results.zip|74455001B/255|6bf2cedeb1b643ebd83a32dd37184f7abb7d5ed3950b1b42e24856a0dcc1b58d|
|project/experiments/runtime_cache/results/issue-85/final/selected.zip|588490B/98|6b1c561d6098a04cf84859bca1d26261fd5a65139a1a93ecc1cc9106e611dd40|
|final/index.json|索引|f1958bf049c54749bc1930c2068a77f3fdb9273f66f27a72728ae55625e17c1b|
|final/comparison.json|测量与资源|5cee08ae5a13bde8102b4b5d7fb2b3f3688d3dffc45af053f44fee8afa7193c3|

full/selected均逐字节核验PASS；5phase86原Git源blob与冻结SHA/index一致；不是把当前文件当历史源码。初版delivery01及results/issue-85根的v1证据保留，最终以final/为准。最终全包byte接收90751、归档90747通过；所有本任务Slurm状态见slurm-final.txt，未执行依赖取消与90697构建失败原日志完整保留。源码配置重放命令见project/experiments/runtime_cache/README.md和execution.json。

## 限制与恢复第一步

新增32bit epoch接口的实际NoC打包/线网未定；恢复环境2槽至少320bit payload/tag加控制未计core面积。Global reset需fabric共同复位；soft_abort允许迟到带tag响应。会话epoch禁止wrap，溢出注入未执行。宏/STA/门级等价/CDC/多context/更大H/K/通用V/完整M阵列和整模型质量未验收，不能说Block电路全部签核。86结果不可自动变成85时序资格。

下一位先核最新Issue85、父84/并行86、PR与成员55/63记录，确认branch/HEAD和真实认证Liangruizhi；读final/index和两份字节/原Git接收。可先沿明确cmd_ready/accept和tagged软中止接口推进总线集成，补epoch边界/真实tag费用，然后在目标宏/PVT/STA约束可用时处理物理资格，不重复加载模型。无须继续旧已完成Slurm作业。未上传/PR状态由主会话完成；登记management-hub PR5 pending、看板配置/read:project权限沿父任务记录未解决，管理员/审查人待指定。

远端交付：[PR89](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/89)已上传，Issue85为in_review；待指定独立审查与合并，未done。已按不可变commit读回报告/交接/个人进度，与原Git blob逐字节相同；后续仅文档同步，不改变实验源码和结果SHA。
