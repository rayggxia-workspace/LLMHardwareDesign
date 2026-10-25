# Issue93：流式 gamma 的真实 RTL、完整整数消费者与容量闭合

2026-10-25，负责人 Liangruizhi。[Issue93](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/93)，分支 `task/93-gamma-stream`，基于 Issue92 reset/epoch 修复与 Issue91 合同。真实张量、Verilator、独立整数复算和 Yosys 映射均在本人服务器 `lrz-i93-*` 完成；本机只做源码、管理检查与证据字节接收。未下载模型、未解封 Phi、未重复成员55/63的交付。

## 可收敛的结论

**保留整行 X/Y、先完成全 H 统计，再分256元素装载 gamma 的方案，已成为有完整数值和有限存储证据的 RTL 候选。** 它保留六组真实 Granite 的完整 M→RQ→专家合并→残差→RMSNorm 结果，并让 H2560 归一化在单16KiB存储、保留4KiB A缓存与512B向量帧的条件下成立。H2560只验归一化，不是完整M/整模型；这也不是通用V、完整Block库或物理签核。

划分启发是把全行统计状态、单分母与原位输出控制留在相同服务域；gamma容量可以用有界搬运替代整行驻留，不必复制宽算术或增加存储端口。M/norm目前严格分阶段，共享端口成本已计，但不能据此声称并发V/R/S仲裁无代价。新非线性消费者和驻留A入口由Issue97独立接续，实际网表物理资格由Issue98接续。

## 数值、来源与处理流程

`norm93` 使用 I32 Q12 的X/Y、I32 Q20 gamma、U128平方和/分母中间状态、共享有符号32×32→64乘法；均值先floor，`den=isqrt((floor(sum(x²)/H)+epsilon)<<40)`，输出为 `RNE(x*gamma*4096/den)`。RNE使用绝对值商余数和偶数规则，最后恢复符号；无运行时浮点。epsilon=17是1e-6在Q24下的RNE编码。零分母明确status2，越界输出有status3守卫；INT32极值的平方和低于2^74，rad低于2^103，保留U128裕量，不能把更宽格式自动视为已支持。

Gemma原捕获是BF16检查点经CPU FP32计算，固定 `google/gemma-3-4b-it@093f9f388b31de276ce2de164bdc2081324b9767`。选既有prefix128、层0/5的第0捕获行，每行完整H2560。实际原实现 `modeling_gemma3.py` SHA `b92013d0558381b76b0f74d2b30890cd3aaa9daa58a269d7a12b5a5c5a8e9eb7` 确认 **effective gamma=1+raw_weight**，不是raw权重本身；NPZ为267293179B、SHA `2dca116bd7cf013ad7686e85372a20f4d933576acb75ab602ee15c5e49a0922b`。原公式先对捕获输出核验，再离线RNE编码，无饱和偷偷截断。

|实际全行|整数输出相对捕获FP32的relL2|max abs|
|---|---:|---:|
|Gemma层0行0|5.642248350943738e-5|0.008209228515625|
|Gemma层5行0|8.821398292969913e-5|0.00015017390251159668|

这两个数字只描述选定归一化行的编码误差；没有事先约定整模型质量门槛，不能称模型精度通过或原生BF16逐位复现。六Granite输入来自只读Issue84/input01（层0/13、token0/64/71），每项8expert×K512×H1536，原payload及manifest逐SHA核验；独立接收重新计算全部INT32部分和、重定标、merge、残差和norm，没有host注入中间运算。

## 存储、接口、仲裁与实际新增硬件

S为1024×128bit单1RW。地址以下用byte、半开区间；每个gamma tile有256个I32、64行。**必须先统计整行，再写任何gamma或Y**；每tile装入所有64行且逐写ack，消费256元素后才覆盖下一tile。原位输出不会覆盖未来统计所需X。

|布局|X/Y|gamma|保留V frame|A缓存|剩余|
|---|---|---|---|---|---:|
|H1536 resident基线|[0,6144)|[6144,12288)|无空位|[12288,16384)|0|
|H1536 stream|[0,6144)|[6144,7168)|[7168,7680)|[12288,16384)|4608B|
|H2560 stream|[0,10240)|[10240,11264)|[11264,11776)|[12288,16384)|512B|

保留帧和未用区由canary检查；frame未执行通用V。A缓存开时在norm后核验全部256行仍与原payload相同，关时亦检查对应canary。gamma复用旧gline128寄存器，无新增双缓冲。外存桥仍单请求在途、一个有限返回；M阶段与norm阶段的地址/请求/ready/valid/take按phase mux。共享S32仍有两个client各一个64bit响应槽及仲裁；此批没有M与norm同时竞争，不能宣称已验证下一V集成并发。

新增命令输入46bit（norm_only、stream、H12、gamma_address32），在cmd_accept锁存；通用64B描述符未实现，不计作免费已有。H1536完整M两模式、H2560 norm-only/stream为实测范围；H1536单独norm-only是接口允许但未单独测试。gamma地址16B对齐，当前93限定[16MiB,32MiB)且33bit end检查，非法描述符status16/17。这个无程序实验地址图不等于91 program[0,32MiB)/Data[64,128MiB)，97整合必须搬迁数据并计mux成本。norm93子模块接受由父控制器检查后的任意base。

新增有效锁存/迭代字段84bit（chain45、norm39），观测计数96bit，合计generic寄存器增加180bit；新增sum/den及写事件是可观察端口，保持逻辑带来的实际综合成本也计入。没有整套旁挂byte ALU、额外8乘法或ROM。SRAM、通用byte ALU、程序/LUT和DMA成本不能以后无偿拼接。

