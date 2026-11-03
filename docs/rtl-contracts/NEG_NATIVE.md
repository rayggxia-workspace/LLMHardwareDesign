# N/E/G 冻结 RTL 审计与可实施控制序列候选

本文供 Issue151 总方案重写使用；**观察事实**与**新增 wrapper/控制方案**分别说明。本附录记录只读源码审计；独立审计未改RTL或服务器，没有执行RTL/SystemC/EDA。总方案文档与任务状态由本轮主交付统一更新。读取规则为 rayggxia-project-collab 1.0.0；认证连接读回为 Melodydt；Issue151 在本轮审计启动前为 in_review，重写期间为 in_progress。本地管理检查 `python scripts/check_project.py` 通过，只证明管理结构。

## 1. 来源身份与审计边界

- 仓库冻结点：`faabeda68b3b098ba562d68517319e02725f5bc3`，其中七宏来源为 `643c6012a11cbf461146ac40fbf61485223fe946`；本轮不追随 PR144 后续提交。
- 本地来源根：`work/Melodydt/151/merge-pr144-643c6012/integrated/`，这是 API 检查资料包，不是完整 Git clone。`upload-receipt.local.json` 和集成 `rtl-baseline.json` 记录来源；本轮重新逐字节计算下列文件 SHA-256/Git blob SHA，与该清单比较。
- 固定链接：[N](../../project/rtl/block_v2/block_v2_n.sv)、[N group](../../project/rtl/block_v2/block_v2_n_group.sv)、[N EXP include](../../project/rtl/block_v2/block_v2_n_exp.svh)、[E](../../project/rtl/block_v2/block_v2_e.sv)、[G](../../project/rtl/block_v2/block_v2_g.sv)、[G tables](../../project/rtl/block_v2/block_v2_g_tables.svh)。以下简称 N/E/G/group，行号对应这些文件。
- 本地包没有 `make_tables.py` 或 N/E/G 原测试平台；不得把本地缺文件解释成远端删除。本轮不重跑上游叶宏验证，也不转移其资格给新控制器或整模型。

| 文件 | 行数 | SHA-256 |
|---|---:|---|
| block_v2_n.sv | 240 | 0ddd23ec62631f64d689678b026a508944928fdb1cedf26ef73900f5e58fd861 |
| block_v2_n_group.sv | 34 | d6a4bc66bc525ee74962bb918bf57d72bfa20ecdf224ca78df785ea5b0a8e232 |
| block_v2_n_exp.svh | 1032 | a421489100aa883f645baeabfcefa1f4022010059d956f9770f44f2817c2a0ab |
| block_v2_e.sv | 92 | 865ff289b05c5bcd045ae4bc40feeb9402b928b281951367c31e8c4c2c752b0b |
| block_v2_g.sv | 86 | 7cb5da1d1625c97f8c8486d9c9eeef97076d6a1974d41229e3280b6df37a8ad7 |
| block_v2_g_tables.svh | 2572 | d4e1e5d11b845f44e9c5674b4e12c1ad8e9afaec6e524a1866c95c17b3e80d14 |

## 2. 真实端口与共同约束（观察事实）

| 宏 | 原生输入 | 原生输出 | 接受/保留条件 |
|---|---|---|---|
| N | clk/reset；cmd_valid；cmd_op[3:0]、cmd_count[3:0]、cmd_param[31:0]、cmd_data/aux[127:0] | cmd_ready；rsp_valid/data[127:0]/error/saturated；busy | N4–8、54–55：`cmd_ready=!reset && phase==IDLE && (!rsp_valid || rsp_ready)`；`busy=!cmd_ready`，所以 busy 也可能仅表示响应被背压，不是统计上下文是否占用 |
| E | clk/reset；in_valid；in_op[3:0]、in_shift[4:0]；in_a/b/c[127:0] | in_ready；out_valid/data[127:0]/error/saturated | E6–10、25、48–55：单命令执行；上一输出可在被接受同拍接收下一命令；不是每拍八元素流水 |
| G | clk/reset；in_valid；in_fn[2:0]、in_gated；in_x/gate[31:0] | in_ready；out_valid/data[31:0]/error/saturated | G4–12、69–84：四级流水，`advance=!out_valid || out_ready`；输出背压时整条流水一起停，II=1 仅适用于下游不阻塞 |

