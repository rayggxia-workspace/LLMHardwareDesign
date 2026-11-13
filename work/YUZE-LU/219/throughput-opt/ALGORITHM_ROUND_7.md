# 迭代7：受限tile接入与外存账（部分交付）

2026-11-09；Refs #219 / PR220，继续in_progress，不作为算法20%或系统性能验收。

此前完整Qwen2.5-3B B1/S2无KV计划的逻辑搬运约65.8%为A重复读、23.4%为静态B；一般tile/脏结果驻留未解决。
此次复用迭代6不变M/P/E/S/feeder的已测配方，保留全部旧候选，新增准入形状/尾块、真实转换/描述符、有限S与外存临时区。
每次贪心/DP扩展明确使被覆盖的P.S旧前缀失效，后续使用必须冷填充。独立检查器重推全部工作、成本、地址、资源和静态端点。
没有免费scatter、额外M上下文或不计成本的动态打包；packed/flag均为显式外存对象。

**同一E叶宏不代表相同外围适配器。** 新服务必须提供`native-tile-instance-services-v1`清单，包含规范资格表SHA、P/E实例名单及来源证据。
本次核对c4d7b960源，将PU P服务绑定P0/P1/P2，四客户端compact-E服务绑定U0/U1；C/F/J不自动继承。
这只证明原生服务候选模型的绑定，不声明完整MC/LC/DMA或物理实现已验收。

`tile_replay.py`逐K/分量使用有限128位SRAM字、最多8×8 S64累加tile、ReadFinal打包、逐S16 ASR15与三次M scatter语义。
下游消耗实际重建S32，独立参考只作对照；损坏基向量必须失败。PreparedOperands只保留当前外存准备区引用，绝非新增本地S。
搬运/占用/描述符报告同步；P/E服务包含适配和ACK，不标成纯MAC周期。S64界计入分量校正前的瞬态上界。

Windows与独立WSL/Linux CPython3.12.8各 **178项通过**，冻结160个源文件。
包含尾块、负数/饱和、S32边界、shift0/8/16/24、失效/冷填充、伪造成本/资源/常量拒绝及有限S小例子数值。
既有347/184例RTL资格不扩大为完整新计划RTL通过。

真实首层FFN：88原语、74服务，九组、每S16KiB、相同18束上限；准入180个新绑定，共2885个已审计绑定。

| 配置 | 模型ticks | 逻辑128位搬运记录 | 选中线束成本 |
| --- | ---: | ---: | ---: |
| 旧动作池已有计划 | 11,261,130,658 | 593,160,141 | 18 |
| 新同池贪心 / HEFT式基线 | 5,924,316,864 | 195,172,656 | 10 |
| 新同池旧DP / 条件尾部DP | 5,304,003,776 | 195,172,656 | 18 |

搬运下降 **67.0961%**；旧动作池到新选中计划模型时间下降52.8999%，共同后端扩展**不计算法20%**。
新DP比同池贪心好，但条件策略相对同池旧DP额外仍为 **0**，不能选择较弱分母宣称达标。
实际10/18束分别列出，不假装选中连线数相同。A加载50,724,864条、静态B67,633,152条，另有真实零/基向量/转换搬运。
P峰值528字，旧预处理的其他S服务峰值8字；不把剩余S当成已实现的一般缓存。

**该FFN计划及新tile整网均未完成数值回放。** 这里只新增有限S小例子数值和真实切片规划/搬运审计；
完整36层三输入的最新已验数值仍是迭代5旧计划，无新SystemC整机、KV decode、能耗、token/s或FPGA对照结论。
3–4B权重装不进局部S，B1 decode仍需权重流式读取；prefill可跨行复用。逻辑记录数不能冒充实测DRAM字节。

[35份精确字节压缩原件/SHA及源快照](results/column-tile-round7/compressed.json) · [有效结果阅读视图](results/column-tile-round7/summary-view.json) · [开发失败](results/column-tile-round7/failures.md)。
首次错误套用C/F/J成本的试验整体作废，原件在`superseded-unqualified-E`；有效试验在`valid-ffn`。
首次新测试因方法插入位置错误报IndexError，移动原负对照回原方法后完整回归通过，没有删除检查。

恢复索引中的before-ir、instance-services、旧计划及迭代6资格原件后，可复跑：

```text
python project/experiments/block_synthesis/tile_review.py BEFORE_IR NEW_OUTPUT --column-proof COLUMN_V3 --row-proof ROW_V5 --instance-services INSTANCE_SERVICES --wire-budget 18 --incumbent OLD_SELECTED --write-ir
python -m unittest discover -s project/experiments/block_synthesis -p "test_*.py"
```

后续：有效FFN及新整网数值、占用分析、实际可实现的驻留/调度优化；新能力共用强基线，缺硬件通路另建PR。
算法约20%、更多轮、完整KV/校准SystemC时间能耗/token/s及最优适配ASIC/FPGA仍未完成。
登记pending，看板unverified/同步pending，待独立审查，不自合并/关闭。
