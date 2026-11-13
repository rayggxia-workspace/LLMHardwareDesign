# 迭代22证据

Issue219 / PR220；2026-11-09 CST；[结果与范围](../../ALGORITHM_ROUND_22.md)。
[evidence.tar.gz](evidence.tar.gz) 3,886,469 bytes，SHA256
`fee3fdd080f1780634ad19b1c4be500f419a813c0bc04c2977813f424582f24e`。
[manifest.json](manifest.json)记录394个逻辑成员，71个完全相同的成员通过aliases复用；全部实际归档成员解压读回验证SHA。
恢复时先校验压缩包SHA，再校验每个成员；别名从指向的成员恢复，不依赖原本机路径。

- runtime/mask-services-v2：冻结未修改RTL、四初态各288例、实际错行故障、合格合同；v1缺少状态区分标记的预实验保留。
- runtime/batch-programs-v1：三策略×四输入×四初态共48条真实完整冷程序；实际M/E/feeder/S和外部整字搬运，错行故障被检出。
- runtime/batch-programs-v2-profile：只读监视器的12程序；ISSUE请求位点约1.745%，不是系统利用率或能耗。
- runtime/masked-v209-r2-width2：完整计划、四输入、冻结算法和数值回执；width8在mask-partial/generated-2，仅有限S验证，尚未完整RTL。
- layout-terminal：101660终态COMPLETED0:0，3tile/18计划/72独立重验；负结果完整保留。
- mask-partial：101683运行期间已完成的两行不可变文件及SHA；receipt状态是当时RUNNING，不是整个调查终态。
- frozen：attempt303提交时的源tar；previous-audit保留上一轮零静态死spill的分析源和结果。

[独立综合审计](audit.json)、[旧布局终态审计](layout-terminal-audit.json)、
[宽2逻辑流量](traffic-audit-width2.json)、[宽8逻辑流量](traffic-audit-width8.json)可直接查看。
执行与准入合同见[RESIDENT_OPERAND_MASK](../../../../../../project/experiments/block_synthesis/RESIDENT_OPERAND_MASK.md)。

流量审计先执行所有输入的独立数值回放，再观察每次写入和剩余副本；已有副本不授予免费布局转换或跨S链路。
这是合成边界/随机输入的冷tile证据，未完成新实际权重、循环、共同注册、整模型、MC/LC/DMA、DRAM、SystemC、能耗或token/s资格。
20%算法目标未达到；强贪心启用相同能力，同合同DP额外只有0.57703%，旧过强补零约束的修正不冒充算法收益。
