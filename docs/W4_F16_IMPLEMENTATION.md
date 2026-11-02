# 主线四F16有界FFN实现与服务器验证

Issue151 / PR152；Melodydt；2026-11-02 Asia/Shanghai。输入febc0428，实际通过源码b77d6b7bae17e265bf20509e9ea53c1cdc5c4c9d。新增H8/I8的RMSNorm→gate/up→SwiGLU→down→原始残差完整有界F16计算链，保留旧F8/A8/native源与历史证据。

## 本轮结果及边界

服务器job95209在node1/c64/8CPU、Verilator5.042运行，Slurm COMPLETED0:0，编译与仿真exit0，30个预声明CASE各一次，最终PASS_W4_F16 cases=30。10组独立整数向量逐阶段和最终结果核对通过，覆盖非8倍S16低位、非unity/负/零gamma、稀疏/随机、正负边界/饱和；另验证最终gamma真实写ACK前不stored、背压保持、prestart/RUN abort、DONE保持、reset及M/N/E/G/helper错误后恢复。test中的helper error注入不冒称native S具有错误输出。

首轮95206/源码63ce0f3d在编译阶段失败，未执行测试：line125定宽十进制数字紧邻?导致词法误读。b77d只补该表达式空格；旧静态源检查未发现此错误，两轮原始日志均保留。第二轮保留24条Verilator警告（14 TIMESCALEMOD、3 WIDTHTRUNC、7 WIDTHEXPAND），仅使用-Wno-fatal，不屏蔽类别，不称lint clean。

S16Fin10入口/原残差和可变gamma解决旧F8的窄输入/残差低位丢失及unitygamma限制。F16仍是明确新整数profile：epsilon_code1对应2^-20，旧S8Fin7平方单位epsilon与其相差64倍；未验证浮点模型质量、训练权重量化或真实模型H/I。A8当前仍是QK→Softmax→PV核，缺完整Attention；A8单字输出也不能裸接F16的17拍混合帧。跨岛stored ACK/母控/共同底座物理与外存供给未实现；当前仍L4，未启动L5。

正常单任务39次普通S请求及ACK（29W/10R）、另3loader/6宽读、15M、4N、2E、1G服务/4pair、1T字已在scoreboard逐阶段核验。全套abort/reset场景统计可能丢弃在途请求，不能将全套聚合Sreq1439与Sack1436的差值当正常成功任务计数。

静态/生成验证和运行命令见[数值合同](W4_F16_NUMERIC_CONTRACT.md)及ARCHITECTURE；原始证据见[结果回执](../work/Melodydt/151/f16-rtl-evidence/runs/r02/results/run-receipt.json)、[完整模拟日志](../work/Melodydt/151/f16-rtl-evidence/runs/r02/logs/simulate-f16.log)、[来源/输出SHA索引](../work/Melodydt/151/f16-rtl-evidence/evidence-manifest.json)。镜像SHA为c742bf99ea498fb4da5135bc83fd1677abcebe0e64470e6a115f2baecb3905df；g++11.4.0/Make4.3/Python3.10.12。25输入在计算节点校验，结束导出再校验；23文本证据与下载archive SHA均核对。build/二进制留本人服务器目录，仓库只存小型文本证据。

下一项L4实施建议为A16 H8/Sq2/head1因果Attention：真实hidden输入/preNorm、QKV、RoPE、因果前缀归一化、PV、Wo与原始残差；详见[A/F数值存储路线](AF_NUMERIC_STORAGE_PLAN.md)。这是一项待实现候选。扩大H/I、样本模型epsilon/数值质量、Norm计数/工作集和真实供参各需准入。

## 结构设计记录

下述为RTL作者的结构与静态审阅记录；作者未执行仿真的措辞只描述其分工，当前真实运行结果以本报告及服务器回执为准。

# W4 F16 有界 FFN 顶层实现草稿

Issue151 / PR152；输入研究版本 `febc0428e9d47d9bb4d4c83446690ff2e0c7926d`；原生叶宏选定 `707878621b2add4ed218b8c43df2e95c9a56e2ba`。本文件对应新增 `block_w4_f16_top.sv`。旧 F8、N/E/G controller、S helper 和原生宏均只读复用，不修改。

当前状态：RTL 草稿及静态源差异审阅已形成；本作者未编译或运行仿真，不预填功能 PASS、完整模型质量、跨岛或物理验收。

