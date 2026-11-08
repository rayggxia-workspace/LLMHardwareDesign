# 原生多列复用与 S32 标量转换

2026-11-09；Issue219/PR220；真实 RTL 局部证据和共同成本配方，**尚未接入完整模型候选池**。
不改变 M/E/S/feeder、端口数、宏数量或 Block 的控制归属，不声明新增物理资格。

## 为什么不只交换循环

现有标量路径在多个输出列之间重复读取 A。现有 M 支持多列，共享同一 A；
但 `ReadFinal(width=32)` 每次给出四个打包 S32，旧程序消费者要低 S32 标量记录。
不能在 Python 侧免费拆包，也不能在原 Dot 累加上下文还活着时清掉 M 去做转换。

`tb_column_tile_probe.sv` 使用不变的 P/S/feeder、compact E 服务、四客户端 S 仲裁和第二颗真实 SRAM S：

1. 准备好的 S32 A 仍用 low16、high16、low-negative flag 三分量。每 K 搬入 r 行 A，
   同时计算 n 列；后两个分量复用已装入 M 的 B。N≤8、R≤8、K段=1。
2. 完整 K 的 S64 一直留在原生 M。最后读取并写 S，检查真实写 ACK、最终舍入及饱和。
3. **先保存全部打包输出**，再复用 M。完整128位记录送第二颗 S，由真实 E 服务 `ASR(15)`
   得到各 S16 limb 的负号，并真实写 S/等 ACK。测试台只搬完整字，不拆包、不做算术转换。
4. M 用有限的离线基向量选择第 j 个 low/high/负号，执行
   `x = low + 65536*high - 65536*(low ASR 15)`，最终原生 ReadFinal写出低S32标量。
   每个输出三次实际 Execute，不能计作免费 scatter。

原生 B 的布局是 **B[n*8+k]**。当前 K段1的每列 B 占一个128位标量记录，
不能将 n 列错误地挤成一次128位加载。首次写错布局的失败及源保留，修复只改测试台。
动态 A 的三分量准备沿用已有准备服务边界，本探针不宣称新验证了一套 CPU 免费准备通路。

## 实际证据

首轮219例、扩展347例四态 Icarus12仿真通过；包含1..8行、1..8列的已列明形状、尾块、
R2/N8/K2048、正负边界/随机数、正负 ties、shift=0/8/16/24，完整S64和转换后S32都对照独立Python金值。
刻意翻转首例S64金值1bit同时被RTL断言和独立SHA门拒绝。

| 已执行例子：Dot staging逻辑记录 | 原逐输出方案 | 多行/列方案 |
| --- | ---: | ---: |
| R1/N8/K17，A | 408 | 51 |
| R1/N8/K17，B | 136 | 136 |
| R8/N8/K7，A | 1344 | 168 |
| R8/N8/K7，B | 448 | 56 |

这是 Dot 阶段记录数，**没有抹去 E/M 转换、基向量、打包/标量结果的读写**。
测试台串行host运输和故意背压的总周期不作产品性能、算法20%或token/s。
E服务 `ASR(15)+S写ACK` 的接受到首次完成时间差14，包含接受拍的串行服务槽15。
M/P/feeder也分别测量，不能拿P命令总成本再叠一次相同的S写确认。

[347例及分边界原件](../../../work/YUZE-LU/219/throughput-opt/results/column-tile-v3/summary.json)、
[冻结输入/源SHA](../../../work/YUZE-LU/219/throughput-opt/results/column-tile-v3/manifest.json)、
[负对照](../../../work/YUZE-LU/219/throughput-opt/results/column-tile-v3/negative-result.json)、
[完整原件归档](../../../work/YUZE-LU/219/throughput-opt/results/column-tile-v3/storage.json)。
测过的形状点登记在 qualification.json；不是所有64种R/N组合都宣称已测。

## 共同成本配方

`tile_recipe.py` 将已测的 P/E/feeder 服务与现有虚拟外存描述符组合，不增加免费本地复制。
只允许准入的形状点及尾块，完整K须满足保守S64界；绑定时还须另查共享静态B、最终shift、资源、地址和端点。

对一个 r×n、完整K tile：Dot的 A读取为 `3rK`，B读取为 `nK`。
当 n>1，设 `p=r*ceil(n/4)`，另计打包结果P STORE、E LOAD/STORE、每输出六次P LOAD
（三次数据、三次基向量），以及最终标量STORE：

```
外存读取 = 3rK+nK+p+6rn
外存写入 = 2p+rn
```

全部grid之前另计16次真实零记录加载。n=1尾块直接原生Final写出标量，不强制走E/scatter。
暂时保留探针实际使用的目的地址，P窗口最高到576字、E占两字；这不是硬件最小S容量结论。
所有中间packed/flag记录都在有限外存临时区显式STORE再LOAD，绝不把测试台变量当成硬件缓存。
当前按完整服务保守占有 M/E/S/LC/通道直到最后STORE ACK，没有跨任务免费重叠。

120组独立逐命令/描述符枚举对照闭式成本，覆盖非整除尾块、缺E/缺形状点拒绝、S64越界、
转换延迟传播与全部读写计数。当前 Windows/独立Linux各169项通过。

接入综合时仍必须同步：只读旧前缀的显式失效、独立原生成本/排程检查器、有限S数值回放、
全图共同候选池与强基线。当前没有这些新计划资格，不将配方本身改善计入算法约20%。

## 复跑

```
python column_tile_probe.py prepare --source-root ROOT --bank-model BANK.v --rtl-ref COMMIT --output NEW --long-k 2048
iverilog -g2012 -Irtl/block_v2 -I. -s tb_column_tile_probe -o probe.vvp -f compile.f
vvp probe.vvp > simulate.log
python column_tile_probe.py analyse . simulate.log
```

准备器逐文件核对RTL与指定Git ref一致，并冻结源、输入和派生include；不会改被测RTL。
完整归档含全部RTL/银行模型/输入，读取资格使用原始冻结目录而不是缺少RTL的轻量索引。
仍无完整MC/LC binary、实际DMA/DRAM、全芯片/后制线、能耗或完整KV token/s资格。