三者原生都没有 tensor/job/version/tag、地址、向量总长、last、T 提交或 S 访问端口。**E/G 没有 count 或 lane mask**。N 的 cmd_count 只是本命令实际元素数，不是任务总长。错误/饱和是响应属性，不会自动使外部存储回滚或阻止 T 提交。wrapper 必须记录被接受的命令、响应归属、有效数、类型和写确认；不能把这些字段写成现有宏端口。

## 3. N 命令位域、许可阶段与输出（观察事实）

opcode 名称采用冻结 BLOCK_V2.md L68；实际许可由 N85–100、138–164 决定。除表中字段外，cmd_param/count/data/aux 不参与该命令判断或语义，调用方宜填零，不能赋予不存在的功能。

| op | 含义/有效字段 | RTL 许可 | 成功响应/状态改变 |
|---:|---|---|---|
| 0 | BEGIN：param=0 Softmax/1 RMS/2 L2；epsilon=data[31:0] | param 整个 U32 必须≤2；mode1/2 epsilon 必须非零；不检查旧上下文是否完成 | 清零 count/sum/sumsq/EXP/replay 统计及 factor_valid，设置 context_valid；立即成功响应；不清 TopK 装载上下文 |
| 1 | STATS：count=1..8；data 低 count 个 S16 | context_valid 且未 FINALIZE；累计数不得超过65535 | 累计 S32 sum、U48 sumsq、S16 max/min、U16 count；响应 data=0 |
| 2 | FINALIZE | context_valid、未 FINALIZE、count>0 | Softmax 只锁定统计；RMS/L2 发起内部除法/根/因子，结束后响应；**无 expected_length 检查** |
| 3 | EXP：count=1..8；data 为原分数回放 | Softmax、已 FINALIZE、无 factor；exp_count+count≤统计 count | 逐元素减已保存 maximum，输出 UQ1.15 EXP；累计 U32 exp_sum 和 exp_count |
| 4 | FINISH_EXP | Softmax、已 FINALIZE、无 factor；exp_count==count 且 exp_sum!=0 | 求 floor(2^44/exp_sum)，写 U32 factor；group_error 或因子高32位非零时报错 |
| 5 | NORM_REPLAY：count=1..8；data 为原 x，aux 为逐元素 gamma | factor_valid，mode1/2；replayed+count≤count | 每元素 RNE30(x_raw×factor×gamma_raw)，S16 饱和；累计 replayed |
| 6 | SOFT_REPLAY：count=1..8；data 为 EXP 回放，aux 无数学作用 | factor_valid，mode0；replayed+count≤count；每个有效 data 的 U16 值≤32768 | EXP 按无符号扩展，RNE30(EXP_raw×factor)，夹到0..16384；累计 replayed |
| 7 | READ_STATS | context_valid；可在统计完成前读取 | [15:0] count；[31:16] maximum；[47:32] minimum；[79:48] sum；[127:80] sumsq |
| 8 | TOP_BEGIN：param=1..8 指定 k | 无普通统计阶段限制，整个 U32 param 在1..8 | 清 top_count，保存 k，top_loading=1；不会清普通 Norm/Softmax 上下文 |
| 9 | TOP_LOAD：count=1..4；每32bit为低16 S16 score、高16 U16 ID | top_loading，累计≤40 | 保存输入记录；可有重复 ID，RTL 不校验 ID 唯一/连续/地址范围 |
| 10 | TOP_SELECT | top_loading、记录非空、记录数≥k | 按 score 降序、同分 ID 升序逐轮扫描；输出低16k位的 **ID**，其余零；结束 top_loading=0 |
| 11 | READ_FACTOR | factor_valid | 低32位 factor，其余零 |
| 12..15 | 非法 | 总是失败 | rsp_error=1、data=0，不执行有效命令状态改变 |

