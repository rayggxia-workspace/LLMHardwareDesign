# 主线五首轮RTL：真实edge S DMA与表顺序器单元

> 主线五G1首切片最终：源码7a656a3fe4a86342d24b72ebecdc524052bf86d7，96208/n03/node1/c64/8CPU自然COMPLETED0:0/3分1秒；12终态定向+18实际AF及10actualSHA通过。另unit96170的DMA29/SEQ30通过，共89项不同预声明检查，非全图证明。n01/96183原18项成功、n02/96192失败及12项组件成功均保留，不把失败整合当通过。当前无本任务在跑作业、无自动监测。

Issue151 / PR152，Melodydt，2026-11-03（Asia/Shanghai）。输入 `9f63d50b7c1aa3d9ff62bc7a06e1391ba2460f70`，本轮单元实跑源码 **`a3ef3778502abfca279ff88a9ce47d33c73b9f16`**。Slurm **96170 / zenanyan-w5-unit / node1 / c64 / 8CPU / COMPLETED 0:0 / 00:00:29**；真实DMA **29 CASE**、真实表顺序器加mock服务 **30 CASE**通过，共59项。编译与仿真退出码均0。

这是H2/L5的首个有限单元实现与实测，不是完整原生A→F运行、通用控制图、模型质量或金属控制存储验收。原生AF executor/top及其集成TB是另一交付门，准备中的源码不能据本回执预写通过。旧54份RTL/TB/include及历史source-lock保持；本轮没有重跑全部旧54源回归。

## 1. 实际新增与原理

### 1.1 真实S路径，而非TB代替存储

[block_w5_edge_dma](../project/rtl/block_connection_w5/block_w5_edge_dma.sv)实例化一个既有`block_feed_s_macro`及一个`block_p2_s_ctrl`。S包含真实4×256×128bit银行，共16KiB；DMA只用普通128bit req/rsp，loader入口关闭，没有新增第二存储端口或私有payload数组。

命令固定为方向、10bit字基址和10bit字数，支持每命令1..256个128bit字。11bit扩位检查`base+words<=1024`，索引从0连续到count−1，last只在末字成立。命令数据不是程序/opcode/shape下载接口。一次只有一个owner、一笔native请求；helper对写操作同样等待真实S响应。

写方向的状态顺序为：

```text
源保持valid/data/index/last
    → DMA捕获当前字一次（此时in_ready仍0）
    → helper接单 → 真实S写请求被接受
    → 真实S valid && take写ACK被消费
    → helper响应退休 → DMA向源给in_ready
    → 源字退休，才允许捕获下一字
```

因此写侧`in_ready`不是入口holding空闲，也不是对S发出了请求，而是本字目的写ACK已经建立之后的源退休许可。若源在等待期间撤回/改变已捕获offer，模块报错；已实际写入的RAM不承诺回滚。

读方向先检查字有效，再发真实S读，消费响应后用同一个128bit holding保持data/index/last至`out_ready`。读取不会自动关闭整个edge对象，DMA也不把输出take解释为任意远端存储ACK；对象何时FREE由上层生命周期控制。

### 1.2 字有效性、部分前缀与终态

DMA新增1024bit `word_valid`元数据，**另计128B逻辑状态，不占用或减少S的16KiB payload预算**：

- 新native写被接受时先使目标字无效，避免未ACK覆盖后仍把旧版本标成有效。
- 本字native写ACK实际消费后才置有效；读无效字产生held error DONE，不返回旧RAM为有效数据。
- hard reset清有效位和控制状态，不清RAM本体。单独DMA abort协调复位helper/S响应状态，保留此前已ACK字的有效性；未ACK覆盖字继续无效。
- 写`done_words`记录实际native写ACK前缀；读`done_words`记录实际输出take前缀。写ACK后但源尚未退休即abort时，写前缀可比源take多1，TB专门覆盖。
- 正常完成仍须所有源字真实退休或所有输出字被消费；DONE的error/words保持到done_ready。已有DONE上abort不能撤销或改变该completion，abort+ready同拍只消费一次；hard reset直接取消，不补发DONE。

这些位不含graph对象版本、任务generation或消费者引用计数。地址里的旧字有效，不代表新分配对象已经有效；上层对象合同必须防止未建立当前对象存储事实就LOAD。集成cohort如果把abort映射成DMA的hard reset，会清全部`word_valid`；不能把独立DMA abort的保有效性质扩大为cohort reset后旧对象仍可读。真实RAM写入不回滚的边界不变。

### 1.3 固定表顺序器已成为RTL，但服务还须单独接收