编译更正记录：根任务报告首轮服务器 r01/job95206 在 node1 的 build 阶段退出1，未开始测试。首版 line125 的 `5'd16?10'd475` 被词法分析器错误结合为常量 token；原有九项机械源检查没有识别此编译错误。根任务在 commit `b77d6b7bae17e265bf20509e9ea53c1cdc5c4c9d` 为该行两个三目表达式补空格。本作者只读确认：恢复旧行可精确重建首版SHA，除空格外没有字节变化；意图仍为 index16写475、其余写448+index。首版不可编译，不能据此宣称RTL功能等价已测；修复后的编译/仿真结果等待新的真实回执。

## 1. 目标与数值路径

实现固定 H8/I8 的 RMSNorm → gate/up 两投影 → SwiGLU → down 投影 → 原始残差。X 与 gamma 均为真实输入的8个 S16 Fin10；三份权重各为64个 S8 Fin7。输出为8个 S16 Fin10，一个128bit字。

相对旧 F8，新核取消 Norm 输出的 RNE3/clip-to-S8；Norm 的完整 S16 结果直接供给三次投影的 wide-A 路径。原始残差也不再做左移3的单位转换。该改变建立一个明确的新数值 profile，不是把旧 F8 输出数值简单重命名；并未证明任一完整模型在此量化下的精度。

N 保持真实原生算法：mode1、count8、epsilon_code1。若 X 原码为 x_i，先计算 `q=floor((sum(x_i²)<<16)/8)`，再取 `d=floor(sqrt(q+(1<<16)))`、`factor=floor(2^38/d)`，最后按原生 `clipS16(RNE30(x_i*factor*gamma_i))` 输出。这里 epsilon_code 是输入原码平方单位；X Fin10 时对应实数 epsilon=2^-20，不能把它当作通用浮点 epsilon=1。gamma Fin10 的1024表示1，允许逐 lane 变化、零值及负值；最终饱和按原生标志保留。

三次 M 投影均使用 A16 Fin10 × B8 Fin7，scale factor1/scale shift0，EXEC descriptor `0x9885`（A wide、B narrow、clear-result、K8/N8/1tile/1row），op5 read descriptor `0x107`（RNE right7、S16输出格式）。累加结果在读出时由 Fin17 变为 Fin10；每次 op5 仍是四个32bit槽，`pack_m_four` 仅抽取各槽低16并拼接两次响应，不进行额外算术。M 的 ACK/EXEC status 与两次数据响应仍按原状态机分类。

G 仍以 fn0/gated1 运行：gate 投影作为 SiLU 输入，up 投影作为乘数，S16 Fin10 结果写回；原生两 lane 共4个输入/4个输出 pair，controller 按退休顺序收集。E 两次服务分别为 op7/shift0 的 S16 原样复制和 op0 的 S16 残差加法；所有实际饱和均 OR 到 done_saturated，和 done_error 分开。

## 2. 固定17拍入口与地址

| input_index | 内容 | 真实普通S写地址 |
| --- | --- | --- |
| 0 | X：8×S16 Fin10，完整128bit | 448 |
| 1..3 | 硬件强制写零，不信任 host padding | 449..451 |
| 4..7 | gate 权重，64×S8 Fin7，n-major | 452..455 |
| 8..11 | up 权重，同格式 | 456..459 |
| 12..15 | down 权重，同格式 | 460..463 |
| 16 | gamma：8×S16 Fin10，完整128bit | **475** |

总帧272B，其中有效 X16B+gamma16B+weights192B=224B，实际零填充48B。input_index 从4bit扩为5bit；第17个真实写ACK消费后才建立 frame_stored。index16 有专用地址选择，不会按448+16写到464，也不会覆盖之后的 gate 结果。

start 后先把寄存保留的原始 X 写到466并消费ACK，再请求 N。历史内部观察名 `x_unpacked` 保留，但其内容现在是完整原始 S16 X，没有 unpack/缩放。gamma 已由最后入口写ACK建立，删除旧 `L_GAMMA`/unity literal 写步骤，不能在 start 后覆盖真实 gamma。

| S region | 运行中用途及生存期 |
| --- | --- |
| 448..451 | Norm 后448为8S16，449..451仍为实际零；供 gate/up 两次 loader |
| 452..463 | 三份权重，全部三次 load 完成之前不覆盖 |
| 464 / 465 | gate / up S16 投影，均保存后才启动 G |
| 466 / 467 | 原始 X / E7 shift0残差副本；最终 E0 前不覆盖 |
| 468..471 | G 中间结果及3个真实零填充字；供 down loader |
| 472 / 473 | down 投影 / 最终残差输出 |
| 474 / 475 | N 完整 S16 输出 / 输入 gamma |