N142–220 表明每条命令先缓存 data/aux，再内部两路处理；例如 count=8 的 STATS/EXP 分四对处理，NORM/SOFT replay 每对再经乘法、gamma/格式化步骤。按 `rsp_valid && rsp_ready` 等待，不使用臆测的统一固定周期数。N 没有整向量 RAM，也没有自动读 S 或重放原值。

### 3.1 N 数值公式、容量及未强制的语义

由 N57–75、148–153、191–219 与 group1–30 得到，`RNEx` 均为有符号最近偶数舍入：

- Softmax 分数为 S16 Q5.10。差值以 S17 形成：d=x_raw−max_raw；d<−16384 输出0，d≥0输出32768，否则按1/64网格的 include 表及低4bit做 RNE 插值。EXP 的 raw 32768 是无符号的1.0，不能当有符号 S16 的−32768。
- Softmax `f=floor(2^44/ΣEXP_raw)`；概率 `p_raw=clamp_{0..16384}(RNE30(EXP_raw×f))`，是非负 S16 Q1.14。独立量化后各概率 raw 之和不保证精确16384。
- RMS：`a=floor((sum_sq<<16)/count)+(epsilon_raw<<16)`；L2：`a=(sum_sq<<16)+(epsilon_raw<<16)`。两者 `root=floor(sqrt(a))`，`f=floor(2^38/root)`，`y_raw=sat_S16(RNE30(x_raw×f×gamma_raw))`。
- epsilon 是 **原始输入整数平方单位的正 U32**；若输入实际为 raw×2^-Fin，应把模型 epsilon 换成约 epsilon_real×2^(2Fin)，并冻结取整方法。小于1后强制为1、以及把模型的 `max(norm,eps)` 换成 `sqrt(sum_sq+eps)`，均可能改变算法，不能默认为等价。N 没有 epsilon=0 Norm 路径。
- gamma 原生为 S16，声明语义为 Q5.10；无 gamma 时也必须显式回放对应常量。gamma_raw=1024 产生约 Q5.10 的单位增益归一化。N 没有 beta 加项、均值中心化或 LayerNorm；“RMS0”是外部先生成1+weight，而不是 N 的新 mode。
- 65535×32768 的和、65535×32768² 的平方和分别不溢出 S32/U48；正确回放时 Softmax EXP 和≤65535×32768<2^31。统计不提供溢出/饱和标志；长度上限来自累计 guard。
- group 是 **N 内部** U64 精确整数除法/U64→U32 floor sqrt；除法64轮、根32轮（group28），除零 error；没有通用外部 coefficient/EXP 服务口，也不是可直接另发命令的独立七宏服务。

**未由 N 硬件强制的语义**：FINALIZE 时是否已收到指定 head/行的全部元素、回放的 x/EXP 是否与统计原值一致、gamma 和位置是否配对、mask 含义、输出是否完整写到 S/T。EXP 和 replay 只检查累计上界，错误数据只要形状和值域合法仍可能被接受。普通上下文和 TopK 可以在 IDLE 间交错，但单个响应端口及多周期执行资源共享；首版 wrapper 应把整个任务作为唯一 N lease，不能从“内部存着两类状态”推导任意并发。

**有限 mask 特别限制**：N 没有 mask 位或−∞。若一行全为同一个有限哨兵，减 max 后会成为近似均匀分布。使用−32768不能自动保证被 mask 的 EXP 为0；必须证明该行至少一个有效 key，且有效 maximum 与被 mask 值的 raw 差至少16384（对应差值≤−16），或另外定义新的 mask 数值处理。全 mask 行/极低有效 max 必须是显式拒绝或独立算法分支。

