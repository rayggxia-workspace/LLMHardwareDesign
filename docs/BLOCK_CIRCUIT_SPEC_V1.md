# Block电路规格v1：从逻辑合同到首轮数字原型

2026-10-25 UTC+08；Liangruizhi；Issue80，基于PR77@889ca420181c932598c8e70c500dcdb01156b59c。用户批准计划1—3，完整M/A/R子系统和最终物理宏仍属后续阶段。六模板不是已冻结的六种硬宏；本文件区分电路义务、候选组织和已执行证据，状态以Issue80报告/收据为准。

## 1. 六类逻辑Block的电路合同

|模板|数据通路与必需状态|内部候选预连线|外部接口与实现状态|
|---|---|---|---|
|M矩阵|S8乘法、同单位INT32 fullK局部累加、A/W行与tile双buffer、有效lane/partial/complete状态；不同单位须宽重对齐|operand→MAC→acc反馈，完整归约→可绕过RQ；时钟门控按实际启用资源|ACT8/16、PARTIAL32/完整宽结果、unit/组计数/完成事件。当前仅M输出cut接宽服务核，未新实现阵列；32KiB/16×16为原候选库存|
|V向量/转换|标量/行/列运算、宽归约、scale/RNE/guard、norm/RoPE/激活/残差；完整行统计与必要spill|byte ALU＋有限临时＋控制器＋单ROM接口的局部连接；不能赠原生宽乘/除/开方|首轮真实RTL实现18typed宽函数和有限调用；单context，指令数据无关，未实现任意向量ISA或多任务并行|
|A注意力|QK归约、max/exp/概率、PV及online统计m/l/O、KV profile/window|M↔A矩阵服务与统计反馈是候选，不能复制免费矩阵或多口ROM|KV单位/有效长度/位置、完整归约及typed概率。仅规格，不新增attention RTL；旧整数证据保持各自精度|
|R递推|conv history、old/proposal/shadow状态、完整group范围guard、因果rescale/retry|反馈、两代状态/提交、全tile屏障；复用V宽引擎须真实仲裁|owner/unit/epoch/version/position/abort/commit。仅规格；首轮私有scratch的abort不能替代R原子发布，不宣称GDN/Mamba完整RTL|
|S存储|实际容量/布局/scale与数据同版本、bank/地址、部分写RMW、有限应答|单口仲裁、信用与响应保持、局部读改写反馈；多读副本须算复制容量|首轮32×128bit frame，只有一请求端口且读或写互斥，无byte mask；真实SRAM宏尚未映射|
|D控制/接口|命令/计数/寻址、依赖/任务tag、完成保持、非法指令/PC/栈/范围错误|有限队列/PC/cache/CALL/RET反馈、ready/valid与流控|首轮实际PC/取指/译码/4深返回栈、tag/status/done握手；unit/owner/epoch全系统适配仍在上层合同，不冒充硬件状态事务|

制造前优先固定局部反馈、有限存储/仲裁、错误和完成协议；M/V/A/R的合宏与相邻关系、动态expert分发、bank/backing端点和产品金属连接仍须实现/物理证据决定。

## 2. 首轮宽服务核的真实电路

正式RTL在project/rtl/wide_service：byte_alu、wide_engine、ram128/lut32、memory_link、wide_block。输入不是逐动作软件刺激：host只加载入口frame/只读程序与发一个命令，RTL自行取指、读操作数、算术、RMW、循环展开程序执行、CALL/RET和LUT写回。输入值不会改变微码；动态移位由RTL读取自身算出的selector选择程序地址表。旧807case与新链的独立数学接收另见正式报告。

