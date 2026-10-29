# Issue130：S 的已接收原生候选

2026-10-30 02:34 中国标准时间。[Issue130](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/130)／[PR132](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/132)。本侧任务的新 M 与配套 S 均已完成原生布局布线、同源独立验收和实际文件收件；V/R/T保持固定基线4a0b04e的接口与RTL回归边界。

| 项目 | 实际结果 |
| --- | --- |
| 结构 | 16KiB标准单元存储，4×256×128单1RW bank；宽512bit读取占用四bank，128bit兼容读写；供数控制固定计入S |
| 有限供数缓冲 | 两个512bit A槽和一个512bit B槽共192B；另有宽512bit＋窄128bit响应保持80B，合计272B数据寄存，控制另计；不是SRAM宏或无限DMA |
| 尺寸／金属 | 1680×1680µm，固定M1–M10 |
| 最终单元面积 | active 1181315.842µm²；physical-only 1504512.758µm² |
| 信号接点 | 966位，全部为宏内部M10的2×2µm实际接点 |
| 约束 | Nangate45 typical、300MHz；不确定度0.1ns，输入BUF_X2/Z，输出50fF，I/O max0.8/min0.2ns |
| 最终提取setup／hold | +0.028545ns／+0.0072ns；全部134097个实际数据端点验收 |
| 电气／物理 | cap/slew/setup/hold违规均0；驱动、RC、PG、放置、实际pin及连通全部通过 |
| DRC | 最终ODB独立whole-chip报告为空；完整未修改FreePDK45 GDS deck total_items=0，FEOL/BEOL/OFFGRID/ANTENNA全部保留 |
| 最终功能 | S和已接受M的完整物理网表，配合原T RTL测试夹具，三个初态均128972检查／63250拍；649次A/B同拍、360字T接收 |
| 严格等价 | 全边界严格UNSAT/IDENTICAL，未匹配边界0，实际正反例控制通过；与新成功功能的完整物理视图逐SHA绑定 |

原S35在最终检查中有4条native/1条完整deck间距记录，已拒绝并保留[原始失败档案](rejected-s35-final-drc.zip)和[索引](rejected-s35-final-drc.json)。S41只替换dout[58]的M10折返路径；完整非目标DEF与目标终端连接均一致，修复证明随最终包保存。实际最终ODB/DEF/SPEF重新产生，原生finish/RCX和各最终门重新接收，没有把原失败候选当作合格。

服务端共同前缀P=/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/。修复源cc00845b1fc64b61acfb1c2c746c84bfc493206c，P/issue130-m-feed-repair41-20261030/results/repair-s-04（93509）。封存和物理为qualify42的93511/93512；完整原deck计算93510与finish并行，93513要求最终DEF与受检几何完全相同，并对最终ODB重新全片检查，才接收完整deck。函数93524对新封存源重跑三个初态，严格证明接收93525，交付93526，几何93527，压缩包93528；qualify43源码749b5dae563a079ddf1e36fc1d6e973abc90af65。

编译复用只接收已成功完整物理功能构建的原二进制，全部有序实际输入和二进制逐字节相同，新三个初态仍重新运行。严格证明计算原producer93463在UNSAT/IDENTICAL后因缺尚未完成的功能回执而总体FAILED，其原始失败receipt保留；新接收重新哈希全部原输入/输出/代码、运行实际控制，并按完全相同的RTL/综合输入/完整物理视图绑定成功计算子阶段与新功能，未转移原总体资格。相应原始回执、日志和证明均在包内。

最终六文件与图在P/issue130-m-feed-qualify43-20261030/results/delivery-s/native/；包在同根results/bundle-s/block-feed-s-native.tar.gz，641348100字节，SHA256 `c16601282ea8944e8b35fc9c95f9c44ec1dd9253918d7482e8834c70e8053f06`。本地原始包及44成员已逐SHA接收于D:/Data/LLMHardwareDesign-issue130-runtime/deliverables/S；六文件在unpacked/native，证据在unpacked/evidence，候选LEF及实际几何小文件在geometry。

仓库保存[41个原始回执小文件](accepted-s-receipts.zip)、[索引](accepted-s-index.json)和[7个原始几何文件](accepted-s-geometry.zip)。运行：

```powershell
python -X utf8 project/experiments/block_feed_v1/verify_evidence.py
python -X utf8 project/experiments/block_feed_v1/verify_bundle.py D:/Data/LLMHardwareDesign-issue130-runtime/deliverables/S
```

本轮合法性为上述合同下的原生M1–M10叶子候选。层级Liberty、abstract coverage、M11/M12系统互连和制造签核未取得，50fF不能代替任意外部线长的负载验收。完整M→V→R、生产模型调度和四M阵列另行验证。本侧没有改动父任务运行目录或并行成果。
