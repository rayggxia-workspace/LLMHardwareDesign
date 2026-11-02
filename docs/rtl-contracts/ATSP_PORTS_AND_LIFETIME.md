# L4-A-TSP RTL接口与机制合同（本轮候选）

Issue151 / PR152；输入研究7aba36a，main4b1df2c7，原生7078786精确字节。新增模块 `project/rtl/block_connection_w4/block_w4_atsp_top.sv`，不修改继承46份RTL/TB/include。本说明是新RTL的接口合同，不是编译、仿真、物理或模型质量回执。

## 1. 范围与资源

本模块实现H1024、Sq2、S16原残差的真实T保存、岛内S回放与E残差闭环。Wo投影结果由明确的外部切口提供，**没有M、QKV/head/Softmax/Wo计算，也不是完整Attention或L5网络**。实例为一S_macro、一T(transaction6k)、一E、一S helper和一个原有E controller。S_macro内loader固定不启动。

顶层只有一个128bit `held_data` 数据holding，没有原X、Wo或输出的私有向量数组。S/T及已有helper/Econtroller内部真实寄存器另计；不能把128bit写成完整控制面积预算。本模块是需要在M1–M10预制的有源控制/捕获/MUX逻辑，不是M11可以新增的器件。

数值合同为八路S16有符号、共同固定单位（本切片采用Fin10）。E op0、shift0、count8逐字加法，结果S16饱和；saturated单独累计，不把饱和当协议错误。不声称真实训练分布下的量化质量已经接受。

## 2. 公共端口

| 端口 | 语义 |
|---|---|
| clk/reset/abort | 单时钟；reset高有效同步，硬reset清任务、不造DONE；abort协调复位全部叶/适配器 |
| job_valid/ready、job_generation[31:0] | 独立任务接收；必须先接job再送输入。generation由调用方提供和协调，当前不提供全系统防回绕/抗重放管理 |
| in_valid/ready、in_data[127:0] | 256字token-major：X0[0..127]后X1[0..127]；一次仅一个待S写ACK字 |
| in_generation[31:0]、in_index[7:0]、in_last | input_fire时严格核对job generation、顺序0..255及仅末字last；错误不发S写，直接error DONE。新job收到旧tag不会静默污染，也不自动丢弃旧tag继续 |
| input_stored、start_valid/ready | 第256个真实S写ACK退休后stored/start_ready；start只能接受一次 |
| busy | 从job接收到DONE消费，含部分输入、等待start、HEAD_HOLD和终态保持 |
| spool_saved | 原X的T事务已COMMIT并进入可读保持，直到原残差lease真正RELEASE；不是整个Attention完成 |
| work_valid/ready、work_addr[7:0]、work_data[127:0] | 仅HEAD_HOLD可真实写S0..255，供覆盖旧S原X的有限测试/未来head工作切口；不是完整head执行器 |
| work_rsp_valid/ready/error | 实际S写ACK之后的独立响应，stall时保持。单在途，响应消费前不能resume；S本身没有error pin，正常error恒0 |
| resume_valid/ready | 结束HEAD_HOLD，进入Wo/residual流程。work offer优先；work写/响应在途时不可resume |
| wo_valid/ready、wo_data[127:0] | 每组g依次提供Wo0g、Wo1g，共256字；每字真实写S256/257并等ACK |
| wo_index[7:0]、wo_last、wo_generation[31:0] | 接受时检查index=2g+row、last仅255、generation匹配。错序/身份产生错误DONE，不写目的S，不自动丢弃旧tag继续运行 |
| out_valid/ready、out_data[127:0]、out_index[9:0]、out_last、out_generation[31:0] | 最终结果token-major 256字，取自第二次T事务。输出valid在正常背压期间保持，data/metadata稳定 |
| done_valid/ready/error/saturated/partial | 独立保持终态；partial仅表示错误终态前有最终host输出被接受，不表示S写回可回滚 |
| done_words[8:0]、done_generation[31:0] | 最终host输出实际握手数0..256及任务generation；正常256。RUN内S/T写、内部raw take不计入done_words |

job握手形成完成义务：之后在输入加载、等待start、保存/HEAD_HOLD、回放或输出阶段发生abort/error，均返回同generation的error DONE。未接job的abort无DONE。DONE期间abort保留已有结果；同拍done_ready只消费一次。DONE消费后无需硬reset即可接下一任务，所有输入必须重新完整写ACK。X和Wo身份/顺序检查是固定任务接口保护，不是运行时数据类型系统；generation防回绕仍由调用方协调。

