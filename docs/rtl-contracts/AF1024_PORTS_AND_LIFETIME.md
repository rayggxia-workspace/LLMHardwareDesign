# L4-AF1024：固定完整A→双行F接口与生命周期

Issue151 / PR152，Melodydt；研究输入ddc6b42、main4b1df2c7，叶源沿用7078786相同字节。新增`project/rtl/block_connection_w4/block_w4_af1024_top.sv`，实例原样`u_a=block_w4_afull_top`及`u_f=block_w4_f1024_top`，继承52份RTL/TB/include不改。本文是候选实现合同；作者未运行本地RTL编译/仿真、服务器或远端操作，实际source/TB/golden/服务器回执由根任务另行冻结，不能由本文预报PASS。

## 1. 本轮固定组合与资源

完整A为H1024、Sq2、KV8/Q16、D128、Wo及原残差，输出两行Y。一个baseline F1024采用H1024/I3072，顺序处理Y0和Y1，各做post-A RMS→gate/up→SwiGLU→down→原Y残差。双方接口是S16 Fin10、权重Fin7，直接逐bit传递Y，不做RNE3/S8窄化，不把F残差误取为A原X。

两个子实例合计M2/N2/E2/G1/R0/S2/T2，即11个叶实例。新增唯一向量payload存储是`gamma_bank[0:127]`×128bit，共16384bit/2048B，供F两行回放独立gamma；没有4KiB Y holding，也没有新的T/S宏。父只转发A/F数据和参数流，子内部S、T、输入holding及controller寄存器仍是真实成本，不能把2KiB当整个系统面积。

此为L4固定纵向验证top，不是L5通用母控/peer storedACK网络，不冻结AF产品岛，不说明任意模型、MEM或M11/M12系统物理已实现。M1–M10最终必须预制父FSM、gamma FFbank、路由/MUX/保持和元数据逻辑；金属不能新增这些有源器件。

## 2. 公共任务与输入输出

| 端口族 | 合同 |
|---|---|
| clk/reset/abort | 单时钟；reset高有效同步且不造DONE。abort/error协调reset两个子树，父保留已接任务的错误终态 |
| job_valid/ready、job_generation32 | 独立接单形成完成义务；之后输入、prestart、A、F装帧/等待/运行等任一阶段错误或取消均held errorDONE |
| weights_a_version16、weights_f_version16 | 在父job握手分别捕获；A允许0，baseline F不允许0。若F version0，父接单后直接errorDONE，不发A job或任何输入数据 |
| in_valid/ready/data128、in_generation32、in_index10、in_last | 576字，接受时核generation、index0..575、仅575为last；坏拍不写子S或父gamma FFbank |
| input_stored、start_valid/ready、busy | 576字都已接受且A的真实input_stored建立后才父stored/start；busy覆盖job接收到DONE消费 |
| out_valid/ready/data128、out_index10、out_last、out_generation32 | F两行最终输出共256字；父index=row×128+F index，last仅255，generation为父捕获值。F T在正常背压期间真实保留输出 |
| done_valid/ready/error/saturated/partial、done_words9、done_generation32 | 独立held终态；正常words256。partial仅error且已有最终host输出被接受，不代表内部S写能回滚 |

父input0..447通过valid/ready转给A原448字帧，重建A child index9及**child last仅447**；父第447字的last仍必须0。父input448..575写gamma_bank0..127，第575字last1。F gamma独立于A inputNorm gamma、Q/K head gamma，不能混用。

Gamma FFbank不依赖reset清数据；只清有效性/计数，每个新父任务必须重新写完128字才能进入RUN。硬reset后的旧FF值不可作为新任务输入。没有把父gamma接受伪装成S ACK：它是父FF写入；稍后两次F帧中都必须经过真实F普通S写ACK。

接单后F version0或F ID预算不足均有明确错误终态，不无穷等待。未接单abort无DONE；DONE期间abort保留已有结果，ready同拍只消费一次。错误/取消reset两个子树并作废在途；已接受S写和host输出前缀不回滚。硬reset直接取消父义务，不补DONE。正常DONE消费后无需reset复用。

