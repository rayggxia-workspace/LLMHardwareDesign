# R3 真实四-bank有限 M 服务测试

Issue247 / PR243；2026-11-10。本目录提供独立数学/布局oracle、向量和testbench；RTL由feed/round3提供，runner/job/control replay由root和模型代理提供。正式位置统一为 `project/experiments/rtl_iterations/round3`。不改正式M/P合同，不改R1/R2，不在Windows或登录节点运行EDA。

当前仅执行Python AST、任意精度oracle和生成检查，未运行RTL。测试通过与实际周期只能依据后续Slurm回执。

`numeric.py`不导入RTL或条件模型，使用Python任意精度计算S32×signedW8、完整K前缀、负数floor余数RNE及S32饱和。`vectors.py --out NEW`产生固定seed的vectors.txt/json，其中所有计时输入均来自有限16KiB实际S图像。oracle另验证初始化完成后的最终memory图像仍逐packet匹配预期，防止重用源地址被后续fixture覆盖。

最终suite共66个case：K/N尾与0/1/16 shift、8个明确非饱和正负奇偶RNE ties、A/B/out最后合法位置、未对齐B跨三line、非法tag/first/nextK/N/total/地址、final closing、读response延迟4、写ACK延迟4、done hold至8票满；完整同ctx K2048/K11008，及8ctx按每ctx16包旧group顺序的完整K2048/K11008。仅四个完整大K case为qualified、无人工hold，主合同是W8/r1/N8/shift16/K16 packet。

长K数据是按有限源位置重复的确定性不同packet数据，并非真实模型权重。每个packet仍实际读取A64B和B128B；没有用testbench直接供A/B或减少S事务。所有slot/列、不同B组使用可区分数据和32位tag；原始S初始化及最终结果读回在计时区间外，全部经真实128bit S请求/ACK支付。每个有效packet在实际leaf commit后读取真实S96寄存器逐列比较，最终还经真实S回读全部输出。

testbench唯一参数BUFFERS=1/2，两个配置采用同代码/输入/8 completion tickets/2 read metadata/同延迟策略，只有输入槽容量不同。每槽A64B+B192B=256B，BUF2没有额外MAC或SRAM端口。实际选中后端为正式 `block_feed_s16k_sram.sv` 与固定SHA的真实4×256×128 1RW功能宏；最多64B读或16B写，服务不同时发读/写。首末S请求/response、写/ACK、接受/commit/退休均守恒。源槽在leaf input_accept就释放，未把单buffer故意拖到drain。

R3_PASS实际包含20个不同reset时点，复位同时作用于服务和S后端，恢复20个周期内逐周期禁止幽灵请求/完成。响应hold期间严格检查数据/状态稳定；read request为逐边offer合同，可因写优先暂停未接受请求，未接受不计事务。

## 编译和输出协议

父代理在4核Slurm中使用相同Verilator5.042，顺序编译两个BUFFERS值，运行1:143、2:143、2:144。SV编译源为 `tb_r3_m_finite.sv,r3_m_finite.sv,m_s32_stream_candidate.sv`、正式S控制器和固定SHA bank。每个binary使用独立cwd，复制生成的vectors.txt后运行；所有副本SHA必须相同。源/输入/工具版本、bank/source/generated/log SHA和实际命令留回执。

每个cwd产生：

- stdout中的 `R3_CASE` 为实际计数与周期；`first_accept,last_done,next_ready` 全是control.txt同一globalcycle。
- `accepted_to_done_cycles` 为首cmd接受到最后done**消费**；`accepted_to_next_ready_cycles` 另在所有done退休后，用合法未来FIRST、valid=0且descriptor_ok&&ready观察真正可接纳边沿。不能取invalid descriptor的ready作新服务可用。
- `R3_EVENT` 保存主要case的真实请求/ACK/leaf/commit/done事件。控制费用重建以连续control.txt为完整来源，不依赖stdout精简事件。
- `control.txt` 每周期47个十进制字段，前20是control_probe输入（含cycle），后27是实际pre-NBA控制观测（首项同一cycle）。从初始reset一直连续记录，包含初始化/运行/回读和reset压力；具体顺序与模型代理control-protocol.md一致。无效payload按valid mask比较，初始第一个reset边沿前的随机未初始化值不取得资格。
- `R3_PASS buffers/cases/checks/reset_cases` 在全部实际S回读、前缀断言及reset检查后才出现。

完整RTL连续程序的wall是该实际驱动程序的结果，**不直接当旧K256服务费用**。旧模型主方案每old tile发16个同ctx K16 packet并等全部tickets退休，再推进下一old tile；context保留但不跨old tile预取。独立有限控制FSM先与同外部ready/response/done输入逐周期比对，再把S外部条件换成旧Calendar；S请求每笔只预约一次，最终真实两写ACK替换原p_result_store，DDR/WB边界另保留。不同策略不能混用连续RTLwall申领收益。

声明寄存面积代理由feed账本列明。独立核对BUF2−BUF1为2048 payload＋110 metadata=2158位=269.75B，两个配置的read/completion credits和leaf固定。它不是综合FF数、mm²、P&R/STA、功耗或300MHz资格；S仍16KiB，不宣称完整P/DMA/LC或完整LLM实际生成。
