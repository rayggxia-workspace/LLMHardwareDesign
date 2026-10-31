# 从现有七宏RTL展开的固定产品控制规格 v0.2

配合[总方案](SIX_CONNECTION_SYSTEM_DESIGN.md)和[原生审计](RTL_NATIVE_CONNECTION_AUDIT.md)。基线为研究分支faabeda、导入PR144固定643c6012。外部控制均待实现，不改变叶宏接口，不宣称已有统一控制总线。

## 1. 两级控制与端口独占

母控MODEL_CTRL保存固定程序PC、有限循环、token/layer/head/tile索引和等待事件，发完整局部任务，不发送每拍payload。局部控翻译为原生握手、地址和命令，叶宏FSM继续内部计算。首版只新增这两层，单时钟域。

| 原生端口/资源 | 唯一驱动/接受者 | 协调原则 |
| --- | --- | --- |
| M.cmd及M.rsp_ready | M_CTRL | bank、唯一结果上下文、scale版本 |
| M.A/B payload和metadata | 现有S_LOADER | M_CTRL通过S_CTRL请求，不另接输入驱动 |
| N.cmd/rsp | N_CTRL | 全组锁定，轮次和目标长度在外部记账 |
| E.in/out | E_CTRL | 收齐A/B/C后提交，保存输出和tail |
| G.in/out | G_CTRL | x/gate配对、两lane流水在途标签 |
| R.cmd/rsp | R_CTRL | 装载有效位、候选与局部commit/revoke |
| S.req/wr/addr/din/take及loader描述符/done_take | S_CTRL | 读写均排空响应，首版与loader串行 |
| T控制、write、read_take | T_CTRL | 单租约、顺序写、发布、读完释放 |
| 外存请求/响应 | MEM_CTRL（新增） | 地址/故障/写确认，平台接口待定义 |
| 系数/宽归并 | NUM_CTRL（新增） | 缺失算术独立计成本与误差 |
| 外部state/history根 | STATE_VERSION_CTRL（新增） | 初始化、导出、失败恢复与切根 |

Attention/FFN/GDN/SSM/MoE是固定程序段。多个物理簇若复制宏可以分别拥有局部控；共享M/S仍不能被两个阶段并驱。

## 2. 外侧任务与完成合同

以下为逻辑字段，位宽待完整产品编译和资源规模决定，不是已综合端口宽度。

任务：`valid/ready, task_id, epoch, template_id, op, src_handles[], dst_handle, valid_elems, type_id, frac_bits, layout, parameters, expected_version`。handle绑定S/外存、base/word数、有效元素、lane顺序、owner、版本及引用数；有效范围不得超预留空间，使用中禁止覆盖。

完成：`valid/ready, task_id, epoch, event_kind, status, saturated, produced_handle, progress`。valid保持至握手且payload稳定；响应排空前不复用ID。旧epoch事件只能排空，不能完成新任务。母控复位/取消不能凭空清掉仍在叶宏中的操作。

| 事件 | 成立条件 | 不能据此推出 |
| --- | --- | --- |
| compute_done | 计算应答接受、错误已锁存 | 输出已读出/写入S |
| data_ready | 全部结果保存到保持槽/目的存储，写应答已接受 | T或外部版本根已发布 |
| publish_done | 指定T批commit握手无协议错误，或外部根发布完成 | 下游已取完或外存已耐久 |
| release_done | 最后消费者取完、资源释放完成 | 其他资源也回滚 |

首版每叶宏一个局部任务、一个保持型完成槽；N一个整组，R一个局部context，T一个租约。G可多项在途，按接收顺序维护标签/tail队列，队列满反压。最终深度由仿真和物理预算决定，不能默认无限队列。

## 3. 最小局部状态机

### 3.1 M_CTRL与S_CTRL

`RESERVE → ENSURE_SCALE → REQUEST_LOAD → WAIT_LOAD → EXEC → WAIT_EXEC_RSP → READ_RESULT → PACK/STORE → COMPLETE`。

