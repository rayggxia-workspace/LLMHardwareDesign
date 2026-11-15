# PR185 修正与完整短程评估结果

当前结论：完整 36 层 Qwen2.5-3B 的两 token prefill + 一步自产 KV decode 已通过定点功能验收。其余 benchmark 的 20 张图均已尝试转换，尚无一张生成完整选择计划。两项结论不能混用。

## 架构修正

P/U/C/F/J 仅表示控制归属；30 个功能宏保持独立硬边界。服务控制、有限程序存储、仲裁和传输逻辑逐项登记。旧固定 U/P 供数封装和未登记计算实例被禁止进入当前底座；13 个违规 RTL、32 个历史参考文件均有排除记录。候选数据连接包含同组内部路径，落实到实际宏或父层适配单元端点，并由 prefill/decode 的同一静态连接集合承载。完整装配检查包含 51 个违规拒绝案例。

结构检查证明资源/端点绑定；完整 TLM 证明所选指令包的短程功能执行。没有用它们替代完整 RTL 周期级执行或物理后端验收。

## 完整短程 Qwen

| 项目 | Prefill | Decode |
| --- | --- | --- |
| 调用数 | 141490 | 70457 |
| 母控页 | 13 | 4 |
| 逐字节比较张量 | 651 | 723 |
| 比较字节 | 17026048 | 8734208 |
| 差异 | 0 | 0 |
| 模拟执行时间（未校准） | 1.601322395079 s | 0.807066455283 s |

Prefill 两个位置的 top-1 与 FP32 相同；实际 token 16 及该次执行提交的 72 份 KV 输入用于 decode。Decode top-1 与 FP32 同为 15，logits 余弦相似度 0.9992718618、相对 L2 误差 0.03816616。上述精度指标只覆盖本次场景，不构成广泛模型精度合格结论。

时间不包含程序装载和外部阶段切换/输入准备；宏服务时序未校准，不报告连续请求稳态吞吐。未运行 P512/D128。

## 剩余 benchmark 的真实转换结果

来源是项目登记的 10 类完整 decoder layer，各有原始和简化图，共 20 张 B1 S2 图；不是 10 个完整网络。Llama 来源含随机参数，其他来源范围以源目录回执为准。每张 ONNX 的实际哈希与登记值核对后才导入。

| 模型/层类型 | 原始图首个阻断 | 简化图首个阻断 |
| --- | --- | --- |
| falcon | bind positive runtime dimensions before layout | missing operand recipe: Mul |
| gemma_global | bind positive runtime dimensions before layout | missing operand recipe: Mul |
| gemma_local | bind positive runtime dimensions before layout | missing operand recipe: Mul |
| granite | bind positive runtime dimensions before layout | missing operand recipe: Mul |
| llama | bind positive runtime dimensions before layout | missing operand recipe: Pow |
| phi | bind positive runtime dimensions before layout | missing operand recipe: Mul |
| qwen25 | bind positive runtime dimensions before layout | missing operand recipe: Gemm |
| qwen3 | bind positive runtime dimensions before layout | missing operand recipe: Mul |
| qwen35_global | bind positive runtime dimensions before layout | missing operand recipe: Mul |
| qwen35_linear | bind positive runtime dimensions before layout | missing operand recipe: Sigmoid |

责任首先在 Algo1 前端：原始图需要把中间张量尺寸解析到可用布局；简化图需要完善语义识别和 operand lowering。任务在这些阶段已失败，尚未到硬件候选选择，因此本次结果不能证明底座缺少相关算术能力，也不能据此添加 RTL 核心。表中只列每张图实际遇到的首个阻断，后续缺口尚未验证。

## 证据与交付

- 短程验收及证据哈希：Qwen-short-acceptance-115200.json。
- Prefill：macro-prefill-115069/receipt.json、prefill-bit-exact-115071.json。
- Decode：macro-decode-115084/receipt.json、decode-bit-exact-115086.json、decode-FP32-comparison-115100.json。
- Benchmark：remaining-benchmark-conversion-115202/summary.json；逐图目录保留源、识别结果和异常记录。
- 全部计算和工件留在远端。远端原始目录不是 Git checkout；本次源码和小型回执通过已认证的 GitHub 连接器集成到 PR #269。完整二进制工件留在远端并提供索引，审查/合并状态以 PR 为准。
