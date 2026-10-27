# 八模型算子计算图与 ONNX/onnxsim 对照

生成日期：2026-10-26；项目：rayggxia-workspace/LLMHardwareDesign。

打开 [交互图册](./operator-graphs.html)。页面内嵌全部SVG与节点数据，离线可用；可切换模型、并列比较、放大图形、点击节点看输入输出和shape。

## 本轮实际交付

- 八个模型，十种decoder层：Qwen2.5、Qwen3、Llama3.2、Gemma3局部/全局、Phi4-mini、Qwen3.5全局/递推、Granite MoE、Falcon-H1。
- 20份独立手工语义算子图（prefill/decode），20份实际ONNX算子图（导出/简化）；SVG、DOT、JSON均保留。
- 十种层均完成定长 B=1、S=2、FP32、eager、eval 的prefill数值核对。原始ONNX对原生前向使用 rtol=atol=3e-4；简化对原始使用 rtol=atol=1e-5；三个随机hidden-state种子17/31/73。它们是层计算核对，不能称为模型任务准确率评测。
- 成功产物索引在 `results/render01/manifest.json`。每个receipt记录工具/源码/权重绑定/文件SHA256。失败尝试保留在native02/03等目录，不把Slurm退出0当成实验成功。

## 范围与证据

这里是完整单decoder层内的算子DAG；不是整个多层网络的一次端到端ONNX导出。词嵌入、RoPE频率生成、掩码生成、最终norm/LM head和采样均不在导出边界；cos/sin与mask是外部输入。层数和混合层序列在各config中可查。

手工decode图显示KV/卷积/递推状态依赖，但本轮没有cached decode ONNX或非零历史状态验证。手工prefill中的StateWrite表示可选缓存接口；实际use_cache=False导出不会保留这些写出。手工图按数学算子语义独立编制，省略常量/权重节点和若干轴广播细节，不是可执行的shape完备IR。

Llama-3.2-1B使用先前报告记录的架构配置重建与随机参数；未找到原检查点。其他模型均加载指定层真实检查点权重，绑定完整性见receipt。

Qwen3.5递推层与Granite各使用一个明确记载的导出适配，数值参考保持原生实现。Falcon仅补入原模型构造时的非持久MuP向量，并将导出器生成的负数Transpose轴按rank取模；未合法化ONNX保存在服务器。

## 实际结果

| 模型/层 | 手工prefill节点 | 原始ONNX节点 | 简化ONNX节点 | raw/native最大绝对误差 | sim/raw最大绝对误差 | 状态 |
|---|---:|---:|---:|---:|---:|---|
| Qwen2.5-3B | 65 | 232 | 67 | 3.337860107421875e-06 | 7.152557373046875e-07 | pass |
| Qwen3-0.6B | 74 | 253 | 80 | 1.9073486328125e-06 | 0.0 | pass |
| Llama-3.2-1B | 62 | 230 | 64 | 8.195638656616211e-07 | 7.599592208862305e-07 | pass |
| Gemma-3-4B · 局部层 | 98 | 300 | 110 | 0.00054931640625 | 0.0 | pass |
| Gemma-3-4B · 全局层 | 98 | 300 | 110 | 0.00146484375 | 0.0 | pass |
| Phi-4-mini | 70 | 305 | 74 | 1.9073486328125e-06 | 0.0 | pass |
| Qwen3.5-4B · 全局层 | 89 | 335 | 95 | 2.6226043701171875e-06 | 0.0 | pass |
| Qwen3.5-4B · 递推层 | 101 | 374 | 132 | 2.7418136596679688e-06 | 2.384185791015625e-07 | pass |
| Granite-3.3B · MoE | 77 | 285 | 84 | 1.2516975402832031e-06 | 0.0 | pass |
| Falcon-H1-3B · 混合层 | 140 | 998 | 173 | 2.86102294921875e-05 | 0.0 | pass |

手工数包含Input和状态说明节点；ONNX节点数包含Constant、不含initializer和图I/O。两套口径不同，不应拿手工与ONNX节点数计算优化率。Gemma通过的是绝对+相对容差条件，最大绝对误差可高于3e-4。

## 对比得到的结论

1. onnxsim主要去掉/折叠形状计算、常量和冗余布局节点，也会作局部融合。例如Qwen2.5的三组MatMul+偏置Add变成Gemm。节点更少不等于硬件面积/功耗同比减少。
2. 手工Rsqrt在ONNX中通常是Sqrt+Div；手工平方Mul在ONNX中常是Pow；SiLU仍是Sigmoid+Mul；Gemma的GELU为Tanh等展开。必须先统一算子语义，才能比较覆盖率和Block边界。
3. 同样的模型数学式可有不同算法图：Granite分组scatter与gather-batched-matmul、Falcon分块扫描与逐token递推、Qwen3.5分块与递推核。这是算法/导出边界的差异，不只是简化器删节点。
4. Gemma本次两种层都是110个简化节点，但S=2小于局部窗口，且mask/频率在层外；不能由这个结果得出局部和全局的存储/通信成本相同。
5. 对本项目，这些DAG可以支持算子语义核对、候选Block边界和路由/状态算子的遗漏检查。还不能证明六类或十五类物理Block更好；需要实际精度、长序列prefill/decode、shape/字节数、调度/复用、存储端口、通信切割及面积时序能耗证据。十五项可作为能力标签，六类可作为候选资源族，二者无需一一对应。

## 文件与复现入口

- `results/manual02/`：当前手工图；manual01为首版，manual02修正了卷积history更新必须保留“旧历史+当前输入”的尾部。
- `results/render01/`：原始/简化ONNX完整节点SVG/DOT与成功索引，未隐藏Constant或shape节点。
- `results/native02/`、`native03/`、`native04/`：实际图JSON、配置和receipt；本地包不包含数GB的权重ONNX。
- 服务器完整产物：`yuzelu@10.129.166.172:/public/home/yuzelu/project-circuit/LLMHardwareDesign/operator-graphs-20261026/`。
- 对应的 `raw.onnx` / `simplified.onnx` 在每个成功receipt所在的服务器目录；可按manifest定位，用Netron直接打开。图JSON保留全部算子、数据边、形状和属性，不含权重值。
- `sources/native_export.py`、v2、v3及Slurm脚本为实际执行源码；`sources/manual_graphs.py`不读取ONNX。raw/sim导出源具体版本以receipt的source_sha256为准。
- 依赖：torch2.10.0+cpu、transformers5.20.2、onnx1.17.0、onnxruntime1.20.1、onnxsim v0.8.1。不同工具版本可能产生不同DAG。
- 例：`sbatch sources/batch.sh`；这是已经执行过的固定输出目录脚本，再跑前应另取新输出目录，不能覆盖现有证据。所有重计算应在分配到的Slurm计算节点执行。

## 提交回执

规则版本：rayggxia-project-collab1.0.0；本次是用户授权的旁路实验与本地交付，未改主仓库。
仓库基线：0cc36f3238c7084d7126d94c314fe7d8bf0f9c5d；工作区检查干净。
Issue/PR、登记及看板：本轮未创建/更新；本地包尚未提交项目，不宣称在线任务完成。正式入库动作pending，处理人待指定。
验证：管理检查此前通过；十种层的科学验证逐receipt核实；HTML/SVG核验见本地QA记录。
