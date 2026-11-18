# GDN 与 Mamba 状态更新的第一轮标定

2026-11-18，Melodydt，关联 #280 / PR #281。结果在本地独立目录。目标是验证能耗 v3 中两个递推代理的候选实现；当前阶段与服务器作业见 [本轮交接](DELIVERY.md)。

从 BSCC 的 `~/LLMHardware/zenanyan/issue-280-bscc-t6-01/operator-capture-02` 取回 `run-38830192`（Qwen3.5）和 `run-38830193`（Falcon）的 prefill、decode 两份 operator-observation.json，逐份对服务器清单和固定 SHA-256。原始数据在本地 tmp/recurrent-step1，模型文件名和散列见 replay.py。

每模型取两个短 prefill 块、两个首步 decode 块和两个第二步 decode 块。先用冻结浮点表达式独立复算捕获输出，再核对前一 token 的 Q16 写回与下一 token 的实际输入状态完全相等。每个 16 通道块拆成两批八路，第二步直接使用 COMMIT 后保留的状态。仿真经 LOAD、EXEC、READ_OUT、COMMIT、READ_STATE 的正常接口核对每个输出及所有状态元素，对照按候选格式独立计算的定点期望。每个候选 12 次 EXEC。

| 候选 | 命令数 | 输出最大差 / Q16 LSB | 平均绝对输出差 / Q16 LSB | 状态最大差 / Q16 LSB |
|---|---:|---:|---:|---:|
| Qwen3.5 原 R，S16/Q14 key、query | 5,596 | 1 | 0.0104 | 2 |
| Falcon，S16/Q11，修正 SSM 的更新及读出移位 | 17,292 | 625 | 31.4583 | 33 |
| Falcon，S32/Q24，四系数一拍载入，72 位点积累加 | 18,060 | 53 | 12.6250 | 12 |

三项 ModelSim 2020.4 回放对各自定点参考逐字一致。表中差异相对于冻结 TLM 的 Q16 状态及舍入到 Q16 的输出。Falcon 的 delta×value 入口使用 Q16×Q16 后 RNE，由测试驱动预计算并载入 inject；该入口的实际硬件、系数转换与端到端精度仍需验证。测试时钟周期 5 ns，计数包含测试读回；无时序或功耗签核。与冻结结果的剩余差异没有预设可接受容差。不得据此替换 v3 区间。

可在仓库根目录运行以下命令。基础 R 取自 #242 的确定版本，文件 SHA 在驱动中固定。宽系数候选仅用于独立 SSM 验证。源文件、命令向量散列、工具版本及各窗口的结果见三个 receipt.json。

```powershell
python -B work/Melodydt/280/recurrent-step1/replay.py qwen35
python -B work/Melodydt/280/recurrent-step1/replay.py falcon
python -B work/Melodydt/280/recurrent-step1/replay.py falcon --wide-ssm
```

后续已加入 32 步交替捕获输入的状态压力测试、Falcon 注入／舍入来源诊断，并提交两模型综合及其依赖门级功耗作业。压力序列不是新的真实模型长序列；独立层、真实后继输入和模型级精度仍未验收。具体结果、作业追踪及交付状态见 [本轮交接](DELIVERY.md)。

## 本轮复现入口

最终采用的门级目录及作业以 `fast-jobs.json` 为准。`power-full` 生成完整引脚追踪；`power-trace-opt` 将相同生成代码的 Trace 函数编译为 -O1；若标为 `opt_stage: logic`，还将 FAST 门级计算函数编译为 -O1。各路线只有在全程数值回放、原生引脚覆盖、全部配对功耗及波形前缀一致性通过后才能选用。后面的构建描述同时保留历史尝试，不能仅凭某个历史脚本名判断最终结果来源。

`replay.py qwen35 --stress-steps 32` 和 `replay.py falcon --wide-ssm --stress-steps 32` 执行连续压力测试；`diagnose_rounding.py` 生成仅 Python 侧的舍入诊断。

数值回放沿用本机 `D:/EDA/modeltech64_2020.4/win64` 的 ModelSim 2020.4；跨主机需配置实际工具路径并重记驱动/工具散列。结果包的模型积分和独立核验仅依赖 Python 标准库，不依赖 ModelSim。门级大网表、工具镜像和完整波形保留在指定服务器，通过清单 SHA 复核。

