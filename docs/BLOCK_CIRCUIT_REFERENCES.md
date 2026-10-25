# Issue80 参考电路到本项目的映射

2026-10-25；定向阅读base889ca42 Git对象中的ref-project/llm-routing/阅读说明.txt和模块与接口报告.html，以及已有Gemmini笔记/来源说明。ref-project未在当前worktree实体化；仅GIT_NO_LAZY_FETCH=1读已有对象，不修改/例行审计/全面hash或下载整个参考包。精度/接口和工程范围必须先匹配，不按报告黑框直接生成硬宏。

|来源|具体借鉴点|本项目选择与证据边界|
|---|---|---|
|Gemmini MeshWithDelays|MAC/局部acc反馈、数据对齐和任务标签流水|报告仅4×4阵列核心，ASAP7，非完整系统；用于M结构参考，不与整openTPU比较绝对端口/线长|
|llaccel gemm_engine|INT8/INT32、W双buffer、A行流、输出FIFO和完整归约/RQ|贴近主精度，但数值依赖/NUMERICS/pkg/LUT不完整；本轮不复制其算法来声称逐位复现|
|llaccel vec_engine|双读walker、credit/FIFO、完整norm两遍、标量sqrt/div和回写控制|借鉴V的控制/存储组织；实际数字算法沿用本项目已独立验证18typed源，不凭函数名推定舍入|
|llaccel attn_engine|Q/K/V流水、score缓冲、max/exp/除法与输出FIFO|A仅规格；共享M/ROM/带宽须计资源，不能另赠一套矩阵和64lane|
|llaccel sram_xbar|请求仲裁、grant/rvalid、地址分发与返回路由|只到16bank引脚，无SRAM宏位置；连接逻辑不等同整个S存储体|
|openTPU MXU/VPU|取数/FIFO、start/go分离、矩阵/向量/量化之间的生产消费|存在FP32后处理/VPU，不能作为纯整数支持依据；其协议/格式与本项目分别标明|
|openTPU TMEM/ACT_RAM|共享存储/旁路、激活与scale联合保存、多读组织|TMEM逻辑64KiB、复制物理192KiB；多读不能免费，ACT_RAM不是激活运算器；共享线路不能重复累计收益|
|本项目Issue29|1RW仲裁、有限response FIFO、反压/同址验证范式|512bit/64KiB原库存不直接挪为128bit/512B，真实端口和mask合同另实现；不称完整算术RTL|
|本项目Issue76|18typed S8/byte算法、807case/132真实码、原LUT和独立oracle|原wide/address控制器与frame在软件，本轮新RTL补齐；旧slot/费用与新cycle不混排|
|NVDLA SDP/LUT/precision文档|缩放转换与查表非线性的数据路组织|只借鉴组织，不将CNN算子/原舍入直接视为LLM本合同；https://nvdla.org/hwarch ，https://nvdla.org/hw/v1/ias/precision.html|
|VTA官方设计介绍|load/compute/store模块、FIFO及局部SRAM解耦|组织参考，不导入新ISA或FPGA资源换算；https://tvm.apache.org/2018/07/12/vta-release-announcement.html|

原参考包没有完整工程、ODB/DEF/GDS、全量网表或完整环境；其LEC/STA状态只是源分析记录，非本项目重跑。Gemmini ASAP7与openTPU/llaccel Nangate45不跨工艺排名，线长总和不直接当时延/功耗。复用完整外部RTL前须核对官方revision、许可/依赖和数值规范；本轮仅组织借鉴，实际微码源为本仓库76固定版本，未新增第三方RTL复制。

R状态没有可直接照搬的参考引擎。应从本项目Qwen/Falcon范围、两代状态、完整归约/guard、epoch/owner/原子提交规格出发，待V/S/D可复用底座真实闭环后实现。阶段1的M/V/A/R/S/D规格见BLOCK_CIRCUIT_SPEC_V1.md；完整六硬宏、时钟树/门控、布线与工艺资格仍属后续。