外部恢复夹具有2个响应槽，每槽128bit data+32bit epoch，至少320bit另加控制/延迟/valid；**夹具未综合进core面积**。第二槽只用于旧/新epoch同时在途压力。32bit epoch是独立sideband；当前包协议没有序列化它，物理互联成本待后续。cfg128入口的物理外部header未定义，仅实际请求/应答边沿与payload计数。

## 真实验证与边界

两种确定性停顿模式各51完成记录：48正常逐位一致、1零分母预期错误、2实际给错gamma内容的数值负例。每路67接受命令、5非法命令、9个norm阶段abort/restart、10次硬复位前真实soft-abort、1次真实stale丢弃、4类cfg/reset冲突、5个terminal拒收边沿、3次M↔norm模式切换。4拍done保持/ack、cfg pending阻止cmd、每busy周期翻转参数仍使用锁存值，以及raw M counters在norm-only命令中保持不变，均实测；不能把旧M debug值归给当前norm命令。

quiet路实际18,880行canary读回、46,785次整行den写屏障观察。错误gamma负例把tile移位或反复使用首tile，**RTL返回正常数值状态，而独立参考拒绝与正确gold不符**；本协议没有内容语义签名，不声称RTL自己识别了错误tile。接收器另外拒绝输出、分母、缺字段、布尔计数及4类协议结构篡改。复用旧输入时再次查每个artifact SHA。

terminal测试直接注入Verilator RTL的真实epoch寄存器，确认ffffffff不wrap、旧响应排空；这不等于对门级输出赋值能完成同一注入。门级适配必须落到真实FF或列未执行。未穷尽所有任意地址/重排/CDC、H1536独立norm、地址窗末端溢出动态故障或更大H；不把有限测试说成形式完备。

## 周期、I/O与逻辑成本

下表包含实际caller setup、cmd、active、done保持/ack、结果cfg读回；canary仪器边沿单列在receipt，未算业务。H1536的X由真实M在S中产生，不重复算成“省掉的外存输入”。所有六样本相同shape计数一致。

|完整H1536条件|resident总边沿|stream总边沿|增加|
|---|---:|---:|---:|
|quiet，A关|9,063,373|9,067,213|3,840|
|quiet，A开|5,920,717|5,924,557|3,840|
|背压，A关|10,691,917|10,696,907|4,990|
|背压，A开|7,156,812|7,161,802|4,990|

quiet active分别增加4608，预装cfg省768边沿；stream norm为213700边沿（resident209092）。背压active增加5758，stream norm219458（resident213700）。这些是同核心库存、不同入口协议的实际计数：resident gamma由cfg128预装，stream gamma走五拍128bit桥，**不能据此给出同外存入口速度优劣或论文端到端加速结论**。

H1536 stream norm：1152 S读、768 S写（其中384 gamma）；比resident多384 S写与384外部读。每次读是两请求header、两响应header、一个data，共 **5×128bit=80B**，额外实际线传30,720B，payload6144B。不是简单把FP32字节除4。

H2560两真实行quiet active356038、总358604；背压active365636、总368202。包括1280 cfg预装X边沿、1cmd、5completion、1280结果读回。S1920读+1280写、gamma640外部读、3200×128bit=51,200B线传，payload10,240B；5120次共享S32运算。片内全行统计仍只一次。

本批paired映射原库SHA及实例直方图/Decimal面积求和独立核验：

|同配方本批映射|92旧chain85|93新chain93|增量|
|---|---:|---:|---:|
|logic-only µm²|52,599.904|54,810.630|+2,210.726（4.20291%）|
|mapped cells|35,784|36,956|+1,172|
|DFF_X1|3,823|4,019|+196|
|generic register bits|4,309|4,489|+180|

两个实际generic库存均精确8个S8乘法、1个S32乘法、1个16KiB128bit1RW；无隐藏native div/mod/pow。整个store82 wrapper黑盒排除，故不含宏/外部fabric面积。新基线不直接使用92报告52,387.902：本批源读入顺序不同，ABC映射结果有差异；未专门证明因果，不把跨批差值解释为RTL退化。所有结论只比较本批paired输出。88的电气结果不能继承到93；98仍需新网表测量。

## 失败、修正与交付边界

首次inputs01因捕获键命名误用evaluation失败，读取原capture后按实际prefix128明确修复；原SHA此前已通过。build01因C++变量gamma与libm同名失败，修复驱动后build02/03和两路RTL通过；仅取消本人两个永不满足依赖的排队任务，日志保留。

cost01曾将beat按4B换算，实际是16B。cost01和初包保留并标记失效成本字段；**最终只用final/cost02.json及receipt-s005/s105**。phase7独立接收从真实memory_link声明读出128bit，并断言read状态图、5beat和payload，成本工具再次独立断言384×5×16/384×16。整数输出、cycle、RTL与mapped inventory未改动，不靠“工具报告PASS”掩盖原记账错误。

源码冻结、实际命令、输入版本、Slurm、完整输出和失败记录见`work/Liangruizhi/93`、`project/experiments/gamma_stream/results/issue-93/final`及交接。全包服务器、精选入仓，独立字节与原Git SHA接收分开。发布由主会话执行；本地已验证不代表远端PR已上传/已审查合并，当前不得标done。

补充验收：根审阅要求的两个真实文件语义负例已完成（phase8/Slurm90920）。复制正式rtl-s003，实际改首个输出码或全局den，重写JSONL和manifest内artifact size/SHA；冻结phase7完整receiver main先通过所有字节检查，再分别以`independent full row integer output`、`one entireH sum/den`拒绝，returncode均1，无PASS文件。补充全量11,221,672B/145成员、精选37,566B/32成员独立字节PASS，8phase112原Git源核验PASS。根据此复查的不是单独内存check函数。路径/SHA在交接与semantic-supplement/index.json。
