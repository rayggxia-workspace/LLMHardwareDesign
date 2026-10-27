# 严格C8等价检查的常量单元前端对照

170/92338实际双1CPU图诊断通过，27秒、TotalCPU35.644秒；Slurm MaxRSS返回0，视作无有效采样而不宣称真实内存为0。前后全部已用integer bit和顶层输出均有驱动。A/C未使用DFF QN总数各保持141482，DFF实例无增删；因此没有证据把未匹配PI当作真实电气浮空。

166封存图中before的LOGIC0_X1=995、LOGIC1_X1=9，总数1004；after为1020、12，总数1032，A/C相同。全部原生未匹配标签后缀均79.0.，数量恰好与tie输出对应。这是常量前端处理问题的候选解释，尚未证明具体Naja ID映射；不能因此直接豁免输入匹配门。

新171小例子将分别用真实Nangate Liberty的LOGIC0_X1/LOGIC1_X1、改名tie和resize DFF构造原生对照。native_tie_projection只允许实际库明确单Z输出、function恰好0/1、无输入和时序状态的两种master；必须没有参数、额外pin或多driver。Boolean view删除这些常量单元、将其唯一被驱动bit全部替换为已核明literal；逐位置记录及全部cell原件必须精确逆变换为原图，其他硬件/状态/连线保持。physical Verilog、ODB、PG、时序和功能仿真均保留真实tie资源。

本地用实际Liberty SHA8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1和声明小图检查精确逆变换；错误function/时序状态/pin/参数/多driver五反例拒绝。171尚未运行。实际原生对照必须在保留原始日志的同时，看到literal后严格全部正向边界对应/UNSAT/IDENTICAL通过，改变真实tie极性和DFF时钟均明确拒绝；之后才能考虑完整C8同源重验。该编码不更改native_formal.inspect验收门，也不把任何小例通过当作完整宏资格。


2026-10-27 17:58 CST：171/92340实际两路常量极性对照通过，9秒、CPU6.149秒，MaxRSS=0记为无有效采样。原生改名tie每侧1个未匹配输入；真实库常量literal编码后严格4输入/4输出全对应、UNSAT/IDENTICAL通过，错误tie极性和错误DFF时钟均有SAT/Found difference而拒绝。原inspect严格门不改。172准备对134原失败的两份完整C8图逐项逆变换/发射重读回证明，再重复完整严格LEC；同c96双2CPU，200GiB/路加20%RAM预检，本次提交尚未运行，仍非实际完整C8资格。167最终输出仍RUNNING，未取消旧作业。

完整172重验只读取134封存图，不改变其原失败、实际ODB/PG/RC/时序或功能网表。通过仍需与新167源的完整接收/最终功能绑定，不能把旧图形式结果直接宣布新物理宏合格。
