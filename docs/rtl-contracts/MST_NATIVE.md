# 冻结 RTL 重规划：M/S/T 原生合同审计

本稿只读审计本地集成源码，供重新生成总方案；不修改正式稿、远端或服务器，不以此前文字合同代替操作码解码。研究版本固定 `faabeda68b3b098ba562d68517319e02725f5bc3`，其中导入 PR144 的 `643c6012a11cbf461146ac40fbf61485223fe946`；不追踪 PR144 后续提交。源根为 `work/Melodydt/151/merge-pr144-643c6012/integrated/`，这是指定的集成参考包，不自行宣称完整 Git checkout。

以下行号均来自实际文件逐行读取；完整字节 SHA-256、Git blob SHA-1、结构化字段见同目录 `mst-facts.json`。M/S/T 都使用 `posedge clk`、高电平同步 reset；接口的 ready/valid 还组合受 reset 抑制。没有执行 RTL 仿真、综合或物理验证。

## 1. 必须用真实 RTL 重写的要点

| 原生事实 | 总方案必须落实的设计含义 |
|---|---|
| M v2 只实现 opcode **3/4/5/6/10/11/12** | 不能沿用旧 V/M 控制表；不存在可任意解释的通用 load/start/commit 指令 |
| v2 `op4` 只配置全局有符号 S16 factor 和左移 0..31，`op10` 已完成缩放合并 | 旧 `block_feed_m` 的 EXEC→op4逐行合并流程不可复用。必须先 SET_SCALE，再 EXEC，再 READ_RESULT |
| `op6` 不恢复 factor/left_shift | 模板必须显式配置或证明尺度版本匹配；只写“factor=1”或做 CLEAR_ALL 不足 |
| M 的两个输入 bank 共用一份 8行×8列 S64 结果 | 可预载非执行 bank，但不是两个独立矩阵结果上下文；下一投影前保存旧结果 |
| M `op5` 即使选择 S8/S16，仍返回四个 S32 容器 | 两次读出后需要真正提取/转换/合包；不能把低128bit直接当八S16 |
| S 普通写也返回 `valid/dout`，载荷为刚写入的 `din` | 等待并排空写应答；S 本身无 `rsp_error`、无初始化有效位或越界错误端口 |
| S `busy` 只反映 loader | 不能用它判断普通口应答/全S空闲；S宽口不对外暴露为通用512bit DMA |
| T 无 `cmd_op`、无 `commit_error`、无独立完成响应 | 生命周期按各自 valid/ready 和状态观测生成外部事件 |
| T owner/generation 仅登记，不检查调用者身份 | 租约、版本和唯一端口所有者必须由外部控制实现 |

旧详细稿的小 FFN 对齐分配及257回放总体思路可以保留，但必须升级为下文带字段值、原生应答归属和状态依赖的实施合同；不能只补来源 commit。

## 2. M：`project/rtl/block_v2/block_v2_m.sv`

### 2.1 端口、装载与阻塞

- L5–15：命令为 `cmd_valid/ready + op[3:0] + index[5:0] + data[63:0]`；应答为 `rsp_valid/ready + data[127:0] + error + saturated`。没有统一任务 ID、完成计数或 M 自主 S 读地址端口。
- A：`a_valid/ready, bank[0], row[2:0], tile[1:0], wide, data[127:0]`。每拍装8元素；S16使用全部128bit，S8只用低64bit，逐字节符号扩展。A地址为 bank/row/tile，最多2bank×8row×4tile×8元素。L138–141。
- B：`b_valid/ready, bank, tile[1:0], wide, half, data[511:0]`。S8一拍64元素；S16需要 half0/half1各32元素，half1前必须已有同bank/tile的S16 half0。B按 **`8*n+k`（n-major）** 编排，不是未经转换的常规 K×N 行优先。L45–46、L75–76、L142–145。
- L38–46：命令接受条件为 IDLE 且旧响应已空或本拍被取走。A/B装载独立；EXEC接受的同拍阻止装入所选bank，执行期间锁所选bank，另一个bank可加载。CLEAR_ALL同时阻止两bank装载；CLEAR_BANK只阻止所选bank。
- `busy=!cmd_ready`，所以响应被背压或reset期间也可能busy；它不是单纯的算术活动信号。输出响应保持到 `rsp_valid&&rsp_ready`，可同拍取旧响应、接新命令。L42–43、L124–137。

