# 完整算子计算图与验证说明

[返回索引](README.md) · [精简字符图](COMPUTATION_GRAPHS_SIMPLIFIED.md) · [实验分析报告](MODEL_EXPERIMENT_ANALYSIS.md)

## 1. 完整图册

打开 [operator-graphs.html](graphs/operator-graphs.html)，选择模型后可并列查看手工语义图、实际原始 ONNX 图、onnxsim 简化图。图册内嵌全部 SVG 与节点数据，离线可用；附原始/简化图的输入输出名、推断 shape 和属性。GitHub 不直接执行此 HTML，需下载后在浏览器打开。

八个模型共十种层类型：Qwen2.5、Qwen3、Llama3.2、Gemma 局部/全局、Phi4-mini、Qwen3.5 全局/GDN、Granite MoE、Falcon-H1。手工图覆盖 prefill/decode，共 20 张；实际 ONNX 覆盖原始/简化 prefill，共 20 张。

| 层类型 | 手工 prefill SVG | 原始 ONNX SVG | onnxsim SVG | 原始→简化节点数 |
| --- | --- | --- | --- | ---: |
| Qwen2.5-3B | [图](graphs/results/manual02/qwen25-prefill.svg) | [图](graphs/results/render01/qwen25-raw.svg) | [图](graphs/results/render01/qwen25-simplified.svg) | 232→67 |
| Qwen3-0.6B | [图](graphs/results/manual02/qwen3-prefill.svg) | [图](graphs/results/render01/qwen3-raw.svg) | [图](graphs/results/render01/qwen3-simplified.svg) | 253→80 |
| Llama-3.2-1B | [图](graphs/results/manual02/llama-prefill.svg) | [图](graphs/results/render01/llama-raw.svg) | [图](graphs/results/render01/llama-simplified.svg) | 230→64 |
| Gemma-3-4B 局部 | [图](graphs/results/manual02/gemma_local-prefill.svg) | [图](graphs/results/render01/gemma_local-raw.svg) | [图](graphs/results/render01/gemma_local-simplified.svg) | 300→110 |
| Gemma-3-4B 全局 | [图](graphs/results/manual02/gemma_global-prefill.svg) | [图](graphs/results/render01/gemma_global-raw.svg) | [图](graphs/results/render01/gemma_global-simplified.svg) | 300→110 |
| Phi-4-mini | [图](graphs/results/manual02/phi-prefill.svg) | [图](graphs/results/render01/phi-raw.svg) | [图](graphs/results/render01/phi-simplified.svg) | 305→74 |
| Qwen3.5-4B 全局 | [图](graphs/results/manual02/qwen35_global-prefill.svg) | [图](graphs/results/render01/qwen35_global-raw.svg) | [图](graphs/results/render01/qwen35_global-simplified.svg) | 335→95 |
| Qwen3.5-4B GDN | [图](graphs/results/manual02/qwen35_linear-prefill.svg) | [图](graphs/results/render01/qwen35_linear-raw.svg) | [图](graphs/results/render01/qwen35_linear-simplified.svg) | 374→132 |
| Granite-3.3B MoE | [图](graphs/results/manual02/granite-prefill.svg) | [图](graphs/results/render01/granite-raw.svg) | [图](graphs/results/render01/granite-simplified.svg) | 285→84 |
| Falcon-H1-3B | [图](graphs/results/manual02/falcon-prefill.svg) | [图](graphs/results/render01/falcon-raw.svg) | [图](graphs/results/render01/falcon-simplified.svg) | 998→173 |

同名 `.dot` 与 `.json` 保存图结构；实际 ONNX 的 JSON 在对应 native 目录。手工 decode 图使用 `-decode` 后缀，也可在图册切换查看。

## 2. 为什么复杂度不同

