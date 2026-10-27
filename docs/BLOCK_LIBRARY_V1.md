# 第一版物理 Block 清单与基本规格

2026-10-27 CST，Refs #121。状态：**四种独立边界已形成 RTL 候选；不是四块均已完成 P&R**。本轮必须推进到每个最终入选 Block 的最终布局布线与检查，不以本文件结束任务。

## 六种职责放在哪里

| 原职责 | 首版物理归属 | 共享/独立理由 |
| --- | --- | --- |
| M 矩阵计算 | M8 提供八路 S8 乘积；VS 保留 dot 归约、完整 K 累加、scale/RNE 和 M 控制 | 从现有真实资源出发；当前不是独立完整 GEMM 引擎，乘积跨块接口是否合适必须由物理结果判断 |
| V 向量、归一化、激活、格式 | VS 的标量乘法、SFU、加法/归约、移位、guard/RNE、原有 V/norm 控制 | 共享已有标量服务；不声称八路通用向量机或新的 EXP 硬件 |
| A 注意力 | VS 的 attention 控制、统计/除法；M8 的字节乘法；S16K 的有界临时空间 | 不再复制一套乘法器/SFU；保持现有三遍 materialized 算法与有界输入 |
| R 递推与状态 | VS 的 Falcon/GDN 控制、S32/wide104 lowering、全 head guard；S16K 临时空间，外存持久状态 | 不把持久 KV/状态当作16KiB片内容量；不复制另一套宽乘法器 |
| S 存储 | S16K 为工作存储；T6K 为提交前/消费中的结果存储 | 两种生命周期和协议不同，不能合成一份可同时读写的免费多端口 RAM |
| D 搬运与控制 | VS 中的单 owner 仲裁、generation、排空与128bit有限 memory_link；T6K 中的 commit/revoke/释放 | 本轮不单独硬化一个调度处理器；控制和桥接全部计入 VS，交接容量计入 T6K |

这是一组**两种计算块＋两种存储/交接块**，不是每类职责各一套硬件，也不是把 C8 改名成六块。原 C8 的共享方式是来源证据，物理清单需要独立顶层与独立结果。

## 各块规格和固定连接

### 1 八路 INT8 乘积块：block_v1_m8

八个独立 S8×S8→S16 组合乘法器；输入 `a[63:0]`、`b[63:0]`，输出 `product[127:0]`，第i个16bit段对应第i对8bit输入。没有时钟、握手、队列、K计数器或累加器，不承诺一个周期完成整个矩阵运算。内部8组线固定在 M1–M10；256个信号位均需要真实 M10接入。

来源为 shared109 的 SHARED_BYTE；当前 VS 仍持有加法树/累加、完整 K 与一次 RNE。该边界便于来源和资源验证，但跨块搬运原始乘积可能不划算。最终定型前必须记录 pin 数、外框/有源面积比、IO→IO 时延与接入压力；必要时将局部乘加闭合到同一块，不能把这个候选写成完整 MAC8。这里的“8”是8个乘法 lane，不是8×8阵列。

### 2 向量、归约与状态处理块：block_v1_vs

保留现有 shared109 的四profile控制器、M归约/累加、V prep/norm、attention、Falcon/GDN、wide104、宽 guard/舍入、单 S32→S64 乘法器及两有限响应槽、一个 U128 除法/整数开方 SFU。四profile互斥，单owner；不增加多profile并行、通用ISA、额外乘法器、免费scratch或通用128bit乘法。SFU乘法占位op0不是受支持计算功能。

内部固定：各控制器→owner mux→S32/SFU，M/A的字节操作数→对外M8端口，原S访问仲裁→对外S16K端口，128bit有限外存桥→原外部接口。R的shadow/epoch/metadata/root协议保留；abort排空、旧response过滤与commit不可取消均保留。

外部接口：保留原命令/配置/响应、外存地址32/data128/generation32与真实调试端点；新增M8操作数64+64输出/乘积128输入，以及S请求/写使能/地址10/写数据128、ready/valid/take/读数据128。接口是直接组合/同步合同，不默认为跨任意长线的弹性网络；当前不能凭单块时序宣称任意系统连接满足时钟。

首版保留全部原观察口，以实际 pin/面积计价；后续若删观察口须另定源码/协议与重跑，不能在布局困难时偷偷删除。所有宽算术、比较/移位/查表控制和复用选择器都属于此块成本，不能只统计乘法器。

### 3 16 KiB 工作存储：block_v1_s16k

恰好一份 store82，1024×128bit=131072bit=16KiB，单1RW、10bit word地址、无byte mask。端口 `req/wr/addr[9:0]/din[127:0]`，`ready/valid/take/dout[127:0]`，共用clk/reset。

请求在ready时接受，下一拍valid；响应在take前保持，valid尚未清除时不接收新请求。写响应也是有限响应，不能当作双端口或每拍无条件流水。reset清控制和响应，不清 words；每个实际读取必须有初始化/有效性依据。首版沿用完整标准单元映射，不能把理想blackbox容量当实体SRAM宏；库实现方式和面积必须在最终报告写明。

