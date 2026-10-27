# 首版宏命令接口

Refs #121。功能/容量与数值范围见[五宏规格](BLOCK_LIBRARY_V1.md)。下述合同对应当前RTL；R195与V196均已通过服务器原样RTL回归。逻辑周期不等于布线后的频率。

M/V/R共有 `clk/reset`、`cmd_valid/ready`、`cmd_op[3:0]`、`cmd_index`、`cmd_data[127:0]` 与持有型响应 `rsp_valid/ready/data[127:0]/error`。M/V另有`saturated`。一份命令/响应所有权；响应未消费不接下一命令。非法命令返回错误，不静默执行。`reset`清控制/有效性，不清整份数据存储；未装载的数据不可当作零。

## R：10bit index，8个lane

| op | 功能 | index / data |
| --- | --- | --- |
| 0 | OPEN上下文 | data：length[8:0]=1..256，owner[40:9]，epoch[72:41]，position[104:73]；高位0。使全部装载有效位失效；候选未决时拒绝 |
| 1 | 装旧state | index=2*row+half，每拍4×S32；有效row<length |
| 2 / 3 | 装K/B、Q/C | index=8元素分组0..31，每拍8×S16/Q1.14 |
| 4 | 装V/X与注入 | index0/1为原V/X的8×S32，2/3为SSM的dt*X；每拍4lane |
| 5 | 参数 | index0：decay[31:0]、beta[63:32]，高64为0；index1/2：8lane独立skip D，4×S32/Q16.16每拍 |
| 6 | EXEC | mode[1:0]：0 GDN、1 SSM、2四抽头卷积；owner[33:2]，epoch[65:34]，position[97:66]，其余0 |
| 7 | COMMIT | owner[31:0]、期望epoch[63:32]、期望position[95:64]、next_position[127:96]；成功epoch加1，不能回绕 |
| 8 | REVOKE | 丢state/history候选与候选输出，不改活动state/history；SSM因素须重装 |
| 9 | 装三拍history | index0..5，每拍4×S32，顺序为t-1的8lane、t-2、t-3 |
| 10 | 装四抽头 | index0..3，每拍8×S16/Q1.14；tap0对应当前X |
| 11 | 读活动state | index同op1，每拍4×S32；计算候选完成、尚未commit时仍返回旧state |
| 12 | 读候选输出 | index0/1，每拍4×S32；commit/revoke使其失效 |
| 13 | 读元数据 | position[127:96]、epoch[95:64]、owner[63:32]；低32：length[8:0]、pending_state9、pending_history10、output_valid11 |
| 14 | 读活动history | index同op9；候选未commit时仍返回旧history |
| 15 | 装SSM逐元素decay | index同op1，每拍4×UQ1.31；复用shadow，执行消耗有效位 |

`decay/beta`范围0..0x80000000，1的编码为0x80000000；S33乘法因子保证其为正。GDN：RNE31(state*decay)→全key K点积/RNE14→检查V-pred→RNE31(beta*error)→K外积/RNE14加state→Q读出/RNE14。SSM：逐元素decay→B*dtX/RNE14加state→C点积/RNE14→D*X/RNE16 skip。每个阶段都检查S32范围；中间点积S128。

卷积先生成history候选，可在外部V处理后装载新V/X，接着执行状态更新，再共同commit。若后续状态执行错误，之前成功的history候选仍未提交，可显式revoke；调用者不得忽略错误而将history单独commit当作整轮状态更新成功。纯卷积也允许单独commit，next_position由调用者显式给出。commit复制state期间接口不可访问；reset中止后整个上下文失效，必须重开/重装，不承诺断电回滚。

原始RTL已逐次检查：GDN=8N+6拍、SSM=6N+4拍、卷积10拍（接受命令后到响应）；state commit按row复制N拍，纯history commit1拍。响应消费/装载/读回额外占用接口周期，不计成零成本。

## V：8bit index，128bit口分拍装8lane

