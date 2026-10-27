# 模型分析与计算图

将八模型的实验分析、精简字符算子图和完整图册集中在本目录。整理任务：[Issue #116](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/116)，2026-10-26，中国标准时间。

| 入口 | 内容 | 建议用法 |
| --- | --- | --- |
| [精简版：字符算子计算图](COMPUTATION_GRAPHS_SIMPLIFIED.md) | 八模型、十种 decoder 层类型；保留主要算子、分支、残差与状态关系；附折叠算子的展开定义 | 先阅读，比较模型差异和候选 Block 边界 |
| [复杂版：完整算子图与验证说明](COMPUTATION_GRAPHS_FULL.md) | 手工图、原始 ONNX、onnxsim 图的区别、完整图册与底层文件索引 | 追查节点、shape、导出适配和验证范围 |
| [打开完整交互图册](graphs/operator-graphs.html) | 40 张 SVG 图，模型切换、缩放、查找、节点输入/输出与 shape 检查 | 下载后用浏览器打开；GitHub 页面只展示 HTML 源码 |
| [真实模型实验分析报告](MODEL_EXPERIMENT_ANALYSIS.md) | 为何运行这些模型、已有数值/状态/访存/服务结果，以及对 P1–P15 和 M/V/A/R/S/D 的约束 | 阅读实验结论、失败与硬件研究证据边界 |

## 阅读顺序与范围

先读精简版了解算子依赖，再用复杂版及图册核查实现细节，最后对照实验分析报告理解这些计算和状态需求如何约束候选硬件边界。

计算图实验覆盖的是完整单 decoder 层，实际 ONNX 验证为 B=1、S=2、FP32 prefill；未执行整网端到端导出或带非零历史状态的 decode 导出。Llama 使用重建配置与随机参数，其他模型的指定层使用真实检查点。精简图和完整图册不是对模型任务准确率或物理 PPA 的验收。

实验分析报告此前由 [PR #115](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/115) 合入 main，本次仅迁移正式路径并调整相对链接；旧入口 [docs/MODEL_EXPERIMENT_ANALYSIS.md](../MODEL_EXPERIMENT_ANALYSIS.md) 保留跳转。其来源与历史验收记录仍在 [work/YUZE-LU/114](../../work/YUZE-LU/114/README.md)。

## 文件组织

```text
docs/model-analysis/
  README.md                             阅读索引
  MODEL_EXPERIMENT_ANALYSIS.md           既有实验分析报告
  COMPUTATION_GRAPHS_SIMPLIFIED.md        精简字符算子图
  COMPUTATION_GRAPHS_FULL.md              完整图册说明与证据索引
  graphs/
    operator-graphs.html                 自包含离线交互图册
    README.md                            原始导出实验说明快照
    comparison.csv                       节点数与数值误差汇总
    delivery-manifest.json               原始图册/说明/CSV摘要
    results/manual02/                    20张手工图的JSON/DOT/SVG
    results/render01/                    20张实际ONNX图的DOT/SVG与成功索引
    results/native02|native03|native04/   原始/简化图JSON、配置、成功和失败回执
    sources/                             导出、适配、手工图及图册生成源码快照
```

含权重的 `.onnx`、模型权重、依赖 wheel 和压缩备份不放入本目录。服务器完整 ONNX 位置与文件摘要见复杂版及各 receipt。

`graphs/` 是原始实验产物快照，导入时逐文件核对 SHA-256；历史说明中的“未入库”等表述属于原实验时点，当前归档与在线提交状态以 [本次任务回执](../../work/YUZE-LU/116/README.md) 为准。精简版已校正的 Falcon 表达与旧手工 SVG 的差异见复杂版，不把旧图静默改写成新的实验结果。