**L2→R Q1.14 候选**：基于上述 raw 公式，可令单位增益 L2 的 gamma_raw=16384，使输出 raw≈16384×x/sqrt(sum_sq+eps)，再将该张量声明为 Q1.14；这在 gamma 的既有 S16 数值范围内，物理上相当于 Q5.10 gamma=16。它是 **参数与输出类型绑定方案**，不是把已有 gamma_Q10 合同或所有 L2 模型自动改成 Q14，仍需对目标 epsilon、factor/floor/RNE 和模型误差作独立 oracle。另一方案“先 gamma=1024 得Q10，再左移4”会先损失4bit精度，不能称等价。

## 4. E 全操作、打包与数值边界（观察事实）

E12–43、58–87 的真实行为如下，所有正常输出默认 S16 饱和；shift 是5bit，只能0..31。没有外部 format 字段，操作码决定对 A 的解释。

| op | raw 操作 | shift/特殊格式 |
|---:|---|---|
| 0 / 1 | a+b / a−b | shift 忽略；两输入必须同尺度 |
| 2 | a×b | S32 乘积经 shift RNE，最后 S16 饱和 |
| 3 | a×b+c | **先**将 S16 c 加到 S32 乘积单位，完整和只做一次 shift RNE；不是自动把同 Q10 c 左移10 |
| 4 / 5 | max(a,b) / min(a,b) | signed S16 比较；shift 忽略 |
| 6 | c!=0 ? a : b | 每lane c 为选择条件；shift 忽略 |
| 7 | a<<<shift | 局部 S48 左移后 S16 饱和，不增加通用输出宽度 |
| 8 | a>>>shift | 算术右移，**无 RNE** |
| 9 | 相邻 pair：偶=x_even×cos−x_odd×sin，奇=x_odd×cos+x_even×sin | B_even=cos、B_odd=sin；两轮乘法后完整和做一次 shift RNE；前后半区 RoPE 必须外部重排成相邻 pair |
| 10 | a 的 RNE 右移 | 输入仍只有 S16，不能代替 S32→S16 |
| 11 | abs(a) | −32768 的绝对值饱和到32767并置 saturated |
| 12 | a 饱和到 S8 并紧凑打包 | 八个 S8 放低64bit，高64bit零；shift **忽略**，不能直接当缩放量化 |
| 13 | A 解释为四个小端 S32：A[32i+:32] | 四值各 shift RNE、S16 饱和后放低64bit，高64bit零；B/C无数学作用 |
| 14 / 15 | 非法 | 接受后返回 error=1、data=0、saturated=0 |

乘法类的尺度应使用整数公式：`Fout=Fa+Fb−shift`；FMA 的 c 必须按 Fa+Fb 的乘积单位编码。op13 的 `Fout=Fin−shift`，只支持非负右移0..31。Fin<Fout 的宽输入升尺度不由 op13 完成。若 M op5 已按 S16 饱和且仍以四个 S32 容器返回，则 op13 shift=0 只是包装，不能再按输入原始 Fin 重复缩放。

`out_saturated` 为整条命令任意 lane 被夹紧的 OR，不能指出具体 lane；op13 的高四lane为0不算额外四个有效元素。普通 E 始终计算八lane，tail 必须给所有使用的操作数补0，外部另保存 valid_count；RoPE 则应按完整逻辑 pair 组织，不能把任意单数尾元素凭空配成另一个坐标。E 不作 transpose、gather、格式标记或 S 地址生成。

## 5. G 编码、门乘尺度及 join（观察事实）

实际编码为 **fn0 SiLU、fn1 Sigmoid、fn2 GELU_tanh、fn3 Softplus**，fn4..7 会作为错误包进入流水，最终 out_error=1、data=0（G43–66、73–83；表的 fn1/x0条目 raw8192、fn3/x0条目 raw710 与冻结文档的函数对应一致）。

