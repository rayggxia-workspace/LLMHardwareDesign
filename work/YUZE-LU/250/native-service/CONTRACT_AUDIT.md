# 原生服务回校边界（Issue250 / PR251）

这是时间模型的修订台账，不是整模型 RTL 或系统物理验收。旧 `native-s/`
与 `performance/` 的文件、费用和结果均保持原样。

| 服务或资源 | 已取得的边界 | 本轮如何使用 / 尚缺什么 |
|---|---|---|
| DDR | 原模型 `Memory` 有两条全局通道；每条通道共享一份32 beat credit，另有32个 descriptor 信用 | 保留51.2GB/s总预算、64B beat、所有流共用通道。bus读与logical读分开。尚非板级DDR实测。 |
| G32纯计算 | 102078/102104：128值68拍，包括最终Mid S32 RNE | 不能再外加旧 `NV_MID=1`。 |
| G–S128 | 102104：96B有限寄存器、64读/32写；首S请求到最后实际ACK107拍，时钟LC最早take108拍 | 替换旧“1536B批量S访问 + 68拍”。后续Mid A16量化独立，已用102168真服务95/60替代旧66+批量S费用；不是68+96。 |
| 新M普通组 | 102118：8拍A/W输入、1个K128 RAW、1次RF/RNE；exec→输入ACK9拍，exec→结果12拍 | `measured-m-core.json` 冻结18份CSV的校准行及每份原CSV SHA。12拍不含独立CTX控制、guard、S、MC/LC序列化。 |
| 新M head组 | 102118：8个K16 RAW、8次独立RF/RNE；同样exec→结果12拍 | 每次RNE事件都保留，不能把head合成一次RNE。1152B记录与128B scale metadata保留。 |
| A tile | 2×256B真实寄存器；`private_a_tile_frontend`只有一个共享inflight S请求，正常RTT2，连续请求间隔4；102140已测单LOAD66拍 | 两个LOAD同时接收会轮转两tile；不是两个独立64B端口。本轮明确前LOAD终结后才接收第二LOAD，M对前tile重放可与后tile装载重叠。源数据和shift都有效才允许LOAD。 |
| early copy | 一次U128响应送入3×16B真实保持槽，每个槽等各自P ACK；下一响应可停在既有U响应队列 | 旧模型3个worker各重读U一份，和真实RTL不同。本轮按一读、三写及三条ACK建模；布线仍需要3条物理通路。 |
| W / RF / 结果 | 4×1152B W银行、16×8×S32 RF、两个独立32B结果槽；root102160实装6 issued tickets | 6票总寿命持续到真实result terminal，不在INPUT早释；106bit新增metadata明确计入控制。4票作为负对照。W以102172 INPUT EOP11早释，结果槽保持到S/外存完成。 |
| Down状态 | spill每个128值Mid扫完整256组；条带将22,016B Mid分到原3S，固定16RF输出跨完整K | 产品分支独立收RESTORE8flit13拍+32B S读、SPILL14拍；16scope缓存若被86N8/P扫描驱逐还须重新BEGIN。旧run08--12的低费用只作历史参考。 |
| 动态A scale | root已实做两个每P约51B目录，X stride1/Mid stride3；接收端只给当前2A lease关联shift | source32项可放29/29/28，接收端不能存全部86项。COPY两128flit metadata+真实数据/scale ACK尚待联合回校，4/8拍只做敏感性；S512B宽目录只作替代负对照。 |
| MC/LC产品接口 | M128物理aperture102172真RTL：CONTINUE EOP14、FINAL EOP16、INPUT EOP11、下一EXEC最早前RF EOP+1 | 不再拿core12冒充完整服务；M物理尚可能需要流水变化，300MHz资格未冻结。完整ALLOC、BEGIN/W预取重叠、母控PM和outer-scope FSM仍需联合时间线。 |

新增K-major服务只接受静态 `layout=0, row=1, batch=1, A16/W8,
K%128=0, N%8=0`。完整输入仍进原16KiB S，readonly A一次装载256B后供
当前最多16个输出context；下一K或下一组覆盖前检查所有引用。私有SRAM
不增加。若一次行不满足容量约束，拒绝该provider，不暗增S。

## 必须继续保持“不覆盖”的服务

| 服务 | 当前实际证据 | 缺口 |
|---|---|---|
| 动态QK/AV `layout=1/2` | 历史时间模型仍用旧S32×S32 streaming常数 | 新M为W8A16静态provider；分解/新动态精度的算术、周期、KV字节及RTL必须另验，不能原价绑定。 |
| E32向量、RoPE、reduce、量化 | 历史模型假定4×S32 lane及有限中间上下文 | main `block_v2_e` 普通运算是8×S16；op13只做S32→S16 RNE。S32全向量服务、实际端口/II及300MHz需单独实现/验证。 |
| NExp | iteration4实测补充服务14拍/8值，输入语义signed low16 of S32、U16输出zeroextend | profile明确**不含**外侧vector_region的S/cache/DDR/E。未发现重复S费用依据，不能删除它；也不能把该低16格式叫通用S32 exp。 |
| NFactor / RMS / Softmax | main N有独立U64 divider/root等能力，历史组合费用保留 | 从模型S32数值合同到真实N指令序列、归一化、舍入及端口的服务资格仍缺。独立N宏通过不等于这些组合通过。 |

整条完整trace会保留上述服务的旧候选费用以便连续诊断；输出同时列
`whole_system_calibrated=false` 与明确缺口。token/s是有这些条件的时间模型
结果，不是已闭合硬件吞吐。本文不把硬件新增能力或费用纠正计作DP算法收益。