- factor/left是M全局状态，reset默认1/0，op6不恢复。显式op4或证明scale版本匹配，不能跨任务混用。
- loader描述符带bank、rows、tiles、A/B格式、reuse_b、两个对齐基址。银行可装载才提交，保持字段至load_ready；取走done并查done_error。
- EXEC应答只表示计算结束，仍按行/half发op3/op5读取。独立投影首K块clear=1，后续块clear=0且保持结果映射；切换投影先物化。
- op5选S8/S16/S32，但返回四个S32容器；送S16要E13或已验证packer。S64后续运算另列宽算术。
- reuse_b须bank、宽度、tile数、权重身份/版本全部相同。首轮例子禁用，避免残留B。

S_CTRL首版普通口一项在途：`ISSUE(req&&ready) → WAIT(valid) → TAKE → RESPOND`；读写都走应答，不在req握手后报告写完成。loader与普通访问串行，未来重叠需证明内部争用、地址及银行安全。外存搬运也经唯一服务。

### 3.2 N_CTRL

`LOCK_GROUP → BEGIN → STATS_LOOP → FINALIZE → [EXP_LOOP → FINISH_EXP] → REPLAY_LOOP → STORE → UNLOCK`。TopK另走begin/load/select，仍独占N。

N无expected_total寄存器。外部记录目标N、各轮已接受count、已返回响应与写入数，只有精确达标且排空才FINALIZE/FINISH_EXP/完成。BEGIN不能插入尚在回放的组，raw/EXP/gamma绑定同一版本。

STATS/EXP/REPLAY每次count1..8，TopK LOAD每次1..4对。padding不计数。Softmax至少一个有效key并校验mask；RMS/L2的epsilon、gamma、输出单位由产品指定。错误停止新命令、排空后清理，不能依赖N拒绝所有外部长度错误。

### 3.3 E_CTRL与G_CTRL

E：`FETCH_A/B/C → ALIGN_ROLES → ISSUE → HOLD_OUTPUT → STORE`。收齐同task/range/version操作数；叶宏锁存输入不等于外部已有join。无count，尾字独占、无效lane补零后整128bit写S并记录有效数；共享尾字须新增RMW/仲裁。op13四S32→低64bit四S16，两响应拼8S16；不能用高64bit零覆盖另一half。

G：每8S16字拆四个2lane包，`in_x=激活分支`、`in_gate=线性分支`。fn0 SiLU、1 Sigmoid、2 GELU_tanh、3 Softplus。ungated且fn1输出Q1.14；gated fn1乘gate后右移14、其余右移10，按gate Q10合同输出Q10。整个流水随out_ready停顿，tag推进以真实握手为准，不能固定逐拍计数。

### 3.4 R_CTRL与外部版本服务

`RESERVE_OUTPUT_AND_EXPORT → OPEN → RESTORE_OLD → LOAD_PARAMS → CALCULATE → READ_CANDIDATE → LOCAL_COMMIT → EXPORT_NEW → CLOSE_TILE`。commit前错误可REVOKE；commit握手后进入不可盲撤销窗口。

op12两次读8S32候选输出，COMMIT清output_valid，所以先保存输出；COMMIT成功后按实际装载/更新范围导出：纯state pass只op11新state，纯conv pass只op14新history，融合切片两者都已有效才读两者。pending期间这两个读口仍是旧active，没有通用shadow/history_next导出口。

多tile外部保留old_root：装旧tile→计算→保存输出→局部commit→导出新tile到next_root；所有tile及所需输出完成才发布next_root。失败丢弃未发布next_root，按old_root恢复。cold start必须显式给零状态或校验过的初始版本，不能默认未初始化内容为零。

SSM须预置element decay(op15)，general op5 index0仍须发以置param_valid；所有x/inject、skip半包和使用范围decay均须有效。COMMIT交换bank后下一步重载inactive decay。conv跨多个8lane tile时先遍历卷积：保存输出、局部history commit并导出，再OPEN下tile；状态遍历重装旧state与输入/decay。全head/channel Norm前输出先S/外存物化，不能一直占一个R pending。