### 2.2 真实操作码

| op | index / data 合法域 | 效果与应答 | 源行 |
|---:|---|---|---|
| 3 | `index=(row<<3)|pair`，row0..7，pair0..3；data=0；结果行valid | 读两个S64，低64为列2pair，高64为下一列；不是重新计算 | 198–199 |
| 4 | index=0；data[15:0]=signed factor；[20:16]=left_shift；[63:21]=0 | 更新全局配置，返回零成功应答；factor允许负数/零 | 200–201 |
| 5 | `index=(row<<3)|half`，half0..1；data[5:0]=right_shift0..63；[7:6]=0；[9:8]=width0/1/2；[63:10]=0；结果行valid | 对该行4列做算术右移/RNE，然后按S8/S16/S32夹取；**仍是四S32容器**。裁剪仅置saturated | 202–204、240–248、116–122 |
| 6 | index=0、data=0 | 清A/B有效、结果行valid、partial_valid；不清payload、不恢复scale配置 | 205–207 |
| 10 | index[5]=执行输入bank；index[4:0]=0；data为下表 | 检查A/B格式/有效性，执行K段并缩放/合并；最后返回低8bit故障行mask，error为mask非零；成功响应不是张量 | 48–62、208–215、239 |
| 11 | index[0]=bank，index[5:1]=0；data=0 | 只清该输入bank的A/B valid；保留merged结果及scale配置 | 216–219 |
| 12 | data=0；pair=index[1:0]、index[2]=0；row=index[5:3]；**partial bank=index[3]** 且owner匹配/valid | 诊断读两个S40 partial，分别符号扩展S64；只是当前有限partial槽，不是任意历史结果 | 220–223 |
| 其他 | — | 返回error=1、data=0；不是静默NOP | 224 |

`op10` 的 data 逐位定义（L50–61、209–210）：

| bits | 名称 | 范围/意义 |
|---|---|---|
| 0 | fmt_a | 0=S8，1=S16 |
| 1 | fmt_b | 0=S8，1=S16 |
| 2 | clear_result | 1=本段按零结果开始；0=追加到同N宽度的有效merged行 |
| 3 | reserved | 必须0 |
| 7:4 | last_k | 最后一个tile的有效K，1..8 |
| 11:8 | active_n | 1..8 |
| 14:12 | tiles | 1..4，总K=`8*(tiles-1)+last_k`，单命令至多32 |
| 18:15 | rows | 1..8 |
| 63:19 | reserved | 必须0 |

完整K可由多个EXEC段追加，但现版不在命令中保存“模型总K/段序号/权重身份”，由外层验证各段覆盖和尺度一致性。不要把旧feed_m的k_count65535保护推给v2。

### 2.3 数值与完成语义

每行各列的本段partial为S40，经 `partial * signed_factor` 后 **左移scale_shift**，与零或旧S64结果相加。缩放时不做RNE，读出时才可右移/RNE。L90–104、163–193。

每行8列作为一次原子提交：当前行有partial/对齐/加法溢出则保留该行旧结果；其他成功行可能已更新。最终 `rsp_error=1` 不表示整条EXEC回滚，也不会自动置 `rsp_saturated`（EXEC应答的saturated恒0）。因此失败后不能盲目重放一条追加命令。L184–193、239。

op3/op5读取都不消费或释放merged行，且不会自动检查调用者张量身份。op6、后续clear EXEC或reset等才使它失效/覆盖。总方案应分别维护输入bank可装载、结果上下文可复用、读出已写回三个条件。

