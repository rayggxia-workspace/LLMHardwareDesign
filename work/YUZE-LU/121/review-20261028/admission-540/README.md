# 当前535→537→538→539调度器

Refs #121 / PR #122。10份白名单队列的manifest、queue与实际归档dispatcher/dependency均经SHA/Git字节核验，见config.json与staging-verification.json。配置不启动EDA；部署仅替换旧525登录节点控制进程，不中止任何Slurm任务，继续使用原Issue账本/锁/UNKNOWN reservation及8 allocation上限。6×16即完即补，内存守卫与真实依赖保留。R404/405/406和旧523/524一并保留，新535/536/537/538/539按真实前置放行。

已实际部署PID781719，源/配置fbd2d950；控制正反例和生产配置预检通过，只退休525登录控制进程，未取消/重启任何EDA。capture-start核验UID、命令行、源与配置SHA，两轮时间10:40:48/10:43:50 UTC。accounting-start核验实际5 allocations（92045/92046/R93555/旧V93679/新V93691），旧460→422/93606仍入账，原始历史状态未改。新538/539等待真实前置；不空占节点。
