# W3 源码与实际执行证据交叉审阅

这些记录由代理交叉审阅源码并读回 root 的实际日志形成。不是外部 PR 批准，外部审查人待指定。

# W3 FFN8 顶层独立静态交叉检查

检查对象为另一作者的 `drafts/ffn/block_w3_ffn8_top.sv`、根 `W3_ABI.md`，并结合本目录 E/G adapter 和固定707原生 M/S/T/E/G 接口。本审阅者未启动编译/仿真；随后只读核对 root 实际运行的 `runs/ffn-r02`、`runs/adapters-r01` 和 `runs/regression-r01` 源码、log、receipt。这不是正式外部 PR 审查或批准。

结论：本次只读检查未发现阻断性接口、数值布置、owner 切换或生命周期冲突。已读回的真实 ModelSim2020.4 证据支持本次 bounded FFN8 的21 case、旧 P2/W1 的47 case 回归，以及随后追加的 adapter standalone46 case；各自范围分别记录，不能由 FFN 中只用到的 E7/E0/G0 推断其它 op/fn。

| 检查点 | 源码结论 |
| --- | --- |
| op5 四 S32 carrier → compact S16 | `pack_m_four` 依次抽取各32-bit slot的低16；第一应答保存低4个值，第二应答拼到高4个，顺序与8个输出列一致。格式命令0x104/0x107分别为S16、RNE shift4/7，不是裸截 S64 |
| M 单实例复用 | gate/up 各先写 S464/S465 并消费普通写 ACK，才发下个 CLEAR；G 使用两个已持久保存的向量，M 后续 CLEAR 不影响它们 |
| down 格式与载入 | projection2 选择 A base468、A_wide1、B base460/B_wide0；EXEC0x9885 与 A16/B8 一致；mid padding469..471三字实际写零后才发loader |
| E/G 数据与数值接法 | E7读取466，左移3写467；G fn0/gated1读取gate464与up465写468；E0读取down472和residual467写473。与ABI Fin7/Fin10阶段一致，但不是完整模型定点准入 |
| M/load 固定次数 | 三projection各 CLEAR/SCALE/EXEC/READ0/READ1，共15次M命令/应答；每projection一次loader，共3次 |
| ordinary S 固定次数 | 正常成功路径入口16W、unpack1W、E7 1R1W、M save3W、G2R1W、mid pad3W、E0 2R1W、final1R：共32事务=26W+6R。loader私有宽读不算普通端口事务 |
| helper与owner | 一个 `u_s_ctrl`；LOCAL/E/G为真实MUX。E/G owner保持到adapter response被消费，adapter的最后writeACK在更早阶段已经被消费，helper已回IDLE才切owner；local响应消费后才切给E/G |
| 仲裁门控 | permit_s_req 同时控制helper输入valid与adapter侧ready；permit_s_rsp 对 native ACK valid/take对称；adapter response门控ready，valid保持。未将多个源输出直接短接 |
| done与T生命周期 | 最终一字S473经BEGIN1/WRITE/COMMIT/实际READ消费/RELEASE，release成功后才DONE；out backpressure由T holding保持。done_saturated累积M/E/G返回的sat，与done_error分开 |
| abort/reset/DONE | prestart abort丢frame、不产生done；RUN abort进入error DONE并协调叶/helper reset；既有DONE不被abort改结果，ready可同边沿消费一次；硬reset取消有效状态不造completion |
| 组合环 | leaf_reset只依赖外部reset/abort和顺序寄存internal_reset。error response消费后顺序置internal_reset，不由helper/nativeready构成反馈；本次未见组合环 |

## 实际证据只读核对

`ffn-r02` 的 compile 与 simulation exit 都为0；log 有21条 CASE_PASS，与 receipt.case_ids 相符，最终 `PASS_W3_FFN8 cases=21 cycles=7524`。log末尾 Errors0/Warnings0。读取了正常、零、正负极值饱和、混合/稀疏权重、held start、输入ACK/padding、abort/reset恢复、M EXEC error、E error不写目标、单G beat error后排空不写目标、E/G response在真实写ACK后hold等 case。

