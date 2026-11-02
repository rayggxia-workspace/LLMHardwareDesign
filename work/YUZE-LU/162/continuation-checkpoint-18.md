# Issue162 continuation checkpoint18

捕获：2026-11-02T23:49:44.473371+08:00；YUZE-LU；[Issue162](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/162) / [PR163](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/163)。继续in_progress/Draft，不合并。用户决定：S内部补输出驱动，整块重新验收；其他五宏和原S基线保留；R保留并由并行任务修改。

[证据索引](continuation-proof-18/index.json)：75项远程源绑定记录，74项原文件逐字节复制并复算SHA；1项大报告保留远程路径/大小/SHA。另存本地配置防护检查脚本。运行中的日志/队列状态仅代表捕获字节，不要求其后可变路径仍同SHA。

## 真实定位结果

source123诊断因过窄16层锥边界失败，source124全树清单因超过128支路保护失败；两次原失败完整保留。source125改为从实际GRT最差路径提取feed_input_receiver_174→input175锚点，并验证原ODB连接，测量其全部8条直接负载，实际只读诊断通过。没有修改数据库或SDC；它使用完成GRT数据库上的placement RC，不能当作最终RC或验收。

8条支路中5条AOI21_X1/A的hold约−0.53至−0.61ns，setup约+2.99至+3.08ns；另一条AOI hold约+0.00115ns，另两条缓冲支路setup已很紧。因此准备只在5条快AOI复位输入前增加真实BUF_X1链，不延迟整个复位根、不动其他数据输入、不增加寄存器或周期。每条96/128两个候选；实际全局RC下先复核setup≥2ns，修改后复核该支路min/max非负及电气/setup违例端点不增。完整最终300MHz、全端点电气、DRC、功能及严格LEC门保持不变，局部检查不能替代这些门。

源绑定ECO代码在本次检查点仅完成准备和本地防护验证，**尚未运行真实ECO**。本地检查按source125真实测量确认仅选0/2/3/4/5五支路，拒绝错误master/net/注入名称/裕量不足/额外负支路/非只读证据/非法级数；Tcl语法完整性通过。py_compile和git diff --check通过；这些不是EDA通过证据。

ECO将复用严格绑定的已完成placement/CTS/GRT优化，重跑局部修改、route/finish和全部最终门。源原流程后来失败也只允许复用可核实的成功前四阶段及精确GRT检查点，不继承route/final或验收。SKIP_INCREMENTAL_REPAIR/OPT_POST_GRT_WNS只避免重新进行已完成的全网优化，不更改约束与最终门。新增组合延迟及788输出BUF_X32都归S M1–M10，最终ODB必须逐个证明保留。

## 资源及后继

仍为8个自有节点，c96 6×16/c64 4×16独立任务动态补位。为32GiB诊断腾出准入内存，只取消自有旧route seed927的95119.33、seed929的95119.35两个step，同placement其他候选仍在；父分配、四个新S、其他任务均未动。释放一个后含保护要求476.8GiB仍高于实际可用约449.7GiB，因此再释放一个32GiB预测，保护要求降到438.4GiB才准入。取消不是物理失败，原记录保留；没有降低内存保护系数或新S128GiB全流程预测。

捕获时四个S尚无原生最终资格；随后实时观察1181/1182已有6_final.odb，1180/1183仍在详细布线，此实时观察不在该捕获的SHA快照内。生成文件不等于时序/DRC通过。新S合格后才能替换实际组合并完成全部M11/M12几何/PG/low-base-high实际RC/300MHz及联合六文件、版图和源绑定索引；不能用旧335组合或单块通过宣称系统通过。

规则rayggxia-project-collab1.0.0；登记management-hub PR5 pending；缺board.json，看板unverified/同步pending，处理人待指定。负责人YUZE-LU持续执行；审查人待指定。