[block_w5_table_sequencer](../project/rtl/block_connection_w5/block_w5_table_sequencer.sv)读取永久表的请求/响应接口，保持一条128bit记录，执行ALLOC/FREE/SETOUT/HALT内部动作，向外发ARM/LOAD/PARAM/START/STORE/CLOSE及各WAIT等粗服务，再等待真实的服务完成握手才更新依赖状态。

当前实现是**线性表切片**：8bit PC、256条上限和9bit执行步计数；记录中next仍为16bit，但非HALT须是可表示的PC+1。IF、循环、任意跳转不是本轮已实现能力，非法IF是拒绝用例，不能把它说成分支通过。G2/G3仿真视图虽然随工具生成，不因此取得本轮原生执行资格。

顺序器管理17个对象、4个4KiB槽、两行有效位、消费者refs、producer/参数身份、active岛/行及pending服务；当前类型guard限定`Sq2×H1024、S16 Fin10、自然轴`及声明的A/F入口。它不为八样本自动完成布局/精度/容量适配，也不实现训练权重提供者。

ALLOC先验证对象metadata再选空槽；WAIT_INPUT和WAIT_PARAM区分hidden与参数齐备；WAIT_STORED建立结果存储事实；CLOSE、WAIT_RELEASE、WAIT_DONE分开关闭producer；EXPORT之后还需WAIT_HOST_STORED和CLOSE_OUTPUT。HALT要求没有live槽、未清引用、active kernel或pending服务，不能只看“最后一条调用发出”。

## 2. 真实写ACK与T RELEASE不是同一件事

| 事实 | 本轮实际证据 | 不能扩大为 |
|---|---|---|
| S接受写请求 | DMA TB观察真实`S.req && ready` | 已建立可发布存储事实 |
| S写ACK消费 | DMA TB观察真实`S.valid && take`并核写ACK数据 | producer的T已经RELEASE |
| DMA源字退休 | write in_ready在该字真实ACK后才建立 | 整对象全部消费者已确认或任务结束 |
| DMA读输出take | 真实S响应经holding后输出消费 | 任意host/peer已经持久存储 |
| 顺序器WAIT_RELEASE/WAIT_DONE | 顺序器真实状态/服务协议，由mock返回驱动 | 原生A/F的T实际释放或完成已经实测 |

DMA单元没有T实例。producer最后T字被取走以后仍需实际RELEASE，可能再到其DONE；这些原生事实要由executor及完整AF集成回执证明。本轮mock服务不能替代它们。正常路径要分别等待真实目的存储、源释放和终态，出错时也不能假设已消费前缀能够回滚。

## 3. 新增资源的可审查下限

以下是源码可见资源和逻辑位数，不是综合FF/cell数量、芯片面积或PPA。不同存储结构和读出电路不可按字节数等价换算。

| 项目 | 当前源码可见资源 | 核算边界 |
|---|---|---|
| edge payload | 一份真实S16KiB，4×256×128bit | 对应4×4KiB数据槽；不是复用A/F内部S的免费空间 |
| DMA字有效 | 1024bit | 独立元数据；不塞进已满的四个payload槽 |
| DMA当前字 | 一个128bit holding | 写capture/读保持共用；不构成4096B整对象私有缓存 |
| DMA直接时序状态 | 源码声明合计1199bit：1024有效位+128 holding+47控制/计数位 | 不含P2 helper、S本体响应/feeder及MUX/比较/布线 |
| S helper | 另有269bit源码时序声明及控制逻辑 | 包括请求/响应保持，不因接口相连而消失 |
| 顺序器对象状态 | 17对象×62bit=1054bit源码声明 | 含slot/两行valid/kernel/refs/producer/parameter/source/input/allocated/live；与外部64B永久metadata不同 |
| 顺序器其它时序状态 | 242bit，含PC/步数/128bit记录保持/generation/active/pending/终态等 | 与对象状态合计1296bit声明；组合译码/guard、外部ROM和metadata存储另计 |
| 永久表接口 | 128bit指令读口、8bit地址；512bit对象metadata读口、5bit地址 | 只定义读出边界，未提供金属位单元/实际ROM宏 |

H1的256记录/17×64B对象/16×32B参数引用/6×16B路线/64B头合计5856B，是[H1逻辑预算候选](H1_METAL_STORAGE_PHYSICAL_INPUT.md)，不等于本轮顺序器内部已经集成这些永久存储。参数引用/路线、真实参数供给、事件保持、通用fault handler、全部本地程序、控制存储译码/读出和物理缓冲不能免计。

未来把A、F和edge S组合，候选原生叶数是M2/N2/E2/G1/S3/T2/R0共12，而既有固定AF1024是11叶。**本轮DMA单元实际只实例edge S，顺序器单元没有原生A/F实例**；不能借候选12叶BOM把mock单元描述成完整功能岛已经接收。