分别运行 `replay.py qwen35 --calibration` 与 `replay.py falcon --wide-ssm --calibration`，生成六样本、十二批八路的 `commands.txt` 和 `segments.json`。`validate_calibration_tb.py` 用本机 ModelSim 检查功耗测试台的逐字读回及等长活跃／静默窗口，Qwen3.5 每批 1080 周期，Falcon 2456 周期，均为 5 ns 时钟。该预检不代表门级功耗结果。

服务器采用已通过映射检查的 `run_fast_calibration.sbatch`，再以 `afterok` 执行 `run_gate_power.sbatch`，每项 12 核且无限时。原 `run_calibration.sbatch` 在存储共享后的清理阶段耗时较长，相关作业已被同 RTL 的直接存储映射流程替代，原记录保留。门级活动检查点记录网表、单元模型、命令、测试台和 VCD 的 SHA；只在相同输入和波形时复用。取得 `calibration.json` 后，`rollup_candidate.py` 生成候选情景，`build_delivery_pdf.py` 输出双口径报告。系统基线为 R3 的 200 MHz 算术 v3；候选不自动替换正式七模型小计。

编译加速试点在 `power-clang/` 运行 `run_clang_gate_power.sbatch`。`compile_low.py` 复用相邻 `power-split/obj_dir/` 中已完成的 Verilator 生成代码，逐文件核对散列，用独立 Clang 14 / C++20 / -O0 构建并记录二进制 SHA；随后仍逐字核验所有输出与状态。原 GCC 大分组、GCC 分拆和 GCC -O0 尝试保留日志及终态；不能将它们等同于最终成功结果。独立编译器仅安装在服务器 `opt/eda/clang14-mdt-20261118`，官方包 URL 与散列见 `compiler-install.json`。

活动覆盖修正后以 `power-full/` / `run_full_gate_power.sbatch` 为选用路线：`generate_gate.py` 显式开启 `--trace-underscore`、在 `obj_generated/` 生成完整内部信号追踪，再用 Clang 构建。前述 `power-clang` 默认隐藏综合内部网络，仅保留作编译/数值对照，不作功耗依据。功耗脚本解析真实 VCD 层级而不假定存在 `TOP`，并检查至少十万个下划线内部网络；实际标注覆盖还需逐窗审核。最终作业号和终态以 `fast-jobs.json` 及 `job-final-status.txt` 为准。

最终后处理入口为 `run_final_power.sbatch` / `calibrate_final.py`，依赖成功的引脚图预检与门级回放检查点。当前 OpenSTA 的微型预检对内部网线名标注 0、对两个共享波形 ID 的明确单元引脚名标注 2。完整 VCD 已原生包含单元引脚名，`map_vcd_pins.py` 按精确结构网表连接图逐项核验引脚和初始值，完整时直接使用原始 VCD；缺少原生引脚层级时才启用位连接别名转换。实际路径由 `pins.json` 记录。标注目标分别为 Qwen 4,004,878、Falcon 4,125,979，包含全部已连接单元引脚与顶层端口位，逐窗要求完全相等。波形、图与检查脚本均记录 SHA；图和大波形留在服务器。`verify_pin_mapper.py` 已验证原生覆盖、缺初值拒绝、标量、向量、常量、共享 ID、时间戳与缓存输入不匹配拒绝。120390 短前缀预检独立于正式配对窗口，其数值不进入模型积分。


## 公开副本说明

本次公开版将八份数值回执中的完整商业仿真器原始日志留在本地，仅保留项目自身的数值、窗口计数、PASS 摘要和原件 SHA。原始回执未修改；公开副本新增 public_export 来源说明，并独立重算输入散列，所有模型数值与完整本地包逐字一致。详见 public-export.json。

公开 checkout 可运行 rollup_candidate.py 和 verify_candidate.py 复算模型积分。validate_delivery.py 检查完整本地回收包，包含未公开的构建日志，不作为公开 checkout 的检查入口。原始捕获 ZIP 与大网表/VCD 不在公开交付范围；复跑 RTL 仍需获授权输入和工具。
