# AF16 最终服务器证据独立读回

结论：当前有界 AF16 合同内未发现阻断交付的源码、测试集合或运行结果不一致。本人只读已下载证据和冻结源码，执行本地 SHA、集合、声明和计数核验；没有启动本地 RTL 或服务器仿真，也不代表外部 PR 批准。234 项证据读回检查通过，完整逐项记录见同目录 JSON。

## 实际运行与绑定

实际运行是 `r01`，源码 `a37df8be480d6472627a11419777511042af6a60`，输入父版本 `cd8dfc9a3770f0be04b3e75fe08fe60fd69e47a6`。作业 `95242 / zenanyan-af16 / node1 / c64 / 8CPU`，`sacct` 为 `COMPLETED 0:0`、24 秒。Verilator 5.042 编译、仿真退出码均为 0，首次实际运行通过；运行目录为 `/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/af16-cd8dfc9-20261102/runs/r01`。

30 项输入源码长度/SHA 与服务器清单、回执和当前正式集成副本逐项相同；12 项下载文本长度/SHA 与导出清单相同；本地归档的 13 个文件（12 项文本加清单本身）均逐字节等于已读副本。TB、向量、合同及独立参考还与冻结 draft 绑定一致。

| 对象 | SHA-256 |
| --- | --- |
| AF16 RTL | `96a36f39843d6195169591676371642420c096d37dbe190c94c516495677889c` |
| AF16 TB | `5ea763396f33289546ef02f29e01c41311f0bb5f88a0ea38657910cf6d788c01` |
| 数学向量 | `14037659bfdccf896e964d1bff939e8f67d3e72232d46fed8c86aa26227e3892` |
| CASE 合同 | `092f57ef8e79fe632f5c9a8a001045e2980634b5413076c8e90d842fb898f933` |
| 服务器回执 | `fea595153497a348d667cce0e012ce4ad75810c98ce190dcb0859d2e48a3f3b1` |
| 仿真日志 | `68a887acd425ca166b3d9211d1a5f7497aa44981c9f6aca614808d762970382e` |

## 有界功能证据

33 项预声明 CASE 在日志中完整、按合同顺序、各恰好出现一次；没有删除故障 CASE、重复或额外项。唯一结束行严格为 `PASS_W4_AF16 cases=33`，测试时钟周期 102966。10 组独立整数 golden 与正式 TB 绑定一致，参考文件及数据依赖 SHA 一致。

正常帧单独断言 181 个普通 S 请求/真实 ACK（131W/50R）、M72、N28、E10、G 两服务/8 对、12 次 loader/26 次宽读/A18 拍/B14 拍、子 T 四次 take/三次 RELEASE、host 两字。A 与 F 的每次 S 写入历史及 ACK 后读取版本、F 每行完整 17 拍重帧均有检查；聚合计数不替代这些断言。

A 隐藏结果为 S16 Fin10，逐 bit 送入两行 F16，没有窄化为 S8；每行复用相同 F 权重和 Fgamma，A/F gamma 独立。因果向量对的第 0 行最终结果相同而第 1 行不同；零 Fgamma 时最终结果精确保留 A hidden；正常 hidden 含非 8 倍数的 lane。

父生命周期检查包括 A 真实第27写 ACK 与父40拍 stored 门、F 完整 stored 后 start、A 两字 capture 后实际 DONE/T RELEASE、两次 F 的真实 DONE/T RELEASE、父 RUN 而子未 start 时取消仍产生父错误终态、prestart 子失帧不虚造 DONE、已消费 prefix 不回滚、DONE 遇 abort 保留且 ready 同拍消费一次。新加的坏 A 首字 metadata、坏 F metadata 和未启 F/已关闭 A 的 fake saturation 三项也在真实服务器完整集合内通过。

参数 bank 为 `13×128bit=208B`，A hidden holding 为 `2×128bit=32B`，合计显式 240B FF holding，控制计数器和 flags 另计。源代码没有额外 T；这是静态声明核对，不是综合触发器、面积或布线结论。

## 聚合计数核算

冻结 TB 的正常路径及恢复调用共完成 33 个正常父任务，另有 18 个取消、错误或 reset 事务。按各事务到达的控制/握手边界独立推导，精确累计得到：

| 指标 | 日志与独立累计 |
| --- | ---: |
| 输入握手 | 1924 |
| S 请求 / ACK | 7549 / 7549 |
| M 命令 / 响应 | 2935 / 2935 |
| N 命令 / 响应 | 1183 / 1183 |
| 子 T take / RELEASE | 154 / 111 |
| host take | 68 |

正常部分贡献 S5973、M2376、N924、子 T132 take/99 release、host66；18 个额外事务贡献 S1576、M559、N259、子 T22 take/12 release、host2。后两个 host take 分别来自 prefix-abort 和第二行 F 原生 N 错误之前已消费的第一行。取消/reset 不要求释放所有被复位的 T，故不能把 154 take 与 111 release 当作一一对应关系，也不能把 68 字当作 68 次完整推理。

逐事务分项保存在 JSON。这些分项由冻结 TB 的控制与等待位置推导，并与实际聚合吻合；它们不是新增服务器逐任务 trace，也不构成任意取消点的守恒证明。

## 警告与未接收范围

全部 30 条警告保留：16 条 TIMESCALEMOD、11 条 WIDTHTRUNC、3 条 WIDTHEXPAND。仅使用 `-Wno-fatal`，没有关闭警告分类；本结果不能写成 lint clean。

此结论限于固定 H8、两 causal token、单 head、I8 的 L4 纵向验证顶层。有限 33 CASE/10 golden 不证明穷举数值、错误、四态或活性；S 错误仍是 helper 响应边界注入。未接收完整八样本形状/质量、外存供参、通用 L5 storedACK 网络、共同 ROM/底座、M11/M12 或物理资格。源码上传、实际编译、RTL 功能通过、外部审查和 PR 合并继续分别记录。
