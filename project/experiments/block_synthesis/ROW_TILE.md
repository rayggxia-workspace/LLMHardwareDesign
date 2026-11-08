# 多行复用：先验证原生通路，再登记综合候选

2026-11-09，Issue219/PR220。当前已有真实 RTL 小切片证据，**尚未接入完整模型综合**。
这条通路使用现有 P 原生接口、16KiB SRAM S、有限 feeder 和 M，不增加算术、缓存或端口。
Block 的控制归属不改变，探针使用现有集成 RTL 验证服务，不能据此重新定义物理硬块边界。

## 实际执行什么

对于 S32 的 A 和 S16 的 B，一个列输出的完整 K 归约：

1. 一次取 R 行（R≤8），每行维护 M 原生 S64 累加值。N=1、每次 K 段长=1。
2. 每个 K 只向 S 的 B 槽写一个128位记录。feeder 首次读取两个512位半块；
   其余 padding 已初始化，只有第一个 S16 权重参与当前 N1/K1 计算。
3. A 使用原三分量：signed low16、signed high16、low-negative flag。
   每个分量给每行写一个独立128位 S 记录，feeder 供给各行；后两次使用真实 `load_reuse_b`。
4. `Scale(1,shift=0/16/16)` 与 `Execute(rows=R,columns=1,last_k=1)` 累加全部 K，
   只在第一个 K 的第一个分量清零。没有每 K 舍入，也没有外存 S64 spill。
5. 每行原生 `ReadRawS64` 和 `ReadFinal(width=32)`，通过现有写回客户端写 S 并等真实 ACK。
   一列的低 S32 槽仍是原标量记录格式，不需要动态输入打包或多列输出 scatter。

有限地址：A staging S[0:7]，B/padding S[16:23]，raw 输出 S[32:39]，final 输出 S[64:71]。
探针初始化 S[0:79]，每一例独立复位；不假设其余 SRAM 或 M 数据初态为0。
实际握手、地址和命令由 `tb_row_tile_probe.sv` 驱动；Python 独立生成完整 S64 与舍入/饱和金值。

## 已验证与边界

Icarus12四态仿真：1..8行，K=1/3/7/17，另2行K=2048，正负S32/S16边界及随机数，
正负 half-even ties，最终shift=0/8/16/24，完成背压、S写ACK、feeder A/B握手和宽读数量。
每组同时执行相同数值的逐行R1版本作对照；首轮84个、扩展后184个场景通过。
扩展版另逐边界计量原生M、P命令和feeder，从接受到首次完成的延迟，不含测试台take背压；
[184例和80项分边界记录](../../../work/YUZE-LU/219/throughput-opt/results/column-rowtile-v5/summary-view.json)。
多列激活复用与真实标量转换另见[COLUMN_TILE.md](COLUMN_TILE.md)，没有接入全图前均不算整模型收益。
RTL文件与main `c4d7b960599b9d292f27eb4429d5f226a7156c95`无差异，SRAM银行模型SHA固定。

K2048/R2：B staging 4096→2048条记录，A仍12288条。测试台周期753908→506100，
**含测试台串行事务与故意背压，不是整机时间、300MHz签核或SystemC校准数据。**
这一结果只证明可执行的数据复用及局部开销下降；不计作DP约20%收益。

未覆盖：N>1动态输出格式、动态A打包、任意K段、前缀缓存与新布局互操作、完整MC/LC编码、
实际DRAM字节/控制开销、整模型数值、KV decode、能耗及新物理资格。
Icarus默认四态只是一个仿真初始化模型，不能写成已有Verilator三初态回归。

## 接入算法前必须完成

- 把供数/Scale/Execute/最终写回逐阶段成本登记到同一硬件清单；不能拿测试台总周期直接替代成本。
- 每个候选显式给出行区间、完整K、S布局、B寿命、上下文和ACK释放事件，尾行采用实际行数。
- 现有前缀缓存从S[9:]开始，新布局不能直接沿用。没有真实本地搬移的缓存命中不得减读。
  首版可保留全部旧候选，新多行候选明确流式且无前缀缓存；必须如实计入这项代价。
- 独立检查器重建所有行/列覆盖、逻辑读取与原生命令；数值回放消费相同记录并完成全图对照。
- tile执行器同时提供给贪心、旧DP和强启发式。只有同动作池下的tile/实例/驻留选择额外收益计入算法目标。

## 复跑

`row_tile_probe.py prepare --source-root <仓库> --bank-model <已验收银行模型.v> --output <新目录> --long-k 2048`

在输出目录，用Icarus12：

```
iverilog -g2012 -Irtl/block_v2 -I. -s tb_row_tile_probe -o probe.vvp -f compile.f
vvp probe.vvp > simulate.log
python row_tile_probe.py analyse . simulate.log
```

生成器冻结输入RTL、银行模型、探针和金值SHA，不改源RTL。Icarus10.1不支持当前源的部分SV语法，
首次编译失败原件保留；不能把该工具兼容失败归因于目标硬件。