原始 `block_feed_m.sv` 虽端口形状相同，L216–221 的op4却是逐行 S32 factor/右移/clear_merge操作；现版v2的op4完全不同。其控制driver不能仅因pin宽相同直接替换。旧模块的字节SHA见JSON，只作对照。

## 3. S：普通128bit端口与内置loader

### 3.1 存储接口

`block_feed_s_macro.sv` L4–29 已包含 `block_feed_s16k storage` 和 `block_feed_loader feeder`，外部无需重造loader。普通口为 `req,wr,addr[9:0],din[127:0] / ready,valid,take,dout[127:0]`。地址是**128bit字地址**：bank=`addr[1:0]`，bank内行=`addr[9:2]`；总4×256×128bit=16KiB。L11–18（s16k）。

所有普通请求在 `req&&ready` 接受，下一状态提供一个持有型valid响应。读取返回原存储字；写入在接受边沿更新存储，响应dout为din，可作写ACK。valid在take前保持，消费旧响应和接受新普通请求可以同拍。L19–37。没有byte mask、错误码、初始化检测或外部请求ID；reset清响应valid，不清16KiB payload。

内部宽读512bit从同一行同时取四bank：`wide_dout={bank3,bank2,bank1,bank0}`。当内部 `wide_fire=wide_req&&wide_ready` 时普通ready强制0；仅宽请求存在但未能接受时，不一定阻止普通口。普通和宽各一个响应保持寄存器；不是增加四个外部可独立使用的读口。L12–18、24–26。外层不能凭仲裁器修改内部宽读优先规则，首版可在有界loader事务之间安排窄访问窗口。

### 3.2 loader描述符不是64bit opcode

原生是并行端口：`load_valid/ready, load_bank, rows[3:0], tiles[2:0], a_wide,b_wide,reuse_b, a_base[9:0],b_base[9:0]`；返回 `done_valid/take,error,busy`，输出直接兼容M的A128/B512及bank/row/tile/wide/half。L6–21（loader）。如总方案使用64bit打包描述符，那是**新控制接口**，必须给出到这些引脚的明确解包，不能说RTL已经有该命令口。

合法性（L56–59）：rows1..8、tiles1..4、A/B base均为4字对齐；`a_base + tiles*(rows>4?8:4) <=1024`；非reuse时另有 `b_base + tiles*(b_wide?8:4) <=1024`。即使reuse_b=1，b_base低两位仍必须0。base仍是S的16B字地址，内部才除以4变成512bit行号。

每tile的布局：

- A占4字（rows1..4）或8字（rows5..8）；每行固定一个128bit容器，S8也不紧密打包成两行/字。tile顺序跨步4或8字；缺少的行是容器填充，不发送给M。
- B S8占4字64B，S16占8字128B；S16先half0再half1。B每tile内的元素顺序仍为M要求的`8*n+k`。
- 默认按每tile先B后A发请求；reuse_b跳过B请求。两个512bit A队列项+一个512bit B槽共192B，另有S的128/512响应共80B；最多一个未完成内部读，但允许消费响应与发下一读同拍。L23–54、72–105。
- `load_ready=!reset&&!busy&&!done_valid`，不支持done消费同拍接受新load。非法描述符产生done_error=1且不置busy；合法任务只有所有读请求/响应和A/B传输都排空才done_error=0完成。**只表示已交付M，不表示M已EXEC、计算成功、输出已发布。** L31、68–76、107–108。
- reuse_b没有权重身份或内容检查。必须由外部记录实际bank/tile/格式/权重版本；即使M valid检查通过，也可能是错层/错专家的同格式权重。S宏busy仅接feeder.busy，与普通口valid无关。

## 4. T：`transaction6k.sv`

T为384×128bit=6144B单批次、单消费者交接，不是通用S端口。`begin_owner[1:0] / generation[31:0] / words[9:0]` 只在begin握手登记，后续写/提交/读/释放端口没有请求者ID验证。L4–25。

