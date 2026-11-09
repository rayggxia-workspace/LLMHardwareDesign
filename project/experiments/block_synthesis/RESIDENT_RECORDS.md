# 原生 SSA 与有限 S 驻留原型

迭代15本地更新见[凸覆盖与实测成本合同](RESIDENT_COVERS.md)：已增加服务时延目标、实验候选注册、
按原task完成数分桶的统一前沿和每元素有限S回接。真实3B与全图搜索资格待新服务器作业终态。
以下是迭代14已发布的原型证据与当时缺口，不代表迭代15尚未注册实验候选。

2026-11-09，Issue219/PR220。它尚未注册完整综合器候选，不能把结果当作整模型加速。

当前完整后端有只读 Dot 缓存、受限 tile 和准备复用，但仍大量写出、读回中间结果。
切 tile 本身不保证节省外存；本原型检验实际原生命令是否能从仍在 S 中的记录继续计算。

## 数据与命令

`native_pointwise.py` 将连续同形状 Convert/Product/Add 降成带身份的128位记录和原生 M/E 命令。
原有 split32、M高位提取、E Min/Select、乘加、最终RNE/饱和全部保留，不隐藏CSE或新增算术。
分叉的外部消费者显式成为 live_out；归约、视图和其他算子是边界。

`primitive_slice.py` 从完整图取切片，保留依赖常量、格式及上游边界的来源SHA。
`verify_primitive_cost.verify_source_closure()` 拒绝未声明的操作数。
旧FFN诊断切片丢了v11/v178/v39常量定义及v201上游边界，不能继续充当完整地址资格；
修正切片与旧切片之间的成本下降不计优化。独立重新核验完整8850指令图仍通过。

## 每次前沿实际决定什么

`resident_records.plan()` 的状态包含各S物理槽的记录身份、有效外存副本、
已初始化的宽读保护区、M的B银行身份及累计LOAD/STORE代价。
动作在当前状态中选择实例、实际空槽或替换对象，必要时先STORE并确认，再LOAD并确认。
脏值仍有消费者时不得丢弃；结束时所有live_out必须提交。跨S暂按外存中转，不假设新直连。

对一条实际状态转移：

`g(s') = g(s) + Σ LOAD_ticks(actor) + Σ STORE_ticks(actor)`。

命中实际S记录或有效B银行才省对应LOAD；替换脏记录才产生必要STORE。
这是**串行复制成本**，不含M/E计算时长、并行、母控/局控或真实DMA时序。
不能把copy_ticks直接当整段耗时。宽度None仅用于有限小图穷举；有界DP仍是启发式。

可选`future_copies`以忽略容量/替换冲突的必需复制乐观下界排序。
E小图的多种前沿与独立集合穷举后缀对照；M/E完整计划再经独立有限S回放。
下界不能保证有界搜索优于贪心，因此保留同池最强已验贪心和旧DP。

## 本轮实测范围

真实来源闭合FFN的6个区域、58个原语、18个首/中/末位置，共216个合成边界数值案例：
原整数参考、原生字解释器和实际有限S回放一致。它们不是实际权重/输入的完整FFN执行。
同一动作池的18个位置样本复制成本：强贪心41694，保留最强计划41526，少0.40294%。
对每操作写出的参考122172的显著下降主要说明新增驻留执行方式的机会，不能记作DP约20%。

`resident_probe.py` 在不改功能RTL的P/M/feeder/S与compact E/S上执行生成事件。
6个FFN区域加1个S32边界诊断，8输入模式、3策略，共168程序；三SRAM初态均通过。
M使用4个受限保护槽，E用3字窗口，平移到不同银行及S末端，含实际读写ACK和背压保持。
主机只搬完整128位字，不做拆分/算术；真实负对照修改首个M结果校验位后报错。
探针周期包含额外结果观察和故意背压，不是可用的吞吐校准。

## 继续接入所需条件

1. 凸区域作为同池候选接入完整DP/贪心；与原算子依赖、S缓存失效和真实地址复用保持一致。
2. 显式分片并计入计算、供数、端口、描述符、静态网及所有必要外存中转；保留原方案。
3. 独立重建命令/地址/成本，回放选中方案的实际模型边界数值及完整图。
4. 完整KV、校准SystemC时间/能耗、token/s和最优适配ASIC/FPGA对照继续未完成。

复跑（数据包路径见任务迭代14归档）：

```powershell
python -B -m unittest discover -s project/experiments/block_synthesis -p 'test_*.py' -q
python project/experiments/block_synthesis/resident_survey.py <closed-ir.json> <native-regions.json> <result.json>
python project/experiments/block_synthesis/resident_probe.py prepare <frozen-column-proof> <bank.v> <closed-ir.json> <native-regions.json> <fresh-output>
```

原生仿真在输出目录用Icarus12执行`iverilog -g2012 -I. -Irtl/block_v2 -s tb_resident_probe -o simulate.vvp -f compile.f`，
分别`vvp simulate.vvp +sinit=0/1/2`，再由`resident_probe.py analyse`逐项核验。
