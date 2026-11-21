# 执行位置与状态

- baseline：Slurm101533 COMPLETED，回放8404服务。证据为 baseline/ 中原始回执。
- 原M测量：Slurm101588，4CPU，17s；原M的九个R/K测试 PASS。随后早期模型在simulation开始后创建fifo导致SystemC E113，作业总体FAILED；没有隐藏为整体通过。保留清理尾部空白后的 native/early-smoke-failure.log；精确原字节在同目录 .original.log.gz。
- 修复：有限fifo/semaphore均在elaboration创建；Windows GCC14.2 / SystemC3.0.2完整34场景与独立审计通过。
- 101589：早期版本排队时撤回，没有性能数据。
- 101592：最终Linux复核等待资源期间撤回，没有运行；不宣称Linux完整回归通过。
- 最终本地运行：D:/Data/电路实验/side-systemc-block-study-20261109-02，local-final-sweep.log 以 SWEEP_PASS 34 结束；矩阵/流量/容量审计 AUDIT_PASS 34。
- 无改动其他任务的源、分支或Slurm作业。新能力未实现RTL/物理；没有运行真实权重下的新KV数值回归或能耗计算。

输入为配置/形状/算子和依赖，非在SystemC内进行权重数值执行。实际trace及行结束形式也冻结SHA；LF规范化SHA可核对跨平台导出。源码与结果的逐文件SHA在manifest.json。