- 手工图省略常量与部分轴广播，表达数学依赖及状态接口，并非 shape 完备的可执行 IR。
- 原始 ONNX 保留导出器产生的 Constant、Cast、Unsqueeze、Shape 等全部节点。Qwen3 的 253 个节点中，Constant 有 91 个、Unsqueeze 有 53 个。
- onnxsim 折叠常量与形状计算，去掉冗余节点并做局部融合；Qwen3 简化至 80 节点，Constant/Unsqueeze 各剩 4 个，但 MatMul 仍为 9 个。
- Falcon 实际 prefill 为分块扫描，手工图为逐 token 递推；Granite 手工分组/Scatter 与导出动态 Gather/批量 MatMul 也不是同一种实现调度。
- 手工图的可选状态边与 use_cache=False 的实际导出边界不同；不能假设三栏逐节点对应或都有相同缓存读写。

精简版用于阅读；完整图用于追查。节点数减少不等于相同比例的计算量、面积、能耗或时延减少。

## 3. 实际验证范围

十种层均完成 B=1、S=2、FP32、eager、eval prefill 导出与三组隐藏输入种子 17/31/73 的数值核对。原始 ONNX 与原生前向采用 `rtol=atol=3e-4`；简化与原始 ONNX 采用 `rtol=atol=1e-5`。这是绝对与相对容差组合，不是最大绝对误差都低于 3e-4。

边界和特殊处理：

- 本轮不是整网端到端导出；词嵌入、RoPE 频率生成、掩码生成、末尾 norm/LM head、采样在导出边界之外。
- 带历史状态的 decode 未导出、未验证。手工 decode 只作状态依赖参考。
- Llama 未找到原检查点，使用报告配置重建和随机参数。
- Gemma S=2 小于局部窗口，两种层简化后节点数相同，不证明长序列窗口与全局层的访存成本相同。
- Qwen3.5 GDN 仅在导出时把不支持的分块三角求解核替换为官方逐 token 递推等价核；数值参考仍使用原生分块实现。
- Granite 为保持动态 TopK，导出采用 Gather 专家权重与批量 MatMul；参考仍使用原生专家实现。
- Falcon 补入原模型构造时注册的非持久 MuP 向量，并将导出器生成的负数 Transpose 轴按 rank 取模合法化；未合法化产物在服务器保留。

工具版本、权重绑定、源码 SHA、原始/简化 ONNX SHA 与误差见 [成功产物索引](graphs/results/render01/manifest.json) 及各模型 receipt；汇总见 [comparison.csv](graphs/comparison.csv)。失败尝试也随 JSON 回执归档，不用 Slurm 退出 0 代替科学验证通过。

## 4. 原始手工图的已知差异

完整图册和 `graphs/results/manual02/` 原样保留原实验产物。后续字符图核对发现：原 Falcon 手工图误标了部分 RoPE，且遗漏了 K 投影后的额外 key_multiplier；本次实际配置使用完整 128 通道 RoPE，并在 RoPE 前另乘 K 缩放。精简版第 9 节已校正。

因此，Falcon 的旧手工 SVG 只作历史语义草图参考；具体实现优先查实际 ONNX 与精简版的校正说明。本文没有改写旧 SVG/JSON 或冒充已经重跑手工图生成。Granite 的通用 scale 标签也应按配置读取为 0.015625，精简版已明确写出。

## 5. 原始数据与源码位置

- [原始实验说明快照](graphs/README.md)：原始边界、全部误差及工具说明；其中未入库等表述属于实验时点。
- [图册原始摘要](graphs/delivery-manifest.json)：绑定原始 HTML/README/CSV，归档时保持字节不变。
- `graphs/results/`：SVG、DOT、图 JSON、配置、成功与失败回执；不含权重值。
- `graphs/sources/`：实际运行的导出、适配、渲染、手工图与图册生成脚本快照。脚本中的源路径和固定输出目录属于原环境，再运行前应选择新输出位置，避免覆盖证据。
- 本次导入摘要：[archive-manifest.json](../../work/YUZE-LU/116/archive-manifest.json)。

服务器完整产物目录：

```text
yuzelu@10.129.166.172:
/public/home/yuzelu/project-circuit/LLMHardwareDesign/operator-graphs-20261026/
```

成功模型的 `raw.onnx` / `simplified.onnx` 位于成功索引中 `result` 指向的 native02/03/04 子目录。原始独立本地实验目录保留，本次仅复制轻量图与证据、迁移分析文档，没有重新运行模型或接触远程作业。
