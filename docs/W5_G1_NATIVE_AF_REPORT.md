# 主线五首轮：表顺序器驱动真实G1 A→双行F

> 主线五G1首切片最终：源码7a656a3fe4a86342d24b72ebecdc524052bf86d7，96208/n03/node1/c64/8CPU自然COMPLETED0:0/3分1秒；12终态定向+18实际AF及10actualSHA通过。另unit96170的DMA29/SEQ30通过，共89项不同预声明检查，非全图证明。n01/96183原18项成功、n02/96192失败及12项组件成功均保留，不把失败整合当通过。当前无本任务在跑作业、无自动监测。

2026-11-03（Asia/Shanghai），Issue151 / PR152，Melodydt。输入研究提交`9f63d50b7c1aa3d9ff62bc7a06e1391ba2460f70`。本报告先记录原`30a00e22`/96183的首轮事实和随后发现；根任务正在增加完整终态holding修复、独立测试及新source/n02的native回归，**最终修复源码、模块/测试增量和实际结果以根任务补充的最终回执为准，本文不预报通过**。

首轮新增4个RTL模块和3个TB，保留既有54份RTL/TB/include及历史source-lock。先完成DMA/顺序器59项单元验证，再由同一固定表顺序器实际驱动完整H1024/Sq2 Attention及同一F1024的两次调用；**不是mock服务代替计算**。

完整系统首轮n01实际源码为 **`30a00e220108e4288a175087854fbebc1518df7c`**；作业 **96183 / zenanyan-w5-af / node1 / c64 / 8CPU / COMPLETED 0:0 / 00:02:58**，18项预声明CASE及10份实际输入/参数/权重/输出流长度、SHA全部通过。接收范围为所测synthetic Fin10/W7/epsilon1的G1真实控制/数据链，不是trained质量、全部H1图、整个主线五或物理ROM资格。

## 1. 新增模块与改动动机

原[AF1024固定组合](W4_AF1024_IMPLEMENTATION.md)由专用父FSM控制A及两次F，并让A_T直接保活输出。本轮按[H1图与表合同](H1_GRAPH_CONTROL_SPEC.md)实现新的共同控制和实际边存储路径：先物化A结果，再由F从边存储逐行消费。产品层序由只读控制表表达，kernel和译码/执行硬件不按该产品重新改写。

| 新RTL | 实际职责 |
|---|---|
| [block_w5_table_sequencer](../project/rtl/block_connection_w5/block_w5_table_sequencer.sv) | 取指/记录holding、字段/PC/对象guard、17对象/4槽分配、消费者引用、服务调用及独立终态；本轮接收线性G1，拒绝IF等未支持控制 |
| [block_w5_edge_dma](../project/rtl/block_connection_w5/block_w5_edge_dma.sv) | 实例一份真实S16KiB和原P2 helper；单owner/一字在途，写端以真实S ACK退休源，读端保持真实读响应；1024字有效位是metadata |
| [block_w5_af_executor](../project/rtl/block_connection_w5/block_w5_af_executor.sv) | 实例原A2/F1，展开IMPORT/LOAD/PARAM/START/STORE/释放/导出服务；适配两种参数与权重ABI，F逐行执行；没有整hidden/gamma数据数组 |
| [block_w5_af_top](../project/rtl/block_connection_w5/block_w5_af_top.sv) | 接单锁存generation及两版本，连接共同母控和executor，协调cohort reset，增加首ARM许可和终态外abort门 |

三个新TB分别为[真实S DMA单元](../project/tb/block_connection_w5/block_w5_edge_dma_tb.sv)、[顺序器mock服务单元](../project/tb/block_connection_w5/block_w5_table_sequencer_tb.sv)及[真实G1系统TB](../project/tb/block_connection_w5/block_w5_af_tb.sv)。mock只用于可控验证顺序器，不与真实G1数值证据混同；59项单元覆盖和资源声明已在[独立单元报告](W5_EDGE_DMA_AND_SEQUENCER_REPORT.md)逐项说明。

## 2. 资源和永久表边界

系统硬件包含A的M1/N1/E1/S1/T1、F的M1/N1/E1/G1/S1/T1、新edge S1，即 **M2/N2/E2/G1/R0/S3/T2，共12叶**。每S物理16KiB，每T物理6KiB；这些存储属于不同实例，不是可任意互借的统一池。A内部S峰值满16KiB，F预约14912B；A_T先保存原X4096B，释放后再装Y4096B，F每次T输出2048B。新edge S的四个4096B槽是额外真实资源，G1峰值两槽8192B。

