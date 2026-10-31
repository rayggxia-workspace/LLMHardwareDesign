# V320：316完整placement只读诊断

Issue #121 / PR #122。实际捕获2026-10-29T00:37:18.597811+00:00；93096自然COMPLETED/0:0。仅在316真实do-place完成后提交，原316继续CTS，没有修改原ODB/SDC/输入网表/配置/库/RC文件。

原生placement估算、ideal-clock：setup worst −1.595670104ns，hold worst −0.004727372ns，8980 setup/3 hold违例。最差max路径cmd_data[12]→slice599370/D，Q直接对应实际输入网表group_unit.denominator[79]，与先前global-place/resizer定位同一分母寄存器。path-source-mapping.json保留原路径和真实端点/输入声明。

11原始文件、7稳定输出、303归档Git blobs与实际receipt输入核验。诊断执行成功不是时序通过，不能授予316或修订322资格；新源322必须自行完成全部原生阶段和独立最终门。
