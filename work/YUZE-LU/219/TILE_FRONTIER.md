# Algo1 自动分块与 Qwen 首层对照

2026-11-14 CST。Refs #219，基线 3e696988d18829a583d573b8cb474ae587301660。

## 自动分块

类型化算子图入口按算子签名、属性、张量形状和切片轴匹配已有硬件配方。切片必须覆盖原张量范围。编译器沿数据依赖自动发现可共用切分网格的连通区域，并检查区域外可见结果的拼接配方。DP 比较整算子方案和最多 `--event-tile-trials`（默认 8）个自动布局，按模型工期、DDR 字节和静态线束成本排序。

同个算子内按原本的 tile 顺序排定。某个原算子有已排和未排 tile 时计为部分排定。DP 按原图依赖的可达关系限制同一依赖链上同时部分排定的原算子数，`--event-tile-depth` 默认为 2，设为 0 关闭自动分块。运行时的并行、窗口生命周期和完成事件仍由所选绑定决定。

## Qwen2.5-3B 第 0 层

输入来自归档的真实 Qwen2.5-3B 整数图，batch 1、序列长度 2，使用 Block V2 归档的有限循环事件 IR 和服务时长。截取同一完整 decoder layer，保留 30 个原生任务、120 个绑定候选以及层内依赖。Embedding 输出在层入口已可用。各方案生成 30 条母控派发，读回并校验 292 条整数原语的顺序和控制依赖。

| 束宽 | 部分排定深度 | 层调度模型工期（拍） | 候选展开 | 截断前最大状态桶 | 深度剪枝 |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | 0 / 1 / 2 / 3（四次相同） | 93,582,477,980 | 208 | 4 | 0 |
| 8 | 0 / 1 / 2 / 3（四次相同） | 93,582,477,980 | 1,224 | 28 | 0 |

这份归档的每个绑定只有 `native_loop_final_ack`，tile 配方和带 tile 归属的任务均为 0。因此深度限制对这份原生计划没有作用。现有原生 lowering 要提供可寻址、可独立发布且能编码为真实指令的 tile 服务，才能实验性地测出跨算子交接的增益和状态膨胀。现有结果的拍数来自保守的原生命令及逐记录访存模型，实测芯片延迟和原生二进制执行未在此项评估中覆盖。

## 复现

在远端 Block V2 归档 `blockv2-mod/evidence/full-algo1-113543` 的 `event-ir.json`、`hardware.json` 上执行以下命令。束宽 1 和 8 分别对应 113875 和 113876。

```sh
python3.12 project/experiments/block_synthesis/benchmark_event_layer.py EVENT_IR HARDWARE \
  --layer-path /model/model/layers.0/ --width 8
```

- `event-ir.json` SHA-256 `e1846dd16b8be62f6ae4a7668baf63c846b8c62399f14f8bfc4072a27a51977e`。
- `hardware.json` SHA-256 `98cc6272924aea457d2ba82e58fef94dfd1e7001c50b64c60f8a6cc1102dba8a`。
- ONNX SHA-256 `0950df534497881f416a3f8b8fac1a265764ea2f4879943695a2d800a5c9158f`，全图整数程序规范散列 `3463d31d34531a876b8b2e146fb81917ce37d369db8b0d86c5a555a945294056`。
- 隔离目录 `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/qwen-layer-TOmcZu`。结果 `layer-w1-113875.log` SHA-256 `a21f185b4e99b067954db850442e301dafd30dc8340bcf65c6cffc9c97f4f579`，`layer-w8-113876.log` SHA-256 `3bbd7c559eec51221ef289d268019351ba66c5a1a1332b27681f001cb292a7c6`。
- 完整回归 113977 通过 420 项，日志 SHA-256 `e9c60da3e1e836960eea971d2abf0a284a8ad3b9fc561ee6fa2386e90d4f2620`。结构检查 113979 通过。
