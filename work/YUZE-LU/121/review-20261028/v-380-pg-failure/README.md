# V380 finish 供电与时钟短接失败

Refs #121 / PR #122。93441/node17于2026-10-29 23:43 CST自然FAILED/1，已完成synth/floorplan/place/CTS/route五阶段；finish失败，6_finish最终RCX时序报告未产生。

6_report.log明确：VSS与clk在metal3的(525.910,340.150)–(526.035,340.270) µm短接，PSM-0043后PSM-0069 VSS连接检查失败。不是内存或观察超时：原进程树RSS采样峰约22.49GiB，保留原回执/状态/数据库。原生详细route计数0不能覆盖finish的PG短接失败。VDD连接通过及工具功率估计不构成整块接收或功耗资格。

流程内最终LEC实际UNSAT/IDENTICAL，51206公共输入/51195公共输出、diff0/diff1全0，仍不能绕过PG门。源5a6e0be8/归档b6854770；15原始文件SHA/长度、failed receipt与源归档输入核验，308源Git/远端绑定沿用同一v-380-stages-diagnosis/verification.json。

当前仍只有一个基础V实现；不缩位、不降频、不改验收门。后继381/382不会用失败380充当前置。只读诊断384在原R344/93237/node21空闲16–31槽启动，无新增allocation，原ODB不写回；最终修复尚待实际几何定位。R344继续原全局布线，345/346待真实前置，M/S/T保持。
