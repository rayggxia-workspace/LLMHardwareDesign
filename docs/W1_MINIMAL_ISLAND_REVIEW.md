# W1固定DOT8可变tensor首切片：独立源码与运行证据审查

Issue151 / PR152；parent `bfe62ad179af72aef591622aa5c7a000f5d8b681`，叶源`707878621b2add4ed218b8c43df2e95c9a56e2ba`。审查者只写drafts/review，未修改RTL/TB/正式树/远端/服务器/ref-project，**没有执行仿真**；实际ModelSim运行由根任务完成，本审查只读回源码、TB、receipt和日志。

**结论：已审14项合同门，在固定W1最小切片范围内未发现未关闭的阻断问题，可接收相应有界功能证据。**这不是外部独立PR批准、完整W1阶段完成、P2整阶段验收、完整profile或物理资格。

## 1. 绑定的最终版本与真实运行

| 文件 | SHA-256 |
|---|---|
| block_w1_mst_top.sv | 4d421e333ac4f176c2a9d5df76f54aa41fd76068493ef1465a06e7a8a2cb1b08 |
| block_w1_mother_rom.sv | 5c7c631d758808fcfbd55e6303d51b50f89172080abbf4597b8d43923eeffa78 |
| block_w1_mst_tb.sv | 178318886fe1b91d8fed13c6b6870663a77dc057b6ace8b1b531c0fa9799daac |

已核对以上draft与integrated正式文件、`runs/w1-r03/source/`快照及r03 receipt的输入SHA全部一致。r03的28个唯一`CASE_PASS`与receipt集合一致；`PASS_W1_MST cases=28 cycles=4422`存在、无FAIL/Fatal，全部工具退码0。

- r03 receipt SHA：`614b5513966449a5129367eb07cb742aaabc9f37563bc9e87762dbaf6cd00152`。
- r03 simulation日志SHA：`e634abc7662737167635fac53cd6bc1fc61b90c022a584fe5e0b9dcb4be39d4a`。
- 日志位置：`runs/w1-r03/simulation-block_w1_mst_tb.log`。28个标签属于一个新TB进程，不是28个独立仿真进程或全域覆盖率。

根任务同时运行旧P2回归`regression-r01`，helper6/MST13共19标签、各工具exit0；只证明原P2所列范围回归。N/E/G/R仍只有编译门，未借本轮获得功能组合资格。

## 2. 14项有限合同核对

| 检查 | 源码与独立TB要点 |
|---|---|
| 输入8次接受＋8次ACK | input_index只在INPUT_RSP收到helper响应后推进；单在途由状态及helper保证；最后第7索引ACK才frame_stored。TB独立数ingress accepts和真实native S ACK，末拍ACK停顿期间不准start |
| padding和输入锁存 | canonical_input将第0拍高64与第1..3拍写零，held_data捕获输入；TB先污染四个A字RAM并发送非零用户padding，再验真实写入及读回，56B不依赖reset |
| start/新frame | start_ready要求frame_stored、未launched及mother ready；early pulse不排队，held start跨最后ACK后仅接受一次；RUN/DONE期间in_ready低 |
| frame busy与RUN busy | busy是frame_active或mother_busy，部分/完整未start frame也占有生命周期；最终TB在每入口accept后及完整待start时直接断言busy/in_ready |
| literal移除 | ROM slot2为INPUT_CHECK，直接检验marker/launched，不写literal A/B。TB禁止RUN期间再次写448..455，五向量证明实际入口数据未被覆盖 |
| 单S owner | 入口和RUN只经同一block_p2_s_ctrl；TB只许一个ordinary pending，逐请求/ACK检查地址、write echo和读出数据 |
| M状态/数据分开 | CLEAR/SCALE及EXEC响应只检查状态；M_STORE的op3 payload保存后写S并收ACK才读下一包；非法EXEC一拍注入后不发布输出并可恢复 |
| T结束顺序 | 四字按index0..3/last输出；反压时data/index/last保持；成功done前TB要求四字都take、T不busy且实际RELEASE一次 |
| prestart abort | 部分frame、已写未ACK、完整未start都清frame不造task done，恢复须新8拍输入 |
| RUN/DONE abort | RUN协调reset并产生保留error；已有DONE不因abort撤valid或改error，abort+done_ready公开握手严格计一次；已消费prefix不回滚 |
| hard reset/重用 | 清控制/marker/完成，不回滚RAM或外部已接受数据；测试输入、RUN、输出prefix及DONE不同位置reset后均重新完整frame恢复 |
| 分阶段计数 | 正常frame+RUN16笔S（入口8写、RUN4写/4读）；RUN区间8笔，M7命令/响应、A/B各1、loader1、T4及release。没有沿用原P2从start数16的错误边界 |
| TB独立oracle | 点积只由TB-owned A/B数组计算，再与W0五套literal预期逐列交叉；覆盖131072/-130048两端、全零、原P2和不同列，不用DUT结果生成期望 |
| 有限范围 | shape/address/bank/factor/程序固定、只tensor可变；没有bootload、通用运行配置/handle/epoch接口或全局rollback；仍只有M/S/T |

