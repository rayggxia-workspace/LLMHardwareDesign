# Issue23：固定真实Qwen3权重的缓存与边界轨迹

2026-10-22，UTC+08:00。负责人Liangruizhi，[Issue23](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/23)。这是第一个完整实际权重的推理正确性/状态轨迹案例，不是最终跨架构benchmark、生成质量或目标芯片性能评测。

## 固定输入与实际执行

正式源码commit `d63bc2d37a5f1457a4a170b17afba343fb54998d`，两次运行开始/结束均核对源码清洁、commit和文件SHA不变。官方模型Qwen/Qwen3-0.6B固定revision `c1899de289a04d12100db370d81485cdf75e47ca`；8个模型/配置/分词器/许可文件逐项绑定SHA和字节数，运行后再次核验。权重1503300328bytes，SHA `f47f71177f32bcd101b7573ec9171e6a57f4f4d31148d38e382306f42996874b`。

本机D盘隔离CPython3.13.14、torch2.10.0+cpu、transformers4.57.6、NumPy2.5.4；CPU FP32/eager，4线程，interop1，eval/inference_mode、确定性算法。25个runtime wheel源SHA与锁定安装、pip check/原生类导入均验证；未用GPU或服务器。原生模型实际独立参数596049920，state_dict元素751632384；embedding与LM head实际共享storage。不得把模型名0.6B直接用作序列化权重大小。

固定自拟文本、无特殊token/chat template、teacher-forced；输入IDs及SHA随结果保存。比较32-token一次prefill+16次decode、16+16分块prefill+相同16次decode，与每一步独立完整prefix计算；另以96+8（48+48分块）确认长度变化。没有将argmax反馈成下一输入。`logits_to_keep=1`只投影末token logits，所有新增token的hidden/KV仍计算。

实际命令见工具README；输出D:/Projects/Codex/qwen3-inference-20261022/results/run-01、run-02。单次campaign总墙钟约52秒，包含加载/验证/重复参考/观察开销，**不是模型部署延迟或吞吐**。

## 验证结果及精度口径

- 54次正例调用全部通过（主案例35、长度确认19），4次实际权重状态负例全部检出：各长度的decode位置错误置零和独立cache交换KV head。旧cache前缀按原始FP32位哈希保持不变；所有28层KV形状/长度及数值逐步与fresh完整prefix核验。
- 预声明逐元素门槛为 `abs(a-r) <= 1e-4 + 1e-4*abs(r)`，未更改。logits最大绝对误差2.64645e-5、最大相对L2误差1.54324e-6；KV最大绝对误差4.04358e-4，仍满足对应元素的绝对+相对门槛，**不是所有绝对误差均小于1e-4**。54次top1一致仅作诊断，不承诺自由生成轨迹或语言质量。
- 主案例35次观察调用、每次全部28层14个阶段，共13720事件。选定0/13/27层末token共1365个边界数值比较通过；全28层边界数值并未全部保存/比较。
- 临时包装真实eager入口，捕获实际post-RoPE Q与cache更新后、GQA重复前K/V；K/V与当前cache一致，记录实际additive mask的SHA和允许位置并核因果条件。观察路径与无观察缓存流logits及所有层KV一致；观察样本副本不算固有驻留。
- 三个真实trace元数据变异（缺事件、错KV head数、把raw K投影误标为cache）均检出；开发6项协议检查、随机小模型196事件/异常恢复集成通过。独立静态协议另3个正常schema/27变异通过，独立真实结果审查见本人辅助目录。
- 两次运行的inputs、两份numeric、trace及events.gz这5份科学结果逐字节一致；运行时间/时间戳manifest不要求字节相同，不把重复样本当独立统计证据。

## 对划分有用的实测反例

同一32-token前缀、同一模型和精度，下表是单层的**实际观察张量逻辑字节**。全部28层形状相同；它不是所有张量同时驻留的峰值或目标硬件通信流量。

| 观察对象 | 一次32-token prefill | 16+16 chunked prefill |
|---|---:|---:|
| 单次最大attention概率张量 | 64KiB | 32KiB |
| 两次调用累计attention概率张量 | 64KiB | 48KiB |
| 单次最大SwiGLU中间乘积 | 384KiB | 192KiB |
| 累计SwiGLU中间乘积 | 384KiB | 384KiB |
| 单次最大Q投影输出（norm/RoPE前） | 256KiB | 128KiB |
| 32-token处理完的全28层持久KV | 7MiB | 7MiB |
| 续传到48-token的全28层持久KV | 10.5MiB | 10.5MiB |

分块改变了临时张量尺度，却没有减少同一最终prefix的持久KV。概率张量累计减少25%，来自本次eager形状/因果分块所避免的部分未来位置，不是已经改变硬件Block边界；已有因果跳过或在线attention的公平基线不能再免费重复计入这项收益。矩阵调用/权重访问是否增加及真实代价仍需带缓存/端口/带宽的模型或测量。

因此下一轮候选应显式区分长期KV归属、短期FFN/attention workspace和真实调度自由度；固定连接基线也必须允许合法chunking。只把较小临时张量塞进一个Block，再把容量优势归因于物理合并，会重复计益。当前数据不决定bank合并/分离最优，也没有量化芯片端到端收益。

## 成果与交接

正式归档 `project/experiments/qwen3_trace/results/issue-23-run01/evidence.zip`，350398bytes、9成员，SHA-256 `d9f6701fcea9553e557a63a718787ade5da908b44f43f2dae7e2701da7d5de76`；封装后逐成员读回与原运行manifest一致。权重/venv/wheelhouse不进Git，位置及SHA清单在work/Liangruizhi/23/environment/与model-download-manifest。共享远端大文件存储未配置，不声称本机权重已共享。

实验主源码与后续封装/分析脚本分别记录；归档器、从真实事件推导本表的脚本、重放比较、安装及独立审查回执在work/Liangruizhi/23/。交付版runner另补科学summary为FAIL时返回非零退出码；本轮实际运行使用上述d63bc2d3原源码，验收读取summary/全部结果，不只依赖退出码。所有错误/失败记录保留；本轮正式run-01/run-02无数值失败。安装过程中wheel内嵌vendor元数据识别和Windows长pycache预编译问题已记录，未改系统设置，未当成科学结果。

后续：同一真实trace下加入固定容量/端口/带宽约束与公平chunk/tile对照，再扩有差异的代表架构并接真实物理校准。静态产品定制不得在prefill/decode间自动重连；运行时能力另计成本。Issue15由原负责人继续物理收敛，未接管。登记pending、看板未核验/同步pending；本任务待PR审查合并，不done。
