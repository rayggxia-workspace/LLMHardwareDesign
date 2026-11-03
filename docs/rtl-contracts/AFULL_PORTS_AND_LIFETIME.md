# L4-A-FULL：完整Sq2整数Attention接口与生命周期合同

Issue151 / PR152，Melodydt；研究输入cddcdc2，main4b1df2c7，native7078786相同字节。新增`project/rtl/block_connection_w4/block_w4_afull_top.sv`，复用已有叶宏与controller，不修改继承50份RTL/TB/include。此文描述候选RTL与静态计数；作者没有执行本地RTL编译/仿真、服务器或远端操作。服务器实际源码SHA、独立golden/TB及结果由根任务另行冻结，本文不预填PASS。

## 1. 范围与唯一资源

固定H1024、Sq=Sk=2、Q16、KV8、每head128维、Q宽2048。计算完整input RMS→Q/K/V投影→每Q/K head RMS→split-half64 RoPE→QK→因果Softmax→PV→完整Wo K2048→原X残差，最终两行H1024，共256个128bit字/4096B。

只有一M、一N、一E、一S_macro、一T，以及单S helper、N-long controller、E controller。没有实例AH2/ATSP验证top，没有G/R、额外S/T或私有向量数组。新增顶层payload holding为三个128bit及一个64bit寄存器，共448bit；raw捕获与输出装包复用held_data128。原生宏和已有helper/controller自身holding、控制寄存器另计，448bit不是全岛寄存或面积预算。

这是明确整数profile的完整固定Sq2计算链候选；不承诺训练模型质量、任意token长度、KV cache/decode、完整28层、A→F、八样本变体、L5网络、真实MEM或M11/M12物理绑定已经完成。完整权重经有序provider流输入，不等于MEM控制器已实现，也不是启动装载新控制程序。

## 2. 公共端口

| 端口族 | 合同 |
|---|---|
| clk/reset/abort | 同一时钟；reset高有效同步、不造DONE；abort/错误协调复位M/N/E/S/T/helper/controllers/loader |
| job_valid/ready、job_generation32、weights_version16 | 先接单并捕获generation/version；此后任何阶段abort/error，包括部分输入或等待start，都形成该generation的held errorDONE |
| in_valid/ready/data128、in_generation32、in_index9、in_last | 448字固定输入；接受时核generation、index0..447、仅447为last，坏拍不发S写；每字实际S写ACK后才接下一字 |
| input_stored、start_valid/ready、busy | 第448个输入实际写ACK后stored/start_ready；start一次。busy覆盖接单到DONE消费，不能用stored当计算完成 |
| wreq_valid/ready、wreq_job32、wreq_seq16、wreq_version16 | 一请求在途，seq0..24575；每请求16×128bit/256B，全部字真实S写ACK后才用此chunk |
| wreq_matrix2、wreq_head4、wreq_group7、wreq_chunk6 | matrix0K/1V/2Q/3Wo；K/V head0..7，Q head0..15，Wo head固定0。K/Q/V group0..15、chunk0..31；Wo group0..127、chunk0..63 |
| w_valid/ready/data128、w_job32/w_seq16/w_version16/w_index4/w_last/w_error | 只WEIGHT_RX接受，严格当前job/seq/version、index0..15和仅15为last。任一接受的旧/未来/错tag或error产生errorDONE，该坏拍不写S；不自动drain |
| out_valid/ready/data128、out_index10、out_last、out_generation32 | 最终两行Y的token-major256字；index0..255，仅255为last。来自第二次T事务的真实holding，正常背压期间保持 |
| done_valid/ready/error/saturated/partial、done_words9、done_generation32 | 独立held终态；正常words256。partial仅错误DONE前最终host输出握手数非零。saturated累计本轮实际M/N/E响应，不表示离线权重量化clip |

version0合法；version是参数身份，不能改变本地数值常量或加载新程序。generation的新鲜性/防回绕由调用方协调；硬reset须provider一起清理旧流。非WEIGHT_RX时w_ready=0，不能承诺无界旧流排空；旧流维持到下个接收窗时会使当前job错误结束而不会静默污染。

无job abort无DONE；接单后prestart也有完成义务。DONE期间abort保留已有终态，同拍ready只消费一次。正常DONE消费后无需reset复用，但必须重新完整装入448字。错误作废在途并reset全部叶与controller，特别清N poison；不回滚已接受S写或最终host输出前缀。S原生没有error pin，TB force helper错误只是验证传播，不能描述成新增S硬件故障检测。

## 3. S/T容量与不可跨越的完成门

输入index0..383写同地址：X0 S0..127、X1 S128..255、input gamma S256..383；index384..447写S512..575，依次为Q gamma16字、K gamma16字、position0/1 canonical系数各16字。总7168B。

