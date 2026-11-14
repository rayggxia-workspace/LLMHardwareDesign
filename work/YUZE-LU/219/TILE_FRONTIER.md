# 通用 tile 前沿搜索对照

2026-11-14 CST。Refs #219，基线 3e696988d18829a583d573b8cb474ae587301660。

在类型化图的硬件 event_model 中配置 tile_groups。每组指定 nodes、各原始输出张量的 axes 和 tile_size。精确匹配原算子签名、属性、切片范围及输入输出轴的硬件 recipe 提供实现。组内每个算子的 tile 保持原序，消费端连接同块输入，组外可见结果通过已登记的 Concat 实现恢复原张量。DP 按 tile 任务分桶，允许不同算子交错排程。编译仍检查数据生命周期、资源容量和目标完成信号。原图未提供 tile_groups 时沿用既有 lowering。

## 对照

三组均为已有输入驻留的模型用例，每行 513 个 INT32 元素。16 行对照在两种模式使用相同任务、宏、地址、时长和完成事件。整算子屏障对照仅给消费端增加最后一个生产 tile 的完成依赖。

| 算子对 | 工期，拍 | 中间值峰值，行 | 束宽 8 截断前最大状态桶 | 候选展开 |
| --- | ---: | ---: | ---: | ---: |
| MatMul→Softmax | 224 → 149 | 16 → 2 | 1 → 16 | 33 → 353 |
| MatMul→ReLU | 176 → 146 | 16 → 2 | 1 → 16 | 33 → 353 |
| Add→RMSNorm | 176 → 131 | 16 → 10 | 1 → 16 | 33 → 363 |

只给两块循环复用的中间窗口时，三个流水方案仍分别得到 149、146、131 拍，峰值均为两行。整算子屏障无法在给定窗口和无 DDR 溢出路径的模型下完成。束宽 1、8、32 得到相同工期。收益来自允许交接，扩大束宽只增加了这些规则模型的搜索开销。模型时长、行序、端口及服务完成由 fixture 声明，实际底座和整图吞吐待测试。中间值峰值只统计生产端开始占用到消费最后读取这一组 score/中间窗口，输出拼接的窗口另外预留。

## 复现与校验

远端隔离目录 `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/tile-frontier-AEuhvK`。Python 3.12.1。
- 113585，项目管理结构检查通过。
- 113624，三组算子对、2／4／8／16 行、束宽 1／8／32 和两窗口控制全部完成。
- 113625，`python -B -m unittest discover -p 'test_*.py' -q`，418 项通过。日志 SHA-256 `8343a2f18b0e3eefd564ca0ec21eb47d1d1f25bd8b3a599f3a8c02ecedadb2ae`。
- 16 行输出 SHA-256 在 `general-113624-{3,7,11}.jsonl` 中分别为 `c4ba0872a0512942d77f771d93624168c4a7fd699c8527e4e7bcd70c34d7b69e`、`254ea69935de2a11a1aaa5c5c52a14d46706b29c9e45a43967f60b8bd9923230`、`21cded9cd339ba804d2d0c1cdbeead3db7c665bc603b38b330bb9336b6f6855b`。
- 复现示例 `python -B project/experiments/block_synthesis/benchmark_tile_handoff_dp.py --rows 16 --case add-rmsnorm --slots 2`。可选 `--barrier`、`--width`。
