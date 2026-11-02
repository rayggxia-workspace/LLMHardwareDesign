# C/D 并行推理实验

Issue #153 / PR #154。该目录与 `llm/` 平行，保留此前程序和证据。用户授权本次SystemC实验继续覆盖R；不因此修改RTL或生产选择。

## 阶段1实现

复用PR146的 `control::C`、`DModule`、描述符和地址/信用规划，新增 `payload.hpp` 执行真实载荷运输。每次把至多16KiB输入放进固定32KiB外存窗口，C执行五条可装载指令：SUBMIT LOAD、WAIT、SUBMIT STORE、WAIT、END。两个描述符共用排他租约；完成必须经D返回。D发出的每个burst逐128bit字调用原 `SEngine` 写入或读出，响应成功后才ACK并释放规划信用。输入输出逐字节核对；一个Tensor超过S容量时分窗，未扩容S。

资源：16KiB S、32KiB模型外存暂存窗、两项任务/完成/描述符/burst/ACK FIFO；D规划至多两项突发/32字保留信用。payload worker串行服务burst，不能据此宣称RTL两读两写并发。1ns字服务与2ns确认只是实验假设。

`run.py`只在新的输出目录复制原始 `llm` 和宏头文件，读入指定control源，生成并行程序 `llm_cd_bench`。仅生成副本的TensorLink exchange改接C/D载荷通路，旧 `llm/` 文件不改。原Tensor序列化与数值算术复用，R算术仍在原推理程序中执行，不受C端点禁用影响。

当前接入点仍是外层Tensor边界：静态权重、原始KV/R状态和计算命令调度尚由原host路径承担；C只控制这里的LOAD/STORE，不能称已接管七模型全程序。此阶段用于验证C/D有实际数据运输，而不是只有地址和虚假ACK。后续需把宏命令适配器、权重与状态访问逐项纳入，保留数值门。

## 复现

在具备SystemC3.0.1/GCC10.3/CMake的环境执行：

```bash
python3 project/systemc/llm_cd/run.py \
 --control-root /path/to/issue-145-systemc \
 --systemc-prefix /path/to/systemc/install --out /new/empty/output --save-evidence /persistent/new/results
```

该命令构建真实SystemC并运行载荷竞争/分窗测试和原llm数值selftest，使用-Werror与UBSan。`receipt.json`记录输入SHA、实际日志和结果；生成程序也可以按原 `llm_bench CHECKPOINT OUTPUT` 调用。七真实模型完整九位置的冻结门需单独重跑，不能从selftest推导通过。

持续记录见 [EXPERIMENT_LOG.md](EXPERIMENT_LOG.md)。本阶段不进行RTL/综合/P&R，不使用物理面积、M11/M12或芯片tokens/s结论。


阶段1最终phase06：2/2 CTest通过。载荷测试27窗口/18570字/1194突发，C提交/完成54/54；原数值selftest实际经过C/D，479窗口/42632字/3504突发，C提交/完成958/958。-Werror与UBSan通过，完整日志见results/phase1/LastTest.log。以cd-payload.json和C/D计数为准，副本保留的旧TensorLink计数不表示新通路性能。
