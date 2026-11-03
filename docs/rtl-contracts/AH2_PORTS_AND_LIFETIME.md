# L4-A-H2：新RTL接口、调度与数值合同

Issue151 / PR152，Melodydt。实现输入a0610aff研究包、main4b1df2c7、native7078786相同字节。根任务另归档历史Issue后父提交可前进至7436dc0d；这不表示修改或重验继承48份运行源。新增文件为`integrated/project/rtl/block_connection_w4/block_w4_ah2_top.sv`，没有新增ROM/生成器，没有修改叶宏或既有适配器。

本说明记录候选实现及静态推导。作者没有运行本地RTL编译/仿真、访问服务器或写远端。真正编译、独立TB、实际provider流SHA与服务器结果由根任务单独冻结和记录；这里不预填PASS。

## 1. 有界计算范围

H1024、Sq2、每head128维；KV头0的K/V各投影一次，先后供Q头0、Q头1复用。实际链为完整input RMS1024→K/Q RMS128→split-half64 RoPE→完整D128 QK→因果Softmax count1/2→PV，输出两token×两Q头×128维共1024B、64字context。没有Wo、原残差、全部16Q/8KV、F、KV cache或L5网络；ATSP保留独立证据，尚未和此切片集成。

实例是一M、一N（N-long controller）、一E（E controller）、一S_macro及单S helper。没有T/G/R，M与S loader使用同一固定bank0，rows2，时间复用。母控不逐条发这些细粒度op；当前为新本地固定控制程序，还不是永久产品ROM/M11绑定的物理实现。

顶层数据holding只有`held_data128`、`v_hold0/1`各128、`m_low_half64`共448bit；没有向量payload数组。现有M/N/E/S、helper、loader和服务controller自身存储/寄存器另计，448bit不代表全岛寄存预算。

## 2. 公共端口与完成义务

| 端口族 | 固定合同 |
|---|---|
| clk/reset/abort | 单时钟；reset高有效同步且不造DONE。abort和失败协调复位M/N/E/S/loader/helper/controllers |
| job_valid/ready、job_generation32、weights_version16 | 先独立接单；generation/version在job握手捕获，后续不能通过外部字段改变。接单后任何阶段abort/error，包括部分输入或等待start，都有带该generation的held errorDONE |
| in_valid/ready/data128、in_generation32、in_index9、in_last | 448字；接受时检查generation、index0..447、仅447为last。错身份/顺序不发S写，errorDONE。逐字真实写ACK后才接受下一字 |
| input_stored、start_valid/ready、busy | 第448字实际写ACK后才stored/start_ready；start仅接受一次。busy覆盖接单、输入、等待start、运行、输出和终态保持 |
| wreq_valid/ready、wreq_job32、wreq_seq16、wreq_version16、matrix2/group4/chunk5 | 恰2048个有序请求；matrix0K、1V、2Q0、3Q1；每matrix group0..15、chunk0..31。seq0..2047，不回绕 |
| w_valid/ready、w_job32、w_seq16、w_version16、w_index4、w_last/error、w_data128 | 一请求16字；index0..15、仅15为last。只在WEIGHT_RX接受；每字实际S写ACK后才开放下一字。任一接受的旧/未来/错tag、version、index、last或error均errorDONE，绝不写S；不自动drain |
| out_valid/ready/data128、out_index10、out_last、out_generation32 | 64字token-major→Q头0/1→group0..15；index0..63，last仅63。每字真实S读响应捕获后输出，正常背压期间保持 |
| done_valid/ready/error/saturated/partial、done_words9、done_generation32 | 独立held终态；正常words64。partial仅错误终态前有最终host输出被接受。saturated累计M/N/E服务真实响应，不把离线量化clip混入 |

DONE期间abort保留已形成的终态，同拍ready只消费一次。DONE消费后无需硬reset即可接下一任务，新的448字都必须重新实际写ACK。已接受S写和host输出前缀不回滚。未接job的abort不造DONE。

