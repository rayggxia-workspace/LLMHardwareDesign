历史准入335已退休：仅替换其登录控制进程，当前341管理新V337/338/339及原R311/312/313；所有Slurm EDA继续。实际退休原记录见../admission-341/retirements/。以下为原335部署时证据。

# 本轮六队列准入控制（当前335）

仅服务已stage的R311/312/313和V330/331/332，每60秒检查实际前置与本Issue空位，复用每份原dispatch.py。源0029a9b99a3a8f0b4eb4905dd142e01b30bd7ea6，配置acbd45e9478a3a1dd2b3ff8c346108005218b5bb/config SHA88b80eb281acfcf67f59e546c270b76b5ee06d14ac308cb0cab3128b25224799。

24个manifest/queue/dispatcher/dependency SHA固定。六原manifest/queue远程字节与已提交工件、原提交器和依赖模块与归档Git blobs一致，归档SHA已核验。只计本Issue原dispatch-state记录ID；其他成员及同账号无关作业不占本任务名额。原全Issue提交锁、先落盘reservation和含pending/unknown的8allocation限制保持；任何旧提交记录均不重投。观察错误不是终态；失败不自动重跑。不执行EDA、不取消Slurm作业、不改变节点内队列。

本地与部署端同字节控制测试通过。旧334的额外同账号无关作业负例暴露预检查过于保守，已保留；仅其登录控制进程经UID/命令行/源SHA/进程start ticks核对后终止，退役回执在../admission-334/retired.json。新335替代它，原8个EDA作业均继续。

capture-start保存六个原始小文件、SHA及实际/proc身份：2026-10-29T01:45:05Z捕获PID2121001存活；首轮01:43:56，后轮01:44:59。allocation-scope-readback.json在01:45:45核对8个本Issue allocation；330正确ready_at_allocation_cap，其他等待前置，无新作业。

实际部署：/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/admission-20261029-335。下一轮先读真实status.json、launch.json及/proc；不要以历史PID或锁文件认定存活，也不要并行再启控制进程。控制状态finished不代表五宏验收完成；仍须V/R新原生、独立四门、六文件、完整几何和接口全部通过。
