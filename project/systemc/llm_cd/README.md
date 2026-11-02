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

## 与 Issue162 / PR163 的关系

这里复用 PR146 的 SystemC `control::C` / `DModule` 及 256bit 描述符 ABI，是功能级接入实验，不另设计一套 RTL DMA。只读核对 Issue162 的 `CONTROL_V1.md`：其 C 指令/描述符编码与同一参考模型一致，但真实 D 已有 AXI 读写通道、S 确认、各两项在途及错误排空；当前 SystemC payload 的串行 burst 服务不能冒充该 RTL 的逐周期模型，也不能替代 PR163 的验证。

| 职责 | 本实验实际归属 |
|---|---|
| 五条可装载指令、任务/完成槽、排他租约 | 复用 SystemC C，每窗口重装程序 |
| 描述符、burst、保留信用及 ACK 后完成 | 复用 SystemC DModule/DmaPlanner |
| 16KiB 工作存储 | 原 SEngine，按真实命令读写 |
| 32KiB 外存暂存窗口、burst 载荷服务、窗口互斥 | 新 Payload；不是 DDR/HBM 控制器 |
| Tensor 序列化/反序列化、分窗、重装 C 程序 | host 服务，仍有完整 Tensor 向量 |
| 宏算术命令、尺度、静态权重、KV/R 原始状态、专家寻址、T 生命周期 | 原推理程序/原宏模型；未交给新 C/D 控制 |

外层输入会实际完成往返并逐字节核对，随后原算术继续使用相同 Tensor；外层输出使用桥重建的 Tensor。不能称已由 C 驱动全部计算宏或已禁止 host 旁路。当前只验证成功搬运和有限信用回收，未新增 AXI 错误排空、运行中复位或双 S 并发验收。后续若要和 PR163 对接，应复用其已定接口、将计算适配器/权重/状态逐项接入，不能从此轮数值通过推断这些合同已通过。

## 七模型执行入口

`remote_suite.sbatch` 使用独立输出目录，六个单线程模型任务动态补位，完成后继续运行独立参考验证及原冻结数值门。服务器 GCC8 缺少 UBSan runtime 时使用显式 `--no-sanitize` Release；本地 UBSan 仍需单独通过。生成 control 副本仅为 completion accessor 添加 noinline，以避开 GCC8 对空 optional 的误诊；上游不改，-Werror 不关闭。

`collect_remote.py ROOT --job JOBID` 只在七模型全部通过且 Slurm COMPLETED/0:0 后封存证据，逐文件重算实际输出 SHA，并补齐 prompt、二进制参考、全部编译源及程序绑定；大数据保留在授权服务器。该封存计算也应在本任务独立 Slurm 资源内执行。最终七模型结果与失败保留见 EXPERIMENT_LOG.md 及 results。


## 本轮最终结果

新C/D程序七真实模型各九位置全部通过原冻结数值门，63/63 Top1且独立greedy一致。C提交/完成3,120,438/3,120,438；95069完整运行、95083封存审计、本地原始数值及编译源复核全部通过。详细指标见EXPERIMENT_LOG.md，原始证据入口为results/seven-cd-03/index.json。前述“尚未重跑”是阶段1历史状态，现已完成重跑；主机职责限制保持如上。复核：`python project/systemc/llm_cd/verify_evidence.py project/systemc/llm_cd/results/seven-cd-03`。

源绑定范围说明：sealed-index 的 compiled_source_files/source-audit 的 compiled_files 是构建目录源文件清单，共24份，包含未参加本次编译的 gdn_bench.cpp 和 link_test.cpp；可执行目标仅 cd_payload_test 与 llm_cd_bench，不把目录文件数当作实际编译单元数。
