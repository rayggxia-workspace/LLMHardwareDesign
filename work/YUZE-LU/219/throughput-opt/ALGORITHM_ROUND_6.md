# 迭代6进行中：实际 tile 复用与接口成本

2026-11-09 CST；Issue219/PR220；原生tile通路与成本配方的部分交付。
完整目标继续 in_progress，未声称新增整模型加速或算法约20%。

## 外存问题没有解决

现有完整执行器主要仍是标量记录流式服务和受限只读前缀缓存。
此前资格化计划中 A 重复读取占逻辑记录约65.8%，静态 B 约23.4%；
不是测量得到的 DRAM 字节、带宽或功耗。阶段重叠的改善不意味着访问被消除。
参见[有限 S 与复用合同](../../../../project/experiments/block_synthesis/MEMORY_REUSE.md)。

## 新增实际证据：184个四态场景

在迭代5原生多行探针上补齐 R=1..8 的尾行，K=1/3/7/17，另 R2/K2048、正负 half-even ties。
同一数值分别运行多行及逐行版本。所有184例的 S64、最终S32、背压和真实 S 写 ACK 检查通过。
被测 M/P/S/feeder RTL 与前轮完全相同；只修改测试台和证据分析器。

新增被动计时，不驱动 DUT。三个边界分别记录请求被接受的上升沿到首次完成有效的上升沿之差；
故意施加的完成 take 背压不计入这些延迟。每种边界的样本数量由各例 R/K 和命令次数独立守恒。
观察到下表，R1..8 均有真实测量，表内公式只是这些已测点的归纳，不外推到未测配置。

| 边界 | 上升沿时间差 |
| --- | ---: |
| 原生 M Scale | 1 |
| 原生 M Execute，N1/K段1 | 10R+11 |
| 原生 M ReadRawS64 | 1 |
| 原生 M ReadFinal | 4 |
| P命令 Scale（含适配） | 3 |
| P命令 Execute（含适配） | 10R+13 |
| P命令 Raw并写S/ACK | 8 |
| P命令 Final并写S/ACK | 11 |
| feeder 首次含 B | 2R+10 |
| feeder reuse B | 2R+6 |

各表项所有样本 min=max。原生 M 的 R1 Execute 时间差21，计入接受拍为22，
与既有序列驱动22的边界相容；Scale/Final同样分别1+1=2、4+1=5。
P命令已经包含适配及指定写回，不能再机械叠加一次相同 S commit；
还没有把这些点当作完整 LC/DMA/系统校准或最终服务成本。

[184例结果与80项分边界测量](results/column-rowtile-v5/summary-view.json)、
[原始日志](results/column-rowtile-v5/simulate.log)、
[冻结源/输入SHA](results/column-rowtile-v5/manifest-view.json)、
[10份回收文件SHA](results/column-rowtile-v5/receipt.json)。
含CRLF的六份原件以gzip保留全部原始字节，JSON另提供LF阅读视图；[压缩/视图索引](results/column-rowtile-v5/compressed.json)。
冻结生成器是在本轮最后一次分析器防护修订前复制；其SHA保留不改，
当前分析器增加了额外行覆盖拒绝检查，未改变该冻结包的生成逻辑或 DUT/测试台。

新增分析器回归：缺项、重复、错误行、样本篡改、无效时长及截断执行应拒绝；
可变延迟原样保留，不能偷偷当作常数。后续连同多列/成本配方共169项，Windows与独立Linux都通过。
冻结生产源和Linux日志见[原件](results/column-tile-v3/linux-tests.log)。

## 接入前必须解决的实际耦合

1. 多行 N1 共享 B，尚未减少主要的 A 重复读。原生多列可共享 A，但其打包输出不是当前低S32标量 ABI。
2. 新 staging/输出槽覆盖旧 S[9:] 前缀。首版流式 tile 可以显式放弃只读缓存，
   不能仍记录命中；必须同步搜索、独立检查与有限 S 数值回放。