## 4. 59项有限覆盖及实际计数

完整预声明CASE顺序和编译源列在[unit-contract.json](../work/Melodydt/151/h2/unit-contract.json)。该合同保留运行前`PREPARED_NOT_EXECUTED`标记，实际是否执行/通过以96170的[run-receipt.json](../work/Melodydt/151/h2/evidence/units-u01/runs/u01/results/run-receipt.json)为准，不能把两者状态混用。

| 单元 | CASE数 | 主要实际检查 | 明确不含 |
|---|---:|---|---|
| DMA真实S/helper | 29 | native req/ACK及source退休顺序、正常精确字数、256字/末址1023、16组确定种子随机重叠读写、req/rsp/输出/DONE背压；count0/257、越界、index/last、改源、无效字；ACK前后abort、前缀、reset与不同数据复用 | 远端网络、CDC、外部MEM、无界随机/所有形状、T释放 |
| 顺序器+mock服务 | 30 | G1真实生成表与正常复用；ROM请求/服务/完成背压；DONE/abort/reset；opcode/flags/reserved/对象metadata/长度/PC错误；FREE/START/重入/CLOSE/RELEASE/EXPORT/HALT次序guard、服务/ROM错误及恢复 | 原生A/F计算、真实producer T RELEASE、通用peer stored ACK、G3分支或CALL/LOOP |

顺序器TB使用延迟可背压的**mock service endpoint**，没有替代算术或S/T硬件却声称完整AF。这是可控验证顺序器发令、WAIT和错误收口的方法，不能与真实executor证据拼接成已经完成集成测试。DMA TB的scoreboard只在真实native事务上更新，没有向DUT RAM赋值或借DUT输出制造期望。

原始日志保留以下混合统计：

```text
DMA: cycles=7022 cmd=73 Sreq=1024 Sack=1022
     writeACK=515 readACK=507 source=514 output=507 DONE=71
SEQ: jobs=30 dones=29 rom_req=456 svc=364
```

不能把这些含故障/reset的全局数字当成正常帧守恒、系统吞吐或PPA。DMA两次native写请求在ACK前由abort/hard reset取消，所以req−ACK=2；ACK后、源退休前的定向abort使writeACK比source多1；两次hard reset取消任务/held DONE使cmd−DONE=2。顺序器hard reset在途用例不补终态，故jobs−dones=1。正常DMA读写任务另有逐命令req/ACK/流字数相等断言。

## 5. 实跑条件、warning与证据

工具为Verilator **5.042（UNKNOWN.REV）**、g++ **11.4.0**、容器Python **3.10.12**；SIF SHA256为`c742bf99ea498fb4da5135bc83fd1677abcebe0e64470e6a115f2baecb3905df`。使用`--binary --timing --assert --threads 1 -j 8 -Wno-fatal`，不是本地RTL执行。两次编译的warning原样保留：

| 单元 | TIMESCALEMOD | WIDTHEXPAND | WIDTHTRUNC | 合计 |
|---|---:|---:|---:|---:|
| DMA | 5 | 2 | 0 | 7 |
| 顺序器 | 1 | 14 | 2 | 17 |
| 合计 | 6 | 16 | 2 | 24 |

本轮功能检查通过，**非lintclean**。没有用删除CASE、`Wno-width`、黑盒或算术替换消除有效检查。完整argv、退出码、输入SHA和生成日志/表SHA见[实跑回执](../work/Melodydt/151/h2/evidence/units-u01/runs/u01/results/run-receipt.json)；[manifest](../work/Melodydt/151/h2/evidence/units-u01/evidence-manifest.json)、[源码manifest](../work/Melodydt/151/h2/evidence/units-u01/input-u01/source-manifest.json)、[Slurm脚本](../work/Melodydt/151/h2/evidence/units-u01/submit-u01.sbatch)、[DMA原文](../work/Melodydt/151/h2/evidence/units-u01/runs/u01/logs/simulate_dma.log)、[顺序器原文](../work/Melodydt/151/h2/evidence/units-u01/runs/u01/logs/simulate_seq.log)可逐项复查。

服务器任务目录为`/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/w5-9f63d50-20261103`，源码`input-u01`，运行`runs/u01`，Slurm日志`slurm/zenanyan-w5-unit-96170.out/.err`。本报告只确认该已结束的单元作业，不替其它正在准备的集成作业给状态。

## 6. 可复现入口与永久存储边界

