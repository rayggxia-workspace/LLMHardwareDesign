# 当前535→537→538→539调度器

Refs #121 / PR #122。10份白名单队列的manifest、queue与实际归档dispatcher/dependency均经SHA/Git字节核验，见config.json与staging-verification.json。配置不启动EDA；部署仅替换旧525登录节点控制进程，不中止任何Slurm任务，继续使用原Issue账本/锁/UNKNOWN reservation及8 allocation上限。6×16即完即补，内存守卫与真实依赖保留。R404/405/406和旧523/524一并保留，新535/536/537/538/539按真实前置放行。
