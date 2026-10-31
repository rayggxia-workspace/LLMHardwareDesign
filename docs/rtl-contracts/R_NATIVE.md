# R 原生 RTL 审计与总方案重写输入

本稿仅为 Issue151 的独立源码审计草稿。冻结研究提交为 `faabeda68b3b098ba562d68517319e02725f5bc3`，引入的 PR144 来源提交为 `643c6012a11cbf461146ac40fbf61485223fe946`。只写本目录的 `r-audit.md` / `r-facts.json`，未改正式文档、叶宏、服务器或远端。

## 1. 来源、校验与证据边界

直接审计文件：`work/Melodydt/151/merge-pr144-643c6012/integrated/project/rtl/block_library_v1/block_v1_r.sv`，13710 bytes、267 行，Git blob `a09828d702ca1c6f9883d0a532c0588a142676a7`，SHA-256 `458359b93c07a74056f77d1616610688eec13f7231acc791257aaf83f1a8c246`。本次重新按原始字节计算，且与第一阶段 `sources/r.txt` 完全相同。以下 `R:Lx` 均引用该文件的一基行号；线上固定入口为 [冻结 R RTL](../../project/rtl/block_library_v1/block_v1_r.sv)。

当前跟踪文件是临时算术缩窄候选：`rne` 的输入 S65、返回值及 `value` 为 S52；state 仍 S32、乘积 S65、点积 S64（R:L16、29–39、48–65）。原源 R4032 的封存物理数据库与这个文件不能互换。`BLOCK_V2_RESULTS.md:L43` 报告了全输入局部 SAT 与三初态回归通过，但本次没有重跑该证明，也没有读取该证明完整包；不得据此宣称整宏 LEC 或最终物理通过。该页 L117–129 在冻结时仍记录 053/062 拥塞失败、076 hold 修复缓冲上限失败；R 尚未取得最终资格。

本次实际运行 `python scripts/check_project.py`，管理结构检查 PASS；本稿其余结论为 RTL 阅读及字节检查。未运行 RTL 仿真、形式工具、SystemC、综合或 P&R。

## 2. 原生接口、时钟与资源

| 项目 | RTL事实 | 对母控/子控的约束 |
|---|---|---|
| 时钟/复位 | `always @(posedge clk)` 内同步高有效 `reset`，无异步 reset 事件（R:L98–107）；`cmd_ready` 组合受 `!reset` 门控（L46） | 单时钟候选可直接同步；跨域必须新增真正 CDC。reset 不能作为撤销已确认外存写/系统发布的方法 |
| 命令 | `cmd_valid/ready`、4-bit op、10-bit index、128-bit data（L5–8） | payload 在握手时有效；不是 start/done 旧接口，也无独立 abort 引脚 |
| 响应 | 128-bit data、valid/ready、error；无 tag、无 saturation 位、无分行错误掩码（L7–8、108–110） | R_CTRL 唯一发令/接受响应，以串行在途记录归属任务。外层 job_id/token/tile/scale/version 不能假定存在于 R 总线 |
| 接受条件 | `phase==IDLE && (!rsp_valid || rsp_ready) && !reset`（L46） | 可在消费上个响应的同拍接受新命令；拒绝在计算中插入 REVOKE。普通加载/读命令也有响应，须逐一消费 |
| busy | `busy=!cmd_ready`（L47） | pending 候选存在时也可能 busy=0。busy/ready 不表示 context 可换 owner 或可 OPEN |
| 存储 | 两银行各 2048×S32；一个 active、一个 shadow（L16–23）；state 为 `length×8`，length=1..256 | 最大 active 8192B、shadow 8192B；shadow 被 SSM 逐元素 decay 复用，不存在第三份因子 RAM |
| 其他数据 | Q/K 各256×S16；x/inject/skip/输出各8×S32；history/history_next 各24×S32；taps32×S16（L25–28） | 输出只有32B；history 是3个过去采样×8lane，每份96B；有限缓冲不能充当全 token 版本库 |

复位清有效位、pending、owner/epoch/position、bank_role 及流水标志，但不清 state/history/key/query/x/inject/skip/taps 的 payload 数组（R:L99–106）。reset 后必须重新 OPEN/装载，不可因残留 payload 看似正确而使用。总线外层、外存访问器和事件槽也必须协调排空/换代，防止旧响应被新任务认领。

## 3. 完整 opcode、index 与位域

所有命令先置 `rsp_data=0、rsp_error=0`；非法条件使响应 error=1。下表中“忽略”指 RTL 没有检查或使用该字段，不代表产品程序应允许随机填充。建议发令器把所有忽略字段清零，但这是外层规范。