| 阶段/端口 | 真正接受条件/效果 | 必须区分 |
|---|---|---|
| BEGIN | EMPTY且words1..384时begin_ready=1；接受后记录owner/gen/count进入FILL | 非法words使ready=0；在EMPTY仍拉begin_valid会置sticky protocol_error，不会发失败响应 |
| WRITE | FILL、revoke_valid=0且write_index==received；接受后写128bit | 索引必须从0连续；最后一字自动SEALED，没有seal指令；错误索引不接受并置sticky错误 |
| REVOKE | FILL或SEALED，可优先于写/提交使状态回EMPTY | 不可撤销READ_REQ/READ_HOLD/RELEASE；不清payload或protocol_error |
| COMMIT | SEALED且无revoke_valid时握手进入READ_REQ | 无commit_error/rsp_valid。随后有一次同步首读，再进READ_HOLD |
| READ | 仅READ_HOLD时read_valid=1；take后自动前进并保持下一字 | 接收方不提供随机read_addr。stall时data/index/last保持；连续take可II=1 |
| RELEASE | 末字take后进入RELEASE；release_valid&&release_ready才回EMPTY | 末字take不自动释放；release不清owner/gen/count/protocol_error |

条件和实现分别见L27–39、L41–69。protocol_error仅reset清零；不是每个批次独立错误位，也不是对所有非法时序都检查（例如提前commit或release仅不握手）。read_data/index在read_valid外可能保留旧值，不得当有效数据使用。reset不清payload，消费者/fabric复位时须协调hard reset（L1–3）。

## 5. 可以连接什么、哪些必须加真实逻辑

| 路径 | RTL原生可复用部分 | 新控制/适配最低义务 |
|---|---|---|
| S.loader→M | A128/B512、所有bank/row/tile/wide/half及ready逐pin匹配 | 生成load、先检查done，再配置/启动M；不能复用旧feed_m命令语义 |
| 普通S→N/E/R等128bit输入 | 读响应data128可作为载荷 | 保存命令字段及应答归属，只有真正消费时take；不同宏的命令/格式不统一 |
| M.op3/op5→S | 128bit载荷可写S普通口 | 识别当前响应是结果读、屏蔽错误数据、计数地址、保留rsp直到S接受并排空写ACK；EXEC/SET_SCALE ACK不写成张量 |
| M.op5→E13→紧凑S16 | 两个四S32响应分别转换成四S16 | 两次低64bit合包；尺度/saturation策略明确；M直接低位连线不等价 |
| 生产者→T | T写data128为不透明容器 | 先BEGIN并计数index；所有应答保持/检查；错误处理区分SEALED前撤销与提交后恢复 |
| T→S | read_data128可写S；read_index可作字偏移 | `addr=base+read_index`需真实加法/范围检查，owner/gen策略；接收握手及最后写ACK均完成。只有base0固定布局才能直接用read_index |
| T→多个消费者 | 仅一个原生read_take | 不可将多个take简单OR/并联；需要外部复制/保持/引用计数或多T实例 |
| S→M直接普通128bit写B | 无对应B128装载路径 | 需真实4拍/8拍收集成B512及half控制，或使用已有loader；金属不能补造此缓冲 |

当前指定本地包没有将这些新访问器/控制器实现为统一top。可行接法不表示已有驱动硬件，更不表示任意布线/负载取得物理资格。

## 6. 最小FFN：S16×S8的实际命令字

保留此前H=I=8、一token、三个8×8 S8整数权重、X/G为Q5.10的受限验收切片（不含Norm）。字地址分配可直接沿用：X A组0..3；Wgate4..7；Wup8..11；Wdown12..15；packed Gate16、Up17、Mid18、padding19；down A组20..23；packed Y24。共400B S预留，T另1字16B；支持逻辑的保持寄存器另算。