## 3. 两个独立权重provider

A/F权重端口保持两个子原位宽与语义，不伪造一个统一job号：

| A端口前缀a_ | 位宽 |
|---|---|
| a_wreq_valid/ready；job/seq/version | job32、seq16、version16 |
| a_wreq_matrix/head/group/chunk | 2/4/7/6 |
| a_w_valid/ready/data、job/seq/version/index/last/error | data128、32/16/16/4/1/1 |

| F端口前缀f_ | 位宽 |
|---|---|
| f_wreq_valid/ready；job/seq/version | job16、seq16、version16；job由baseline F真实start计数生成 |
| f_wreq_matrix/group/chunk、f_wreq_row | 2/9/7，额外只读row1标识当前父第0/1行 |
| f_w_valid/ready/data、job/seq/version/index/last/error | data128、16/16/16/5/1/1，和原F一致 |

A端严格拒绝任何接受的坏/旧/未来tag；baseline F按原合同可以drain严格旧tag。父只在对应当前已启动且未关闭子任务期间开放provider，并对请求/响应两端对称门控，不改变子错误策略。f_wreq_row在同一F任务及其完整请求/响应期间稳定，不能把它当作返回包中已校验的父generation字段。

两个F行都实际请求完整9MiB权重流，不能因同version免费复用上次权重：父任务实际A6MiB+F18MiB共24MiB。两个provider可由同一个外部源实现，但本轮不代表真实MEM、带宽或共享仲裁器已经完成。跨子reset/abort后，调用方须协调provider清理旧流；原F job16会随reset重用，不能宣称已经隔离任意外部晚返回。

## 4. A T保活→F真实stored→逐行完成

1. 有效父job先发A job握手，再接576字；A448字的每字S写ACK依旧由A helper实际完成。父可在A最后ACK尚未完成时继续捕获F gamma，但父stored/start必须再等A实际stored。
2. 父start后启动A，直接等待其真实T输出。A完成全部计算并提交256字Y后，F_HIDDEN先把当前A T字送到F input接受一次，置f_y_pending及f_frame_seen，但保持A take=0。F inputholding捕获后in_ready下降；该字真实S写ACK退休、F回IDLE重新开放in_ready时，pending允许父才take源A T，清pending并推进下一字。等待期间不重复向F发送此字；新增成本只1bit，不是Y holding。
3. 每行128字Y后，A source T停止take。第一行结束时A nativeT停在index128，必须跨整个F0装gamma、运算、输出、release及DONE保持，不能等A DONE才启动F0，否则死锁。
4. 父F_GAMMA重放128字gamma；F实际接收Y128+gamma128，最后普通S写ACK建立f_input_stored后，父才可发f_start。一次input ready/接受本身不是stored ACK；上述Y专用两阶段门依赖已锁定baseline F在Y索引0..127的“capture后ready下降、前字ACK退休后才重开”合同，不是无条件把ready当ACK，也不能未经适配搬给另一种F实现。
5. F0的128个最终host输出都接受后，还必须等F真正T RELEASE后的正常DONE，消费它才取A第128字开始F1。F1重复真实gamma回放和全部计算，参数流不省略。
6. 第二行A最后Y字在F真实S写ACK退休后才被源A T消费，所以A实际source RELEASE晚于全部256个Y目的写ACK。父独立A collector检查A已交接256字、done_words256、generation及无partial/error后收A DONE，允许它发生在F1装gamma/等待/运行期间。它仍不表示F的256字整帧（Y128+gamma128）或F计算已经完成。
7. 父正常DONE要求A已实际关闭、F0和F1各真实stored/start、最终输出take及T释放/DONE全部闭合。若F1已完成而A DONE被背压，父留WAIT_A_DONE，不能提前报成功。

源A保留每个Y字直到其在F S真实写ACK；F原有128bit输入holding只负责目的写入过程，没有新增整Y缓冲。A T已释放后，父仍继续等包含gamma的F整帧实际stored。f_frame_seen在F capture时即建立，不能等源A take才置位；因此capture后F prestart helper错误导致丢frame/ready重开时，父先通过seen+busy/stored检测阻止A take/gamma feed并形成自己的errorDONE，不能把错误重开当成功ACK。

