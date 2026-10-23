# Issue29接续：分阶段综合与共享组合选择原型

2026-10-23（Asia/Shanghai），Liangruizhi，[Issue29](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/29)/
[PR30](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/30)，task/29-port-rtl，D:/Projects/LLMHardwareDesign-portrtl。
新原型不是原916dcf9e RTL的静默替换；原代码、1872程序测量和89838超时证据保留。

## 两个独立问题

原RTL能仿真并不证明通用综合检查已经通过。依据上次交接，先固定mode0/depth1，用read_verilog -defer、hierarchy
分离前端与后续proc/memory_collect/check。仅在本人服务器目录、只读已有容器，限额/失败单列。

| job | 实际代码 | 资源/终态 | 结论 |
| --- | --- | --- | --- |
| 89939 | 原RTL，SV SHA decaf90749dbbfca37d95af006b0b4066d5b3b76ebc5d434858af7e6cefa5890 | 1CPU；6分12秒；FAILED124 | 单配置-defer前端360秒超时，无RTLIL检查点 |
| 89944 | 原型491bf3eaa08879b890c141b9db2f3d7c180fa444 | 8CPU；6分01秒；FAILED1 | 27组Verilator被unused-index高位警告拒绝；前端360秒也超时 |
| 89946 | 修正原型0d607f5ebc575764a62a7ebb14aba451f2f22748 | 8CPU；6分01秒；FAILED1 | 27组仿真全过；综合前端仍360秒超时124 |

89939首次带16G内存请求被调度器拒绝，没有分配作业。只读核实node27的Slurm RealMemory=1MiB后，
按现有节点配置提交不带内存申请的有界任务；没有获得16GiB内存预留，不改调度器配置。保留拒绝记录。
89946的time记录前端约359.33秒user、最大RSS271452KiB、退出124；没有后续proc/check/JSON通过证据。
原89838更长运行曾进入PROC_MUX；不能把本次更短前端限额与其不同命令直接当性能优化配对。

## 原型改动和回归

`project/experiments/port_rtl/bank_port_fabric_factored.sv`只把每bank/slot的req地址/512bit数据/64bit strobe选择提取为
共享组合信号，保持原64KiB×2 bank、端口、FIFO、同址与握手合同；没有增加存储和接口。
第一次严格Verilator检查发现旧int ep高30位不再参与byte索引；改为2bit内部endpoint索引，未关警告或断言。
原型是独立文件，未改原bank_port_fabric.sv，也未把旧测量数值重标为新源码结果。

89946在8CPU配额内并行3组×2编译线程及1个Yosys；与Issue53的32CPU模型job并行，互不覆盖目录。
原27配置、1872程序、54stress实际重跑，零仿真失败。服务器逐记录对照原formal01/run-01，
1926条完整结果（含stdout/exit/result）相同，33个已保存trace及gzip哈希相同。
本机又针对冻结旧evidence.zip（SHA f678cc7ed3ec88789fee88a234afd9a02c7bd3696ae51a2c3734680052a33d83）
独立读取全部1926结果核对通过；不是只核两个summary，也不是全1872程序的独立逐拍重算或形式等价。

## 证据与复现

原始回传factored-return01.zip=2,107,687B，SHA256
d25070997ac179c6d0d12b155b8627e95dba78340611a281659bc1dca2384548，实际下载、186成员大小/SHA核验通过。
含原始失败、命令、各配置build log/result、冻结source/bundle、参数index、time/Slurm回执，不含编译二进制或工具副本。
新trace本体保留服务器本人factored02目录；因33份trace/gzip与旧基线相同，可复用原Issue29共享trace包按既有SHA核验，
不重新提交重复的大trace。小包同时进入仓库results/issue-29-factored01，索引逐成员含SHA，未把服务器目录当作已上传Git。

```powershell
python -B scripts/check_project.py
python -B work/Liangruizhi/29/factored/audit_results.py --baseline project/experiments/port_rtl/results/issue-29-run01/evidence.zip --returned project/experiments/port_rtl/results/issue-29-factored01/return.zip --out D:/Projects/Codex/port-factor-review-new.json
```

结果仍然是“行为仿真回归通过、通用综合未完成”。该组合因子提取没有解除有界前端阻塞，
不宣布更小面积、更高频率、SRAM宏映射或可制造Block。下一步需要最小化工具输入/内存写端口表示与单配置诊断，
不是重复扩九配置或无限延长相同扫描。主线E2b/整数算术与本次存储控制器资格分开。