1. 普通S写入输入/权重和必要padding，每笔 `req&&ready` 后消费 `valid&&take` 写ACK。W按`8*n+k`；可用S8单位阵，小范围Q5.10输入。非单位权重仍须受数值范围约束。
2. M发 `op6,index=0,data=0` 并检查成功ACK。每个矩阵job明确执行 `op4,index=0,data=0x1`，即factor=1/left_shift=0；或在独占整个切片且已证明配置未变时只配一次。
3. Gate：S load `bank=0,rows=1,tiles=1,a_wide=1,b_wide=0,reuse_b=0,a_base=0,b_base=4`；等done_error=0并消费done。
4. M `op10,index=0,data=0x9885`：A16/B8/clear1/lastK8/N8/tiles1/rows1。bank1时只改index=0x20；**CLEAR_BANK op11的bank1 index却为1，不能混用**。
5. 等EXEC应答并检查低8bit mask/error；不把这个ACK当数据。M分别发 `op5,index=0,data=0x100` 和 `op5,index=1,data=0x100`，即row0两半、right_shift0、S16夹取。各返回四S32容器。两次E13 shift0转换得到低64bit四S16，再拼成一个字写S16并等写ACK；任何saturated按切片策略处理。
6. Up同理，load的Bbase改8，EXEC仍0x9885且clear1，结果写S17。不能在保存Gate前覆盖M结果，也不能reuse旧B。
7. G从Gate/Up各保存一个128bit字，分4批32bit送入x/gate端并拼回四批输出成Mid→S18；激活/门乘opcode与定点域由E/G专门审计确定。读取S18复制到A对齐地址S20、填充S21..23；loader `a_base=20,b_base=12`，同一M序列完成down→S24。
8. E把S24与仍有效的S0残差相加；T先BEGIN(words1)接受，再write_index0、等待SEALED、COMMIT握手；下游最后TAKE后RELEASE。这里所有外层操作尚需新的控制RTL，不宣称已有完整测试top。

S16×S16替代切片的EXEC字是 **0x9887**，B每矩阵需8字且base对齐；不能只改fmt_b而沿用上述4字权重区。

## 7. 257元素Softmax：本审计负责的S/T装载边界

score为S16 Q5.10：普通S字0..32，共528B；EXP为UQ1.15：字64..96，共528B；T预留33字=528B。两个S区实际数据1056B，未使用的中间地址不可重复算作缓存收益。最后一包只有lane0有效，padding不参与N计数；T只知道33个字，不知道最后一字只有一个元素，必须外部保留有效数257。

score写ACK全部完成后，N子控按**实际源码操作码**运行BEGIN/STATS/FINALIZE/EXP/FINISH_EXP/SOFT_REPLAY（精确码/字段由N审计给出，本稿不猜数值）。每次S读要等待valid并在N输入真正接受后take，或先转入有容量的保持槽。EXP响应逐包写S64..96并排空写ACK；不得只留exp_sum。SOFT_REPLAY输出逐字写T index0..32，最后写自动SEALED后再COMMIT。读取T并写普通S目标时仍要加base和等写ACK；T read_last说明包尾，不说明元素数或N组长。

## 8. 建议的可执行边界与验证

原生模块可以先通过一个**MST事务驱动切片**串起：S普通口初始化→S内loader→M SET_SCALE/EXEC/READ→外层写回S或T。它需要的新增逻辑可直接列为：M命令所有者、S普通口请求/响应所有者、loader任务控制、结果/错误保持、T生命周期与顺序写计数、必要紧凑打包。先限制一个M job和一个T租约，随后再谈并发/区域控制。

必要负例：不对齐loader base、reuse错误B身份、S写ACK未消费、EXEC无效A/B、错误op4旧编码、M op5容器误解、追加失败后盲重试、错误T长度/写索引、T早释放、多消费者take及reset不协调。静态字段核对只能防编码错误，不能替代这些真实时序/背压/数值组合测试。

本轮实际执行：逐行源码审阅、原始字节SHA-256与Git blob SHA-1计算、示例描述符位域算术检查、JSON与引用范围自检。未运行RTL/SystemC、综合、EDA或服务器；不改变任何叶宏/系统资格。
