#102220 RF/scale单位门

执行源`53b9edf5e97787f1c797f535acbb2871b543f175`，c64六任务各10CPU。
严格Verilator编译无新增warning屏蔽；六seed×三初态的18次RF和18次独立
默认三段scale全部通过。每seed约4195条命令，覆盖全部控制/数值/错误原子
和有限16RF复用，独立Fraction/state oracle未改。STEP仍至少3拍，不是
缩短算术；同owner八个head STEP实际逐拍接受并逐拍retire，最多3packet。
三处算术/held-output reset均清除在途与live owner，随后CREATE能重用。

101个小回执已回收，SHA-256为
`54a7a7c1cb486c5b37aefd1d6dd8b15ff43c155e3435e4be902939d8d64f98d2`。
独立auditor核冻结源码manifest、全部回执hash、18份accept/retire CSV、
tag顺序、实际三拍下界、同ctx II1以及峰值3owner；audit.json为PASS。

新two465bit metadata pipeline是实际930bit控制寄存器；没有增加SRAM。
面积净变化需综合：旧scale的previous/bias携带在ROUND_ONLY模式可消除，
不能仅凭寄存器声明推算最终面积。晚读RF的mux+prefix+bias时序也须重新P&R。
此门只证明有限RF/scale，不代表完整M/guard/300MHz或整模型通过。
已交W agent做同源真实leaf联测后再mapping/physical；保守源物理继续保留。
