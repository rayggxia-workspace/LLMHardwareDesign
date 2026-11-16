# 连续元素的有限 S 状态与完整循环成本

2026-11-09，Issue219/PR220，迭代16。原有冷启动候选保留；`--continuation`额外注册连续执行候选。
这里解决循环内部的只读数据/保护字/B银行继承，不宣称一般跨服务脏驻留、跨S直接传递或搬运计算重叠。

## 初态必须来自实际前序程序

`resident_records.plan(..., persistent=..., initial=...)`在每个原生命令前沿重新选择有限S中的位置、替换与必要写回。
可继承的对象仅为图中常量和整段循环中索引不变的标量输入。数组第i个元素的中间结果不能冒充第i+1个元素。
状态还包含实际已初始化的M保护字位置，以及有身份的M B银行；不继承累加上下文或旧的脏备份。

`resident_replay.replay(..., session=...)`继承真实有限数组、标签和银行内容。
每次进入都检查地址/索引/数值/银行身份，清除未声明的旧标签，所有新数据仍须执行LOAD或原生命令。
单独执行热程序、凭相同符号名复用另一个数组元素、损坏的保留字或银行均会被拒绝。
全部live_out依旧STORE并等待ACK，跨私有S仍执行明确的外存中转。

## 计算整个循环，不能只用稳定段乘元素数

`resident_continuation.compile_loop`从空的逻辑初态开始，生成一个程序，再将其实际可继承末态作为下一次输入。
固定的分配策略会产生一段过渡，之后可能进入状态周期；周期可以有多个程序。
只有初态元数据完全相同才认为重复，搜索上限内未闭合则不注册该连续候选，原冷候选继续存在。

若有c个前缀程序、周期长p，N-c=qp+r，则完整成本为：

`C(N) = Σ前缀成本 + q·Σ周期成本 + Σ周期前r项成本`。

LOAD、STORE、经测量的计算/供数服务都逐项累计，包含第一次冷启动和最后一个不完整周期。
`verify_resident_continuation.py`独立重建不变量、前序连接、周期闭合和完整计数；不调用分配器。
连续数值回放实际执行各个程序，不通过相减若干ticks来模拟缓存。

此处固定策略的重复不是跨所有迭代的全局最优DP。它将不同分配策略的完整可执行程序作为共同候选，
供原图覆盖前沿选择。外层仍根据当时的资源/缓存失效/静态网集合计算转移；一个候选预留整个相关S，
入口不借用外层旧缓存。因此封闭服务的完整执行成本可以预先计算；一般跨服务热入口尚未实现。

## 运行与验证

```text
python resident_cover_survey.py CLOSED_IR FROZEN_PROFILE_PROOF FRESH_OUTPUT --width 8 --wire-budget 18 --cover-lengths 2 4 8 --continuation
python resident_cover_compare.py REGISTERED_IR FRESH_OUTPUT --width 8 --rank hypergraph_completion
python -B -m unittest discover -s project/experiments/block_synthesis -p 'test_*.py' -q
```

`resident_loop_replay.Execution`支持连续实际SRAM会话，将每个元素的原生结果接回原整数图。
`resident_model_loops.py`沿用完整权重/输入/原输出哈希门槛；替换切片通过不等于全36层均在新硬件程序上执行。

`resident_continuation_probe.py`在冻结的原P/M/feeder/E/S RTL上生成多元素链：每链只复位一次，元素间不复位。
全部数组输入逐元素变化，检查真实写ACK和响应保持。另加独立SRAM观察读检查继承保护字，观察读不算外存搬运，
也不计入被动测量的计算服务槽。未使用的M行可能不影响被选结果，所以不能仅靠算术错误判断保护字合同。
故障注入分别检查保护字合同，以及清除B银行后的原生命令失败。正/负原件和初版失败均保留。

上述时延仍是原生服务槽加显式虚拟外存模型，不是完整控制/DMA/DRAM校准，更不是能耗或token/s。
真实FFN新共同候选的收益、同池强贪心与DP差异必须分开记录，不能将减少重复常量初始化算成DP独有20%。
