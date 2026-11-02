# L4 A8：有界 QK → Softmax → PV RTL草稿

输入parent `1d722477564e14f7dc93e39ce8e28b8e2d150cb0`，native锁 `707878621b2add4ed218b8c43df2e95c9a56e2ba`。新增独立 `block_w4_a8_top.sv`，复用未改的W4 N controller、P2 S helper和native M/N/S/T。没有E/G/R实例，没有修改旧P2/W1/W3/W4文件。本稿没有compile/simulation结论；按本轮规则，后续RTL仿真在服务器Verilator执行，独立oracle/TB和root runner另行记录。

## 算法与整数合同

一个query、一个head、8个有效key、D8、8个输出channel。Q/K/V为S8 Fin7，输入内容可变，shape/地址/op/scale固定；不含QKV/输出投影、preNorm、RoPE、GQA、mask、残差、多head/group或真实模型完整A。

QK的第key列为dot(Q[dimension],K[key,dimension])，raw Fin14。M精确乘整数11585（`round(2^15/sqrt8)`，有界固定近似，不是数学精确1/sqrt8），left_shift0。op5按S16模式RNE19得到score Fin10。Softmax固定mode0/count8，用现有N控制器先整组统计，再保存/重读exact U16 EXP，输出S16 Fin14非负概率。概率码和不要求恰好16384，必须遵从native整数factor/RNE语义。

PV使用A16 Fin14概率和B8 Fin7的V，raw Fin21，M factor1/left0，op5 S16/RNE11得到最终8S16 Fin10。没有额外通用NUM；缩放/RNE来自原生M，外侧只是锁存与按既定格式拆拼。

| 阶段 | CLEAR | SCALE op4/index0/data | loader A/B | EXEC op10/index0/data | 两个op5的data |
| --- | --- | --- | --- | --- | --- |
| QK | native op6 | 11585=`0x2d41`，shift0 | base448/452，A8/B8 | `0x9884` | `0x113`（S16、right19） |
| PV | native op6 | 1，shift0 | base464/456，A16/B8 | `0x9885` | `0x10b`（S16、right11） |

每次loader固定bank0、rows1、tiles1、reuseB0；op5 index0取前4列、index1取后4列。每response仍为4个S32载体，取各slot低16后按列顺序紧凑拼包；不是从S64裸截位。M的CLEAR native opcode是6；top的 `MC_CLEAR=0` 只是阶段编号，不可混为native op0。

K输入必须按 `byte_offset=8*key+dimension`；V按 `byte_offset=8*channel+key`，不能把普通token-major V未经布局处理就当本ABI输入。数据由host提供该固定布局，不存在运行时转置服务。

## 存储、对齐与真实ACK

| S字地址 | 内容 |
| --- | --- |
| 448..451 | Q预留4字，448低64为8S8，其余56B实际canonical写零 |
| 452..455 | 64个K字节，key-major |
| 456..459 | 64个V字节，channel-major |
| 460 / 461 | score8S16 Fin10 / exact EXP8U16 |
| 462..463 | unused，不读取、不依赖旧值 |
| 464 | probability8S16 Fin14 |
| 465..467 | 三字实际零padding |
| 468 | output8S16 Fin10 |

loader的A/B base都要求低2bit为0。原拟prob462不合法，已改464；不是仅把低位丢弃。PV wide A读取464..467的完整512-bit容器，因此三个padding字必须真写并ACK后才发loader。预约448..468共336B，其中462/463不用；19个真正写入地址共304B。S实体容量未变。

入口12×128=192B，Q8B+K64B+V64B为136B有效，padding56B真零。每拍先捕获canonicalized字，再经唯一helper写S并消费ACK；12个ACK全部完成才input_stored/start_ready。RUN不能再接输入，pending DONE也不能覆盖当前帧；完成被消费后新帧须重新12拍。

固定顺序：QK CLEAR/SCALE→loader→EXEC检查状态→op5两half→score460写ACK→N服务→prob464写ACK及N rsp消费→padding465..467逐字写ACK→PV CLEAR/SCALE→loader→EXEC检查状态→op5两half→output468写ACK→真实回读468→T BEGIN1/WRITE/COMMIT/外部TAKE/RELEASE→DONE。

普通S成功单帧23请求/23ACK=19W+4R：入口12W、score1W、N服务2W+3R、padding3W、最终结果1W、T回读1R。RUN为11笔=7W+4R。另有M10命令/应答、2loader、N6命令/应答、T1字take和独立release；loader私有宽读不算普通S事务。

## 控制、错误和复用

本地固定FSM保持LOCAL0或N3唯一普通S owner；N group从req到rsp消费持有owner，不能跨phase交错。helper最后写ACK已在N完成前退休，切回LOCAL后才写padding。所有native命令ACK/EXEC状态与op5数据分开处理；计算失败不把状态字保存为score或输出。QK的scale11585不会依赖CLEAR清除：PV显式重新SET_SCALE1。

busy从首个输入接受至DONE消费，含部分帧和已存储等待start；早到start pulse不排队，held start在ready后只接受一次。done_error/done_saturated保持到take。sat汇总N和M已退休响应，原生错误/fault_rows则进入error DONE。

N runtime error的poison由top顺序internal_reset协调N/Nctrl/S/helper/M/T复位，禁止悄悄复用脏context。prestart abort丢frame不造done，RUN abort保留一次error完成，已有DONE遇abort保留结果且ready可同拍只消费一次；hard reset取消valid不造完成。已接受RAM写或外部消费前缀不回滚。leaf_reset只依赖reset、abort和寄存internal_reset，未用error/ready构造组合反馈。

## 独立测试观察点

公共ports同F8。实例为 `u_s_ctrl/u_s/u_m/u_n_ctrl/u_n/u_t`。state编号沿F8：M_CMD5/M_RSP6、LOAD_CMD7/LOAD_RSP8、N_REQ19/N_RSP20、T13..17、DONE18；projection0为QK、1为PV。`m_phase`的CLEAR0/SCALE1/EXEC2/READ0=3/READ1=4。恒1许可点保留 `permit_s_req/rsp`、`permit_m_cmd/rsp`、`permit_load`、`permit_n_req/rsp`；产品没有这些runtime pins。

独立TB应检查布局转置、非零脏padding、S464对齐、11585整数缩放及两次RNE、EXP原样保存/回放、prob码作为A16而非S8、23事务、M10/N6/2loader、输出与DONE背压、错误无T发布、Npoison协调恢复、重复新帧和Trelease门。该小链是主线四Attention计算链的有限进展，不是主线五或完整A_plain退出。