| op | 功能/索引 | cmd_data 位域/格式 | 合法条件与副作用 | 行号 |
|---|---|---|---|---|
| 0 | OPEN；index忽略 | `[8:0]=length`，`[40:9]=owner`，`[72:41]=epoch`，`[104:73]=position`，`[127:105]=0` | length 1..256，不能有任何 pending；可覆盖一个无pending的旧context。设置context有效，清所有装载/参数/输出有效位；不清payload，不校验旧owner | 112–115 |
| 1 | 装 active state 半行，index=0..2×length−1 | 4个小端S32，lane i在`[32i+:32]`；地址`4×index+i` | context有效且无state/history pending；立即写 active，标 active_valid[index]。不是写候选 | 117–123 |
| 2 | 装 key / SSM B；index=0..31 | 8个小端S16，Q1.14；地址`8×index+i` | context有效且无pending_state；允许pending_history。只对EXEC实际使用的前length元素要求有效；末组多余lane不计算 | 125–128、68–71 |
| 3 | 装 query / SSM C；index=0..31 | 同op2 | 同op2 | 125–128 |
| 4 | 装 x/inject；index=0..3 | 四S32。index0/1装x[0..7]；index2/3装inject[0..7] | context有效且无pending_state，允许pending_history；各半包有独立x_valid位 | 130–132 |
| 5 | index0装公共 decay/beta；index1/2装skip | index0：`[31:0]=decay`、`[63:32]=beta`，`[127:64]=0`；两个无符号Q1.31码均≤0x80000000。index1/2：四S32 skip，Q16.16 | context有效且无pending_state，index≤2；允许pending_history。index0建立param_valid；index1/2分别建立skip_valid | 134–139 |
| 6 | EXEC；index忽略 | `[1:0]=mode`（0 GDN、1 SSM、2 conv），`[33:2]=owner`、`[65:34]=epoch`、`[97:66]=position`，`[127:98]=0` | 必须匹配当前身份、context有效、无pending_state；其余条件见模式表。开始清旧output_valid与failed。成功结束产生候选，不自动提交 | 141–154、249–254 |
| 7 | COMMIT；index忽略 | `[31:0]=owner`、`[63:32]=expected_epoch`、`[95:64]=expected_position`、`[127:96]=next_position` | context有效、至少一个pending、前三字段匹配、epoch≠0xffffffff。next_position任意32bit，RTL不验证+1/单调/无回绕。接受后COPY提交，必须等真实成功响应 | 156–160、255–261 |
| 8 | REVOKE；index/data忽略 | 无原生owner/epoch检查 | 仅在命令口可接受时清 pending_state/history、output_valid、decay_valid；无context要求。不清active、history、其他装载有效位，也不回滚已提交状态 | 162 |
| 9 | 装 active history；index=0..5 | 四S32；地址`4×index+i`，总24值=3×8lane | context有效、无任何pending；立即写history及history_valid。不是装history_next | 163–165 |
| 10 | 装 taps；index=0..3 | 八S16，计算按Q1.14；地址`8×index+i`，总4×8lane | context有效、无任何pending | 167–169、83、88 |
| 11 | 读 active state；index=0..2×length−1 | cmd_data忽略；rsp_data四S32 | context有效且该半行active_valid；允许pending。pending_state时读到旧active，不是shadow；commit后读新active | 171–174 |
| 12 | 读 output_value；index=0/1 | cmd_data忽略；rsp_data四S32，总八S32 | 仅检查output_valid及index；不显式检查context/owner。读取最后一次成功EXEC的输出；不是整份候选state/history_next | 175–178 |
| 13 | 读metadata；index/data忽略 | rsp：`[8:0]=length`、bit9=pending_state、bit10=pending_history、bit11=output_valid、`[31:12]=0`、`[63:32]=owner`、`[95:64]=epoch`、`[127:96]=position` | 无context要求；不返回context_valid/failed/装载mask/phase | 179 |
| 14 | 读 active history；index=0..5 | cmd_data忽略；rsp_data四S32 | context有效且该半行history_valid；允许pending_history，但读旧history，commit后才是新history | 180–183 |
| 15 | 装 SSM 逐元素decay半行，index=0..2×length−1 | 四个无符号Q1.31码，每码≤0x80000000 | context有效且无任何pending。写inactive/shadow并置decay_valid；不是通用shadow导入，更不是导出接口 | 117–123 |