在work错误ACK场景，先保持work响应供调用方消费，再进入错误DONE；期间不再接受work/resume。abort/reset可以明确取消work通道。普通S写被接受后，晚到ACK错误不能回滚已写内容。其他RUN错误协调reset使叶和在途helper失效，已接受最终输出前缀不回滚。

## 3. S与T的真实生命周期

1. 输入256字依次写S0..255，逐字等待native S写ACK再推进input_index。
2. start后T BEGIN256(owner1,generation=job)；对g=0..127真实读S[g]、S[128+g]，依次写T[2g]、T[2g+1]。所有写完后COMMIT，等待READ_HOLD才置spool_saved。
3. HEAD_HOLD及work期间T read_take=0。可通过work接口真实覆盖S0..255，证明不依赖旧S原X；T剩余2KiB不能另开事务。
4. resume后每组接受两字Wo，分别写S256/257并等ACK。然后逐row取T当前原X字进入held_data，真实写S258并等ACK，才给E service租约。
5. E读取S[256+row]和S258，op0/shift0/count8，目的row0为S[g]，row1为S[384+g]。E目的写ACK及service响应都退休后，才复用S258/进入下一row或下一组。E在整个服务直到响应消费期间独占普通S owner。
6. 最后一个原X字消费且最后E写ACK/响应退休后，实际T RELEASE，随后才第二次BEGIN256(owner2，同job generation)。S0..127/384..511按token-major真实读回写T，COMMIT后向host输出，最后take后实际RELEASE，才成功DONE。

raw和output两个lease均检查T owner、generation、word_count256、read_index、read_last；错误元数据不take、不暴露host payload，并产生错误DONE。T protocol_error是真实原生信号；S helper没有原生错误检测，不能因TB force h_rsp_error声称S具备硬件检测能力。

## 4. 正常事务计数

令W为实际完成的work写事务数。

| 阶段 | S读 | S写 |
|---|---:|---:|
| 原X输入 | 0 | 256 |
| raw spool | 256 | 0 |
| HEAD work | 0 | W |
| Wo切口 | 0 | 256 |
| raw capture写S258 | 0 | 256 |
| 256个E服务 | 512 | 256 |
| 最终T封装读S | 256 | 0 |
| 合计 | 1024 | 1024+W |

普通S请求/真实ACK均为2048+W；若覆盖全部256字，则2304=1024R+1280W。T有2次BEGIN/COMMIT/RELEASE、512次write、512次take（raw256+最终host256）。E有256个服务、256个原生输入/输出。M/N/loader调用为0。此表是RTL正常路径推导，实际回执由独立TB和服务器运行给出，不预填PASS。

## 5. 观察点与有限测试入口

实例名：u_s、u_s_ctrl、u_t、u_e、u_e_ctrl；S RAM为u_s.storage.bank0..3，T为u_t.payload（TB不能通过预填这些数组代替实际接口）。公共内部信号沿既有命名：h_req*/h_rsp*、s_req/we/addr/din/ready/valid/take/dout、e_req/rsp/e_in/out、t_begin/write/commit/release/read*。reg为state、owner(0local/1E)、input_index9、raw_index8、group_index7、row_index、wo_slot、output_index9、output_count9、job_generation_hold32、held_data128。

常1的有限TB stall点：permit_s_req/rsp、permit_e_req/rsp、permit_t_begin/write/commit/read/release、permit_work、permit_resume、permit_wo。它们不是产品配置端口；强制故障用于验证控制错误路径，不制造本不存在的原生错误引脚。S响应许可在native S take和helper valid两端对称门控。

state数字：WAIT_JOB0、INPUT1、INPUT_REQ2、INPUT_RSP3、STORED4、RAW_BEGIN5、RAW_READ_REQ6、RAW_READ_RSP7、RAW_WRITE8、RAW_COMMIT9、RAW_SAVED10、HEAD_HOLD11、WORK_REQ12、WORK_RSP13、WORK_ACK14、WO_WAIT15、WO_REQ16、WO_RSP17、RAW_CAPTURE18、RAW_SAVE_REQ19、RAW_SAVE_RSP20、E_REQ21、E_RSP22、RAW_RELEASE23、OUT_BEGIN24、OUT_READ_REQ25、OUT_READ_RSP26、OUT_WRITE27、OUT_COMMIT28、OUT_DRAIN29、OUT_RELEASE30、DONE31。

本作者未执行本地RTL仿真、未访问服务器或写Git远端。候选需由根任务冻结源码、独立TB及实际服务器编译/仿真后给出真实结果。
