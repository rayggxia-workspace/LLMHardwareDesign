# Issue76 受限字节微程序与RTL核校准

本目录只补现有Granite有限expert/merge服务需要的微操作；不加载模型，不修改Issue74数值函数，不新增硬件私有宽ALU。所有真实整数码、完整动作及Verilator运行在本人服务器。PC只有源码和小合成测试。

## 可执行层与限制

micro.py实现18个typed操作：S32×S32、S64×S32、S32×U16（分别25/45/15个signed-high radix128 S8积）、S64加减/比较/最大值/绝对值、U128加法、S16→S64显式符号扩展、S32→S64对齐、S64→S128和U128左移、S64/S128右移RNE及I32拒绝guard、U128恢复除法、U128整数平方根、signed128/U64任意分母RNE到I32。RNE含负数tie、sticky、完整增量carry、符号恢复及高字节guard；零除/溢出记录拒绝，保留原始wrapped输出作诊断。

byte_core.sv只有8个S8/byte lane：两个signed8输入的16位乘积、byte add/sub carry/borrow、byte shift/逻辑/比较/mux，以及一个32位同步ROM读端口。**没有原生宽乘、宽除、开方或免费宽adder。** C++用有限外部byte store的实际RTL返回值，因果串联后继操作；每一步均对输入/输出校验，最后按live地址提取输出。所有8lane轮流覆盖，但没有证明8个宽任务合法同时执行。

宽算法的地址控制器和512B scalar frame仍由Python/C++软件实现；这不是完整宽FSM、RF或RAM端口RTL。RTL核1edge/action与ROM候选返回延迟2cycle、连续II1单列。每动作另1cycle的controller dispatch只是明确候选附加费，不是已校准控制器时序上界；未执行目标工艺综合、STA、PPA、物理线长或模型质量验收。

## 容量、费用与完整控制域

每标量最多512B有限live frame，M/I/F/A/O trace明确地址、初始化、释放和读写；ALU每次需3个输入byte和2个输出byte latch，5B/active lane、全VR8为40B，另列。服务须在既有Vaux容量内保留frame，对所有frame read/write、输入初始化和结果/valid提取，付128bit1RW银行与BUS/FIFO费用，不能当免费内部RF。scalar peak由实际生命周期计数，不能用无限Python临时数组替代硬件容量。

SFU除法/开方控制借已有VR8 lane0做字节算术，同时占SFU1；无额外免费byte ALU。udiv固定128轮，isqrt固定64轮，每轮的shift、sub、mux、borrow、quotient/root更新和控制均实际计数。RNE和guard完整扫描已声明字宽。所有数据相关选择都由byte逻辑/mux完成，不按数据早停。

成本domain bound由固定源码循环及**完整有限shift参数域**决定：align为0..63、左右128bit shift为0..127、RNE为0..128。runner将域内每个zero-input控制拓扑也放入实际RTL重放，按域取每项费用上界并明确padding；数据值不改变拓扑。真实/随机样本仅用于功能和observed_max，不把采样最大值称全域上界。scalar dependency cycles、primitive histogram、candidate dispatch、byte-store IO、peak分别输出，SIMD8_qualified=false；不得无条件将carry总byteops除8。

实际ROM将原Granite SiLU Q12与route exp2 Q24的32位整数逐word顺序装入单口32768×32=131072B候选ROM，unused padding仍占容量。used bytes、原constants来源、完整ROM字节SHA、地址请求及返回顺序保留。128bit payload至少4次32bit读；bank/BUS/FIFO仍由服务计价，RTL单口核不证明宏时序。

## 服务器执行和产物

run_server.py需源binding：commit、micro_sha256、byte_core_sv_sha256、byte_tb_cpp_sha256、run_server_sha256。首次输出目录必须不存在。可用--tool-prefix传JSON argv列表，在既有只读Singularity容器内编译和执行，不安装软件。

~~~text
python -B project/experiments/granite_ports/run_server.py --binding BINDING.json --out NEW_OUT --compiled OLD74/granite-compiled01 --granite OLD74/granite-l0-r16-evaluation01 --granite OLD74/granite-l13-r16-evaluation01 --tool-prefix '["/public/software/singularity-ce-4.3.4/bin/singularity","exec","--bind","/public/home/yuzelu/opt/eda:/eda:ro","/public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif"]'
~~~

默认边界、seed7601随机、真实层0/13的down RQ、U16 gate、nextnorm分母/平方根及真实gamma路径，额外重放全部shift控制域。源码/binding、旧manifest和全部artifact SHA、运行命令/日志、cases.json的精确十进制整数与原数组索引、program.tsv、逐action真实RTL返回、ROM字节/请求、RTL报告、cost_table和manifest可独立接收。真正全值只指被选中的标量操作全部位与完整指令，不代表采集了所有模型值。

cost_table schema为micro-cost-table76-v1，manifest为micro-calibration-run76-v1；只有微程序整数oracle、原真实码、全部逐action RTL和ROM返回通过，才输出PASS_BYTE_CORE_AND_WIDE_MICROPROGRAM。full_wide_RTL_FSM=false保持。解释执行/源码bound、byte RTL功能和候选调度附加费分开；正式服务仍是条件微实现日历，不能改称真实目标周期。