| fn | x raw 解释/域 | in_gated=0 | in_gated=1，gate 按声明 Q5.10 |
|---:|---|---|---|
| 0 SiLU | S16 Q5.10；表域[-8,8]；低于域为0，高于域为identity | Q5.10 | `sat_S16(RNE10(activation_raw×gate_raw))`，Q5.10 |
| 1 Sigmoid | S16 Q5.10；表域[-8,8]；低于域0，高于域16384 | 非负 S16 Q1.14 | `sat_S16(RNE14(sigmoid_raw×gate_raw))`，**Q5.10** |
| 2 GELU_tanh | S16 Q5.10；表域[-8,8]；低于域0，高于域identity | Q5.10 | RNE10 门乘，Q5.10 |
| 3 Softplus | S16 Q5.10；表域[-16,16]；低于域0，高于域identity | Q5.10 | RNE10 门乘，Q5.10 |

表内1/32网格插值也有一次 RNE；门乘是下一次数值舍入，并非从数学激活到最终乘积全程一次舍入。最终 out_saturated 只报告最终门乘结果超 S16，而不是 LUT 域外近似被采用。**输出 format 必须绑定 fn 和 gated 两者**，不能只见 Sigmoid 就标 Q1.14。Sigmoid→UQ1.31 系数的 raw<<17 只能使用 ungated Q1.14 输出，并且只改变容器、不能恢复量化精度。

G 对 `in_x` 做激活，再乘 `in_gate`，端口角色不可互换。FFN 是 x=gate投影、gate=up投影；GDN 输出是 x=独立Z、gate=Norm(R)；Falcon SSM 输出是 x=独立Z、gate=R读出（按声明先转换成 Q5.10），其后再跨完整4096通道 RMS。G 的两个lane没有单独有效位；一元素尾包须给另一lane补0并在 wrapper 排除。

## 6. 可直接落 wrapper 的控制序列（新增候选，尚未实现）

下列控制器只展开真实接口，不把元数据插入叶宏端口。每个服务保留唯一端口所有者；“完成”统一指成功响应已接受、全部结果写确认及规定有效数齐备。错误或饱和如何处理须由产品策略冻结：候选首版对 error 使任务失败；sat 单独累计并与数值策略比较，不把所有合法饱和都改称硬件 error。

### 6.1 NORM_CTRL

1. 固定描述符：task/version、mode1/2、L(1..65535)、input_base、gamma_base/常量、output_base、Fin/Fout、epsilon_raw、尾字有效数、sat策略。预留整个 N lease 及所有存储区，确认 x/gamma 写完成；同头输入不能被其他任务覆盖。
2. 发 BEGIN：op0、param=mode、data[31:0]=epsilon_raw，其余填0；保持至 cmd 握手，等 rsp 握手检查 error。epsilon=0 在发命令前即拒绝。
3. 对 j=0..ceil(L/8)−1，读取原 x 字，等待 S 响应，再发 op1，count=min(8,L−8j)。接受成功响应后再计 stats_done；累计精确等于 L 才允许 op2。不能靠 N 的 `count>0` guard 代替该屏障。
4. 发 op2 并等成功响应。此时因子已由 N 内部 group 算好；op11 仅用于诊断/记录，不是必须额外启动一次除法。失败时禁止 replay/发布。
5. 重新读同版本 x 与同索引 gamma，收齐两操作数才发 op5；count 同上，aux按低16lane顺序。响应 data 只取 count 个有效元素；写 output 并等每字写确认后累计 outputs_visible。若输出覆写输入，应严格保证该位置原 x 的最后使用已经结束；首版优先不同区避免证明复杂化。
6. 仅当 replay计数、output写确认均=L 且策略通过，报告 `norm_ready(task,version,L,format)`、释放输入/gamma/N lease。普通 N 没有 FINISH_REPLAY op，最后完整性由 wrapper 计数。中途失败后先收尽已接受响应，再用下一次 BEGIN 重建上下文；新任务不能复用未收回的旧响应。

