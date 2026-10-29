# 426：七队列准入部署回执

Refs #121 / PR #122。控制源码/配置commit ea9a6a5648035e552cef145e3e2b54e6794056fc；PID3990865，配置SHA2dfd36fd4f02ad6cc3326757d0a8eb7c1cebad209a7e3d5d28dee1c796499492。原始launch与两轮读回、实际/proc UID/cmdline/start ticks/源码及配置SHA已核验，控制正反例通过。只替换413登录节点轻量控制并退休未分配412；Slurm EDA没有取消，旧411独立验收和R404继续。

七队列404/405/406、422/423/424/425的28远端文件、七源归档大小/SHA/Git blobs和提交队列逐字节核验见staging-verification.json。max8只针对本Issue含pending/unknown/旧任务，保留dispatcher原锁和未知提交fail-closed；其他账号/同账号无关任务不操作。真实前置就绪后自动补位，不重试已有终态分配。422已自动93601完成，423自动93602运行，424/425仍待前置；节点内默认六16CPU，只有真实依赖/RAM证据限制。
