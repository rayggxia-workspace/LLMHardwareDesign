# 主线五首轮：共同表顺序器、边存储与串行A→F

> 主线五G1首切片最终：源码7a656a3fe4a86342d24b72ebecdc524052bf86d7，96208/n03/node1/c64/8CPU自然COMPLETED0:0/3分1秒；12终态定向+18实际AF及10actualSHA通过。另unit96170的DMA29/SEQ30通过，共89项不同预声明检查，非全图证明。n01/96183原18项成功、n02/96192失败及12项组件成功均保留，不把失败整合当通过。当前无本任务在跑作业、无自动监测。

2026-11-03，Asia/Shanghai。Issue151 / PR152，Melodydt；输入9f63d50b7c1aa3d9ff62bc7a06e1391ba2460f70。本轮从[H1图规格](H1_GRAPH_CONTROL_SPEC.md)进入主线五首轮RTL（混合方案H2首切片）。本稿先记录实施合同，实际源码/仿真/失败或成功以任务回执为准，未获得结果的部分不预报PASS。

## 本次目标及范围

保留原生A2/F1和既有54份RTL/TB/include，新增固定共同控制硬件来解释粗表，先完成G1：一个A2后接同一F1的两次调用。计算仍为H1024、Sq2、I3072、S16 Fin10/W7/epsilon1的已测整数profile；不将W8、trained质量、cache/decode或全部样本纳入本轮资格。

母控用同一译码/资源管理结构取永久表记录；执行器把粗动作翻译为原生接口和局部数据服务。产品控制内容通过取指/描述符读取硬件边界提供，测试平台的只读hex是永久内容的仿真视图，无启动下载程序接口。尚无M11/M12位单元、阵列、物理读出或产品金属绑定；该硬件边界不代表ROM已物理实现。

## 分工及资源

| 模块 | 本轮职责 |
|---|---|
| table sequencer | 取指/holding、保留字段和索引检查、17逻辑对象/4槽分配、消费者引用和运行义务、服务调用、独立held终态；错误触发cohort abort |
| edge DMA | 一份真实S16KiB及既有普通S helper；单owner、一字在途；stream→S以真实写ACK退休源，S→stream以真实读回应建立holding |
| A/F executor | 独立父任务义务、A admission、F两行顺序、参数帧与权重ABI适配、native start、结果物化和释放/DONE；G1先行 |
| AF top | 接单锁存generation/两版本，连接共同母控和执行器，协调错误/复位域；不逐产品重写父FSM |

叶实例为M2/N2/E2/G1/S3/T2，共12个；新增S即边存储。DMA数据holding、1024个字有效位、17对象/四槽metadata、消费者计数、PC/指令holding、ACK/服务完成保持、原生适配和控制全部另计，不能只报叶数量作为完整面积。原S/T不假借作额外缓冲。物理成本与5856B逻辑表候选不是同一量。

## 数据与控制事实

初始hidden为256个128bit字，由IMPORT真实写入边S；A gamma/QK gamma/RoPE共192字、F每行gamma128字由独立参数服务供给。参数服务是单个有序在途帧，检查index/last/error；当前没有独立warm-reset迟到参数隔离，provider必须参与同一cohort reset并排空，真实MEM适配仍GAP。

ARM先承担任务义务；LOAD/WAIT_INPUT只建立hidden部分的确认。PARAM/WAIT_PARAM等整个native帧的真实input_stored，之后才发native START。F没有一次装完整两行的原生入口：第一行完整输出、T RELEASE和DONE后再装第二行；两行gamma重放、每行9MiB权重均是实际流量，不隐含缓存。

A/F结果由源T保持，DMA捕获一个字后写边S，实际S写ACK退休后才向源提供退休许可。这个接口的in_ready明确定义为stored retirement，不能当成普通capture ready。独立服务DONE在母控WAIT期间保持；母控停取指不能关掉其所等待的数据/ACK进展。