op0/6/7 的身份位域互不相同，不能复用一份未重打包的128-bit描述符。owner/epoch/position只在EXEC与COMMIT校验；装载、读回和REVOKE没有完整身份保护。因此命令端口必须有唯一 R_CTRL 和外层租约，不能把这些字段当硬件访问权限系统。

## 4. EXEC 模式的实际准入与数值

共同条件为context有效、无pending_state、身份匹配、mode≤2和保留位为0。`loaded`要求前length行两半state都有效；`coefficient_loaded`要求覆盖前length元素的全部key/query组有效；`factor_loaded`要求2×length份op15半行均有效（R:L66–72、141–145）。

| mode | 额外有效条件 | 数值过程（RNE均为ties-to-even） | 成功候选 |
|---|---|---|---|
| 0 GDN | state与key/query完整；param_valid；x_valid低两位均1；允许已有pending_history | `D=RNE(H*d/2^31)`；`pred=RNE(sum(D*k)/2^14)`；`e=x-pred`；`eβ=RNE(e*β/2^31)`；`H'=D+RNE(eβ*k/2^14)`；`y=RNE(sum(H'*q)/2^14)` | pending_state=1，y八S32，保留先前history候选 |
| 1 SSM | state/key/query/param完整；全部op15因子；x_valid=0xf（x及inject都齐）；skip_valid=3；允许已有pending_history | `D=RNE(H*d_element/2^31)`；`H'=D+RNE(inject*k/2^14)`；`y0=RNE(sum(H'*q)/2^14)`；`y=y0+RNE(x*skip/2^16)` | 同上；逐元素decay被消费 |
| 2 conv | 无pending_history；x_valid低两位齐；tap_valid=0xf；history_valid=0x3f。length仍须由OPEN合法建立，但卷积不遍历length | `y=RNE((x*t0+h0*t1+h1*t2+h2*t3)/2^14)`；`history_next=[x,h0,h1]` | pending_history=1，y八S32 |

SSM的准入仍要求 `param_valid`，即使该模式算术不使用op5的公共decay/beta，外层也必须先发合法op5(index0)，例如两个合法占位系数。这是当前RTL的明确条件，不能按数学公式删掉。

mode0/1一开始均清 `decay_valid`（R:L153），不是到commit才清；SSM下轮必须重新装逐元素因子。mode2不消费state/逐元素decay。state和factor复用两银行，SSM在shadow行被覆盖前先捕获该行因子（R:L187–213）；不能把已装因子同时算作一份可随时导出的候选state。

每个需要存S32的算术阶段检查fits32；有一个lane溢出会累计failed，最终rsp_error=1、output_valid=0、不产生新的pending_state/history。计算途中shadow仍可能写入截低32bit的内容，但active不因此更新。若先前conv成功留下pending_history，后续state执行失败不会清它；错误处理必须显式REVOKE或受控恢复，不能COMMIT该history后宣称token成功（R:L87–95、206–217、234–254）。这不是饱和算术接口，缺少外层溢出策略时不能继续消费错误结果。

### S32单位不可从容器推断

RTL只把skip固定为Q16.16；state/x/inject/history/output为S32共同单位F，由产品数值合同声明。Q/K/B/C/taps为Q1.14，decay/beta及逐元素factor为UQ1.31。F应在R状态版本及边描述符中保存，不能因有32位就默认Q16.16。

- R→G：E13右移 `F−10` 才对应G的Q5.10，并须满足该操作可表达的非负shift范围及饱和策略。只有F=16时固定shift6正确。
- G→R x：若G输出Q5.10且R选择F=10，至少需把每个S16分别符号扩展到S32并重打包；若F不同，还需显式宽度/尺度调整。四个S32容器与八个S16容器不能裸接。
- SSM inject不是“把G结果改成S32类型”就已得到。真实inject生成、范围/舍入及公共单位必须由数值服务或已证明的算法分解承担。
- N→R Q/K：N普通Norm回放的 `raw*factor*gamma` 右移30；gamma_raw=1024（数学1）时归一化值为Q5.10，不能自动当Q1.14。候选可用gamma_raw=16384（数学16）直接形成Q1.14编码，或对N结果明确左移4；两者舍入位置/误差不同，必须选择并验证（N:L170、195–209）。另有模型缩放时同时纳入该合同，不重复缩放。
- Sigmoid Q1.14到beta UQ1.31可做明确非负码左移17，但增加容器位宽不增加系数量化精度；负EXP/逐元素因子仍非G现成通用能力。

## 5. pending / read / commit / revoke 合法矩阵

以下均以phase=IDLE、复位无效、响应槽可用为前提；否则任何命令都不能握手。“条件”还须满足上表的index/装载/身份要求。H表示仅pending_history；P表示仅pending_state；PH表示两者都有。