## 5. 有限F ID预算镜像

baseline F `start_ready`要求version非零且16bit job_counter未耗尽。一个父任务需两个F start，因此不能在只有一个ID时接收后卡死第二行。

父维护独立16bit `f_job_mirror`，只数公开的真实F start握手，不读取子私有counter；随同一个child_reset清零，正常父DONE/empty_job不清。父job接受时若mirror>0xFFFD，直接held errorDONE且不发A job，预留至少两次非回绕F start；F_START时若mirror=0xFFFF也立即错误，不靠无限等ready。镜像是新增控制成本，不是payload；错误reset后的ID复用必须和provider协调。

## 6. 元数据、完成与饱和归属

每次A输出检查父generation、全局index0..255、last仅255；每次F输出检查本行index0..127、last仅127，坏数据不暴露host。父将F输出index改为row×128+child index，不把旧16bit F job号当作父32bit generation。

子A有独立接单义务；子F原接口无job admission、prestart可失帧。父自己的job义务覆盖A尚未start、F部分装帧和等待stored等窗口，不能依赖子prestart产生不存在的DONE。unexpected/early DONE、子错误和帧丢失都停止后续发令并协调reset。

saturated只从当前已启动且未关闭的A/F任务采样，父DONE后冻结flags；未启动F或已关闭A的旧flags不得污染当前结果。父done_words只记最终F→host实际握手数0..256；A→F内部256次交接不计作host输出。

## 7. 正常计数：子合同相加，待独立实证

| 项目 | 预期 |
|---|---:|
| 父输入 /A子输入 /两F子输入 | 576 /448 /512 |
| 父gamma FF写 /向F gamma回放 | 128 /256字 |
| A→F Y交接 /最终host输出 | 256 /256字 |
| A job/start/DONE /F start/DONE | 各1 /各2 |
| 普通S请求及ACK | 2582560=503968R+2078592W |
| M命令响应 /EXEC | 111232 /98624 |
| loader /S宽读 | 98624 /787968 |
| A128 /B512流 | 492544 /394240 |
| N服务 /native命令响应 | 84 /2856 |
| E服务 /G服务及pair | 1280 /768及3072pair |
| 权重请求 /128bit拍 /字节 | 98304 /1572864 /25165824（24MiB） |
| T BEGIN/COMMIT/RELEASE | 各4（A两lease+F两lease） |
| T write /take | 768 /768（A raw256+A Y256+F host256） |

这些是现有子合同相加的正常路径计数，不是服务器PASS或吞吐/PPA。A/F两条provider seq和job域分别计数，不能把总98304请求塞进一个假想16bit统一seq。

## 8. 观测与验证限制

实例u_a/u_f，内部子S/T/controller沿原名；新增唯一向量gamma_bank。父reg：input_index10、hidden_index7、gamma_index7、row_index、a_words_taken9、f_out_count8、output_count9、generation_hold32、a_version_hold16、f_version_hold16、f_job_mirror16、f_y_pending1、a_admitted/a_started/a_closed/f_frame_seen/f_started。f_hidden_capture为目的接受事件，a_transfer为其后ACK已完成的源退休事件。

state：WAIT_JOB0 A_ADMIT1 INPUT2 STORED3 A_START4 F_HIDDEN5 F_GAMMA6 F_STORED7 F_START8 F_OUTPUT9 F_DONE10 WAIT_A_DONE11 DONE12。

常1有限TB点：permit_a_job/a_feed/a_start/a_take/a_done/f_feed/f_start/f_done。它们不是host配置或物理pins。应独立验证A T index128跨F0保活、两个F实际S ACK及参数重放、父预start终态、坏metadata/版本0/ID耗尽、子frame_lost、错误/背压/取消、前缀不回滚、DONE保持和正常无reset恢复；不通过直接赋子RAM代替这些数据路径。

本固定纵向组合不等同L5跨岛storedACK网络、外部晚返回隔离、真实模型质量、产品控制ROM/M11绑定或共同底座物理资格。
