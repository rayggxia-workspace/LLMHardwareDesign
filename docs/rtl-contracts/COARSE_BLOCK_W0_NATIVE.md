# W0 七宏原生接口与源码锁

本文件服务于 Issue 151 / PR 152 的 W0 合同固定。研究输入为 `bd7cb2f3060c61e5d28a2ece0653dd9336a024af`，原生叶源码继续选用 `707878621b2add4ed218b8c43df2e95c9a56e2ba`。这里固定的是可检查的接口候选合同，尚未冻结共同物理底座，也不表示六类完整大 Block 已组合完成。

配套 `w0-source-lock.json` 记录 14 个核心文件的 Git blob、原始字节数和 SHA-256；`w0-native-contract.json` 逐端口列出七顶层的方向、位宽、源码声明行、外侧驱动责任，以及命令、阶段、响应分类、错误、数值和取消边界。本文是阅读入口，完整的 149 个端口与 24 个握手通道以 JSON 为准。

## 源码与既有测试的边界

通过 Melodydt GitHub 连接对 PR 144 固定观察头 `d1f26884b13f8d0466bbaefe2fc6322a14c66df9` 执行了只读 GET。该观察时 PR 仍为 open、未合并。14 个核心文件逐字节和 Git blob 均与选定的 707 源相同：**14 / 14 相同，0 个变化**。比较范围只覆盖列出的 14 个文件，未导入或合并整个 PR 分支，未比较其余上游文件，也不转移任何物理资格。

P2 的 3 个新增 RTL 与 2 个 TB，另用真实运行回执中的 5 组文件 SHA 锁定。真实仿真时它们属于未提交工作区；`7078786` 仅是原生叶宏来源，不能作为这些新增实现的运行 commit。P2 实现随后交付于 `1cc43a93`，当前研究包的这 5 个文件均与运行回执字节相符。回执所载 19 个 bounded case 是既有 P2 证据，W0 没有重新仿真，不能扩展为完整七宏系统、完整模型或物理实现通过。

## 七个顶层的端口形态

| 宏 / 端口数 | 请求与输入载荷 | 输出与握手 | 外侧唯一责任方 |
| --- | --- | --- | --- |
| M / 27 | A：128 bit，bank/row/tile/wide；B：512 bit，bank/tile/wide/half；command：op4/index6/data64 | A、B 各 ready；response：128 bit + error + saturated；busy | S loader 驱动 A/B，M_CTRL 驱动 command 和 rsp_ready |
| N / 15 | command：op4/count4/param32/data128/aux128 | response：128 bit + error + saturated；busy | N_CTRL |
| E / 14 | input：op4/shift5，A/B/C 三组 128 bit 操作数 | output：128 bit + error + saturated，valid/ready；没有 busy/count/mask | E_CTRL |
| G / 13 | 输入 fn3/gated1，加两组 32 bit（每组 2×S16） | 输入 ready；输出 32 bit + error + saturated，独立 valid/ready；没有 count/mask | G_CTRL |
| R / 12 | command：op4/index10/data128 | response：128 bit + error；busy；没有 saturated | R_CTRL |
| S / 38 | 普通 req/wr/addr10/din128；独立 load 描述符 | 普通 ready/valid/take/dout128；loader done/error；独立 A128/B512 出口 | S_CTRL 拥有普通端口、loader 描述符和 done；M 提供 A/B ready |
| T / 30 | BEGIN、WRITE、COMMIT、REVOKE、RELEASE 独立通道 | READ：index10/data128/last；owner2/generation32/word_count10；protocol_error | T_CTRL 驱动各输入与 read_take |

所有 native 宏均使用 `posedge clk`、同步高有效 `reset`。这里没有 CDC 设计或时钟频率资格。多个候选来源即使 valid 互斥，也必须经过已预制的 MUX/选择和唯一 owner，不能将 push-pull 输出直接金属短接。表中的 owner 是责任划分，不代表这些控制器已全部实现。

