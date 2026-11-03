# L4-QUALITY首切片：官方FP32参考与W8真实数据RTL回归

Issue151 / PR152，Melodydt，2026-11-03 Asia/Shanghai。输入77b47e389a0aa3f6d775ea00b7870e9c7c4a573e，实跑源码 **b18e8a5fd6f678fd3d395bedf3ff1cb5320bb737**。**95979 / zenanyan-quality / node1 / c64 / 8CPU / COMPLETED 0:0 / 00:02:55**，28项官方框架阶段对照、8真实数据fixture×7严格CASE、8份9437184B实际权重流SHA通过。本轮不改任何既有RTL/TB/include，原54份及全部旧source-lock保持。

## 1. 解决什么问题

之前的[真实Qwen数值报告](QWEN_LAYER0_NUMERIC_RTL_REPORT.md)用独立C++生成FP32 Attention→Y，再量化F(Y)。它没有实际运行官方框架对照，W8也只有软件诊断而没有RTL。另一方面，[完整AF1024](W4_AF1024_IMPLEMENTATION.md)已贯通整数A→双行F，但只用synthetic数据。这两条证据不能合并成trained整数AF质量已经通过。

本轮新增四个软件文件：[数值wrapper](../work/Melodydt/151/quality/quality_numeric.cpp)、[官方框架比较](../work/Melodydt/151/quality/framework_compare.py)、[独立整数检查](../work/Melodydt/151/quality/check_quality_expectations.py)、[服务器运行器](../work/Melodydt/151/quality/run_quality_job.py)，以及[运行前冻结合同](../work/Melodydt/151/quality/quality-contract.json)和[24个CPU wheel版本/SHA锁](../work/Melodydt/151/quality/python-wheels-lock.json)。wrapper包含原不可变qnum数学源，新增完整阶段导出及固定baseline/W8；不改旧引擎或旧资料。

## 2. 输入、阈值与选择纪律

固定官方Qwen3-0.6B revision c1899de289a04d12100db370d81485cdf75e47ca，复用本人服务器已验证的11个layer0张量和14个embedding行。BF16逐标量展开为FP32并再次核验原始与转换文件SHA；完整1.5GB checkpoint仅有官方expected SHA，仍未完整下载或实算。数据目录沿用旧data01只读，不覆盖；新源码/输出分别在input-r02/runs/r02。

4个前缀分别为cal_text_0/cal_math_0/eval_text_0/eval_math_0，各4个明确vocab-piece token，共16个token位置。原cal/eval名称仅为来源标签：旧eval已公开并影响讨论，**本轮只作已观察回归，不再称未见holdout或代表性语料**，也不声称执行过BPE/chat模板。每split8192最终输出元素不是8192个独立样本。

运行前固定两种profile，不进行cal排序或根据新eval调阈值。官方参考一致性的每case/每stage两门为max绝对误差≤5e-4且relative L2≤5e-5，目的仅是容纳独立顺序FP32归约与官方CPU FP32矩阵归约的差别。此容差不是量化模型的产品误差阈值。整数门为导出值/RTL实际值一致、真实流SHA一致、参数和gamma离线clip为0。

## 3. 官方框架参考实际如何核验

隔离安装Torch2.6.0+cpu、Transformers4.51.0、NumPy2.2.6；只在本人任务environment/deps，未修改系统Python。24个wheel大小/SHA及221552640B转移包SHA均核对，实际安装回执与日志保留。通过官方Qwen3Config/Qwen3DecoderLayer/Qwen3RotaryEmbedding严格加载11个权重，仅实例化layer0，CPU FP32/eager/eval/no-cache，显式因果mask与位置0..3，线程最多8，不借完整模型运行作证明。