### 3.5 T_CTRL

`WAIT_EMPTY → BEGIN(1..384) → FILL_IN_ORDER → WAIT_SEALED → COMMIT → DRAIN → RELEASE`。write_index从0顺增，写满才sealed。非法begin大小使begin_ready=0且置protocol_error，不能无限等一个不存在的错误response。

T单租约同步读，commit后经READ_REQ产生首读启动等待，READ_HOLD在take边沿直接refill，连续take可每拍一字；反压时read_data保持。吞吐需计首读/填充/提交/释放开销。最后take后到RELEASE，release握手才EMPTY。read_last无元素tail。protocol_error粘性，首版停止发布、记录上下文并走平台安全复位恢复，不假设REVOKE清错误。

T只保护本批。大于6KiB分批时需定义部分可见还是外存根一次发布；分批commit不是全tensor原子。R/T没有联合原子提交。

## 4. 资源、取消和故障

母控首版串行取得整组上下文，S在微命令间仲裁。接受任务前预留目的槽、输出保持槽与必要外存；禁止持有不能释放的输出再等待已被自身占满的输入槽。仲裁须无饥饿或有界轮询；运行无死锁是仿真/形式验收项，静态DAG不构成证明。

fork用引用数，消费者领取同版本只读handle、最后完成才释放。join校验task、epoch、范围、类型和版本；不能简单valid相与丢失不同延迟分支。

| 取消点 | 动作 | 恢复限制 |
| --- | --- | --- |
| 尚未向原生口呈现valid | 撤销本地待发、释放预留 | 不影响其他owner |
| valid已呈现但未握手 | 保持valid与payload至握手，之后按已接受操作排空 | 除非另有允许撤回的明确原生合同，不中途撤valid |
| S loader已接受、M未EXEC | 继续允许A/B接收，等done排空；必要时M op11清输入bank，再释放 | loader无abort，不能停A/B造成WAIT_LOAD卡死 |
| M/N/E/G已接受 | 停新输入、排空响应后丢未发布槽 | 无整命令rollback；M清结果，N清理后重BEGIN |
| R pending、未commit | 排空读应答、op8 REVOKE并取回应答 | 旧active保留，先前已提交conv不被此次revoke回滚 |
| R commit已握手 | 保护输出staging/T、等R应答 | 成功后下游失败为partial_completion；仅旧根仍保留且新根/输出尚未可见时从旧根恢复，已有可见部分则走另定恢复协议 |
| T未commit | 在原生允许状态revoke | 只撤销T，不能撤销R/S/外存修改 |
| T已commit/在read | 按原生状态完成排空/释放或平台定义丢弃 | 消费者可能已看见，不宣称整步回滚 |

保留原始macro/op/index和错误状态。M/N/E/G饱和由产品策略决定允许、计数或失败；R无saturated口，T无commit_error口。平台外存故障恢复待实现，不能凭新增逻辑字段宣称已有能力。

## 5. 固定程序与物理约束

程序原语包含有界CALL、循环、指定事件等待、错误跳转、缓冲申请/释放和版本发布。译码、ROM容量、计数宽度及错误分支在预制前实现。产品选择冷复位锁定；运行参数只改变合法长度/地址/专家ID。

编译器拒绝不存在路径/算术、超S/T/R/ROM容量、未定义数值尺度、长度不符、端口重复驱动和未定义故障恢复。完整产品程序未编译，不虚构ROM字数；可写控制存储备选单列装载/锁定成本。

局部控靠宏，S仲裁靠S、T_CTRL靠T，母控只传任务/事件；长ready链用预制寄存隔离，CTS/复位一起预算。区域层依据线长、扇出、拥塞证据增加且保持资源独占，不凭层数估PPA。

运行验证待做：随机反压/长停顿、G在途tag、S写应答、N早FINALIZE外部拦截、M scale跨任务、R pending/commit窗口、T非法begin/tail/首读与连续refill、异常后无资源泄漏、版本失败恢复和非法产品选择。当前仅静态核验，未由系统RTL测试证明。