| 命令 | 无context | context，无pending | H | P | PH |
|---|---|---|---|---|---|
| OPEN op0 | 允许 | 允许、使旧装载失效 | 拒绝 | 拒绝 | 拒绝 |
| state op1 / factor op15 | 拒绝 | 条件允许 | 拒绝 | 拒绝 | 拒绝 |
| key/query/x/inject/param/skip op2–5 | 拒绝 | 条件允许 | 条件允许 | 拒绝 | 拒绝 |
| EXEC conv | 拒绝 | 条件允许 | 拒绝 | 拒绝 | 拒绝 |
| EXEC GDN/SSM | 拒绝 | 条件允许 | 条件允许 | 拒绝 | 拒绝 |
| COMMIT op7 | 拒绝 | 拒绝 | 条件允许 | 条件允许 | 条件允许 |
| REVOKE op8 | 允许 | 允许 | 允许 | 允许 | 允许 |
| history/taps op9/10 | 拒绝 | 条件允许 | 拒绝 | 拒绝 | 拒绝 |
| READ active op11 | 拒绝 | active_valid时允许 | 同左，旧active | 同左，旧active | 同左，旧active |
| READ output op12 | 只检查output_valid；正常复位后为0 | output_valid时允许 | output_valid时允许 | output_valid时允许 | output_valid时允许 |
| READ meta op13 | 允许 | 允许 | 允许 | 允许 | 允许 |
| READ history op14 | 拒绝 | history_valid时允许 | 同左，旧history | 同左 | 同左，旧history |

REVOKE是清候选标志而非回滚active；op1/op9本来就是立即覆盖active/history的装载命令。在系统版本根尚未发布时，外层可决定显式重新装旧根，但这属于恢复协议，不是R原生回滚。

## 6. 提交、取消与事件的真实含义

op7合法接受时只保存next_position、转入COPY并撤下响应有效。下一次执行COPY时才根据pending_state翻bank_role、根据pending_history复制history_next，清pending，position更新为调用方next_position、epoch加1，清全部x_valid及output_valid，并发成功响应（R:L156–160、255–261）。必须在发op7前用op12保存输出。op11/op14在op7之前读旧值，在成功COPY响应后读新值。

母控事件至少区分：EXEC完成、候选输出已写ACK、R_LOCAL_COMMIT_DONE、STATE_TILE_SAVED、STATE_ROOT_PUBLISHED、OUTPUT_PUBLISHED、R_CONTEXT_RELEASED。命令握手和busy下降不能代替任一写确认或版本发布。

软停止在EXEC中只能停止新任务，继续接收实际响应；命令口空闲后才能op8。op7一旦合法接受，不能通过op8插队撤销；必须先收真实提交结果。成功后至少进入“R活动状态已改变、私有版本/输出未必发布”的部分完成状态，保留staging及恢复资料。候选T在SEALED也不能因软停止提前丢弃这个保护窗口所需数据。复位可能打断提交可观测性，必须由全系统恢复边界定义，不能给出恰好一次或掉电原子性承诺。

epoch=0xffffffff的OPEN/EXEC可被接受，但COMMIT必定拒绝；产品在启动会修改状态的任务前应检查提交余量。op7不约束next_position递增，OPEN可重新选择owner/epoch；外层必须防止旧身份重用，排空后才重新装context，不能靠本地32bit epoch回绕掩盖迟到响应。

## 7. 在当前R上可行的tile方案

### 7.1 一个完全驻留的局部融合切片

无pending时OPEN→op1装state→op9/10装history/taps→SSM时op15装全部逐元素factor→op5建立param/skip→op4装本轮卷积x。EXEC conv并收响应→op12保存卷积输出并等写ACK。此时保留pending_history，母控执行外围E/G/N等，再在同一R context用op2/3、op4、op5补齐状态计算输入，EXEC GDN/SSM。成功后op12保存最终八S32输出→约定下游/结果staging完成→op7共同提交history/state并等待响应。该顺序只有当外围依赖不要求换入其他R tile时可行；它不能覆盖128或4096通道全组Norm的一般场景。

SSM的state/op15必须在conv产生pending_history前装完；op5/op2/3/op4可在pending_history期间补充。GDN虽不需要op15，旧state同样不能在conv后才用op1装入。失败留下的history候选须处理，不得以state EXEC error误认为所有pending已清。

### 7.2 完整多tile：外部版本服务与两个pass

