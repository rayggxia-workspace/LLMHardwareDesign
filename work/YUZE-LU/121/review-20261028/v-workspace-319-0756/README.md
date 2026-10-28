# 当前 V 流水的真实 S/V 调度、占用与预算

Issue #121 / PR #122。319/93080 node23自然COMPLETED/0:0，七项独立16CPU任务全部通过，采用六并发槽、结束补位。源db4905bd3534e4f89e82469980fa12efd3092727，archive38af4ca2c3bc7d56ee2537c2e597ae56dfac0371e6811a3c694bddd7e68247bb，V RTL与315相同。

两项占用测量与315公共结果/周期/流量逐项一致；实际乘积寄存使能只在M_EXEC24，操作数七取数阶段、P_TOTAL25与P_ROUND26分开计数。函数有效token逐级采样；这些是逻辑使能占用，不是功耗或有用MAC峰值。

五项真实S16KiB/V工作空间及模型长度测量，每项27情形、两初态：总270次执行，其中216次模型长度执行。保持一组V2KiB replay、S16KiB单1RW，无附加payload队列；全组统计/回放屏障、S初始写入/读写、背压、最后消费均计价。3072元素连续RMS/L2各10479拍、Softmax16707拍。不是集成物理或整模型吞吐证明。

`index.json`封存47原始小文件、实际终态；`verification.json`核验35稳定输出和303源Git blobs/实际receipt输入。`previous-resource-budget.json`保留旧V预算原字节，`budget-comparison.json`记录80候选新预算及选中对照：矩阵/递推/卷积成本保持，只更新实测S/V周期。16M、4V/4S、递推模型6R、context2048下，Phi/Qwen3.5/Falcon已计价部分101.18659/99.027537/94.93499ms，超过假设90ms设备窗口；其他未计价成本仍列出。容量/端口与源SHA据实验证，未授予整模型10token/s或整数质量资格。