start后先T BEGIN256(owner1，同job generation)，真实读S[g]/S[128+g]，交错写T[2g]/T[2g+1]；完整写完COMMIT并等READ_HOLD才raw_saved。T持原X4096B，整个head阶段read_take=0；不能把剩余2KiB当第二个并行事务。

随后N0 src0/gamma256/dst384/count1024，N1 src128/gamma256/dst0/count1024；Norm0在384..511、Norm1在0..127，完整保活到所有head完成。真实搬64字参数S512..575→128..191，再允许context覆盖临时参数区。

| S地址 | 内容 |
|---|---|
| 0..127、384..511 | 两行完整Norm，共4096B；所有head完成后才可被最终残差结果覆盖 |
| 128..143、144..159、160..191 | Q/K gamma、两位置canonical cos/sin |
| 192..223、224..255、256..287 | 当前KV的两行Krot/V及当前Q的两行Qrot |
| 288..319 | 两行head RMS目的scratch，与src/gamma互斥 |
| 320..335 | 四tile A容器：每tile row0/row1/zero/zero |
| 336..367 | B staging，S8用前16字，QK S16用32字，PV S16用前8字 |
| 368..373、374 | 两row score/EXP/P及RoPE pair gather |
| 512..1023 | 两token×16Q heads×128维完整context，共8192B |

峰值Norm4096+work4096+context8192=16384B；没有额外S余量。T原X4096B是另一真实事务容量，不是随机读RAM或免费context restore。若改为更长序列/宽精度/额外持久scratch，必须重新准入，不自动借R或MEM。

context地址为512+token×256+q_head×16+group。每个实际PV结果S写ACK才递增10bit context_words；全部512字后进入CONTEXT_READY，再允许Wo。不能把尚未产生的head当zero，也不能直接把两个验证top并排当此单S方案。

### A padding一次初始化

参数搬运结束、input gamma生存期结束后，PAD_A阶段逐字真实写ACK：322、323、326、327、330、331、334、335全部zero。最后ACK才padding_live=1。随后每个A staging仅写两行槽320+4t/321+4t；这8个padding字跨全部heads和Wo一直保活。

padding_address定义S320..335且低两位为2/3。padding_live之后任何普通S writer欲覆盖这些字，padding_violation在h_req门前阻止请求并errorDONE，E/N的ready也对称禁止；正常程序的参数、N/E结果、context和最终输出都不覆盖它们。这个新top的有意优化不修改旧AH2反复清zero的计数或历史资格。

## 4. head/GQA、Wo和两次T事务

按kv_head0..7依次计算该head的K与V；K两行RMS128/RoPE后保持，V保持原轴。依次完成q_head=2kv_head和2kv_head+1的Q投影、两行RMS/RoPE、QK、两行Softmax及PV；两个Q的context都已写ACK才覆盖这份KV。

所有512context实际建立后，Wo每8输出group采用rows2、64个K32 chunk完整归约2048维。两行A从context S512+4chunk+t及S768+4chunk+t真实读入；M最后量化后分别保存S256/257且ACK。

随后该group逐row消费T当前原X：T take→held_data128捕获→S258真实写ACK→E0/shift0/count8，srcA S256+row、srcB S258，目的row0 S[group]、row1 S[384+group]。目的写ACK和E响应退休后才复用S258、处理下一row/group。Wo输入context和最终输出区域互不覆盖；Norm已结束生存期，才能把最终结果写到S0/384。

最后原X字消费、最后E目的ACK/服务响应退休后，实际raw T RELEASE。之后才第二次BEGIN256(owner2，同generation)，真实读S0..127/384..511按token-major写T，COMMIT/DRAIN；最终256个host take后实际RELEASE，才成功DONE。没有外部Wo cut、work/resume口，也没有第二T。

raw T在Norm/参数/heads/context等待期间须保持read_valid/index0/last0、owner1、job generation、words256，否则head_t_violation触发错误，rawtake仍为0。Wo逐字捕获时检查当前index2g+row/last；最终输出检查owner2/generation/count/index/last。错误元数据不会作为host payload或原X capture被接受。

## 5. 固定数值与原生M命令

向量S16 Fin10、投影权重S8 Fin7；input/head gamma为S16 Fin10，epsilon_code1代表2^-20，和source1e-6有差异，质量未接受。

| M服务 | EXEC与尺度 | 最后量化 |
|---|---|---|
| K/V/Q投影 | factor1，首0x14885/后0x14881，32×K32完整1024 | READ0x107，RNE7→Fin10 |
| Wo | factor1，同EXEC，64×K32完整2048 | READ0x107，RNE7→Fin10 |
| QK | factor2896，首0x14287/后0x14283，4×K32完整D128 | READ0x119，RNE25→Fin10 score |
| PV | factor1，0x11827，K2/N8/rows2 | READ0x10e，RNE14→Fin10 |

