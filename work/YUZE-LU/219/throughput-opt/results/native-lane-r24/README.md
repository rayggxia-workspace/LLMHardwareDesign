# 迭代23/24证据包

Refs #219 / PR220；报告见 `../../ALGORITHM_ROUND_23.md`、`../../ALGORITHM_ROUND_24.md`。
`evidence.tar.gz`：7,736,011 bytes，SHA256 `aa5228f4b01d899f1647a7eddc196a21878cdeb21b36a98f77f5481cda634921`。
716个逻辑文件、317个按内容去重的别名；全部压缩成员已重新读取核对SHA。
`manifest.json`记录每文件原始长度、SHA和别名目的地。解包后须按aliases复制同内容文件再逐项核对，不能把缺少的别名当成缺证据。

内容：runtime23逐行写回/48完整程序；runtime24原生覆盖、旧/新计划、输入、两平台测试、84合成和36保存真实边界的完整程序RTL；
304/305/306独立服务器终态；307失败审计及308修复后的全流量守恒结果；每个作业的冻结源、脚本、输入/输出SHA和提交回执。
原始程序v1故障未检出、真实边界地址上界v1预实验保留；最终版本分别为`lane-programs-v2`、`lane-actual-rtl-v2`。
编译后的`.vvp`和Python缓存不入包，真实RTL源码、编译列表、测试台、金值和原始日志均保留。

仓库根目录、`project/experiments/block_synthesis`可导入的Python环境下，解包并补齐别名后执行：

```text
python work/YUZE-LU/219/throughput-opt/audit_lane_round.py EVIDENCE/runtime23 EVIDENCE/runtime24 EVIDENCE/resident-scatter-terminal-r24 EVIDENCE/runtime24/integer-reference.json NEW_AUDIT.json --server24 EVIDENCE/native-lane-terminal-r24
python work/YUZE-LU/219/throughput-opt/audit_actual_lane.py EVIDENCE/runtime24 NEW_ACTUAL_AUDIT.json
python -m unittest discover -s project/experiments/block_synthesis -p test_*.py -q
```

Windows测试需要可写临时盘；本轮使用D盘临时目录，未把磁盘不足解释为代码通过。
`integer-reference.json`保存原IR的完整整数参考程序与来源SHA，不是完整综合输入；完整IR位于已授权服务器，精确路径和SHA见流量/作业回执。
RTL重编译需要Icarus12和冻结真实SRAM模型；`compile.f`记录原实验绝对目录，迁移时需将路径对应到解包后的同一份冻结文件，保持文件SHA。
原始探针带观察读及背压，周期不作系统性能。独立审计不把未运行的物理后端、母控/局控/DMA、全KV、SystemC、DRAM、能耗或token/s记成已验证。

便于查看的摘要：`audit.json`（308条独立合成轨迹/84真实程序及负对照）、`actual-audit.json`（21真实边界轨迹/36真实程序）、`traffic-accounting.json`（完整旧选中图逻辑请求，80.19亿条）。
两行覆盖的7.421%为模型切片服务改进，新DP仍比新强贪心慢；四行调查少8.574%但未跑四行完整RTL。
完整流量不是新覆盖整模型性能，也不是物理DRAM流量。20%算法、真实系统时间/能耗与充分适配3–4B FPGA/ASIC对照仍未完成。