### 6.2 SOFTMAX_CTRL（含257元素实例）

1. 固定 L、score Q5.10、EXP UQ1.15、prob Q1.14、输入/EXP/输出独立版本及地址；确认 mask 数值约束；预留 N lease。257元素时每遍33条命令，count序列为32个8和最后1。
2. op0 param0 →逐字 op1 STATS→确认累计=L→op2 FINALIZE。每条命令/响应严格握手；max直到全向量统计完成才固定。
3. 重新读原 score，发 op3 EXP，取得每字 UQ1.15 输出，写 EXP 区并等确认。该遍必须累计 L；EXP buffer 在后续回放前不得被概率结果覆盖。
4. 确认所有 EXP 命令响应成功及 EXP写确认=L，再发 op4 FINISH_EXP，检查 rsp_error。该命令本身不输出 probability，也不返回已格式化 factor（如需读 factor另发op11）。
5. 读同版本 EXP，发 op6 SOFT_REPLAY，**按 U16 传递32768**，不符号转换；逐字保存概率并等写确认。最后一字count1，其余7lane不作为新元素；向T写时仍是整128bit字，真实count需外包元数据。
6. 全部 L 概率可见且无失败后才报告 `softmax_ready`；若走 T，由上层按 T 真实协议提交，N 响应不等于 T 提交。257例原 score33字528B、EXP33字528B，共 S 有效分配1056B；输出另528B；地址间隙、队列和T容量另外计算。

### 6.3 CAST_PACK_CTRL（四S32容器→八S16存储字）

1. 描述符固定 source raw type/Fin、目标Fout、元素总数、数值右移s=Fin−Fout以及源/目标版本。s不在0..31、输入实际不是四S32或缺失有效数时拒绝；M已S16夹紧的读出采用s=0包装描述符。
2. 每次捕获源128bit响应及其原始顺序/有效数1..4；补零无效S32。发 E op13、shift=s、A=原始128bit，B=C=0；等待 E 输出接受，检查 error/sat。不能先截低16bit再交给op13。
3. 只取 out_data[63:0]；第一个半包存到64bit保持槽，第二个半包与其拼接为 `{second_low64,first_low64}`，形成八S16顺序。若剩余仅一个半包则高64填0，并保存准确有效数。先拿到第一半包就写满128bit或消费其高64零会产生错误布局。
4. 整字写入S/T并等确认后发布。最少需要半包保持64bit、输出保持128bit及计数/类型状态；它们是新增 wrapper 存储，不能只以算法的净S16数据量计容量。输出阻塞时须保持E out_ready=0或已有明确接收槽，不能丢掉已完成包。

op12是另一种 pack：八S16→低64bit八S8，不带可用的右移量化；与op13不能共用“总是四元素低半包”的解释。transpose、任意gather、相邻RoPE重排都由其他有界搬运/布局服务完成，不伪装成 E opcode。

### 6.4 G_JOIN_CTRL（八元素分四包）