每个M group只先CLEAR6/SCALE4一次；不在chunk之间READ或RNE。两行carrier cmd_index为0/1/8/9，各四S32槽低16位已经是native S16量化结果，拼compact16 S字；QK只读0/8并保留前两score、其他六lane实际zero。完整K必须结束才开始这些READ。

权重每chunk256B均tile-major byte=`64*t+8*n+k`。K/V/Q的globalK=32chunk+8t+k、输出channel=128head+8group+n；Wo的输出channel=8group+n、输入channel=32chunk+8t+k（完整16head拼接顺序），head字段固定0。总K1MiB、V1MiB、Q2MiB、Wo2MiB=6MiB，实际24576请求/393216个128bit拍。

K/Q源轴split-half64，真实读scratch[g/2]与[g/2+8]选择前后半区四对，gather到S374再E9/shift14；系数直接读S160+16token+g。仅position0/1，K/Q相同维度置换保持QK dot；V不置换。N两row真实count1/2排未来key，exact U16 EXP存S后回放，概率S16 Fin14；不能bitcast EXP当概率。PV真实读原轴V0/V1两字转8列B16 `[V0[n],V1[n],0,...]`。

## 6. 正常事务计数：静态推导，待服务器实证

| 对象 | 计数 |
|---|---:|
| 输入 /最终host输出 | 448 /256字 |
| 权重req/128bit拍/字节 | 24576 /393216 /6291456 |
| M groups | 912=512 QKV投影+16 QK+256 PV+128 Wo |
| M EXEC /READ /总命令响应 | 24896 /3616 /30336 |
| loader服务 /S宽读 | 24896 /198144 |
| A128流 /B512流 | 197632 /99328 |
| A宽读 /B宽读 | 98816 /99328（不能把A宽读当A128拍） |
| N服务 /native命令响应 | 82 /2340=2×258+48×34+32×6 |
| E服务 /native输入输出 | 1024=768 RoPE+256 residual |
| 普通S读 /写 /请求和ACK | 205984 /600424 /806408 |
| T BEGIN/COMMIT/RELEASE | 各2次 |
| T write /take | 512 /512（raw256+host256） |

其中8个A padding只初始化一次。若机械复用AH2每chunk重复清padding的程序，会增加197624次S写至1004032总请求，不能把本计数套给旧实现或省略真实初始化。

## 7. 观测与状态

实例u_s/u_s_ctrl/u_m/u_n/u_n_ctrl/u_e/u_e_ctrl/u_t。共享普通口owner LOCAL0/E1/N3，整个N/E服务直到最终写ACK和响应消费持续持有；loader只在LOAD阶段从真实宽口供M，没有额外普通RAM端口。

关键reg：state6、stage4、kv_head3、q_head4、group_index7、chunk_index6、request_seq16、weight_index4、context_words10、padding_live、pad_index3、raw_saved、raw_index8、row_index、output_index9；数据寄存器仍为held_data/v_hold0/v_hold1/m_low_half。wire context_complete、padding_violation、head_t_violation为真实控制保护。

stage：IN_NORM0 PARAM_MOVE1 PROJECTION2 HEAD_NORM3 ROPE4 QK5 SOFTMAX6 PV7 WO8 RESIDUAL9 OUTPUT10 PAD_A11。state沿AH2编号0..16、DONE18；新增RAW_BEGIN19 RAW_READ_REQ20 RAW_READ_RSP21 RAW_WRITE22 RAW_COMMIT23 RAW_SAVED24 RAW_CAPTURE25 RAW_SAVE_REQ26 RAW_SAVE_RSP27 RAW_RELEASE28 OUT_BEGIN29 OUT_READ_REQ30 OUT_READ_RSP31 OUT_WRITE32 OUT_COMMIT33 OUT_DRAIN34 OUT_RELEASE35 CONTEXT_READY36。17以及未使用旧tag槽保留编号，不是另一个host输出通道。

local_tag沿AH2的0..20，新增L_PAD_A22；Wo保存仍L_M_SAVE17。raw capture写258使用独立state26/27，E残差由stage9选op0；L_A_Z2/3旧清零路径不再执行。

有限常1TB点沿AH2permit_s_req/rsp、permit_m_cmd/rsp、permit_load、permit_n_req/rsp、permit_e_req/rsp、permit_wreq/wrx、permit_output，另加permit_context_to_wo与permit_t_begin/write/commit/read/release。它们不是runtime配置或已冻结物理pins。独立验证必须覆盖完整context写ACK、8padding保持、KV共享、Wo全2048、raw T保活/逐字capture ACK、两lease顺序、provider真实流、错误/背压/取消和正常无reset复用。

当前合同和源审不替代真实仿真、外部PR批准、训练质量、共同底座物理或制造签核。