Nsrc466、gamma475、dst474 对 count8 互不重叠，满足现 N controller 的地址准入。N 完成后普通S读474并原样写448；这是本轮选择的显式搬运路径，未改为 N 直接写448。E7从466复制到467也保留，便于和既有服务路径逐项核验。

三次 loader 的 `load_a_wide=1`；gate/up A base448，down A base468；B base分别452/456/460；rows1/tiles1/B narrow/reuseB0。A/B base均4字对齐。真实 loader 每次读取一个512bit B容器和一个512bit A容器，只发A容器第一128bit到一行M；因此实际3次load含6次宽口读，不能和下面普通S事务混为一类计数。

S 使用448..475共28字=448B的固定布局；T仅预约/写/读一个字16B。它们仍分别属于S16KiB与T6KiB，不是共享RAM，也不代表完整FFN中间维度能装入此空间。

## 3. 正常成功路径事务账

| 阶段 | 普通S写 | 普通S读 |
| --- | ---: | ---: |
| 17拍实际入口写与ACK | 17 | 0 |
| 原始 X 保存466 | 1 | 0 |
| N RMS服务：src统计、src回放、gamma、dst | 1 | 3 |
| Norm474读出并完整写448 | 1 | 1 |
| E7 shift0：466读、467写 | 1 | 1 |
| gate/up投影保存464/465 | 2 | 0 |
| G读取gate/up并写mid468 | 1 | 2 |
| down A padding469..471 | 3 | 0 |
| down投影保存472 | 1 | 0 |
| E0残差：读472/467、写473 | 1 | 2 |
| 最终结果473读出进入T | 0 | 1 |
| **总计** | **29** | **10** |

共39个普通S请求、39个真实原生ACK、39个helper响应；只有无故障、无reset的完整服务适用此守恒。相比F8，入口16→17新增1写，删除原unity-gamma写1次，净数量保持不变。

M为3投影×5命令=15：每组 op6 CLEAR、op4 SCALE1、op10 EXEC9885、op5 READ0/READ1各一次。loader三服务。N为一服务/四命令：op0 mode1 BEGIN、op1 count8统计、op2 FINALIZE、op5 count8带gamma回放。E两服务、G一服务/4pair，T一BEGIN/WRITE/COMMIT/输出take/RELEASE。它们是本实现固定正常路径的期望计数，不是本作者已经运行获得的测量结果。

## 4. 协调、背压与错误边界

外部19个信号/282逻辑bit与现F8相同；相同信号宽度不代表相同帧。in_valid&&!in_ready时host保持data；每拍输入经唯一S helper真实写ACK后才推进index，未完整frame不接start。RUN/DONE期间不能覆盖入口。早到start脉冲不排队，持续valid只在start_ready时接收一次。

LOCAL/E/G/N共用唯一普通S owner。整服务从请求握手至服务响应消费一直持有lease，包含目的写ACK；loader在M执行前单独运行，不以S loader busy推断普通口是否空闲。所有 permit_* 仍是固定TB故障/背压观察点，不是host配置端口。

reset为高有效同步协调复位，清帧/控制，不保证S/T RAM清零。prestart abort丢帧不造DONE；RUN abort协调reset并形成一个保持的error完成；既有DONE在abort期间保持，DONE+ready同拍只消费一次。native/controller/helper错误后停止新正常发令，并由单周期internal_reset清参与叶及controller，再等待host消费DONE。已完成S写或外部已消费输出不可回滚；done_error没有partial/错误原因字段。

T按BEGIN→WRITE→COMMIT→DRAIN→RELEASE推进，输出stall时由真实T保持；只有最后输出take且实际RELEASE接受后才正常DONE。这里out_ready仅代表本地接收，未新增跨岛stored ACK、CLOSE或受保护重放。未来母控/跨岛wrapper不能把本地DONE作为目的存储成功。

## 5. 交付与验证归属

本作者只新增此草稿RTL和设计/receipt；旧模板只读。静态审阅确认无旧 S8 narrow、unity gamma、9884/104投影描述符残留；端口/owner/错误及T生命周期沿模板复用。真正编译、独立数值oracle、背压/错误/复位测试与远程回执由根任务及测试作者执行，结果应以其实际日志和对应源码SHA补充，不能由这份设计稿预先宣称。

F16仍固定H8/I8、一帧绑定X+权重+gamma，尚无独立权重驻留接口、完整shape/profile编译、跨岛网络、完整A/F模型质量、外存供给或PPA资格。
