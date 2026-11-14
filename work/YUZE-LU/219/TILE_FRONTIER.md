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

共享同一计算资源时，三组工期分别保持在 224、176、176 拍，中间值峰值仍从 16 行降到 2 行。这一对照支持工期收益来自真实可重叠的资源，以及提前消费本身能够缩短窗口寿命。

## 复现与校验

远端隔离目录 `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/tile-frontier-AEuhvK`。Python 3.12.1。
- 113585，项目管理结构检查通过。
- 113624，三组算子对、2／4／8／16 行、束宽 1／8／32 和两窗口控制全部完成。
- 113625，`python -B -m unittest discover -p 'test_*.py' -q`，418 项通过。日志 SHA-256 `8343a2f18b0e3eefd564ca0ec21eb47d1d1f25bd8b3a599f3a8c02ecedadb2ae`。
- 113648，PR 源码的五个 Python 文件与远端文件逐个 Git blob SHA 匹配，5 项新测试复跑通过。
- 113649，三组共享计算资源的负对照完成，`shared-113649.jsonl` SHA-256 `4418138c9a8e10f4460a69dd35f5028c2d90b557c4c2c59a17901bb388044633`。复用 `benchmark_tile_handoff_dp.problem`，将消费服务的资源声明改为 `{'Producer': 1}`。
- 16 行输出 SHA-256 在 `general-113624-{3,7,11}.jsonl` 中分别为 `c4ba0872a0512942d77f771d93624168c4a7fd699c8527e4e7bcd70c34d7b69e`、`254ea69935de2a11a1aaa5c5c52a14d46706b29c9e45a43967f60b8bd9923230`、`21cded9cd339ba804d2d0c1cdbeead3db7c665bc603b38b330bb9336b6f6855b`。
- 复现示例 `python -B project/experiments/block_synthesis/benchmark_tile_handoff_dp.py --rows 16 --case add-rmsnorm --slots 2`。可选 `--barrier`、`--width`。

## 自动分块与部分排定深度

类型化 `--event-graph` 默认扫描整图。对每个节点从登记的硬件配方匹配签名、输入输出轴和切片坐标；验证切片覆盖原范围；沿值依赖发现可共用同一切分网格的连通子图；核查边界拼接配方。使用有界枚举比较整算子方案和自动分块方案，按工期、DDR 字节和静态线束成本选择。手工指定 `tile_groups` 仍可用于固定布局对照。原生循环入口沿用其单独的 lowering。

给定 DP 部分计划，原算子的 tile 有一部分已排且尚有未排 tile 时，该算子计为部分排定。按原图依赖的可达关系，统计同一依赖链上部分排定的原算子数。DP 在扩展前剪掉超过 `--event-tile-depth` 的动作，默认 2；0 关闭自动分块。限制作用于编译搜索的状态，运行期并行与 SRAM 生命周期仍由绑定和调度检查。搜索比较最多 `--event-tile-trials` 个自动布局，默认 8，另外保留普通整算子方案。

远端作业 113827 使用无 `tile_groups` 的 16 行图，包含一个只登记整算子配方的 Identity 尾节点。行内归约保持完整，配方的时长和资源是评估假设。三种算子对的深度 0／1 工期分别是 MatMul→Softmax 240／165 拍、MatMul→ReLU 192／162 拍、Add→RMSNorm 192／147 拍。下面是带三个可切分算子的链，后面同样有普通 Identity。

| 深度上限 | 工期（拍） | 选中布局的候选展开数 | 最大状态桶 |
| --- | ---: | ---: | ---: |
| 0（关闭自动切分） | 288 | 4 | 1 |
| 1 | 168 | 50 | 1 |
| 2 | 168 | 609 | 16 |
| 3 | 168 | 617 | 19 |

模型用例覆盖自动选择、不同 tile 尺寸、普通算子边界、无拼接配方时拒绝、整算子更快时保留，以及重新编译沿用深度。远端 113828 通过 423 项，113829 定向 10 项通过。全图真实配方覆盖率、原生执行和吞吐尚待验证。

复现：`python -B project/experiments/block_synthesis/benchmark_auto_tile.py --rows 16 --chain --depth 1`。远端目录 `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/tile-auto-9frEuf`。完整回归 `final-reg-113828.log` SHA-256 `fc0fbaff62b854ad386d5993c9210f3442b27e0827729a22f872f144dc359505`，三算子链对照 `final-113827-3.jsonl` SHA-256 `4651dd2b255c109159e532aa2e146a33fa35957b4ededa92caf4eb03b8041c8b`。
