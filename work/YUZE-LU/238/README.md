# Issue238 M长K候选

[任务](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/238)；[草稿PR239](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/239)；YUZE-LU；in_progress。

这是PR235/Issue234的独立后续硬件实验分支 `task/238-m-streaming`，以PR235分支为依赖，保持原M RTL和物理包不变。

候选新增op13 B1 K<=256；旧op10及完整S64数值合同保留。B存储增1→8KiB、B tile端点2→5位，尚未清点综合面积/时序；不能当已验收宏替换底座。

[源码差异索引](candidate-source.json)、[手动RTL实验](rtl-result-002.json)、[统一脚本完整重跑](unified-result-003.json)。Verilator5.042、G++11.4、Ubuntu22.04；只用一核本地构建，顺序测试。160新形状×三初态及1024驻留命令/初态通过；原8192形状×三初态周期/数值表完全一致，SHA=a2cfab5ea74fef6ed5612261da0e7171906a947325847642cbab5050c1c86021。K256 S8接收间隔44拍，是RTL微测试，不是整网token/s。

原始源码/操作数/构建与日志已回收到本人远端任务目录，两个包SHA回读一致；详见JSON索引。

未完成：背压/故障/溢出扩展压力、LC/Sfeeder端点和描述符实现、综合面积与电气/物理时序、SystemC及完整Qwen时间/能量。考虑保留小Bbank的连续供数备选，避免用大批存储换性能而不记面积。硬件/配方收益不计DP算法20%。

登记沿用management-hub PR5 pending；缺board配置，Projects unverified/同步pending，复用Issue7交接。待指定独立审查人；不自审、不合并、不标done。
