# S16桥接及8路E流水落地研究

Issue247 / PR243，负责人Melodydt，2026-11-10 Asia/Shanghai。
修改前备份task/247-before-s16-vector8@ddc12651e35035a25a206d2bdfe46d154864f2d8。

现有N支持8个packed S16；现有E已是8条S16。旧模型vector_lanes=4/8指条件服务，
不能把其直接称为RTL通道数。新增内容均为默认关闭的候选，频率和整图资格未继承。

## S16输入到S32结果

pu_u_group的NEXP_S16=1，且NEXP_BATCH/DIRECT同时启用时开放op15/tag NX16（0x4e583136）。
count=1..8，单源128bit packed signed16；尾部未使用的输入被清零。复用原NExp stateless op12，
每个U16结果零扩到32bit。count<=4写一个128bit字，否则写连续两个字，每次均等实际ACK；
done_data返回低128bit，高半由S保存。count>4且不存储、目标1023、非法count/来源/直接传递均拒绝，
不得在拒绝时访问S。输入与输出可别名，因为所有输入在写前捕获。reset可留下部分输出，需要调用者重装重发；
不会保留旧完成事件，不保证两写事务原子性。原S16 packed输出和NX32协议完全保留。

## E可选流水

block_v2_e_pipeline保留现有14种算术/量化合同，8条S16、4级流水、独立并行A/B/C输入下目标II=1。
全流水在输出背压下冻结，非法操作返回零/错误。block_v2_e_compact新增PIPELINED，U新增E_PIPELINE；默认0。
compact串行A/B/C及U的单命令S取数仍有独立限制，不能据核心II=1宣称完整U每拍8个S32。

## 验证与运行

仅在授权服务器个人全新RUN目录准备SHA锁定source/和inputs.json，复制job.sh后执行sbatch --parsable job.sh。
run.py会验证冻结基线、真实SRAM模型、源码/输入SHA、Slurm核数，然后进行：

- 旧U与默认新U逐周期/数据/存储事件对比，三组初始化/seed。
- 新桥接1..8尾部、未使用输入、输入输出别名、非法描述符、第二写ACK、背压及reset。
- 原NExp全signed16数域与历史scalar路径比较、提取真实packed16计算服务。
- E全部16个操作编码×32种shift×8数据组，用独立Python整数RNE/饱和oracle核验。
- 核心连续输入、随机间隙/背压、reset与有限4级在途证明；完整U内64项数值/周期对照。
- 功能通过后同库综合E核及N前端，报告增量，不称全U/芯片面积或STA。

原四工作负载的SystemC评估需等真实profile产生后另运行；S16桥接费用可由RTL观察校准，
宽向量整条路径未闭合的配置仍标为条件目标。禁止以核心局部增益直接乘旧token/s。