具体文件/行锚点及每项证据范围见同目录`w1-independent-review.json`。源码审查加有界仿真不是全状态形式证明；source marker还依赖真实同步S/helper及协调reset合同，不外推到未设计的异步MEM晚响应。

## 3. 本轮发现与修复，失败记录保留

**REV-C01，声明顺序编译失败。** 根任务首轮`w1-r01`的vlog报告leaf_reset/service_rsp_valid在声明前使用以及重复声明，共4错误、compile exit2，没有功能case。RTL作者移动声明并改显式assign；接口/功能未改，最终top SHA为上表。r01日志/receipt保留，没有覆盖或称通过。

**REV-T01，本审查发现的关键测试覆盖缺口。** r02旧TB把`reset||leaf_reset`作为整个monitor的豁免，因而abort期间不计公开DONE take；finish_job又豁免abort_on_done时的exactly-once计数。虽然RTL的DONE分支按源码正确，旧测试不能充分支持同拍公开握手“只一次”的结论。

测试作者按反馈修复：DONE稳定性和公开take只受hard reset豁免，abort+ready仍计数；所有finish均断言`old_takes+1`；另外补frame部分/完整待start的busy断言。本审查读回相对r02的diff确认只加强监测，根以最终TB SHA重跑r03成功，故该覆盖缺口在本切片内关闭。

运行历史分别保留：r01编译失败；r02旧弱计数TB真实28标签/4422周期PASS；r03强化TB真实28标签/4422周期PASS。r02不能重标成强化测试通过。当前无未关闭的DUT功能阻断，但这不构成任意未覆盖路径的保证。

## 4. 总轨迹与正常事务范围

r03总计inputAccept240、ingressReq239/ACK237、resultReq97/ACK96、readReq96/ACK96、Mcmd176/Mrsp175、Ttake92。总轨迹含显式pre-native取消、已接受但尚未消费的ACK/响应被协调reset丢弃、以及已消费输出prefix，不能把总差额当正常路径守恒或静默错误。所有正常批次的独立nominal_counts才要求上述16S、RUN8S、7M和T4/release；异常路径按其位置和不回滚合同判断。

## 5. 未完成边界

本次是W1固定DOT8/地址/程序、可变tensor**首切片**。完整W1的共同capture/gather/serializer、其他shape/格式/scale/地址profile、N/E/G/R适配、无reset drain、一般跨岛/MEM/NUM、通用phase/版本/transport和完整程序/物理均未完成。原P2矩阵中S16/append/op5/op12、多bank/loader长竞争/reuse_b、全部T非法/长度、随机停顿/epoch等剩余门不因本切片被关闭。

审查建议只接收与精确源、28case和上述合同对应的功能证据；整体W1、P2、完整F/A/D/H/X以及Issue/PR验收状态由根任务按实际证据和要求的外部审查另行记录。本报告不是PR批准，也未代根执行/声称仿真、上传、合并或看板同步。
