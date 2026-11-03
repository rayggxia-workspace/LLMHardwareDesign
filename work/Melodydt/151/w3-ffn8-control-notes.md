# W3 FFN8 fixed control candidate

研究父提交`99d6df2e094febe4ea8fc9896301adbbfdc803ed`，原生叶源`707878621b2add4ed218b8c43df2e95c9a56e2ba`。本目录新增`block_w3_ffn8_top.sv`，不修改P2/W1或原生宏。输入数据可变，操作、维度、地址、尺度与调度均固定；没有host程序/shape/opcode装载。N未接，属于FFN8核，非完整F子层或模型量化验收。

顶层为单个可综合FSM：IDLE接受16拍输入，通过一个`block_p2_s_ctrl`逐拍写S448..463并消费真实ACK；第一拍x高64与第1..3拍全字硬件清零。输入指针只在helper的写应答被消费后推进。第16次ACK后才置frame_stored/start_ready，早到pulse不保存，held valid可在ready出现时接受一次。busy从首个输入接受开始，贯穿完整未RUN、RUN及等待DONE消费。

start后固定程序：写sign-extended x至466；E7将x从Fin7左移3存467；M gate投影、M up投影各按CLEAR→SCALE1→loader→EXEC→op5 half0→op5 half1→S写ACK执行，结果分别存464/465；G.fn0/gated1读取两字，保存468；真实写零469..471；M down按相同流程但A16/B8、op5 shift7保存472；E0读取472与467求和存473；回读473，T BEGIN1/WRITE1/COMMIT/外部TAKE1/RELEASE，然后才给成功DONE。外部消费者反压期间结果保持。

M gate/up输入S8 Fin7，累加Fin14，op5 width1/shift4=`0x104`得到S16 Fin10。每个M.op5应答是4个S32载体，只抽各载体低16，两个half合成8个S16；没有把前64bit直接当四个紧凑S16。down输入A16 Fin10与B8 Fin7，Fin17原始累加经op5=`0x107`得到Fin10。M清空前已保存前一个投影并消费真实S ACK；不声称单M能恢复被覆盖的partial上下文。

owner=LOCAL0/E1/G2。E/G一次服务从发请求前到rsp被消费独占整个普通S helper，req/rsp payload由adapter锁存。helper输入与响应按owner选择，S原生只有一个req/wr/addr/din与take驱动。E/G response意味着目的写ACK已经消费，顶层才交还owner。loader使用S内部512bit真实仲裁端口，LOAD期间顶层不请求普通事务。正常程序普通S为32请求/32ACK，其中26写/6读；M为15命令/应答，loader3次、A/B各3次；E服务2次、G服务1次；T最终只有1字。这些是待实际仿真确认的正常路径参考计数。

done_saturated累计每个已消费M/E/G response的饱和标志；clip是定义的S16裁剪，独立于done_error。error/abort completion保留已经观察到的累计clip；尚未退休阶段不推测clip。DONE期间两个flag均保持，包含abort；同拍done_ready可消费一次。RUN原生错误或abort生成一份error DONE，并发同步叶/helper/adapter复位；未start的abort只废弃输入frame，无任务DONE。硬reset废弃frame、执行和DONE，不保证回滚RAM或已被外部take的输出。

固定TB许可点：permit_s_req/rsp、permit_m_cmd/rsp、permit_load、permit_e_req/rsp、permit_g_req/rsp，真实硬件均恒1。E/G许可对服务valid/ready两端一致；S rsp许可对native S ACK valid/take两端一致。它们只用于有限RTL背压/故障测试，不构成运行时主机配置。

本目录实际执行的管理结构检查PASS；它不验证RTL。本初稿时新W3编译和仿真由根任务准备，尚无本目录独立执行的RTL通过声明。数值oracle和TB由另一agent独立提供，最终以根任务真实ModelSim回执及源码SHA为依据。未执行综合/PPA、完整F、完整模型或服务器任务。