| op | 功能 | index / data |
| --- | --- | --- |
| 0 / 1 | 装A/B | index0/1，各4×S32；计算8lane前必须装全两拍 |
| 2 | 逐元素/格式 | 见下方字段 |
| 3 | 统计start/continue/final | start0、final1、有效lane数[5:2]=1..8、起始ID[31:16]；其余0。最多65535元素，ID不得超65535 |
| 4 | 读统计 | index0=S128 sum；1=U128 sumsq；2=max[31:0]/argmax[47:32]/min[79:48]/argmin[95:80]/count[111:96]/final112 |
| 5 | 两路函数 | data=0 EXP、1 Sigmoid、2 SiLU、3 GELU_tanh、4 Softplus；处理8lane A，输出经op9读取 |
| 6 | 组级函数 | index0 reciprocal、1 rsqrt；data为正的Q16.16原码/U128容器，返回低S32/Q16.16；0拒绝，结果越界显式饱和 |
| 7 | 装回放输入 | index0..63，每拍4×S32，合计最多256元素 |
| 8 | 内置组合 | index0 RMS、1 L2、2 Softmax；N[8:0]=1..256，epsilon[72:9]为U64/Q32.32，其余0 |
| 9 | 读结果 | index0..63，每拍4×S32，末拍不足补0；64=8×低S16打包，65=8×低S8打包，后二者要求结果恰8lane，调用者先选相应饱和宽度 |
| 10 | 装TopK动态ID | index0..4，每拍8×U16，最多40项；与前N个回放值对应 |
| 11 | 多轮TopK | data N[5:0]=1..40、K[9:6]=1..min(8,N)，其余0。每轮扫描N项，分数降序、ID升序、重复ID再按输入位置稳定 |
| 12 | 读TopK | index0..K-1，score[31:0]、动态ID[47:32]；不执行专家寻址或搬运 |
| 13 | 清有效上下文 | 使A/B/回放/统计/结果/ID有效位失效，不清整份数据存储 |

op2字段：算术op[3:0]、RNE右移[10:4]、有效lane数[14:11]、广播B开关15、输出宽度[17:16]（0=S8/1=S16/2=S32）、成对交换B开关18；广播B码[63:32]、scalar C[95:64]，其余0。算术op依次：0加、1减、2乘、3乘加scalar C、4max、5min、6比较A>=B返回-1/0、7左移、8仅转换/右移、9按A<0在B/C间选择。左移使用同一shift字段且限制0..96，再饱和；其他操作在同一声明单位下完成计算后RNE右移再饱和。FMA的C与未舍入乘积同单位。成对交换只影响B供数，RoPE cos/sin由输入给出。

内置norm返回归一化基值；逐元素gamma/1+gamma由本V点通路接续。Softmax内部先取max；差值<-16截成EXP的-16端点（Q16结果0）。mask要先由比较/选择落实为实际有限码，不能隐含无穷浮点。内置组合仅N<=256，更长组需S回放及分段统计/函数/点运算；这些额外读写/屏障仍是映射成本。

### V 实测命令延迟

206以与196数值回归、203物理流程**完全相同的RTL**测量，8243检查/7437仿真周期。计数从命令接受边沿到首个可保持响应；不是端到端吞吐或物理频率。令B=ceil(N/8)、P=ceil(N/2)，无错误操作的控制器周期如下；组合操作实测N=1/7/8/9/64/128/256，与公式逐项一致。

| 操作 | 周期 | 说明 |
| --- | --- | --- |
| 半向量装载、读统计/结果 | 0 | 在接受边沿产生寄存响应；仍须消费，连续此类命令最少间隔2拍，绝非零传输成本 |
| 8-lane逐元素/格式 | 2 | 十种算术均实测；A、B各需两拍128bit命令装载 |
| 一批至多8元素统计 | 2 | start/continue/final的单批执行；跨批装载与响应另计 |
| 8元素EXP/激活 | 7 | 两路函数各3级/II=1，四拍送入八元素后排空；宏命令本身没有II=1 |
| reciprocal / rsqrt | 130 / 196 | 包括组级128拍除法、64拍根及主控握手；不能只报组件周期 |
| RMSNorm / L2Norm | 197+5B | N=256实测357拍；不含gamma接续 |
| Softmax | 134+5B+P | N=256实测422拍；包括两路EXP、统计与归一化 |
| N选K | K(N+1) | 40选8实测328拍；不含ID装载、结果读回或专家搬运 |

2KiB回放最多256个S32输入及同量输出，128bit口每次四元素；N=256需64次装载与64次读回命令。响应被背压时执行结果保持，下一命令须等待消费。上述数值不得写成“每拍接收8元素”或“EXP宏每拍接受新命令”。

## M