generation新鲜性由调用方管理；不要复用未排空的旧generation。weights_version是0..65535的完整不透明身份域，0也是合法值，不表示载入新控制程序或改变数值尺度。硬reset需要provider/调用方一起清理在途旧流。正常非WEIGHT_RX阶段w_ready=0；旧流若一直保持到下一接收窗，会以metadata错误结束当前任务，不会静默污染。这个拒绝策略是有限切片保护，不是通用队列/可靠网络或无界旧流排空协议。

## 3. 输入、S布局与真实生存期

输入index0..383写相同S地址：X0 S0..127、X1 S128..255、H gamma S256..383。index384..447写S512..575：Q gamma16字、K gamma16字、位置0/1 canonical RoPE系数32字。总7168B。输入不含权重镜像；四个128×1024 S8矩阵共512KiB，通过provider实际供给。

N0 src0/gamma256/dst384、N1 src128/gamma256/dst0，分别完整count1024；依次完成并等全部写ACK，Norm0在384..511，Norm1在0..127。此切片不需要保留原X，因为没有Wo/残差；不能据此省掉完整A所需ATSP。

之后真实读写64字，把S512..575搬到128..191，才允许context覆盖原参数临时区。

| S地址 | 用途与生存期 |
|---|---|
| 0..127、384..511 | 两行完整Norm，四矩阵投影全过程保活 |
| 128..143、144..159 | Q/K head gamma，各128项，跨对应head/token复用 |
| 160..191 | position0/1 canonical cos/sin，两个位置各16字 |
| 192..223 | K两token投影→head RMS后RoPE结果，供两个Q头复用 |
| 224..255 | V两token128通道，保持原通道轴 |
| 256..287 | 当前Q头两token投影→RoPE，每完成一头context后才能覆盖 |
| 288..319 | Q/K head RMS独立目的scratch，两token各16字 |
| 320..335 | 四tile A容器，每tile四字：row0、row1、真实zero、真实zero |
| 336..367 | B staging；投影S8用前16字，QK S16用全部32字，PV S16用前8字 |
| 368/369、370/371、372/373 | 每Q头两row score、exact EXP、P |
| 374 | RoPE pair gather临时字；未利用375..383当隐藏向量RAM |
| 512..543、768..799 | 唯一64个有效context字，地址512+token*256+qhead*16+group |

其他Q头的context位置没有写zero，也没有输出为有效数据。K/V只写一次；Q0的全部context先保存，再覆盖Q scratch计算Q1。输出只读取这64个真实写入的位置。

## 4. 本地调度与数值

阶段顺序：IN_NORM→PARAM_MOVE→K投影→K两行HEAD_NORM/ROPE→V投影→Q0投影/HEAD_NORM/ROPE/QK/SOFTMAX/PV→Q1对应流程→OUTPUT。

所有向量为S16 Fin10，投影权重S8 Fin7。input与head RMS的gamma为S16 Fin10，epsilon_code固定1（有效2^-20）；它接近而不等于训练源码1e-6，不宣称模型质量接受。

投影每个8输出组使用同一个M的rows2、4个K8 tile=K32，32chunk完整归约1024；每组先CLEAR(op6)、SCALE1(op4)，首EXEC0x14885、后0x14881，不在chunk之间READ/RNE。最后op5 READ0x107，两行carrier cmd_index为**0、1、8、9**。每carrier四个S32槽低16bit已是原生S16 RNE/clip结果；两个carrier拆拼一个compact16 S字。

每个权重chunk256B固定tile-major：byte offset=`64*t+8*n+k`，t0..3/n0..7/k0..7，globalK=`32*chunk+8*t+k`，输出channel=`8*group+n`。不能把一列连续32K的n-major镜像不经重排直接送入loader。

K/Q各token完整RMS128写到独立scratch，再对每g0..15真实读scratch[g/2]和scratch[g/2+8]，按g奇偶选四个前/后半区值，拼`[x_i,x_(64+i)]`四对到S374。E9/shift14/count8读取S374与原始coeff160+16token+g，写回K/Q对应旋后地址。V不做这个置换。两token共32次E；K、Q0、Q1合计96次。