端点、helper、局控/母控、地址/owner/引用/事件状态、holding、MUX和驱动另计。executor用一个`hidden_pending`控制位区分目的捕获与源退休，没有新增4096B Y数组；也没有沿用旧AF1024父控的2KiB gamma FFbank来掩盖参数来源。外部参数服务必须真实提供gamma等内容，其存储、MEM及带宽仍有待实现。系统TB的最终接收S是**外部测试接收端**，不计入上述共同底座12叶。

顺序器取指接口为8bit地址/128bit返回，metadata为5bit地址/512bit组合读边界。G1使用H1的48条有效记录及对象描述；[表生成器](../work/Melodydt/151/h2/build_control_tables.py)生成256记录ROM视图和17对象metadata视图，余项规范填充。仿真TB通过`+rom/+meta`读取这些永久内容的测试视图，没有host启动下载程序接口。

这不是M11/M12可制造ROM。位单元、译码/读出、读周期、接点/扇出、landing、路线、PG/CTS和STA/PPA均未接收。H1的5856B是完整公共逻辑表容量候选，不等于本轮已集成的内部ROM，也不包含所有运行时/故障/局部程序成本。全部有源控制、端点、holding和修时序资源必须在底座冻结前存在，不能在产品金属阶段补门或buffer。

## 3. 真实执行和ACK关系

正常G1执行以下路径：

1. 母控接单，IMPORT将初始两行hidden共256字/4096B真实写入edge S；最后写ACK后才建立初始`input_stored`。caller随后给一次start许可。
2. ARM由共同wrapper承担任务义务。LOAD从edge S读取hidden，先让原生A/F输入捕获一次，再等这个锁定非末hidden入口经真实S写ACK重新开放ready，才退休对应edge读字。`hidden_pending`防重复捕获，并在F capture时就建立失帧监视。
3. WAIT_INPUT只确认hidden部分。独立PARAM请求按id/island/row/words供应A192字或F128字，检查逐字index/last/error；WAIT_PARAM再等整个原生帧`input_stored`。只有整帧真实建立后，母控才减少消费者引用/允许FREE源对象并发native START。
4. A完成真实算术，其最终Y来自原生T。STORE先捕获T保持的字，发目的edge S写请求，实际写ACK完成后DMA才给源退休许可。最后一字、整帧存储、CLOSE、实际T RELEASE和DONE消费分别处理；不会先等待生产者整个DONE再排数据。
5. F2仍lower为同一F1的row0/row1：每行装hidden128+gamma128，完成全部计算和结果存储，T实际RELEASE/DONE后才重用F装下一行。row1在整槽基址上加128字；SEQ只传槽基址，不重复加偏移。整体F2输入事实是两行历史事实，不要求两帧同时驻F S。
6. 两行F结果物化到edge对象后，EXPORT从edge读出256字。外部接收端先捕获一次，再通过真实S/helper写ACK，然后返回显式`out_ack_valid/index/generation`。匹配ACK才推进edge读指针；没有用普通ready或延时计数伪造REMOTE_STORED。
7. WAIT_HOST_STORED、CLOSE_OUTPUT关闭最终对象，HALT才发布母任务成功。kernel的WAIT_RELEASE观察实际T释放后的child DONE，WAIT_DONE才消费该held DONE；同一实例关闭前不可重入。

DMA action在其done_valid建立后返回服务完成，保留该DMA done供下一条WAIT消费。SEQ只在WAIT服务成功后更新存储事实和引用。母控等待期间，数据/helper、参数和返回通道继续推进，不以停止取指阻塞自己等待的ACK。

### 两个top门控修正

- **首ARM等待真正start**：初始IMPORT完成后，SEQ可能已经取到ARM；top对该服务valid和ready双向门控，直到caller实际start握手。系统TB在`input_stored`后延迟10拍start，期间不误发A任务、不错误完成。
- **已保持终态不再受外部abort改写**：executor的abort连接为`(abort && !done_valid) || cohort_abort`。已held母终态后的外部abort不再改变executor的partial或清F mirror；DONE+abort+ready同拍仍只消费一次。内部错误cohort_abort仍负责停止/清理子树，这不是全部运行中错误窗口的完整证明。

## 4. 帧、参数流及正常预算

本次复用原独立AF1024数学golden的`base`，数据版本绑定原始源码`b3e14e27e1c38afc697d383e33f5d8d90be62267`。原576字输入被明确拆开：host只传前256字hidden，A参数取256..447的192字，F gamma取448..575的128字并真实回放两次。A/F kernel及原生数值合同不变：S16 Fin10、S8 Fin7、epsilon_code1即`2^-20`；不接受源训练模型`1e-6`精度等价，也未将W8自动切到本共同executor。