在新隔离目录中，以固定源码/manifest和同版本容器、Slurm allocation运行[run_units.py](../work/Melodydt/151/h2/run_units.py)。脚本拒绝既有output，要求本人任务目录及`zenanyan-w5-unit`、8CPU allocation；以源码精确依赖集合、编译/仿真exit0、严格CASE顺序/成功marker和运行前后输入SHA共同判定，不能仅搜索PASS字符串。实际可复制argv以本次submit/receipt为准，复跑换新input/output/job，保留u01不覆盖。

```bash
python3 work/Melodydt/151/h2/run_units.py \
  --root NEW_SOURCE_DIR --output NEW_RESULT_DIR \
  --source-commit a3ef3778502abfca279ff88a9ce47d33c73b9f16 \
  --container-sha256 c742bf99ea498fb4da5135bc83fd1677abcebe0e64470e6a115f2baecb3905df
```

[build_control_tables.py](../work/Melodydt/151/h2/build_control_tables.py)从冻结H1图/编码器生成256×128bit ROM视图、17×512bit metadata视图及SHA；TB以`$readmemh`提供这些**仿真读口**。它不是成品boot loader，也不证明普通RTL ROM具备M11/M12逐bit编码能力。真实金属位单元、读出/保持、驱动/landing、几何差分、同底座两产品、STA/电气及PPA仍是独立门。

## 7. 当前状态与下一步

主线五首轮单元已经实测，当前接收范围仅“真实edge S DMA + 线性表顺序器/mock服务”。下一门是executor/top与未改原生A/F的完整G1集成：真实数据/参数、目的ACK、producer实际T RELEASE/DONE、host存储确认、错误/背压/取消和正常复用都要由新的实际回执接收，不能据本59CASE预写通过。进一步多图/分支/反馈、通用端点及晚返回隔离仍待H2/H3分别实施。

L4-QUALITY-AF并行保留：QUALITY95979只证明官方FP32参考和同Fin10 W8旧前缀回归，既有AF1024仍是baseline；完整trained整数AF、新代表性holdout、产品阈值、八样本旧24GAP没有因本轮单元通过而放宽。R/NUM、MoE、真实MEM与M11/M12共同底座物理均须各自退出。Issue151/PR152仍待要求的审查/合并，不把单元PASS写成整个任务done。

按用户要求，每步完成后继续同名覆盖本地交流PDF并做视觉QA；该本地交付由根代理记录实际SHA/回执。本报告不依赖尚未形成的PDF索引，也不提前宣称本轮PDF已经更新。PDF不上传Git、不发送他人。


## 最终修复与复验（本节为当前结论）

主线五G1首切片最终：源码7a656a3fe4a86342d24b72ebecdc524052bf86d7，96208/n03/node1/c64/8CPU自然COMPLETED0:0/3分1秒；12终态定向+18实际AF及10actualSHA通过。另unit96170的DMA29/SEQ30通过，共89项不同预声明检查，非全图证明。n01/96183原18项成功、n02/96192失败及12项组件成功均保留，不把失败整合当通过。当前无本任务在跑作业、无自动监测。

最终增加block_w5_completion_hold及其12项TB，累计新增5RTL/4TB，原54runtime保持。完整error/sat/partial/words/generation在一次事件接收时锁存，partial由error且实际已确认字数非零计算；公共DONE被消费前阻止新任务，busy覆盖终态mailbox。新增mailbox直接状态45bit，不是物理面积结论。
n02的12组件测试通过，但整合在第17项背压测试前失败：TB把仅done_valid有效时可读的公共done_words用作运行计数；该值在新job运行时合法保持上次256。n03仅改TB为检查独立host_count、执行器实际ACK计数及done_valid门，保留真实sinkSACK、源保持、golden和18项全部要求；RTL与n02完全相同。新n03完整通过，未删检查。公共tuple保持缺口已由组件修复并经12项组件测试和18项系统回归；完整RUN/出口故障注入仍是单独未完成覆盖。

最终96208 warning：组件1条、系统62条，非lintclean。19份n03文本实收；四attempt共74份文本逐SHA核验，122次源文件记录及123次数据记录运行后在服务器重核SHA。大二进制保留本人服务器，仓库只有文本与SHA索引。n03含16接单/13DONE，三次hardreset取消，不把16当正常完整job数；正常完整G1恰两次，两者之间无reset，Fmirror2→4。

当前实现仍只接收G1/既定Fin10-W7-EPS1 profile。G2/G3、整图四F编号预约、RUN native错误、输出prefix取消、重复/迟到ACK、真实MEM及控制ROM/系统物理未验收，主线四trained质量门与24GAP保持。下步继续主线五：产品级参数/编号预约、同RTL换表G2重入，再扩G3和系统故障覆盖；不是整个主线五完成。