端口源码：[M L5–15](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/707878621b2add4ed218b8c43df2e95c9a56e2ba/project/rtl/block_v2/block_v2_m.sv#L5)、[N L3–9](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/707878621b2add4ed218b8c43df2e95c9a56e2ba/project/rtl/block_v2/block_v2_n.sv#L3)、[E L5–11](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/707878621b2add4ed218b8c43df2e95c9a56e2ba/project/rtl/block_v2/block_v2_e.sv#L5)、[G L3–9](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/707878621b2add4ed218b8c43df2e95c9a56e2ba/project/rtl/block_v2/block_v2_g.sv#L3)、[R L4–9](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/707878621b2add4ed218b8c43df2e95c9a56e2ba/project/rtl/block_library_v1/block_v1_r.sv#L4)、[S L4–30](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/707878621b2add4ed218b8c43df2e95c9a56e2ba/project/rtl/block_feed_v1/block_feed_s_macro.sv#L4)、[T L4–21](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/707878621b2add4ed218b8c43df2e95c9a56e2ba/project/rtl/block_v1/transaction6k.sv#L4)。

## 命令、数值与响应不能只看 128 bit

| 宏 | 关键操作与阶段 | 响应分类和数据有效性 |
| --- | --- | --- |
| M | op4 配置全局 scale；op10 EXEC；op3 读 S64；op5 读格式化值；op6 清 validity；op11 清单输入 bank；op12 读 partial diagnostic | op10 是 fault_rows 状态应答，不是矩阵。op3 为 2×S64；op5 为 4×S32 carrier，逻辑宽度由 S8/S16/S32 选择决定；op12 为 S40 扩展到 S64 的诊断值。配置/清理 ACK 不能送入数据通路。 |
| N | op0 BEGIN；1 STATS；2 FINALIZE_STATS；3 原 score→EXP；4 FINALIZE_EXP；5 Norm replay；6 EXP→概率；7 stats record；8/9/10 TopK begin/load/IDs；11 factor record | op3 的 U16 EXP 不是概率；op6 才输出 Q14 概率。op7/11 是异构字段记录，op10 是 ID。必须保存已接受命令/阶段，不能凭 rsp_data 的位宽推断类型。 |
| E | op0–13 合法；14/15 报错。数值 op、算术右移与打包操作有不同舍入规则 | op12 为低 64 bit 的 8×S8；op13 为低 64 bit 的 4×S16，高 64 bit 为零；二者不可共用一个“低64均同格式”的 schema。其它 op 以 8×S16 为主。 |
| G | fn0 SiLU、1 Sigmoid、2 GELU-tanh、3 Softplus；gated 选择是否与 gate 相乘 | 未 gated 的 Sigmoid 输出 Q14，gated Sigmoid 输出 Q10，其余函数输出 Q10；Sigmoid Q14 不等于 Softmax probability。四级流水有序，整体因下游 stall 冻结。 |
| R | op0 OPEN；1/2/3/4/5/9/10/15 装载；6 EXEC；7 COMMIT；8 REVOKE；11/12/13/14 读取 | op6 是计算完成 ACK；op12 是提交前的 candidate output，op11 是 active state，op14 是 active history，op13 为 metadata。加载与控制 ACK 不是 tensor。 |
| S | 普通端口与 loader 是两套协议；loader 描述符可重用 B | 普通写也产生应答，dout 回显 din，必须消费 ACK；普通读输出原始 128 bit。loader done 只表明两条供数通道排空或描述符失败，不代表 M EXEC 完成。 |
| T | EMPTY→WRITING→SEALED→COMMITTED/READ→RELEASE→EMPTY | WRITE 没有逐字 ACK。COMMIT 发布 read 序列，没有 commit_error 端口。末字被 take 后只进入 RELEASE，仍须显式 release 才能重用。 |

M op10 描述符：`index[5]` 为 bank，`index[4:0]=0`；data 的 A/B 格式在 bit0/1，clear_result 在 bit2，bit3 保留为零；lastK=`[7:4]`、N=`[11:8]` 均为 1..8，tiles=`[14:12]` 为 1..4，rows=`[18:15]` 为 1..8，`[63:19]=0`。一次 K segment 至多 32。成功行以 8 个 S64 原子提交；某行溢出不会使整个 EXEC 的其它成功行回滚。op5 先按指定右移 RNE 再饱和到逻辑宽度；只有已经选 S16 的 op5 结果才可通过拆包抽取接 G，不能把未转换的 S64 裸截成 S16。op6 清 validity，不清 payload RAM 或 scale。[描述符 L48–62](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/707878621b2add4ed218b8c43df2e95c9a56e2ba/project/rtl/block_v2/block_v2_m.sv#L48)、[格式化 L105–122](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/707878621b2add4ed218b8c43df2e95c9a56e2ba/project/rtl/block_v2/block_v2_m.sv#L105)、[命令及完成 L197–248](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/707878621b2add4ed218b8c43df2e95c9a56e2ba/project/rtl/block_v2/block_v2_m.sv#L197)。

N mode 为 0 Softmax、1 RMS、2 L2；向量操作 count 为 1..8，TopK load 为 1..4，组长度上限 65535，TopK records 至多 40、K 至多 8。Softmax 必须保存原 score 给 op3，并保存同组同 max/aggregate 的原样 EXP 给 op6；无损 S/T 回放可继承该 lineage。数值修改后不能仅凭 code 范围仍合法就继续称原 EXP。Norm 使用正 epsilon 和逐元素 gamma；无 mean subtraction、beta 或 LayerNorm 模式。epsilon 以输入编码平方单位解释，gamma 编码会影响输出单位，不能默认 Norm 输出满足 R 的 Q14 输入。[guard L84–100](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/707878621b2add4ed218b8c43df2e95c9a56e2ba/project/rtl/block_v2/block_v2_n.sv#L84)、[dispatch L134–164](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/707878621b2add4ed218b8c43df2e95c9a56e2ba/project/rtl/block_v2/block_v2_n.sv#L134)、[EXP L168–189](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/707878621b2add4ed218b8c43df2e95c9a56e2ba/project/rtl/block_v2/block_v2_n.sv#L168)、[replay L203–220](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/707878621b2add4ed218b8c43df2e95c9a56e2ba/project/rtl/block_v2/block_v2_n.sv#L203)。

E 没有 count，物理 lane 都参与其相应运算及 saturated 汇总；尾部有效 lane 由外部合同处理。op8 为算术右移，不能将其当所有场景的 RNE；op2/3/9/10/13 的舍入见 JSON 及源码。G 也没有 count；两 lane 全部实际执行。需要 Q14→Q10 时必须选有定义的数值转换，不能只改标签。[E L26–88](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/707878621b2add4ed218b8c43df2e95c9a56e2ba/project/rtl/block_v2/block_v2_e.sv#L26)、[G L39–84](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/707878621b2add4ed218b8c43df2e95c9a56e2ba/project/rtl/block_v2/block_v2_g.sv#L39)。

R state/x/inject/history/output 的 S32 采用同一单位 F，Q/K/taps 为 S16 Q1.14，decay/beta 为 UQ1.31 且不大于 `0x80000000`，skip 固定 Q16.16。owner/epoch/position 是 32 bit，但并非每条命令都检查身份；尤其 REVOKE 无身份比较，metadata 读取不证明 context 有效。当前 707 源算术临时量为 S128，此处只锁定当前数值实现；没有证明其与旧 643 实现逐周期/数值等价，也没有新测延迟、功耗、面积或时序。[格式与寄存器 L1–47](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/707878621b2add4ed218b8c43df2e95c9a56e2ba/project/rtl/block_library_v1/block_v1_r.sv#L1)、[命令 L109–180](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/707878621b2add4ed218b8c43df2e95c9a56e2ba/project/rtl/block_library_v1/block_v1_r.sv#L109)。

## phase、背压、提交、释放与取消

命令或数据只在其 valid/request 与 ready/take 同时为 1 的上升沿被接受。owner 在背压期间保持所选载荷和元信息稳定，并持有已接受命令的分类上下文，直到对应响应被消费。原生响应没有统一 op/type echo；不要求运行时增加通用 role 标签，可以由固定程序阶段和少量在途状态完成分类。error 应答不能误放为正常 payload，ACK 和 metadata 也不能仅因 error=0 就进入 tensor 路径。saturated 与 error 含义不同。

| 宏 | 可见、提交和释放边界 | reset/cancel/error 边界 |
| --- | --- | --- |
| M | A/B 接受只说明输入 bank 已装入；EXEC 完成状态后按 op3/5 读取。读结果不自动释放；结果会被后续 clear/EXEC 改写 | 无原生事务 abort。协调 reset 清控制/validity，不能追回已经消费的输出或把已成功的行当作全事务回滚。非法描述符、行 fault 需按各自状态处理 |
| N | begin/stats/finalize/EXP/replay 严格分阶段；输出消费不自动结束或重建上下文 | op0 重建 Norm/Softmax 统计但不清 TopK loading。上下文/统计/容量等 guard 报错不等于软件所有语义已验证；无通用 cancel |
| E/G | 接受后按序输出；下游 stall 时保持 native 输出。G 是可含多个有序输入的流水，不能假定仅一个在途 | 无逐事务 cancel；协调 reset 丢弃流水有效位。E/G 无 count，不可用无效尾部掩饰溢出/饱和 |
| R | EXEC6 完成后 op12 的 output 可以在 COMMIT7 前可见。COMMIT7 接受后进入 COPY，此时 cmd_ready=0、rsp_valid=0，不能被 REVOKE8 打断；COPY 成功已更新 active/history/epoch，再产生 ACK | COMMIT ACK 后的 REVOKE8 只能清候选，不能回滚已发布提交。reset 可取消控制/validity，不能保证回滚已传播数据；读取身份与上层版本一致性由唯一 owner 保证 |
| S | 普通端口单次请求产生单次读/写应答；写 ACK 必须被 take。loader done 直到 A/B 均排空才到达 | busy 仅表示 feeder，不是 ordinary 是否空闲。普通端口没有 error 信号或初始化有效位；loader 无原生 abort，done_error 属 loader，不能冒充普通响应错误 |
| T | 所有 write 完成后 sealed，仍未发布；commit 后 read 首次有启动等待，后续 holding 消费边沿可 refill，连续 II1；末字消费后显式 release | revoke 仅用于提交前阶段；commit 后不能 revoke 已发布读序列。protocol_error 为 sticky 协议诊断，不是逐命令 rsp_error，也不存在 commit_error。reset 必须与生产/消费双方协调 |

R 的不可中断提交见 [L138–159](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/707878621b2add4ed218b8c43df2e95c9a56e2ba/project/rtl/block_library_v1/block_v1_r.sv#L138) 和 [COPY L246–259](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/707878621b2add4ed218b8c43df2e95c9a56e2ba/project/rtl/block_library_v1/block_v1_r.sv#L246)。S 普通写 ACK 见 [s16k L19–37](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/707878621b2add4ed218b8c43df2e95c9a56e2ba/project/rtl/block_feed_v1/block_feed_s16k.sv#L19)，loader 排空见 [loader L67–108](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/707878621b2add4ed218b8c43df2e95c9a56e2ba/project/rtl/block_feed_v1/block_feed_loader.sv#L67)。T 生命周期见 [L27–69](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/707878621b2add4ed218b8c43df2e95c9a56e2ba/project/rtl/block_v1/transaction6k.sv#L27)。

## 静态检验及仍未解决的内容

本轮静态检查通过：14 个 selected 核心源与输入 source-lock 相符；14 个 latest GET 的 Git blob 与固定观察 metadata 相符，且与 selected 原始字节一致；5 个 P2 文件与真实运行回执相符；七顶层 149 端口重新解析后与候选签名一致；24 个通道、46 个源码范围和 20 个 literal 锚点存在；M/N/E/R 的已列合法操作具有响应分类，T 未出现虚构的 commit_error。

复算入口为 `build_w0_native.py --root <研究integrated> --output-dir <独立输出目录> --observation <w0-latest-get.json> --latest-source-dir <观察头源码树>`。两项可选参数未提供时使用输出目录下的同名 metadata 和 `localonly/latest/`。后续复算者应按 metadata 所列固定观察 SHA 获取原始文件，再核对 blob；不得用移动分支头代替。源码快照 `localonly/**` 只供本地读验，不上传。脚本只读输入、生成 JSON，不联网、不修改 RTL。

仍需后续工作明确：模型实例的数值/shape/lineage 证明、固定程序及 phase owner、存储分配和容量、S/T 重入和共享 route 仲裁、NUM/MEM 能力、完整 profile 组合与负例、时钟复位分配、物理边界及 P&R。系统有外存，本轮不实现或评价外存路径。这里没有将容量不足或缺少 RTL 的合法语义改判为永久非法，也没有将本次静态合同检查称为 RTL 组合验收。