3. 静态 B 必须对所合并行共享。不能把 batched Attention 的不同 B 当作同一权重；
   首版只考虑有源引用与形状证据的共享静态 B。
4. 原生多列输出 scatter 已验证下面的现有宏配方，无需据此增加计算宏。
   先把所有 packed S32 输出真实写出，在原 Dot 上下文释放后，
   用现有 E 算术右移15得到各 S16 limb 的负号，再由 M 选择对应 low/high/负号分量，
   按 `low + 2^16*high - 2^16*(low>>15)` 重建每个 S32 标量。
   实际P/S/feeder、E服务及第二颗S完成347例，host只搬完整字，转换由E/M执行。
   物理端点和真正DMA/LC时序仍需验收，不能把测试台完整字复制当作完整产品搬运资格。
5. 所有合法 tile 执行器给同池贪心/旧DP/强启发式共同使用。后端改善单列，
   当前状态下 tile/循环/实例/驻留选择带来的额外收益才计算法收益。

## 多列通路与实际成本

见[完整服务合同](../../../../project/experiments/block_synthesis/COLUMN_TILE.md)。首轮219、扩展347个四态RTL场景通过，
含尾块、R2/N8/K2048、完整S64、四种最终shift、原生转换后标量S32和真实写ACK。
故意翻转首例金值1bit，被RTL断言和SHA门拒绝。首轮B布局把`B[n*8+k]`写成了另一种排列，
在首例即被检查器拒绝；源和失败原件保留，修复只改探针，不归因目标硬件。

R1/N8/K17：Dot A staging408→51、B仍136；R8/N8/K7：A1344→168、B448→56。
只是Dot阶段逻辑记录数；实际E/M转换、基向量、临时结果往返没有被抹去。
E服务含本地读写ACK的接受到首次完成时间差14，串行服务槽15；不含DMA/LC，不作系统性能。

`tile_recipe.py`按已测形状点构建共同成本，逐命令/描述符显式枚举120组随机尾块对照，
拒绝未测形状/尾块、缺E、S64越界和篡改回执，全部私有S/临时外存/命令开销仍须在实际绑定时验收。
尚未接入完整DP候选、缓存失效、独立整网检查和数值回放；新tile不计算法收益。
[347例结果](results/column-tile-v3/summary.json)、[源/输入](results/column-tile-v3/manifest.json)、
[负对照](results/column-tile-v3/negative-result.json)、[21份SHA回收](results/column-tile-v3/receipt.json)。
全部冻结RTL/银行模型/输入/失败和最终编译器源已归档，压缩包794127B，
SHA256 `8cf33a18cfefab8314629ecefb35960906b4f84827d43aa6c7123910cd121886`，已双端核对，
见[获授权服务器存储索引](results/column-tile-v3/storage.json)。

## 前轮全图数值终态

101213已COMPLETED0:0，4CPU、UNLIMITED。回收6份原件逐项核SHA；完整Qwen2.5-3B、36层、
B1/S2 prefill、无KV，新阶段计划三输入均与原整数程序逐位一致。
HF相对L2仍0.5265177%/0.7250722%/0.5591736%，各位置argmax与logits SHA保持。
输入IR SHA `9fddf5df95e1bc08ae5445b8b09c50a596fd629226b99924243525904c2622a0`、
计划SHA `47077e02ca1ed49f4a181e58ad14a5bc8e0dd542bd34510bc11f9e7ae4e527a8`，
逐项匹配前轮完整Linux输出，不是旧计划重复回放。
[终态回执](results/column-round5-replay-final/receipt.json)、[数值日志](results/column-round5-replay-final/replay.log)。
**这验证的是迭代5阶段计划，不是尚未接入的迭代6tile计划。**

本轮只读核对100972仍RUNNING、UNLIMITED，不取消或重复提交。
一般驻留、算法约20%、完整tile计划数值、校准时间/能耗/KV token/s及最优适配ASIC/FPGA比较仍待完成。
登记pending、看板unverified/同步pending沿用既有回执；未改变在线任务状态或自合并。