| 每次完整G1 | 实际检查预算 |
|---|---:|
| host初始hidden | 256字/4096B |
| 参数请求/参数帧流 | A一次192字、F两次各128字；3请求/448字/7168B |
| A输入/输出 | 448字整帧/256字Y |
| 两次F输入/输出 | 各256字整帧/各128字；两行输出256字 |
| A/F权重 | 6MiB/18MiB，共24MiB，完整实际供给 |
| 权重请求/拍 | A24576/393216；F73728/1179648 |
| 实际M EXEC | A24896+F73728=98624，不省略归约chunk |
| edge普通写ACK | IMPORT256+STORE A256+STORE F256=768 |
| edge普通读ACK | LOAD A256+LOAD F256+EXPORT256=768 |
| native start/DONE | A各1，F各2 |
| 最终源T输出take | A256+F256=512；另有A内部原X消费，不能混作host输出 |
| native T RELEASE | A两lease、F两次各一lease，共4 |
| 外部sink S写ACK/最终目的ACK | 各256，输出4096B |
| 外侧svc调用 | 41；SEQ内部ALLOC/FREE/SETOUT/HALT等不误计为svc |

以上是每个完整正常任务的断言，不由含故障/reset的全局总数倒推。F版本0在A ARM之前拒绝；G1预留两次F start容量，mirror按真实F start增加且正常任务间不清。两完整G1之间不reset，实测mirror由2增到4。G2/G3需四次F启动的预算，不能把当前两次guard原样推广。

## 5. 实际18项系统测试与10份dump

[系统合同](../work/Melodydt/151/h2/af-contract.json)保留运行前`PREPARED_NOT_EXECUTED`标记；实际通过状态以96183的[run-receipt](../work/Melodydt/151/h2/evidence/native-n01/runs/n01/results/run-receipt.json)为准。预声明18项按严格顺序全部通过：空闲abort、ROM未知码/返回错误、输入index/generation/last拒绝、部分输入abort、ROM/IMPORT/参数在途hard reset、F版本0、参数index/last/error及请求取消、两次完整G1、真实目的S ACK背压和held DONE/正常复用。

`base`与`recovery`是**同一冻结golden的两次完整运行**，不是两份不同精度样本或18次完整计算。中间没有reset；第二次在首个外部S真实写ACK后再延迟返回ACK6拍，源数据/index/generation保持不变且不提前退休。每次都逐edge写核A的完整Y和F最终Z，最终4096B与独立golden逐字一致。TB无force算术加速、直接DUT RAM赋值或以DUT结果生成期望。

每次完整运行导出以下五条真实握手流，base/recovery各一组，共10份，长度/SHA均与运行前冻结合同相等：

| 每组文件后缀 | bytes | SHA256 |
|---|---:|---|
| accepted-input.bin | 4096 | `ca75d57949e917781a7b0d154eb72e20364a9b2ad001427031f8ec6b65f01d6b` |
| accepted-params.bin | 7168 | `af41597df4116d4fd4bf3ed7786da8a1a741209dadfe578d4fa3a70ee7991fe6` |
| a-weights.bin | 6291456 | `cce86db8e20a6e6cd7d38d99e8674ee8b1c0cfd87f10928af7239430ecad4928` |
| f-weights.bin | 18874368 | `227865e1b0034d280437d501a301d9f0ac7e4b37530b07bc95c35312be79882c` |
| output.bin | 4096 | `bb445cd19635d0bc8153eb8ebd19897779d562279b0fb339aed71436cc100333` |

实际文件名前缀分别为`base-`、`recovery-`。参数dump来自真实参数握手，F权重dump包含两行的18MiB，不能只hash一份9MiB静态文件代替实际两次接收。权重、binary、hex和构建留本人服务器；Git仅保留必要表/日志/回执及SHA。

原始[simulate.log](../work/Melodydt/151/h2/evidence/native-n01/runs/n01/logs/simulate.log)保留：

```text
H2_AF_STATS cycles=32471594 jobs=16 done=13
PASS_H2_AF cases=18
```

18项CASE不等于18个任务：空闲用例无接单，目的ACK背压标记与第二正常任务共用一次完整计算；共16次实际接单。三个hard reset在途用例取消义务、不补DONE，故13次实际终态消费。混合周期/任务统计不作为正常帧守恒、性能或PPA结论。

## 6. 两个源码与实跑阶段分别记录

