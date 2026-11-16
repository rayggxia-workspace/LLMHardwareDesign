# 有效操作数范围与有限S布局

这是显式选择的硬件合同，不是免费搬运。旧补零约束和全部旧候选保留。
`resident_mask_probe` 复制未修改的M/P/feeder/16KiB SRAM，删除的仅是测试台对无效字的初始化。
288案例覆盖1–8行、K1/K2、单输出列和九种S16/S32格式；零、一、混合、未知四种SRAM状态均实际执行。
每份日志记录四银行的实际状态编号。有效行读错的故障必须被实际RTL检出。

经此资格化，feeder的A输入只要求前rows个128位字，B只要求第0个字。
其他被宽读覆盖的SRAM字可以未初始化，也可以保存其他记录；其地址范围仍必须落在真实SRAM内。
命令仍限定当前已测的N=1、K1/K2，不外推其他宏/格式。

`operand_contract`须与行服务的RTL摘要和实测服务表完全一致，并具有四个不同状态日志和案例回执。
缺失合同沿用旧模式，伪造字段/不匹配RTL或服务表不能触发新路径。
有限S解释器独立检查同一门槛；它不调用分配器的准入或计费函数。

每次前沿重新判断输入所需的实际前缀是否已经存在。尾部不参与该命令时保留原记录，不能为了满足补零而先搬走它们。
部分覆盖只驱逐实际会被写入的字；未覆盖位置仍在下一状态中存活。
现有8字分配单元和对齐约束保持；未实现任意字间重排或更密的4字对齐分配。
位置不合法或前缀排列不匹配时，仍必须执行实际STORE-ACK/LOAD-ACK。
服务时间不因这个开关改写，只减少确实未生成的补零和布局搬运事件。

```text
python project/experiments/block_synthesis/resident_mask_survey.py IMMUTABLE_TILE_JSON REGISTERED_IR MASK_QUALIFICATION FRESH_OUTPUT --width 8
python work/YUZE-LU/219/throughput-opt/run_mask_services.py PREPARED_MASK_PROBE
python work/YUZE-LU/219/throughput-opt/run_batch_programs.py PREPARED_COMPLETE_PROGRAMS
python work/YUZE-LU/219/throughput-opt/audit_mask_round.py RUNTIME22 REGISTERED_IR FRESH_AUDIT --server-programs RECOVERED_PROGRAMS
```

完整程序探针使用真实M/E、feeder和两个有限S，主机只执行完整字外存读写，检查逐行写ACK和所有输出提交。
这些周期包含观察访问和故意保持响应，不能用作系统时延或token/s。
只读监视器的ISSUE位点计数也只描述该阶段请求的数字乘法位置，不能当整芯片利用率、实际开关活动或能耗。

两行冷tile当前改善约10.51%，但DP相对启用同合同的最强贪心只额外0.577%。
原约束过强带来的纠正收益与DP搜索收益分别报告；不凑20%目标。
尚未完成新完整循环/真实权重/共同图覆盖注册/全模型重编译及SystemC、DRAM、能耗、token/s资格。
