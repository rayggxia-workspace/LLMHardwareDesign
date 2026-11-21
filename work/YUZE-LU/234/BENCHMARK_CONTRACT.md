# 用户确认的比较合同（2026-11-09 CST）

任务：[Issue234](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/234)，进行中；成果草稿PR235。

用户确认主场景 Qwen2.5-3B、B1、输入512 token、生成128 token，补128/2048输入。
**生成速度与每token能耗同时不差于充分优化的FPGA**。用户没有板卡，要求公开benchmark，
板卡实测复现不是前提。约10 token/s是预期量级，不可覆盖实际更强的对照结果。

## 时间、能量与数值边界

- 首token计入TTFT；其后127次缓存decode产生余下127 token。报告127/(最后token时间−首token时间)，
  并另外报告128/整请求时间；不得把额外数值warm-through算成有效生成token。
- SystemC须实际执行事件和资源仲裁，服务延迟来自RTL/接口校准。旧DP makespan换单位、
  CPU墙钟、只跑矩阵乘都不能冒充完整decode。先保留冻结老算法，再逐轮比较。
- decode J/token用相同decode区间积分；整请求J/token另报。idle/时钟/控制/SRAM/互联/DDR
  逐项记账，M宏增量不能代表系统。论文板级能量和芯片估计分栏；不以TDP当平均功率。
- 精度/权重/量化质量须记录。精确打包、降低精度、增加硬件、DP搜索各自消融；配方优化
  不能计入用户所指的DP算法20%收益。保留失败轮次，硬件归因充分后另开关联PR。

## 公开对照

原始来源、抓取时间、SHA、数值及限制见 [结构化记录](public-benchmarks-001.json)。
所有数值均是来源原始配置，没有按参数量或带宽线性换算成Qwen性能。

| 对照 | 完整模型与生成速度 | 能耗 | 使用边界 |
|---|---|---|---|
| openTPU 原生生产配置 | SmolLM3-3B fp4/int8 head，8.74设备/8.72墙钟 token/s | 同构建合格功率未找到 | P512/D64，DDR3 17.1GB/s；保留原生优化，不关可选指令。 |
| openTPU | Phi-4-mini 3.8B fp4，6.56/6.55 token/s | 同上 | 不能把较慢模型作为唯一FPGA门槛。 |
| RaiderChip 引用独立测试 | Llama3.2-3B Q4，37.87 token/s | 1.50 token/J≈0.667 J/token | 1024-token prediction；论文系统输入端能量，和P512/D128不直接等同。 |
| RaiderChip 另一官方表 | Llama3.2-3B Q4，41.47 token/s | 1.64 token/J≈0.610 J/token | 与上行是不同结果；具体场景/边界仍待核实，不拼接两表。 |
| U280 作者测试 | Llama3.2-3B Q4_K_M，92.7 token/s | 未公开 | 空KV的tg128，均值五轮；私有后端，不宣称已复现。 |
| EdgeCIM ASIC 架构估计 | SmolLM3-3B INT4，148.7 token/s | 约72.5 token/J≈0.0138 J/token | P128/D128、65nm CIM及16通道LPDDR5X；不是整芯片实测。 |

[openTPU](https://github.com/FeSens/openTPU/tree/91df41092f612361c5bc22f83b31d23382ffabb0)
· [RaiderChip](https://raiderchip.ai/technology/genai-npu)
· [独立测试论文](https://arxiv.org/pdf/2511.22334)
· [U280测试](https://zedongpeng.com/blog/2026/llama-cpp-on-an-fpga/)
· [EdgeCIM](https://arxiv.org/html/2604.11512v1)。

TeLLMe v2的25 token/s对应0.73B BitNet，不作为3–4B门槛。
llaccel目前核对到的公开证据缺完整3B频率/能耗，不能用3ns约束冒充达成频率。

## 如何判定

同时保留公开跨模型/跨资源比较，以及同Qwen checkpoint的原生适配实验。
前者能说明差距和目标，但不能冒充同工作负载胜出；后者仍需完整权重质量、周期、频率和能量。
不得为让接受检查通过而伪填共同checkpoint、相同token或已校准能耗字段。
强FPGA结果必须展示，数据缺项明确保留；“接近10”不是统一通关线。
对照缺项不妨碍继续本方SystemC校准与改进，但当前不得宣称达标。

## 当前仍缺

真实KV整数程序/状态输入、SystemC全组件服务与争用校准、完整能耗、与对照一致的比较场景。
单节点继续按6×10或8×12调度；排队不等于实验已经执行。任务保持in_progress。
