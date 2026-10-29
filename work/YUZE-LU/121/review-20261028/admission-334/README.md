当前状态：已退役，仅保留历史控制证据；生产准入入口为../admission-335。退役只终止控制进程，原8个Slurm实验继续。原因见scope-negative.json与retired.json。

# 本轮六队列准入检查

这是已有Slurm提交器的轻量控制入口，服务于R311/312/313和V330/331/332；没有新宏、候选扫描或额外allocation。源f419f07bb6ad7450d2498ab43b2540f558445412，配置7f23a681c080a0cabdf074eb6f77ca369dc0c3b3/config SHA88b80eb281acfcf67f59e546c270b76b5ee06d14ac308cb0cab3128b25224799。

六原manifest/queue的远程字节与已提交工件一致；每份原dispatcher和dependency模块与源归档Git blobs一致，原archive SHA已核验。只按固定清单和真实前置调用原提交器，其共享锁、reservation及8allocation限制保持。未知提交、任何旧提交状态、观察错误均不触发重投；不取消或修改原作业。

`capture-start/`保存六个原始小文件及SHA、实际/proc身份、启动和两轮观察时间。服务器PID2113064在2026-10-29T01:39:06Z捕获时存活；首轮01:37:30、后轮01:38:31，330为ready_at_allocation_cap，其余等待前置，未新增作业。本地和服务器同字节控制测试均通过。旧运行任务已单独确认仍实际计算。

部署目录：`/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/admission-20261029-334`。后续先读取真实status.json/launch.json及/proc核对存活；不根据本文件中的历史PID或锁文件重复启动。此控制入口不运行EDA、不授予最终资格，V/R仍须新原生、独立四门、六文件、完整几何及接口。