| 阶段 | 实际源码commit | Slurm事实 | 接收范围 |
|---|---|---|---|
| u01单元 | `a3ef3778502abfca279ff88a9ce47d33c73b9f16` | 96170/node1/c64/8CPU，COMPLETED 0:0/29秒 | DMA29真实S用例、SEQ30 mock服务用例；非native AF |
| n01系统首轮 | `30a00e220108e4288a175087854fbebc1518df7c` | 96183/node1/c64/8CPU，COMPLETED 0:0/2分58秒 | 真实G1 18标记、两完整运行、10流SHA |

两轮均为实际首轮自然结束，没有编造失败作业。u01通过不能替代n01集成；n01也不能把所有单元fault直接转写为完整A/F wrapper覆盖。4新RTL/3新TB属于本轮整体新增，运行各自使用精确源清单；旧54源码与叶资格不由本次结果扩大。

n01工具为Verilator **5.042（UNKNOWN.REV）**、g++ **11.4.0**、容器Python **3.10.12**；SIF SHA为`c742bf99ea498fb4da5135bc83fd1677abcebe0e64470e6a115f2baecb3905df`。表生成、工具查询、编译和仿真五条实际命令exit均0；使用`--binary --timing --assert --threads 1 -j 8 -Wno-fatal`。共61条warning原样保留：19 TIMESCALEMOD、28 WIDTHEXPAND、14 WIDTHTRUNC，**功能通过但非lintclean**。

## 7. 数据、工具与复现索引

- [运行器run_af.py](../work/Melodydt/151/h2/run_af.py)，SHA256 `7b71520bd5f718adb803ceccfc6ab8ef44c96c24662e7d6c9e242479a18c9996`；[af-contract.json](../work/Melodydt/151/h2/af-contract.json)，SHA `30bf072f24666d89da76d5cf40c6600dd2cfe168c3a005fb3f96c30c44a0faee`。
- [表生成器](../work/Melodydt/151/h2/build_control_tables.py)，SHA `2b8051639802ef7642b43f70ed982a634e9be16b818117b4764074e5e94749dc`；绑定H1检查器、target及三图源。本次只运行G1，生成G2/G3视图不代表执行过它们。n01 G1 ROM文件SHA为`539423465d5c35737c18e96db272e5307bd21f7eb3e6faefbdcf31011b5a0f25`，metadata为`01df4593a6a97ccf021c26a7db875d9f087d9d1ce1655d31f4350282380f021e`。
- [n01 source-manifest](../work/Melodydt/151/h2/evidence/native-n01/input-n01/source-manifest.json)绑定34份运行输入；包括20个编译源、原生include、H1/独立数学/冻结fixture依赖及实际runner/合同，不只锁4个新RTL。
- [n01回执](../work/Melodydt/151/h2/evidence/native-n01/runs/n01/results/run-receipt.json)列41份来源数据文件的路径/长度/SHA和10实际dump；[17份轻量证据索引](../work/Melodydt/151/h2/evidence/native-n01/evidence-manifest.json)及[submit-n01](../work/Melodydt/151/h2/evidence/native-n01/submit-n01.sbatch)保留源、日志和运行命令。该导出manifest的通用scope字符串沿用“unit text evidence”，本轮资格依据其中绑定的n01/native receipt及实际18标记，不将该历史标签当作测试类型证明。
- 原始golden为本人服务器`/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/af1024-ddc6b42-20261103/runs/r03/vectors/base`，只读复用，未修改旧数据。当前任务目录为`/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/w5-9f63d50-20261103`，源`input-n01`、结果`runs/n01`、Slurm日志`slurm/zenanyan-w5-af-96183.out/.err`。

复跑必须选择新source/output/job目录，在获授权Slurm allocation及固定容器内按submit/receipt的实际argv执行[run_af.py](../work/Melodydt/151/h2/run_af.py)，不得覆盖n01。本报告是读回实际回执后的说明，作者没有本地运行RTL，也没有代根任务启动新远程作业。

## 8. 已知限制及下一门

[实现边界清单](W5_AF_IMPLEMENTATION_LIMITS.md)是本报告的组成部分，尤其保留以下限制：