官方modeling_qwen3.py SHA704c914530530a1acb0b443add1f520404e3ac2c28c0ab7e16f80f86cfe8ccb2，Git blob5fec83d47888e44a0f3e0ffb2b067ce08e4712d3，和[官方v4.51.0实现](https://github.com/huggingface/transformers/blob/v4.51.0/src/transformers/models/qwen3/modeling_qwen3.py)相等；未用本地重写公式冒充官方框架。hook捕获Attention残差Y、F norm/gate/up/mid/down及最终Z，4case×7stage全部完整元素对照。两参考都用源epsilon1e-6，量化路径epsilon_code1的近似误差另计。

| 阶段 | 四case最大maxAbs | 四case最大relative L2 |
|---|---:|---:|
| Y | 7.86781311e-06 | 1.67641115e-06 |
| norm | 1.09672546e-05 | 1.35217365e-06 |
| gate | 1.04904175e-05 | 1.16982991e-06 |
| up | 5.48362732e-06 | 1.56171934e-06 |
| mid | 7.04824924e-06 | 2.17437541e-06 |
| down | 4.88758087e-06 | 2.24108839e-06 |
| Z | 8.82148743e-06 | 1.68356179e-06 |

28项均满足预声明门；跨所有stage最大maxAbs **1.09672546387e-05**，最大relative L2 **2.24108838742e-06**。这些是参考实现一致性，不是整数F的量化误差。不同归约没有被宣称逐bit相同。官方trace二进制留服务器，Git保留逐文件SHA及完整比较原文。

## 4. W8改了什么，为什么端口不变

这里W8表示S8权重的小数位Fin=8，不是改为新的8bit端口。baseline为WFin7、READ7；W8为WFin8、READ8。离线Wq=clipS8(RNE(w×2^WFin))；原M执行完整K的S16×S8累加，最后READ一次RNE右移WFin得到Fin10输出。保持X/gamma/Norm/gate/up/mid/down/Z的S16 Fin10、G Fin10和N epsilon码1，因而输入输出位宽、原S/T布局、job/version和握手完全相同。三个完整权重矩阵安全Fin显式验证均为8，全部量化码独立检查，无参数clip。

**RTL源码零改动**。复用既有block_w4_qnum_top及TB，通过两次独立编译静态-G绑定N_EPSILON=1、M_GATE_SHIFT/M_UP_SHIFT/M_DOWN_SHIFT=7或8；权重内容也相应量化，不能只改version而不绑定尺度。没有运行时装载新程序、增加bridge宏或任何新的有源存储。F核仍M1/N1/E1/G1/S1/T1，S预约14912B、T预约2048B；这次是独立F静态profile验证，**AF1024父控仍为原baseline，未被改成W8产品控制**。Fin12/W9仍不能裸接Fin10父控。

## 5. 独立整数与真实RTL结果

固定两profile各4个旧前缀末位置pos3，共8条完整H1024/I3072 F行。独立Python完整核18,874,368个baseline/W8参数码、8192个N输出、24576个G输出和8192个E输出，另抽192个不分chunk的full-K M点积。C++与Python分别构造9MiB请求序流，先保留C++流再比较重排SHA；不以DUT输出制造golden，也不把抽样M写成全部原始累加器证明。

原TB逐实际S写核所有Norm/gate/up/mid/down/output和元数据，验证256输入最后真实ACK、完整计数、权重请求保持、输出背压、T实际RELEASE及held DONE/abort+ready只消费一次。8行×7CASE严格顺序，共56标记；每行9437184B真实accepted参数流SHA相等，总72MiB。每行S888076次请求/ACK、M40448命令/36864 EXEC、N258命令、G384服务/1536pair、E128服务、host128字及T一次释放；这些有限计数不当系统PPA或吞吐。

| profile（每profile4份actual流相同SHA） | 实际9MiB流SHA256 |
|---|---|
| current_Fin10_WFin7 | 49345f8375ff31be9efeba69a4a19251ae042656e261f6d67f994ed346f39ab1 |
| matrix_safe_x10_n10 | b3b42af5749f88bb0f22fdca5a7b9c7a65ae802c828695e30da4cfcbb6964d62 |

旧eval标签上的输出指标重算如下，只作回归诊断：

| 固定profile | RMSE | relative L2 | max绝对误差 | 参数/gamma clip |
|---|---:|---:|---:|---:|
| current_Fin10_WFin7 | 0.0147745643 | 5.824722% | 0.096906662 | 0 |
| matrix_safe_x10_n10 | 0.00746165691 | 2.941682% | 0.0386241525 | 0 |

W8在这批旧输入上平均与最大误差均降低，输出clip为0；并不据此确定产品profile、放宽其它模型准入或证明完整整数A误差。W9原82权重clip与取舍仍按旧报告保留。

## 6. 尝试、来源与证据

准备源1f391174未部署/无job；随后只修正runner允许已授权只读共享SIF固定路径并核实际SHA，形成首实跑源b551693f。r01/95978在node1自然FAILED1:0/00:00:08：包已包含wheel锁，合同的精确依赖闭包却漏列，数值/框架/RTL均未开始。保留全部现场。r02只在合同reference_dependencies补列wheel锁，强等式检查保留，另加本地闭包一致性预检；算术、容差、RTL和CASE不变，实跑源b18e8a5fd6f678fd3d395bedf3ff1cb5320bb737完成全部门，不将首轮改写为成功。

28运行输入Git blob/服务器SHA一致，r02的55份数据输入、206份生成输入和246份输出均索引并在导出重核；两次运行共56次源出现、54份轻量原文逐SHA核验，8份actual流重核。归档SHA9b0fe61ba3ad54459ac812d67101b4c96f5f304b8de05be463f4572e52f2fd1d。原始权重、hex、binary、框架trace、wheel与build只留本人服务器；Git仅轻量JSON/TSV/log/receipt。[实跑回执](../work/Melodydt/151/quality/evidence/runs/r02/results/run-receipt.json)、[框架原文](../work/Melodydt/151/quality/evidence/runs/r02/framework/framework-summary.json)、[证据索引](../work/Melodydt/151/quality/evidence/evidence-manifest.json)、[最终检查](../work/Melodydt/151/quality/final-checks.json)。

Verilator5.042/g++11.4.0/Python3.10.12，实际容器c742bf99…，全部argv与工具版本在receipt；--assert启用、单线程仿真、-j8构建，仅-Wno-fatal。两编译各35warnings，合70条保留，非lintclean。旧RTL全回归、完整模型推理/困惑度、BF16逐bit、trained整数A→F质量及EDA未执行；旧24GAP与54源/历史锁保持。

## 7. 交付与下一步

当前仍主线四；本轮完成的是L4-QUALITY中的参考核验和W8有限回归，不是整个L4退出。下一 **L4-QUALITY-AF**：建立真实训练参数驱动的完整Sq2整数A→两行F oracle，按FP32完整AF、整数A→FP32 F、FP32 A→整数F、完整整数AF分解误差；保持Q/K RoPE配对轴与自然轴显式映射，不复用仅对synthetic period251有效的点积优化。代表性新cal/holdout、独立产品误差/clip阈值与变体准入须在新结果前冻结，旧eval不复称未见数据。

用户要求每步完成后覆盖同一现有交流PDF，本轮已同名覆盖10页、14links、逐页视觉QA；SHA7d00cf632e252f12d089ed63a22dc6a823ee513a548bab4b38c4e7f1fc10cbe8，索引见[local-PDF-index](../work/Melodydt/151/quality/local-PDF-index.json)。不新建版本、不推PDF或发送他人。PR152待外部审查未合并，Issue交付回in_review/非done；登记PR5 pending，看板unverified/同步pending，处理人待指定。L5母控/通用storedACK、D/H与MoE、真实MEM及M11/M12物理仍分别退出。
