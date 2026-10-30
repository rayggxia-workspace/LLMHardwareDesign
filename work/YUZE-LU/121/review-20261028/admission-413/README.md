# 413 当前 V/R 自动准入

Refs #121 / PR #122。2026-10-30 02:53:46 CST实际启动，PID3818917，控制源33bb0916943a72f5b07860d89a24d088cf6e893c、配置提交bfee9fd72b292087dc6fb600967b4d2ec02315bc。配置SHA26712d260660b79acd7d42780f97d72943cb366d252012f2f06e0582e716a1db，控制源SHA580b896f85836fe06ae4c23ed80b1a6b8843559ad62810be9d13d0da5eca05ea。

六队列按404/405/406/410/411/412固定，24远端文件/六源归档、原Git blobs和本地已提交manifest/queue全部核验。正反控制测试通过，实际UID/cmdline/start ticks/文件SHA与02:53:46、02:54:46两轮状态读回验证，见capture-start。后四项等待真实前置，只有404与410已分配。

只终止旧407登录控制PID3668320；仅退休未分配402，改由412等新411完整几何。2份远端退休原始记录/SHA/长度见retirement-records，明确slurm_jobs_cancelled=false。V401/93578原独立DRC/最终功能/LEC继续，未取消或重启任何EDA，所有旧源/ODB保留。

默认c96六16CPU独立槽、即完即补；本Issue最多8 allocation，含pending/unknown/旧同Issue任务，由原共享dispatcher的锁及预约强制。内存预测乘1.2另留16GiB，结合liveRSS；只有真实依赖/内存限制降低并行。无关账号任务不操作。413只准入，不执行EDA或判定最终宏合格。