与VS之间为独立物理接口；不再同时保留一份隐藏在VS中的store82。既有C8内部存储的P&R数据只能作工程参考，不代替新独立S16K结果。

### 4 6 KiB 事务结果缓冲：transaction6k

原RTL不变：384×128bit=49152bit=6144B，单消费者；begin带owner2/generation32/words10（1..384），连续index10/data128写入，满后SEALED才可commit。commit前revoke优先；commit后不能撤销。同步读到held寄存器，每拍保持到take；最后一拍take后才允许release，释放前不接收新begin。

begin/write/commit/revoke/read/release及busy/sealed/committed/error/debug端口均保留并计价。没有额外多消费者、隐含8KiB宏或无限输出FIFO。内部数据和状态控制固定在M1–M10，payload不在reset时清零。

现有161 A/C可提供真实单块物理证据；最终选用来源、pin和原始结果必须明确。已有LEF/Lib接口导出不等于层次时序模型已资格，相关限制保留。

## M10接入与物理验证

所有实际信号端点在 M10留合法固定形状，PG/clock另按真实网型处理。窄控制/时钟优先边缘，宽数据按完整信号束分组；内部窗口借鉴PR120的方法，但不照搬其ACT/GEMM旧坐标或未合法候选。

逐块先使用一个可解释的默认pin方案。仅当宽数据接入压力有实际依据时，对该块追加一个内部数据窗口对照，不先做全参数扫描。最终报告列出pin XY/层/大小、真实连通、OBS与既有导体；未来via10所需的M10 enclosure由预制形状提供，禁止以后补改M10。

每块跑完整native M1–M10 floorplan/PG/place/CTS/route/finish/RCX及独立接收。M8是组合块，检查真实IO路径且注明无寄存吞吐/CTS；VS、S16K、T6K检查全部端点setup/hold及严格电气。详细布线、全deck DRC/连接、最终网表功能失败都必须解决后才定型。通用十二层提取和跨产品差分不作为这些单块结果的先决条件。

## 已有物理证据与缺项

| 对象 | 目前证据 | 仍需完成 |
| --- | --- | --- |
| M8 | 新独立RTL候选；原8组乘法来源可逆 | 独立功能、综合、最终P&R和全部接收 |
| VS | 除移出S16K和8乘法器外，原body可逐字逆重建 | 独立顶层功能、综合/端点/尺寸、新最终P&R；不得套用原C8面积 |
| S16K | 原store82明确1024×128/1RW；新单实例wrapper | 独立存储功能、映射与最终P&R；不能当已资格SRAM |
| T6K | run161 A/C完整原生物理与三初态最终网表功能通过；49544实际时序端点；全deck DRC0 | 绑定选定最终产物、汇入统一单块报告及版图图；层次Lib模型限制单列 |
| C8旧综合原型 | run167新最终输出/RCX/native router DRC0；完整新接收仍在跑 | 作为工程基线收尾，不直接转为M8/VS/S16K独立通过 |

T6K A：有源面积414678.306μm²；C：415495.990μm²；二者die均1254400μm²（1120×1120），物理填充等成本单列，不能只把有源面积称宏面积。setup/hold最小slack A=5.202862/0.005335ns，C=5.228821/0.016969ns，环境10ns、输出2fF。原始证据为 [A](../work/YUZE-LU/121/results/run161a-receive-terminal/index.json)、[C](../work/YUZE-LU/121/results/run161c-receive-terminal/index.json)；不是新拆分块的实测值，也不是合格通用层次模型。

## 开源参考的具体取舍

2026-10-27重新阅读openTPU固定 [91df410 的otpu_mxu](https://github.com/FeSens/openTPU/blob/91df41092f612361c5bc22f83b31d23382ffabb0/rtl/mxu/otpu_mxu.sv)及授权服务器llaccel固定f7db8a2的gemm_engine.sv。前者将分组乘积、列端累加与有限结果FIFO局部闭合，后者采用16×16乘法阵列/加法树、i32累加、双缓冲与输出背压。由此得到的设计建议是检查“局部乘加闭合、宽数据尽量不反复过边界”，**这不是它们已经证明当前四种边界最优**。

当前只借鉴边界、存储时序与背压方法；尚未复制这些上游RTL。openTPU的48bit整数后转fp32 epilogue、llaccel的分块及requant数值并不直接等价于当前四profile一次RNE/完整K合同。需要采用源代码时核对该固定版本许可证、数值范围、尾块、容量和实际单块P&R，不因开源项目通过就免除本版验证。更多已读来源与SHA见 [计算复用记录](decisions/2026-10-27-block-v1-compute-reuse.md)。

2026-10-27 21:01 CST增量：选取T6K C为首版单块结果来源。相同1120×1120die下，其hold最小slack0.016969ns高于A的0.005335ns，有源面积增加817.684μm²也保留计价。重新对160/161/168实际源码/回执及10份网表、ODB/DEF/GDS、SPEF/SDC、LEF/Lib、完整timing view做只读SHA核对通过，见[最终产物索引](../work/YUZE-LU/121/library-v1-t6k-C-20261027.json)。这次未重跑STA；Lib层次边界资格仍false，版图图和统一交付包继续补齐。其他三块不借T6K资格。