M的LOAD_A/LOAD_B/MAC/READ_PARTIAL/MERGE/READ_FINAL/RESET_CONTEXT及格式、3/9步分解、延迟详见[主规格M节](BLOCK_LIBRARY_V1.md#m完整矩阵乘加)与`block_v1_m.sv`顶注释。

## S：工作存储协议

`block_v1_s16k`仅包装原`store82`：1024×128bit、10bit地址、单1RW、无byte mask。输入`req/wr/addr[9:0]/din[127:0]`，输出`ready/valid/dout[127:0]`，由输入`take`消费响应。reset只清响应控制和dout，不清payload；未写地址不得当作零读取。

在reset=0且`req && ready`的上升沿接受一次请求，边沿后即有寄存响应`valid=1`，读返回该地址数据，写返回0。按本文件从接受边沿起的完整周期计数为0，数据经过响应寄存器，不存在组合读透传。等待take期间响应保持；消费边沿只清valid，即使req同时为1也不接收下一请求。无背压时请求间隔最少2拍，读写合计上界为128bit/2拍=8B/拍。该逐拍行为已由225最终网表的原样`test_store_macro.cpp`回归覆盖。

`ready=!valid`没有独立reset屏蔽，reset逻辑优先于req/take；因此reset期间ready电平不表示事务被接受。调用者须在复位解除后发请求。

## T：结果交接协议

`transaction6k`为384×128bit结果缓冲，单批次、单租约。下表对应已选C的封存RTL及最终网表；操作按各自valid/ready握手，不使用M/V/R的cmd口。

| 通道 | 字段与语义 |
| --- | --- |
| begin | `begin_valid/ready`；`begin_words[9:0]=1..384`、`begin_owner[1:0]`、`begin_generation[31:0]`。仅空闲时接收一批 |
| write | `write_valid/ready`、`write_index[9:0]`、`write_data[127:0]`。必须从0连续写，最后一字接受后自动sealed，没有seal请求端口 |
| commit / revoke | 各自valid/ready；commit仅完整sealed后接受，revoke仅FILL或SEALED接受，同拍竞争时revoke优先。提交后不能撤销 |
| read | 输出`read_valid/read_index[9:0]/read_data[127:0]/read_last`，输入`read_take`。顺序逐字读，背压时数据、索引及last保持 |
| release | `release_valid/ready`；只有最后一个读响应已经被take后才能释放并接受下一批 |
| 状态与错误 | 输出`owner/generation/word_count[9:0]`、`busy/sealed/committed`、sticky `protocol_error`及`debug_state[2:0]`。busy期间标签保持；空闲时的非法begin长度、FILL中且未撤销时的错误写索引置protocol_error，reset清除 |

owner/generation是begin时记录的标签，commit/revoke/release没有身份字段；外部控制器负责将操作关联到当前租约。ready=0时valid不构成操作，不能承诺每次这种输入都会置错。debug_state只作观测，不作为跨宏控制接口。

下面以握手发生的上升沿为c，说明边沿后的寄存状态。它们是封存RTL状态机的逐拍合同；既有161最终网表回归验证数据/租约/有界同步响应/背压，未新增峰值吞吐实测。

| 操作 | 最早可见结果与后继操作 |
| --- | --- |
| begin | c后进入FILL，下一上升沿可接受第一字 |
| 连续write | 每拍最多一字；最后一字接受的边沿后sealed/commit_ready有效，下一沿才可commit |
| commit | c+1沿后首个read_valid有效，首字最早在c+2沿被take |
| 非末字take | c后进入下一字读取阶段，c+1沿后下一字valid，最早c+2沿再次take；读出上界每2拍一字 |
| 末字take / release | 末字在c被消费后release_ready有效；最早c+1沿release，c+2沿接受新begin |
| revoke | 接受沿后变为空闲，下一沿可begin；不清payload，不再发布被撤销批次 |

T无停顿写入上界16B/拍，读出上界8B/拍；整批还有begin、commit、release及完整写完再读的控制开销，不能将两项上界同时报成端到端吞吐。S/T的上述上界只按协议推导；在本轮已通过的10ns时钟条件下分别对应0.8GB/s与T写1.6GB/s/读0.8GB/s，使用十进制GB，仍不表示模型或M11/M12系统实测带宽。

T的reset清控制/held和标签而不清payload，消费者或互联同时复位时须协调硬复位；旧标签、无valid的数据不能当成当前批次。二者均是标准单元存储实现；原始RTL及容量见[五宏规格S/T](BLOCK_LIBRARY_V1.md#st-的沿用边界)。