当前R没有整份shadow/history_next读出，不能先计算全部tile而把各候选都留在一个R。可信候选是外部 `old_root` 不可变、`privateNext` 私有，计算时R只是一个可重装的tile缓存；`STATE_VERSION_CTRL`是母控/存储元数据职责，原生R命令仍仅由R_CTRL发。

1. 冻结产品定义state tile与conv tile各自的逻辑key、长度、尺度、owner/epoch/position，预留old/next state、old/next history、卷积输出和最终R输出区域；外存请求/响应、写ACK和根描述符必须是真实新增服务。
2. **conv/history pass**：每conv tile在无pending时OPEN，装op9/10及op4 x，EXEC mode2，收成功响应；op12两拍读八S32并写卷积staging、等ACK；op7局部history commit并收COPY响应；op14六拍读96B新history写privateNext、等ACK，才能OPEN下一tile。纯conv未装state时不能读op11。失败时旧根不变，已在R局部提交的tile须按恢复协议显式重装。
3. 收齐算法所需全部conv tile后执行激活/布局、Q/K全组L2或B/C/inject等准备。全组Norm不能偷换成每8lane独立Norm。
4. **state-update pass**：每state tile重新OPEN，从old_root装op1旧state；op2/3 Q/K或B/C；op4 x/inject；op5合法公共参数及需要的skip；SSM还必须op15全部factor。EXEC mode0/1，响应成功后op12保存八S32到状态输出staging并等ACK；op7 local commit，等COPY成功；op11用2×length拍读新active到privateNext并等ACK，再换下一tile。此pass未装history时不能无条件op14。
5. 按value-head128或全4096通道收集R输出，执行完整Norm/门乘/投影/残差/分支join。根发布与输出发布分别定义确认、消费者门控和部分完成恢复；本稿不声称两者原子。

history与state pass的原生位置推进是两个独立局部提交，不能盲目“同owner连续next_position++”当同一token的单次语义推进。建议分别记录 `history(tile,t→t+1)` 与 `state(tile,t→t+1)` 的私有子版本，最终只有产品根把完整二者绑定为token版本t+1。OPEN参数从各自描述符取，元数据服务验证映射，不能靠R自动识别两个pass属于同一token。

每个state tile的读/写量至少各 `32×length` B，输出32B；每conv tile的history读/写各96B、输出32B，此外有taps、x、Q/K、inject、factor、skip和总线响应。GDN每128个value通道至少16个8lane输出tile；4096个SSM输出通道至少512个输出tile，实际conv X/B/C映射可能不同。容量须按模型真实state长度和conv通道数计：一份state为 `4×L×C_state` B；一份history为 `12×C_conv` B；old与privateNext各占一份，不能只按R32B输出估算。系数和全组staging还要另计。R最大active8192B本身并不使这些版本能放进S16KiB。

局部commit后外存写失败时，R已经改变而old_root仍可保持不发布；应停止/排空、隔离不完整privateNext，按旧根重装。若已经发布部分输出或新根，则必须报部分完成并走另定恢复；不能自动REVOKE或单独reset R继续算下token。掉电恢复、原子根替换、幂等/恰好一次输出、日志容量及多消费者一致性均未由当前RTL给出。

## 8. 前总稿必须实质修正的点

1. “所有宏已统一接口/只有start-done”的泛述不适用于R；必须按原生valid/ready、每命令响应和无tag串行归属设计真实R_CTRL。
2. “R只有候选state/output一个ready”不够。conv输出会被后续EXEC覆盖，op7又清输出有效；两次候选输出都须在覆盖前保存，pending_history不是端口busy。
3. op12只输出八S32，不导出shadow；op11/op14在pending期间仍读旧active/history。全模型方案必须出现局部commit→新active读回→外存ACK的真实动作。
4. GDN/SSM旧算法表如果把128/4096全组Norm放在首次R局部commit之前，就无法换入后续tile。完整多tile使用版本服务/two-pass，与局部融合共同commit切片分开。
5. SSM不能在pending_history后装state/op15，也不能因为公共decay/beta在数学上不用就漏op5(index0)的param_valid条件。
6. S32不等于Q16.16；N→R Q1.14、R→G Q5.10和反向S16→S32均需明确尺度/扩展/舍入。inject与UQ1.31系数不是免费协议重打包计算出来的。
7. R/T提交及old_root/privateNext不能被描述成已实现的整token原子事务；op7接受后的保护窗口、局部提交后保存失败、根/输出分别发布必须有明确失败状态。
8. 所有源资格写明跟踪缩窄候选与原R4032的区分；旧局部SAT/三初态结果是来源报告，本轮代码审计/静态lint不是新RTL或物理验收。
