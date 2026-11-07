# 通用 Block 前沿搜索原型（Issue #219）

输入只有模型产物、硬件清单与调用参数。`search.py` 不识别 Qwen 等模型名，不固定位宽、实例数、S 容量或 P/U/C/F/J 的数量。硬件文件可为 JSON/YAML；YAML 需要 PyYAML。ONNX 导入需要 onnx/numpy；权重可留作外部参数引用。未解析形状、未登记服务或不支持的 dtype 明确失败。

## 实际实现与边界

已实现固定拓扑决策顺序的有界前沿搜索：服务/实例/有限路径候选；资源区间冲突与最早空窗；完整激活对象的私有存储占用；源对象保持至最后一次本地消费或传输确认；跨整图静态连接并集；连接集合多样性保留；输出计划独立重放检查。拓扑决策顺序不代表执行串行，不同资源上的任务可以重叠。

**这不是先前讨论的完整事件驱动综合器，也不宣称 DP 最优性。** 暂无自动分片、spill、多算子模式覆盖、状态循环 lowering、动态专家分支合同和原生母控/局控镜像生成。资源模型将整段传输视为占用源/目的 S 与通道，计算期间也保守占用其本地 S/局控，尚未利用 #213 的细分握手生命周期。实际 SRAM 字节容量也不代替地址分配、bank、仲裁或电气验收。

`evaluate.py` 的九组架构仅为**假设的分析成本场景**，不是从 #213/#214 验收包抽取的原生服务或 pin-qualified 底座。FP32 算子、布局/索引/系数扩展服务均未取得宏合同资格，清单明确 `qualified_numeric=false`。默认严格模式拒绝该清单，必须显式 `--allow-estimates` 才能探索。没有 CPU 回退。成功计划标记 `analytical_plan, executable=false`，不能作为数值、RTL、端点接入、DRC、STA 或物理覆盖。

## 输入契约

硬件：`instances`（ID→容量等）、`services`（支持算子/dtype、所属实例、独占资源、工作量/周期、启动开销、工作区和权重流窗口）、`links`（真实或候选 ID、方向、带宽、延迟、资源、静态代价、是否预连/启用）、`external_memory`。同一资源 ID 表示争用；同一 link ID 表示可复用的同一静态连接，不能将不同驱动端短接。原型尚未验证选择器互斥配置，录入清单必须已经排除此类不合法组合。

模型：ONNX 或归一化图。归一化图含 `tasks`（id/op/inputs/outputs/dependencies/work/dtype）、`sizes`（张量字节）、`weights`、输入输出及源 SHA。只把 Constant 和明确权重看作外部常量，不把任意 Shape/Transpose 隐式当作免费操作。

计划：映射和资源时间区间、搬运、存储生命周期、静态连接并集、搜索统计、源 SHA、失败位置与证据边界。容量不够返回 `search_exhausted`，只表示保留候选无可行扩展，不构成全局不可行证明。

```bash
python -B -m unittest -v test_search
python -B search.py model.onnx hardware.yaml plan.json --beam 16
# 只有探索假设硬件时才显式开启：
python -B search.py graph.json hardware.json plan.json --beam 16 --allow-estimates
python -B report.py RESULTS report-fragment.html
```

## 代价与搜索

最小化 `完成时间 + penalty * 新静态连接成本`。并行操作不按时间简单相加。完整连接并集贯穿输入整图，未按层重置。beam=1 是同实现下的贪心基线；beam>1 保留部分不同连接集合，再按当前代价补足。没有可采纳下界、没有全局最优保证，beam 增大不保证结果单调改善。完整资源/对象状态指纹用于安全去重，统计中如实报告合并数量。

## 借鉴来源

- ForeSight（多候选与延迟决策）：https://arxiv.org/abs/2204.13142
- LightSABRE（前沿/前瞻启发式；本版尚未加入其增量评分）：https://arxiv.org/abs/2409.08368
- TOQM（映射与执行时间联合建模；本版不是其 A*，也未移植其证明）：https://chizhang.io/publications/papers/asplos21main-p129-final.pdf
- Stream（分片、有限存储、通信与调度；本版尚缺其分片/稳态优化）：https://arxiv.org/html/2212.10612v2
- MATCHA（模式匹配、分片与约束规划，后续强对照）：https://arxiv.org/html/2604.09124v1

未复制上述实现代码；本原型使用通用方法并注明思想来源。

## 服务器复现

`export_full.sh SOURCE CHECKPOINT NEW_OUTPUT` 在 Slurm 上导出完整 Qwen3-0.6B：B1/S2、FP32、无 KV 的 prefill，包含 embedding、28 层和 LM head。固定 S2 因果 mask 避开 legacy exporter 不支持的 `aten::diff`，三组 token 核对原始 HF 默认 mask、显式 mask 和 ONNX Runtime。`raw.onnx` 与 shape-folded `full.onnx` 分开保留；参数为显式 ONNX 输入并绑定真实检查点，未复制进 ONNX。该数值检查仅验证前端。

`evaluate.sh SOURCE NEW_OUTPUT FULL_MODEL_DIR` 对已有十类 decoder 层与完整模型进行分析映射。16 KiB 代表当前容量，4 MiB 是算法适应性和容量瓶颈的**假设扩容对照**，不是宣称已有 SRAM 更新。结果可视化显示完整输入节点的分页图、实例分配、执行时间及连接并集；失败方案同样可选。