1. 保留同 task/token/head/tile/version 的 X128与Gate128或等价存储描述；检查X为Q5.10、Gate为声明Q5.10、fn/gated所决定的输出类型。只有两支对应位置都可用才构成一个原生命令。
2. 首版最小实现可每次只允许一个32bit命令在途：取j=0..3的各两S16，发稳定的 in_x/in_gate/fn/gated 至 in_valid&&in_ready，随后等 out_valid&&out_ready；按j写入128bit输出保持槽并OR error/sat，再继续下一个包。它正确复用现有四级流水，但不声称发挥II=1。
3. 若要连续每拍发包，新增深度至少4的按接受顺序元数据FIFO（job/packet_index/有效lane数），输出时只弹FIFO头；G无原生tag。输出assembler满且存储尚未接受时拉低out_ready，G会整流水冻结。吞吐与FIFO/assembler深度必须共同验证，不能按固定4拍延迟在背压时猜输出归属。
4. 尾包只含一个逻辑元素时第二lane补0，保存valid_count；八元素四包全部接收并拼好后整128bit写S/T，等写确认才报告 `gated_mid_ready`。新的Mid进入单M down前仍需装载为M要求的A布局；G输出完成不等于M loader完成。
5. 撤销任务时，E/G没有原生命令取消口。已接受包必须收完并按旧task丢弃/记失败，或者在独占资源且上层允许时复位；不能只清 wrapper tag就接新任务，否则旧响应会错配新数据。复位也不使S/T或其他宏自动回滚。

## 7. 前稿数字与格式约束复核结论

| 项目 | 可以保留的结论 | 重写时必须精确表述 |
|---|---|---|
| 最小 FFN400B | S8/noNorm、H=I=8；M S16×S8；M op5 S16饱和仍返回4S32，E13 shift0包装；G四个两元素包 | 400B包含25个S字的padding/对齐，非wrapper总容量；本审计只确认N/E/G相关部分，M/S loader由对应审计闭环 |
| 257 Softmax1056B | score与EXP各33×16B；输出另528B；末包count1 | N没有L=257命令字段；子控必须禁止提前FINALIZE及丢尾；UQ1.15 EXP与Q1.14概率不同 |
| G类型 | fn0/2/3 ungated Q10；fn1 ungated Q14 | **gated fn1经>>14后为Q10**，不能只按fn标类型；G门乘并非一次总舍入 |
| L2→R | raw公式允许gamma16384的候选类型绑定 | 不是默认gamma1024的Q10结果可直接标Q14，也不是已完成目标模型数值验收 |
| E宽转换 | op13有效4个S16，shift0..31 | 不能把高64零当第二半有效数据；op12是8个S8，shift被忽略；op8不是RNE |
| FMA/RoPE | 完整乘积/和后一次RNE；相邻pair旋转 | C为乘积单位；Q10输入下同Q10 residual不能不对齐直接当FMA C；半区RoPE要实际重排 |
| 长向量/多头 | N长度≤65535，按≤8元素分批，同组全统计/回放 | N只存统计，S/外存保证原值/EXP/gamma版本；不能对每8/128维独立Norm替代整组 |
| TopK/MoE | 40组score/ID，选≤8 ID；同分按ID | 不返回selected score、地址、rank权重；ID唯一0..39是外部受约束方案，不是N guard；gather与宽归并仍新增 |

## 8. 最小验证范围（新增候选，未执行）

- 真实RTL接口：命令等待、响应背压、复位、旧包drain、error/sat独立传播；G连续四包加随机背压验证FIFO顺序守恒。
- NORM：L=1/8/9/257/4096/65535；RMS/L2不同公式，epsilon0必须拒绝，epsilon换单位、gamma负值/16384、零向量；x/gamma错版本负例必须由wrapper挡住。
- Softmax：257末项新最大值、EXP raw32768、错误回放unsigned、少EXP后FINISH、过量replay；提前FINALIZE是“叶宏可接受、wrapper须拒绝”的测试，不能误写RTL本来会报错。另测全mask行和有限哨兵差值不足。
- E：op8与op10的负数半舍入差别；op12 shift无效及S8饱和；op13四S32正负边界/两半拼接/奇尾；FMA c尺度；RoPE相邻坐标和跨半区外部重排。
- G：全部fn×gated格式组合，sigmoid(0)=8192时ungated Q14与gated乘gate1024得到raw512(Q10)的区别；一元素尾包、错误fn、激活输入支/线性门支反接负例。
- 数值接受需独立整数参考和目标样本范围；本轮只审计源码与设计候选，没有产生新仿真、模型质量或物理通过证据。