QK每Q头采用4个K32 chunk完整归约D128；每tile A为两个Q row与两zero，B16八列为K0/K1两字及六个真实zero。SCALE2896（Fin15）、首EXEC0x14287、后0x14283，最终READ0x119（右移25）得到Fin10 score。只读两行cmd_index0/8；每row取前两个S16 score，其余六lane真zero。两个score都保留，因果排除在N count1/2执行，不能将未来score0加入分母。

每Q头有两次N Softmax服务：src368/369、EXP370/371、P372/373，count1/2。EXP是exact U16编码回放，P为非负S16 Fin14；尾部由N controller实际mask，不能bitcast EXP当概率。

PV每8通道组先真实读取P0/P1并建rows2/tile1 A，另真实读V0/V1两字，按列写B16 `[V0[n],V1[n],0,...]` 到S336..343。SCALE1、EXEC0x11827，最后READ0x10e（右移14）回Fin10。V轴与context通道轴保持原样；两个Q头共享同一个已保存的KV。

唯一普通S helper owner为LOCAL0/E1/N3；完整E/N服务从请求到最终写ACK及响应消费保持owner。N运行时错误会poison，顶层失败对N/N-long/helper和其他消费者协调reset后才允许后继job，不能靠消耗错误响应继续复用旧context。

## 5. 正常计数（静态推导，待独立TB实证）

| 对象 | 正常计数 |
|---|---:|
| 输入S写/ACK | 448 |
| weight requests /128bit实际拍/字节 | 2048 /32768 /524288 |
| M EXEC | 2088=2048投影+8QK+32PV |
| M commands | 2672=196 CLEAR/SCALE+2088EXEC+388READ |
| M READ | 388=256投影+4QK+128PV |
| loader services | 2088 |
| S宽读 | 16576=A宽读8256+B宽读8320 |
| A128流握手/B512流握手 | 16512 /8320（A宽读供两row，不是8256个A握手） |
| N services /native commands | 12 /744=2×258+6×34+4×6 |
| E services /native input/output | 96 /96 /96 |
| 普通S读/写/请求及ACK | 18220 /67564 /85784 |
| host最终输出 | 64字、1024B |

普通S分项：输入448W；inputNorm768R256W；参数搬运64R64W；投影A staging16384R32768W，权重32768W、结果128W；headNorm288R96W；RoPE含E服务384R192W；QK A64R128W、B64R256W、score4W；Softmax12R8W；PV staging128R384W及结果64W；输出64R。

## 6. 观测点与验证边界

实例u_s/u_s_ctrl/u_m/u_n/u_n_ctrl/u_e/u_e_ctrl，沿既有h_req/rsp、s_*、m_cmd/rsp、load_*、a_*/b_*、n_cmd/native_rsp、e_in/out信号命名。额外reg为stage、matrix、group_index、chunk_index、request_seq、weight_index、tile_index、read_slot、token_index、qhead、rope_group、copy_index、output_index。

state：WAIT_JOB0 INPUT1 INPUT_REQ2 INPUT_RSP3 STORED4 LOCAL_REQ5 LOCAL_RSP6 N_REQ7 N_RSP8 E_REQ9 E_RSP10 M_CMD11 M_RSP12 LOAD_CMD13 LOAD_RSP14 WEIGHT_REQ15 WEIGHT_RX16 OUTPUT_HOLD17 DONE18。stage：IN_NORM0 PARAM_MOVE1 PROJECTION2 HEAD_NORM3 ROPE4 QK5 SOFTMAX6 PV7 OUTPUT8。

常1有限TB许可点为permit_s_req/rsp、permit_m_cmd/rsp、permit_load、permit_e_req/rsp、permit_n_req/rsp、permit_wreq/wrx、permit_output。它们不是产品运行配置。真实native E/N/M/loader错误路径和S无error pin必须区分；TB force h_rsp_error不能被描述为新增S硬件故障检测。实际S宽口、普通ACK、参数版本、阶段写值、M全K归约、N全group、tail、背压、取消/恢复、部分host输出及实际流SHA均需独立验证。

这份新RTL候选不使完整A、真实A→F、八模型24GAP、真实外存、L5母控/跨岛网络、M11永久绑定或共同底座PPA自动完成。
