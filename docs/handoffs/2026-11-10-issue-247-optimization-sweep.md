# 七类优化方向的条件模型评估

Issue247 / PR243，负责人Melodydt，2026-11-10 Asia/Shanghai。用户要求继续探究优化并尽可能逐项仿真。
复用远端task/242-r-load-bounds，基线adf8a9c9f1f955eafbb1a86a994b9ccb9214540e；当前为in_progress。

当前正式副本为本地非Git快照work/Melodydt/242/r-load-bounds/repo；根代理独占新增
project/experiments/optimization_sweep及本阶段文档。旧a32-rtl各worktree未提交修改保持原样，未复用或覆盖。
新增源码六文件，生产RTL未改。静态Python AST与冻结生成链通过；管理结构检查通过，均不代替业务仿真。

计划：七类方向（M并行、供数、向量、NExp、DDR、池容量、M窄写修正），原四场景×shared/idealdual，
共112例；先8例base全RESULT复现run25的32B控制，再跑各单项与3种组合。
旧校准账本保留为参考；新M16/NExp8/宽向量只是条件服务目标，不作新RTL已校准证明。
各例检查字节/命令守恒和实际成本差额，A32/A64使用实际生成的池头运行独立数值/FIFO检查。

尚未提交服务器作业。待源码上传读回后打包到本人服务器独立run35，启动信息和结束结果随后补充。
恢复第一步核对PR最新head和本地optimization-source-files.json，再查看run35是否已存在/已提交，禁止重复覆盖或重复启动。
没有自动监测。新性能、面积和物理时序均尚未测量。

登记management-hub PR5 pending；config/board.json缺失，当前无Projects工具，看板unverified/同步pending，管理员待指定。
此前CI validate无steps/runner失败限制保留；不绕过检查。旧run24/25上传阻塞原样保留，本阶段不重传该包。
