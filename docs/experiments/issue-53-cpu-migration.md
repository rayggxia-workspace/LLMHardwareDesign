# Issue53：CPU服务器模型迁移与线程pilot

2026-10-23，Asia/Shanghai。负责人Liangruizhi；[Issue53](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/53)、
[PR54](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/54)，task/53-cpu-model-pilot，base PR52。
正式推理源码70c0157e348dc4bc1b3792fdb12ee3d78a342a57。不是W8A8/INT8、模型质量或目标Block性能结果。

## 环境和固定输入

默认Python3.6不代表没有现代环境：本轮查到系统3.11.7和既有/public/home/yuzelu/python-3.12/bin/python3.12（3.12.7）。
只借用既有解释器，在本人/public/home/yuzelu/RuizhiLiang/issue53-cpu-pilot-20261023/建立独立venv，未修改共享安装。
node27，Xeon Platinum8488C，约503.53GiB物理RAM；Slurm把RealMemory配置为1MiB，不能声称内存已被调度器预留。
只申请32CPU，记录affinity与进程RSS，不称整节点独占。CPU flags不证明AMX内核实际被使用。

服务器无法连download.pytorch.org（连接超时），从本机D盘下载Linux CPU wheel并SCP至本人目录。
torch2.10.0+cpu、transformers4.57.6、NumPy2.2.6；完整离线安装报告、pip check/freeze、wheel SHA均归档。
跨平台pip解析漏掉Linux的hf-xet条件依赖，89940失败后显式补hf-xet1.2.0；89942安装/导入/pip check通过。
只取消了自己未运行且DependencyNeverSatisfied的89941，再提交89943。原失败/调度回执保留。

复用本机已有Qwen/Qwen3-0.6B@c1899de289a04d12100db370d81485cdf75e47ca，原8个文件全部核对Issue23固定SHA。
权重1,503,300,328B，SHA256 f47f71177f32bcd101b7573ec9171e6a57f4f4d31148d38e382306f42996874b。
没有新下载模型或3B以上权重。离线传输包1,754,604,918B，SHA256
f53428713dbf71cfc8546447cf3a513caff40783ed96cf35dd214703dd972716；补充hf-xet wheel SHA256
3651fd5bfe0281951b988c0facbe726aa5e347b103a675f49a3fa8144c7968fd。
模型/wheel本体不进Git；服务器位置和manifest保留，可供后续本人作业复用，未当作全团队模型存储已配置。

固定528个teacher-forced token为原systems文本重复截取，不是自然语言/数学/代码质量集。
inputs.json SHA256 f158411222fefa3935fb197eeb0c6a0b738e84857c65c2b892db01777c906a54。
运行输入包SHA256 8d4b03ab2f94a99eeab090dd00916bc06f679a739148c84394af76f1996f1b5a。

## 冻结协议

8/16/32线程×FP32/BF16，共6条件。每个条件单独进程，eager attention、deterministic algorithms、interop1。
同一模型job内顺序执行，以免模型进程互相抢核；与此同时独立RTL作业89944/89946在服务器并行。
线程顺序未随机化、无绑NUMA实验，三次样本不是可靠的扩展到96核性能预测。

每条件full136、128+8 cached与32token chunk，检查28层完整KV及logits。
FP32 atol/rtol各1e-4；BF16事前2%相对RMSE为迁移pilot门，不是应用质量预算；同时报告严格FP32门与argmax。
性能只计无观察器forward：128/512 prefill、各16个固定token decode，一轮热身/三轮样本，加载/校验不计。
生成采样、tokenizer/host、文件转存、INT8内核、长上下文、其他模型及目标硬件未测。

## 首轮实际结果

89943自然COMPLETED0:0，32CPU、1分48秒。注意作业退出0只说明程序完成，6条件不等于6个数值门全部通过。

| FP32线程 | prefill128 token/s | prefill512 token/s | decode接128 token/s | decode接512 token/s |
| --- | ---: | ---: | ---: | ---: |
| 8 | 687.28 | 794.87 | 29.24 | 25.20 |
| 16 | 1093.94 | 1296.97 | 40.85 | 35.93 |
| 32 | 1226.44 | 1696.88 | 42.37 | 39.49 |