- ALU：8条S8/byte通路、每条3输入/2输出byte寄存，共40B；每个命令选择1条，scalar carry没有除8。只含S8乘法、byte加减/carry、shift/logic/cmp/mux；宽数据运算全部由这些指令构造。
- frame：512B，32行×128bit，1RW逻辑请求口；读/写互斥，所有byte修改先读旧行再整行写，没有隐含byte mask。leaf临时限定前256B，后256B由有界调用者保存链输入/中间值；不会在每个leaf重新由host注入中间结果。
- 控制：64bit指令、16B两指令cache、PC/limit、4×32bit返回栈、微状态、operand与结果暂存、完成/tag/status、计数器和桥寄存均需计入寄存/存储账。指令/地址加法是控制逻辑，不是免费的数据宽ALU。
- 程序：外部只读程序镜像及地址表，明确占用EXT预算；不是免费无限内部ROM。全部取指与CALL表读取都有真实memory_link事务。程序可离线预装，但部署字节/装载下界和运行时取指分列。
- LUT：真实32768×32bit单端口，131072B，原SiLU/exp2有效73736B＋padding57336B。实际ROM读取、2edge响应和4byte RMW写frame由RTL完成；ROM功能仿真不是工艺宏时序。

原始Issue76条件服务没有本轮完整controller/取指；其slot与本轮RTL周期不能横排或换算。Issue29的512bit/64KiB bank也不直接拼成本核的128bit/512B存储。

## 3. 接口与错误语义

命令含entry-PC、程序边界、lane和16bit tag；仅idle且无cfg事务时接收。busy时禁止cfg覆盖frame。完成/status/tag保持直到消费者ack；复位取消当前未完成命令，清控制与cache，不清RAM、不得发布复位前旧完成。输入/输出通过同一frame128bit端口，完整512B setup写32行与结果读取32行另计，不能当零IO。

微码包含byte算术、受限CALL表、RET、LUT和HALT；内核无host计时器。状态码：0命令执行结束（primitive自身valid位还须检查），1非法程序范围，2指令编码，3栈，4selector域，5LUT域，7链内guard，8watchdog。算术溢出/零除的primitive返回valid0；链调用检查valid后才继续。异常可能已改变私有scratch，status非0禁止作为已发布数学结果；这不等于外部R状态事务已实现。

LOCAL与BUS frame共用相同算法、程序、512B/1RW、8lane、单LUT。两侧取指都走同一128bit半双工memory_link。每事务有真实RTL暂存/串行拍：读请求2header拍＋响应2header/1data拍；写请求2header/1data拍＋响应2header拍，均5×16B=80B。完整请求/响应计价，不沿用旧单向48B微frame账本。局部候选frame直连1RW，BUS候选经上述桥；额外mux/端点/控制保留。这里只有一个在途事务，没有免费深FIFO或并发带宽。

## 4. 验证与物理资格

正式协议和工具在project/experiments/block_circuit。最小矩阵为两组织×静默/固定种子外存背压；比较同函数、同输入/程序和资源，实际cycle/边沿/访问/吞吐分开。关键链覆盖动态scale译码、完整8expert单坐标merge/真实残差以及8元素缩小完整norm；不冒充真实1536hidden/fullK矩阵或全模型质量。

Yosys的行为memory结构及通用cell不是SRAM/ROM宏面积；内部read/write两个逻辑信号不授权同时访问。后续物理比较前必须冻结目标工艺、Liberty/LEF、宏容量/端口/mask/latency、PVT/RC/频率、端点/固定层与定制层。团队55工程与63资产适配需按其commit/交接接入，不复制造另一套。额外宽ALU、多端口RF、专用SFU或更大FIFO须作为另一个资源配置，不能与此基线假称同面积。

## 5. 首轮实际资格与下一阶段入口

[Issue80实际报告](experiments/issue-80-block-circuit.md)和[Blockv2第15节](BLOCK_PARTITION_V2.md)已补齐上述宽服务controller/有限frame/ROM：最终895×4命令和五活动状态reset独立通过，generic资源及固定研究库logic-only映射亦有独立接收。对该已实现子集，不再沿用Issue76“完整wide FSM仍在软件”的旧限制；完整M/A/R、外部状态原子发布、商业memory宏、门级等价/STA/物理PPA限制仍成立。

首选局部frame反馈使本批cycles少42.476%—44.029%，逻辑面积增约0.157%（排除共同memory wrapper）。norm8仍平均约579万cycles，程序1.93MB，因此此版是正确性与成本基线，不是最终高吞吐单元。下一轮要以相同数值合同、实际端口/缓冲和新增面积比较宽算术/SFU/RF专用化，再接真实M完整消费者及物理宏。跨模板融合和产品端点继续留待证据决定。
