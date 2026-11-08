# Issue234：Qwen3B SystemC 时间、能量与充分优化对照

2026-11-09 CST，YUZE-LU，[Issue234](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/234)。
独立分支 task/234-systemc-benchmark，正式提交以已知main c4d7b960为底；老算法从375b8fca0/在线冻结1d284bdc只读核对。
不修改母聊天的算法工作树、活动分支或作业。

任务未完成。不得将已有B1/S2无KV模型代价换算、单宏资格或下面的合成测试宣称为整网SystemC/焦耳验收。
用户要求持续多轮直至达到经核对的FPGA门槛；初始主场景拟Qwen2.5-3B B1、输入512、decode128，补128/2048上下文。
主门槛已异步询问，未收到选择时不把暂定口径说成用户确认；对照用平台原生充分优化配置，不强制退到我方标量布局/数值格式。

## 交付顺序与硬门

1. 冻结旧算法、硬件、权重、任务范围和同前缀数值参考；旧B1/S2保留为回归，补实际带KV编译和生成。
2. 复用#145/#153/#197合法来源：七宏无时钟功能模型不能直接提供周期；时序接入实际叶/局控/DMA校准。
3. SystemC事件推进实际资源、S窗口、队列、信用、存储bank、确认；真实命令/搬运事件与压缩循环具有来源及等价检查。
   不以旧计划的start/end或makespan驱动结果；压缩加速必须保留相互作用，不能删真实通信等待。
4. 命令/存储/互联/时钟/控制/泄漏能量分项；逐一绑定活动、库、PVT与外存器件。未知系数保留缺项，不填零。
5. 以同模型/同输入/质量门比较prefill、TTFT、decode token/s、J/token，能量计入边界和不确定性相同或分列。
   不同checkpoint只作为各自平台事实，不据参数数量相近作通过判定。
6. 每轮分离算法、配方与硬件变化，记录占用/等待/带宽/流量/活动；对照充分搜索tile/量化/并行/流水/驻留参数。
   不能证明全局最优时记录最佳合法配置、搜索预算/收敛，禁止伪称最优。
7. 落后先排仿真误差/映射/软件缺口；只有定位到真实硬件限制并有反事实实验后另开硬件Issue/PR，不覆盖旧验收。

## 已核对的复用来源

- 七宏SystemC：本地Issue145 main整合41af0f188，3.0.1；原模型无时钟，E op13和R控制接入有版本限制。
- #197/#198已有整模型SystemC/行为外存，不能继承尚未校准的全芯片周期/器件能耗。
- 服务器SystemC3.0.1库：`/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153/install/lib64/libsystemc.so.3.0.1`。
- llaccel本地参考服务器commit f7db8a22791a1ce9dc13e7c90b0b9b9386169aa5；其44个Llama/Qwen测试明确是小随机模型，不能冒充预训练3B性能。
- openTPU参考服务器commit f237dab2f196855a59a083b1454786df8f01291f；官方当前README还报告原生优化和3–4B支持，需固定上游版本后复现，不能仅取旧较弱配置。
  官方入口 https://github.com/FeSens/openTPU ，板上监控含功耗/带宽，但当前尚无本任务板卡测量。

## 第一轮基础

`project/experiments/systemc_benchmark/timed_resources.cpp` 使用真实SystemC动态进程，从依赖和资源完成事件求开始时间；
测试串行、并行、端口争用、写确认依赖、fork/join和未知能量。当前资源容量为1，TSV时间ps、已知活动能量nJ；
没有泄漏/时钟/外存器件校准，不能声称总能量。`acceptance.py`独立拒绝缺失能量、不同工作负载或弱化对手造成的伪达标。

远端独立目录 `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-234-systemc-benchmark/`。
probe-001/100664为单节点c64、6×10、60核，因SystemC3.0.1废弃SC_HAS_PROCESS且-Werror而失败；保留日志。
已删除过时API而非关闭-Werror；probe-002/100665因服务器Python3.6不支持capture_output失败，保留原件。
改用等价的stdout/stderr PIPE及universal_newlines，probe-003/100675实际COMPLETED 0:0；六个SystemC基础场景全部通过。
probe-result.json原件已回收，与服务器output.sha256的070253396dd4ad5bbe7b7bb90797d88f8d280cd9dcdf27865286f7b37f0eeae8一致。
本地两个验收门测试通过。合成测试不是Qwen3B/能量结果。

2026-11-09：核对官方README的3–4B板上性能及board.md。不能把旧100MHz构建的低可信度8.75–9.70W功耗估计与新133.33MHz构建的吞吐相乘当J/token。
SmolLM3-3B/ Phi-4-mini板上数字只作对应模型的原生参考；正式门须同checkpoint/输入/质量，不得直接替换成Qwen2.5-3B成绩。
用户已收到主场景/门槛选择与板卡/Vivado/功耗数据路径的异步问题，尚未收到回答；独立准备工作继续。

每轮完整计算使用单节点c96 8×12或c64 6×10，限制工具/BLAS线程；不操作其他任务。
项目结构检查通过。PR未创建，整网仿真/功耗校准/ASIC与FPGA适配/多轮优化均未完成。
登记沿用management-hub PR5 pending；未见board.json，Projects状态unverified/同步pending，待有权限维护者。