这只是当前小模型、当前后端、共享节点上的三次样本中位数；不能按参数量或核数线性外推大模型耗时。
FP32三条件全部通过，logits最大绝对差约2.96e-5至5.25e-5，KV/logits最大相对RMSE约3.06e-6。
进程lifetime ru_maxrss约4.47–4.69GiB，包含加载/正确性和计时；不是逐阶段RAM或Slurm内存预留。

BF16的8/16线程各有17项超pilot门；chunk logits相对RMSE0.0204509、最大绝对差0.53125，
chunk logits argmax一致率约98.5294%；全指标最大相对RMSE0.0327083。32线程首轮全部相等。
记录不足以定位是哪个内核/归约路径引起，不能仅凭CPU flags解释，也不能因32线程成功泛化所有形状。
失败条件原始计时留档作诊断，不参加可接受配置的性能获益排序，不放宽事前阈值。
主线CPU参考优先FP32；BF16仍有线程/形状边界。因这一新疑点，89945另作同源码/同token独立重复。

89945也自然COMPLETED0:0（1分27秒），数值门及所有保存的cached/chunk标量逐条件重现。
重复的512-token FP32 prefill吞吐为819.94/1104.45/1316.39 token/s，decode为26.02/36.49/38.15 token/s。
两轮32线程FP32的512-token prefill为1316–1697 token/s、decode为38.15–39.49 token/s；
这是共享节点、eager后端的观测区间，不以较快一次替代重复波动。BF16两个失败和32线程相等均再次出现，
没有据此降低门槛或取消FP32参考。重复launcher唯一改动是输出run01→run02，实际脚本和SHA留档。
重复回传35成员、125,521B，SHA256 1099336204416a1ba2c1e4ba28c2bf304c8e64298d41ded541e1c8fb047a490e，下载逐项核对。

## 审计与适用范围

首轮原始回传46个成员，253,914B，SHA256 8385a8d321604854b3742cf8abce24f73edbfafded371baf99aff24a62be11e5，
下载后逐成员核SHA。audit.py独立核源码/token绑定、28层shape、门判断、全部逐token计时和中位数；
它只审计保存标量，未保存/独立重算全量logits，不能称第二套数值内核。token、KV shape、吞吐篡改3负例均拒绝。
正式代码[README](../../project/experiments/cpu_pilot/README.md)，重复和最终包见交接/索引。

正式[归档索引](../../project/experiments/cpu_pilot/results/issue-53-run01/index.json)包含104成员，evidence.zip=746,176B，
SHA256 19c24995d01d3acafc0365311b74a2f6f83e56aa9712389f616e57f55fed1627。
已核包、安全解压新D盘目录并对两轮再次执行audit.py；24组保存数值字段跨轮比较无差异。

## 哪些师兄任务可以迁CPU

- 可以承载：固定版本浮点参考、算子/形状/布局和代表层张量采集、cached/chunk状态一致性、整数oracle/量化误差、
  划分与端口仿真。当前已证明的是Qwen3-0.6B FP32短上下文迁移，不是所有模型已跑通。
- Qwen2.5/Qwen3.5已有PR36进度先复用，不重下/重跑。Qwen3.5、Gemma窗口和Phi等须逐架构核现代后端、算术/状态合同、
  许可与模型输入、RAM、短pilot；长上下文只按实际峰值和时间扩大，不能由96核与总RAM担保完成。
- 12B高精度在RAM层面有探索空间；4bit GPU加载格式/内核不默认CPU可用。CPU 4bit若换后端，另立格式和语义条件。
- GPU吞吐/显存、真实GPU INT8/4bit内核及对应浮点回退必须保留GPU；CPU时间不代替目标Block周期/PPA。

兄方数值包仍按用户通知后再下载核验整合。本轮只读取其Issue/PR/进度，未接管或重跑已交付批次。
E2b完整attention和E3递推公平端口配对仍未由本次CPU迁移pilot解决；E4/冻结后E5保持原证据边界。