导出结果提供持续稳定的out_valid/data/index/generation，由接收端返回显式stored ACK。只在generation/index匹配并接受ACK后推进；host“已捕获”与“实际存储”不能混用。测试接收端必须实际写自己的接收S并等写ACK，再发出口ACK，不能以延时计数假造存储事实。

边对象的回收与源T释放分开。所有实际消费者整帧stored后才FREE对应edge槽；生产者T在物化时已按SACK退休并关闭。WAIT_RELEASE观察native实际完成T释放后的DONE事实，WAIT_DONE再消费该held DONE；不能先等整个DONE再允许排输出。

## 验证与未完成门

分别运行DMA真实S单元测试、母控mock服务协议测试和实际G1 A→两F数值/供参测试。mock服务只能证明母控译码/保持/引用/错误控制，不能替代native、SACK或A/F数值。实际G1用既有独立整数golden和冻结fixture，核初始/参数帧、A6MiB及F18MiB实际接收流、最终4096B输出、真实SACK/源退休/资源释放及SHA。

全部新RTL仿真只在本人服务器Slurm/Verilator运行。先推源并核Git/server SHA，再提交作业；每次提交立即给真实job/source/运行日志和结果路径。失败attempt保留。未结束的长作业保持in_progress并给可恢复交接，不写通过，不承诺未配置的自动监测。

G2/G3同RTL换表、更多分支/反馈、异步MEM晚返回、全部公共fault handler、生产程序容量、物理ROM与共同底座继续后续验收。主线四的完整trained整数AF、新代表性数据和质量门独立保留；旧24GAP不变。本轮仍通过PR152待外部审查，不自合并或提前done。


## 最终修复与复验（本节为当前结论）

主线五G1首切片最终：源码7a656a3fe4a86342d24b72ebecdc524052bf86d7，96208/n03/node1/c64/8CPU自然COMPLETED0:0/3分1秒；12终态定向+18实际AF及10actualSHA通过。另unit96170的DMA29/SEQ30通过，共89项不同预声明检查，非全图证明。n01/96183原18项成功、n02/96192失败及12项组件成功均保留，不把失败整合当通过。当前无本任务在跑作业、无自动监测。

最终增加block_w5_completion_hold及其12项TB，累计新增5RTL/4TB，原54runtime保持。完整error/sat/partial/words/generation在一次事件接收时锁存，partial由error且实际已确认字数非零计算；公共DONE被消费前阻止新任务，busy覆盖终态mailbox。新增mailbox直接状态45bit，不是物理面积结论。
n02的12组件测试通过，但整合在第17项背压测试前失败：TB把仅done_valid有效时可读的公共done_words用作运行计数；该值在新job运行时合法保持上次256。n03仅改TB为检查独立host_count、执行器实际ACK计数及done_valid门，保留真实sinkSACK、源保持、golden和18项全部要求；RTL与n02完全相同。新n03完整通过，未删检查。公共tuple保持缺口已由组件修复并经12项组件测试和18项系统回归；完整RUN/出口故障注入仍是单独未完成覆盖。

最终96208 warning：组件1条、系统62条，非lintclean。19份n03文本实收；四attempt共74份文本逐SHA核验，122次源文件记录及123次数据记录运行后在服务器重核SHA。大二进制保留本人服务器，仓库只有文本与SHA索引。n03含16接单/13DONE，三次hardreset取消，不把16当正常完整job数；正常完整G1恰两次，两者之间无reset，Fmirror2→4。

当前实现仍只接收G1/既定Fin10-W7-EPS1 profile。G2/G3、整图四F编号预约、RUN native错误、输出prefix取消、重复/迟到ACK、真实MEM及控制ROM/系统物理未验收，主线四trained质量门与24GAP保持。下步继续主线五：产品级参数/编号预约、同RTL换表G2重入，再扩G3和系统故障覆盖；不是整个主线五完成。