- 目前只签收所测G1。G2同岛重入、G3 fork/SELECT、CALL/LOOP/反馈、更多并发和全部合法图未运行，IF尚被当前SEQ拒绝；不能以字段/PC余量或生成过表就宣称支持。
- 系统负例集中ROM、IMPORT和参数/prestart阶段；没有新测运行中M/N/E/G native故障、完整计算取消、最终输出prefix取消、错误/重复/迟到目的ACK。旧kernel测试保留原范围，不自动转成新母控覆盖。
- 参数响应没有返回完整parameter id/generation/version，ROM也不是带任务tag的通用MEM。ROM、参数和权重provider必须参与cohort停止/清理，F job16/mirror复位后会重用。没有任意独立warm reset、无限晚返回或跨域隔离保证。
- `done_words`计已接受的匹配目的ACK，`partial`只反映该ACK前缀。接收端已捕获/写入但未返回ACK时，partial仍可能0；不能据此证明外部没有可见副作用。真实S写和已输出前缀不回滚，没有全局原子事务。
- **原30a源码静态发现的终态窗口，现进入修复/重验**：若EXPORT已有目的ACK后，后续ROM读取报错，SEQ可能先呈现error DONE，下一拍cohort_abort才使executor置poison；非零host_words可能使直接转发的`done_partial`从0变1。96183的18项未覆盖此窗口，正常held DONE外abort门不能证明所有错误的完整终态tuple稳定。根任务已决定增加独立completion holding，在捕获时用error和words形成partial并保持完整tuple，隔离SEQ内部DONE与public DONE，并加入独立TB和新source/n02真实native回归。该修复的实际源码/验证尚待最终回执补齐；这里描述的是历史30a发现，不应被写成最终版本仍接受该bug，或提前写成新修复已通过。
- 共同fault handler、真实参数/MEM、永久控制存储、产品金属绑定及物理闭合仍未实现；61warnings也未被本次有限功能PASS转成lint或时序资格。

当前先闭合上述完整错误终态holding修复、独立测试和n02 native重验，由根任务追加真实结果；之后再补RUN/出口prefix/ACK关联和复位边界，在相同固定资源与RTL上逐步运行G2/G3。H1抽象合法性、H2实现、H3组合覆盖与H5物理是不同门。L4训练参数完整整数AF质量、新代表性cal/holdout及产品阈值、旧24项模型GAP、R/NUM、D/H、MoE和MEM保持独立；本次synthetic结果不接受这些项目。

## 9. 交付和本地PDF

复用Issue151/PR152及原task151→task143依赖分支；真实测试源码保留上表commit，最终报告/资料commit按根任务交付回执，不替换已运行版本。本报告不是外部PR批准、PR合并或Issue整体done，也不声称main已接收全部新控制。

每完成一步覆盖同一现有本地交流PDF的要求继续生效。本报告不预报尚未形成的覆盖/视觉QA结果；最终文件SHA、页数和QA事实见[本轮PDF最终索引](../work/Melodydt/151/h2/local-PDF-index.json)，由根任务在实际更新后记录，不新建PDF版本、不上传PDF或发送他人。


## 最终修复与复验（本节为当前结论）

主线五G1首切片最终：源码7a656a3fe4a86342d24b72ebecdc524052bf86d7，96208/n03/node1/c64/8CPU自然COMPLETED0:0/3分1秒；12终态定向+18实际AF及10actualSHA通过。另unit96170的DMA29/SEQ30通过，共89项不同预声明检查，非全图证明。n01/96183原18项成功、n02/96192失败及12项组件成功均保留，不把失败整合当通过。当前无本任务在跑作业、无自动监测。

最终增加block_w5_completion_hold及其12项TB，累计新增5RTL/4TB，原54runtime保持。完整error/sat/partial/words/generation在一次事件接收时锁存，partial由error且实际已确认字数非零计算；公共DONE被消费前阻止新任务，busy覆盖终态mailbox。新增mailbox直接状态45bit，不是物理面积结论。
n02的12组件测试通过，但整合在第17项背压测试前失败：TB把仅done_valid有效时可读的公共done_words用作运行计数；该值在新job运行时合法保持上次256。n03仅改TB为检查独立host_count、执行器实际ACK计数及done_valid门，保留真实sinkSACK、源保持、golden和18项全部要求；RTL与n02完全相同。新n03完整通过，未删检查。公共tuple保持缺口已由组件修复并经12项组件测试和18项系统回归；完整RUN/出口故障注入仍是单独未完成覆盖。

最终96208 warning：组件1条、系统62条，非lintclean。19份n03文本实收；四attempt共74份文本逐SHA核验，122次源文件记录及123次数据记录运行后在服务器重核SHA。大二进制保留本人服务器，仓库只有文本与SHA索引。n03含16接单/13DONE，三次hardreset取消，不把16当正常完整job数；正常完整G1恰两次，两者之间无reset，Fmirror2→4。

当前实现仍只接收G1/既定Fin10-W7-EPS1 profile。G2/G3、整图四F编号预约、RUN native错误、输出prefix取消、重复/迟到ACK、真实MEM及控制ROM/系统物理未验收，主线四trained质量门与24GAP保持。下步继续主线五：产品级参数/编号预约、同RTL换表G2重入，再扩G3和系统故障覆盖；不是整个主线五完成。