当前 top/E/G adapter 与此次运行快照逐字节相同。`ffn-r01`→`ffn-r02` 的18个RTL/include快照均未变；新 FFN TB SHA-256 为 `61e5427bc13f4ae24afbfd59645d4cfcfecd4ba3b628082ea691404e27ff2582`，追加的错误门为 TB 改动，不能说成 RTL 修复。新 W3 文件在运行时尚未提交，以真实输入文件SHA绑定；707只标原生叶源，不是新增 W3 实现 commit。

`regression-r01` receipt 列47个 case，三个 simulation log 的 CASE_PASS 总数一致，分别为 helper6、P2 MST13、W1 MST28；三个 PASS marker 均存在，compile/三次simulation均exit0。读取的所有compile、simulation、版本和vlib日志SHA都与各receipt记录相符。非零累计req/ACK差额属于明确的reset/abort测试，不能将全suite累计值误解为正常单帧事务计数。两组receipt/log的文件SHA和源码匹配结果见配套JSON。

追加读回 `adapters-r01`：46 CASE_PASS / 2231 cycles，compile和simulation exit0，所有log SHA与receipt一致，当前E/G adapter字节匹配运行快照；TB SHA为 `7eabf9949d4d056e79efaff35f840dabdc94e31412c9d0b1bd748f674496e0f6`。其中22个E数值/guard例、14个G数值/guard例和10个协议例。E op0..13各有定向输入，14/15为真实native error；E13 S32/compact16、E12 compact8、FMA第三操作数、count/tail均有有限例。G fn0..3各gated0/1、odd5与单lane1、invalid fn4/7、count0/9有例；不声称明确测了invalid fn5/6或全部count交叉积。10个协议例覆盖E/G输入捕获/背压、输出背压、真实写ACK门、S请求/响应保持和协调reset恢复；G stall检查至少2个同时在途。

全suite Gissued65/Gretired61含协调reset取消的在途项，不能宣称所有场景全局issued=retired。错误用例会核对目标703保持poison，正常服务会核对实际写ACK已消费才response。这里仍没有写应答故障回滚资格。

这些真实测试支持上表固定路径及所列适配器输入的数值、握手与恢复边界，不覆盖任意输入穷举、所有 E/G 组合、完整模型或时序物理。N/R/legacy在本次runner只做固定源语法compile，没有功能/物理资格转移。更多命令、历史metadata纠偏和有限覆盖解释见 `W3_VERIFICATION_REVIEW_SUPPLEMENT.md`。

限制：abort/error完成时 `done_saturated` 只代表已经被顶层退休/观察到的饱和标志，不代表被取消的未退休native流水是否曾计算出clip。已经接受的S写和已经消费的输出前缀不回滚。目标地址容量由本固定程序静态占用证明，不是通用存储分配器。无PPA、物理资格、全模型或通用FFN支持结论。


---

# W3 E/G适配器独立审阅

研究父提交`99d6df2e094febe4ea8fc9896301adbbfdc803ed`，原生源`707878621b2add4ed218b8c43df2e95c9a56e2ba`。本记录审阅另一作者的`block_w3_e_ctrl.sv`和`block_w3_g_ctrl.sv`，未修改其RTL，也未自行运行仿真。输入SHA、15项检查依据及后续RTL验证义务见同目录JSON。结论是在当前有界W3合同内未发现静态阻断，不能替代实际编译、背压/复位仿真和数值验收。

E端的操作数选择与原生操作一致：0/1/2/4/5/9使用A+B，3/6使用A+B+C，7/8/10/11/12/13使用A。op13按完整S32元素采集1..4项，输出按S16紧凑放低64，未用低64元素及高64清零；op12仍按S16输入，输出按8bit紧凑打包，尾部清零。count0/>8、op13 count>4及RoPE奇数count在发出任何读请求前报错。14/15不被转换为合法操作，而是在采集A后交原生E返回错误；原生错误不会进入目的写阶段。出处为E行33–70、97–130。

每份S读应答在READ_RSP捕获并消费后才发下个操作数，全部采集后才进入一次原生E握手；E输出按实际valid/ready退休，不假设固定延迟。请求参数只在IDLE的请求握手锁存，ISSUE、WRITE_REQ或RESPONSE停顿时依赖寄存字段，不再依赖调用方当前req字段。目的写请求后还必须消费真实写应答，才能形成服务response；response保持到调用方take。出处为E行72–88、97–136。

