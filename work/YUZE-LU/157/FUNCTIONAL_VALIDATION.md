# 功能、数值与证明证据

更新时间：2026-11-01T17:13:51+08:00。这是阶段报告，尚非完整研究验收。

## 已完成

A0/A1/A2均使用冻结原始bench，各自完成all-ones、随机初始化seed157、seed158三次运行。每次passed=true，240递推案例、100卷积案例、379979检查、178456周期。九次原始回执见evidence/attempt001/results/*-rtl/receipt.json中的initial_runs。小规模选择网络符号正例通过，错误银行极性真实负例被SAT拒绝；不能代替完整证明。

63份合成输入共93954508字节，逐文件SHA与全部完整期望状态见evidence/attempt003/results/corpus/MANIFEST.json及远程corpus目录。Python任意精度整数oracle与SystemC内独立C++128位整数实现比较全部输出、溢出标志与全部新/旧状态，不只比较摘要。两轮各1512配置，1212条数值PASS、300条UNSUPPORTED_CURRENT_MODEL；不支持的300条是C的252条及A0超过容量的48条，不能计作正确执行。

同一批二进制输入另由冻结原始R RTL执行：51份PASS、12份W2明确UNSUPPORTED_ORIGINAL_CAPACITY，共57377526检查、29225412个RTL驱动周期。见evidence/attempt006/results/RTL_CORPUS_RESULTS.json。每个可支持case按逐token/layer检查完整状态与输出，并核对EXEC延迟GDN=4*rows+15、SSM=3*rows+11、卷积14。读取、配置和背压的驱动周期也保留在该RTL报告中；它与SystemC模型总周期不是同一指标。

M另完成24组八元素精确S32乘法重构，包含INT32极值、U32极值、signed/unsigned及随机输入；600次M命令、4800个S8乘积逐值核对。25项S8分解精确，但宽归并目前在软件中，不是已有硬件功能。

## 尚未通过的门

完整顺序等价状态（采样）：{"controls": "PASSED", "A0-rtl": "PASSED", "A1-rtl": "PASSED", "A2-rtl": "PASSED", "A1-formal": "RUNNING", "A2-formal": "RUNNING", "A0-map": "RUNNING", "A1-map": "PENDING", "A2-map": "PENDING"}。A1/A2仍运行，未得到equiv_status -assert零未证明点，不能标等价通过。A1/A2标准单元综合依赖该门，无旁路。A0重综合仍运行。

SystemC目前把数值转移与时序资源分开建模：时钟化有限FIFO、串行DMA、S窄端口、DRAM和R阶段延迟均明确，但没有逐拍驱动所有原R命令/响应，也没有实现并发宽/窄仲裁的RTL对照、完整新控制器或缓存数据交换的逐位硬件证明。因此CSV的PASS只表示整数转移及该策略执行无错误，不能表述为端到端周期模型或新架构验收通过。

corpus中拒绝提交/reset/invalid等flags目前约束事务模型的最终发布决策；RTL corpus复核以abort保留旧状态，并未把这些flags都转换成对应接口负例。真实无效命令、在途reset、epoch耗尽、背压、提交失败的接口测试来自冻结bench，不能声称SystemC也已逐拍覆盖这些协议。

## 扩展语义

超过2048元素按相同8lane纵向扩展，保持S32状态、S16 key/query、U32 decay/beta/factor、逐点RNE和fits32检查，所有分块的预测/读出先用有符号宽整数全局累加，最后一次RNE；不能分块舍入。GDN先全状态预测再一次误差广播。任意溢出全事务拒绝，旧版本不变。SSM skip与四抽头历史在全事务成功时才发布。4096/8192参考仅为独立整数扩展，原始R不支持，不能标作原RTL通过。