G将count1..8映射为ceil(count/2)对，issued仅随真实原生输入接受递增，retired仅随真实原生输出接受递增；retired<issued限制不会消费尚未发出的结果。最后retired等于总对数时，所有对都已issued。最后一对结果和转入WRITE_REQ在同一时钟以非阻塞赋值更新，目的写最早在下一拍接受，故最后数据已经捕获，不会把旧尾对写入。出处为G行53–59、68–76、88–104。

奇数count的最后dummy输入在A/gate采集时清零，未门控模式不读B，返回仅捕获声明count内元素，结果其余位维持零。fn4..7实际发往原生G，所有已发出对及剩余对都按计数排空；最后决定是否写回时合并先前error与当前out_error，因此不会漏掉最后一拍错误。即使前面出现error也不能提前释放caller lease或把残留流水线输出留给下一服务。出处为G行33–42、68–108。

caller必须从服务准入到response消费独占普通S owner。适配器内部没有仲裁器，也没有运行时epoch来识别旧结果；单独reset适配器会丢失issued/retired和未完成mem事务的归属，必须与原生E/G、S helper及外部owner协调复位。两个模块的reset会屏蔽valid/ready并清本地上下文，这不等于回滚已接受的S写或外部输出。全部source操作数在同一服务内依次读取，期间也不能由另一master修改；目的地址可以与source重叠的前提是所有操作数已采集后才写回。

错误边界必须分开：非法count、读应答错误和原生E/G错误都发生在目的写之前，可据代码确认这些路径不发目的写；WRITE_RSP的mem_rsp_error发生在目的写已接受之后，只能报告写应答错误，不能撤销已写数据。当前真实`block_p2_s_ctrl`没有native error输入，`rsp_error=0`，所以该写应答错误分支只能由合成测试服务或未来扩展产生。不能把“原生错误不写回”扩大成“任何error均没有写入副作用”。

本审阅没有发现需修改RTL的阻断项。独立适配器测试仍须覆盖：参数在接受后被修改、E12/13紧凑输出及尾部、E3三操作数、非法count、G奇数/ungated/其他函数、独立native背压和更多协调reset阶段。没有执行全opcode数值证明、综合/PPA或完整模型验收。

## FFN-r02实际证据读回

根任务实际在本地ModelSim SE-64 2020.4执行`runs/ffn-r02`；本审阅者只读取回执、日志、TB源快照和源码SHA，没有自行启动仿真，也不是外部PR批准。回执为`PASS_REAL_RTL_SIMULATION`，compile exit0、simulation exit0，日志有21个唯一CASE及`PASS_W3_FFN8 cases=21 cycles=7524`，未出现FAIL_W3/Fatal。机器记录保留全部CASE名称和范围。

审阅draft、正式checkout及运行source快照逐字节SHA一致：E adapter为`e0325cb2a833a6609c3c7996f1bf9a89b0fe02fab32e7a9a108921711e7dd621`，G adapter为`9174cb97a0dd9e969f7d6fce49dc32eda4ab29c50c43f3a3d47503d34fba3c30`，FFN top为`704c3f41a4265517cf768250e9256b59f420c88c8068a066e63e54dd280159e8`。所以此有限运行证据确实对应本次静态审阅的适配器，没有用其他版本的通过结果替代。

FFN正常数值路径只使用E7/E0、count8，以及G.fn0/gated1、count8四对；正常帧逐阶段S数据、32请求/ACK（26写6读）、15M命令、3loader及最终T输出/RELEASE均由该TB检查。故障用例还验证一次真实native E opcode14导致不写残差/最终输出并恢复；四个G对中一次真实fn4错误仍收齐4个输入/输出、不写mid/最终输出并恢复；E/G服务response在真实目的写ACK后保持，以及已存mid而保留G response时的协调reset。这些补足相应FFN有限路径证据，不能扩展成E12/E13、所有count/fn/op或所有adapter阶段已经测试。

回执SHA为`b0f019fb2990960a2190b11ae7bf878b63101db674e8a50482ae1a49757897a4`，compile.log为`7b352f1dac55c952acb27a3071f4447b804f1e879dab84b86aba812b6985215c`，simulation日志为`eb18e9063c3afd90c5fd8c0b168f237c123179d5aee674b19580248614c944a6`。独立adapter standalone TB仍待执行，本记录未计入其任何未来结果。全程累计823个S请求/821个ACK包含显式abort/reset丢弃，不能写成全局守恒；正常帧32/32另有局部检查。
