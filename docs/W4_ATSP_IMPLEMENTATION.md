# L4-A-TSP：H1024双行残差保存、回放与T复用

Issue151 / PR152，负责人Melodydt；2026-11-02。本轮输入7aba36a0，实际服务器源码 `d1efc16b654d0d11f7a833cc92f57ac00ae31740`。首轮r01/Slurm **95277** 在node1、c64、8CPU自然 **COMPLETED 0:0 / 00:00:57**；Verilator5.042严格顺序30CASE和9份实际数据流长度/SHA全部通过。当前仍L4，这只接收残差路径切片。

## 1. 为什么先做这一段

[真实Qwen3 A候选](QWEN3_SQ2_ATTENTION_PLAN.md)需要在S16KiB同时保存Norm/context/work；两行原X各2048B，额外4096B不能免费留在同一S。已有T6KiB提供有限事务存储，因此先把原X真实spool到T，释放S原区域给head阶段，Wo完成后再回放原残差。此机制也是未来完整A所需的容量/生命周期前提。

**真实维度，合成数据，Wo外部切口。** 新top用H1024/Sq2/S16Fin10，实例真实S_macro、T(transaction6k)、E及已有S helper/E controller。没有M/N、QKV、RMS、RoPE、head循环或Wo矩阵计算，Wo由外部128bit流提供；本轮不是完整Attention、训练参数质量或L5通用跨岛验收。

## 2. RTL改动与原理

新增 [block_w4_atsp_top.sv](../project/rtl/block_connection_w4/block_w4_atsp_top.sv) 与独立 [TB](../project/tb/block_connection_w4/block_w4_atsp_tb.sv)，继承46份RTL/TB/include全部原字节不变。没有修改已验收叶宏、S helper或E controller；所有新增FSM、capture、MUX和元数据检查都在宏外，需要在未来M1–M10底座冻结前预制，M11/M12不能新增这些有源逻辑。

| 顺序 | 实际动作及完成门 |
|---|---|
| 接单/存输入 | 接收job generation；X token-major256字写S0..255，检查generation/index/last。第256个实际S写ACK后才input_stored/start_ready |
| 保存原X | T BEGIN256(owner1)，实际读取S[g]与S[128+g]，写T[2g]/T[2g+1]，全部写完COMMIT并进入READ_HOLD才spool_saved |
| 释放原S用途 | HEAD_HOLD不take T；work接口可真实覆写S0..255，逐写收到真实ACK且work响应消费后才允许resume；work优先于同拍resume |
| Wo切口 | 每组接Wo0g/Wo1g，严格检查同job/index=2g+row/last；分别写S256/257并ACK后才回放原X |
| 回放和残差 | T当前字先捕获到128bit holding，真实写S258、等ACK后才发E op0/shift0/count8。E从S读取Wo与原X、做有符号S16饱和加法，目的写Sg或S[384+g]；目的ACK及E响应退休后才复用 |
| T第一次释放 | 全256个原X字消费且全部E目的写ACK完成，实际T RELEASE；下一拍开始第二个BEGIN256(owner2，同generation) |
| 输出与终态 | 从最终S两行token-major读写第二T事务，COMMIT/DRAIN；256次host take之后实际RELEASE才成功DONE。DONE保持到ready，正常无需reset即可接下一job |

顶层只有一个128bit payload holding，没有新的原X/Wo/context/结果私有数组。S/T自身及已有helper/E控制器的holding另计，不能把128bit写成完整岛面积预算。普通S口只有local和E两类owner，同一helper承担读和写ACK；E从请求接收到响应消费全程持有该普通口。

完整 [端口、生命周期和计数合同](rtl-contracts/ATSP_PORTS_AND_LIFETIME.md) 明确本切口不是未来完整head work端点或物理pin冻结。新增X/Wo元数据只负责任务身份/顺序，不是通用运行时数据类型系统。调用方仍须协调generation，当前不提供全系统防回绕和任意旧包排空。

## 3. 取消、错误、背压与前缀

job握手后即拥有完成义务，输入未完/prestart/head/replay/output的abort或错误都会返回同generation的held errorDONE；无job abort不造DONE。坏X/Wo元数据先拒绝计算，不发该坏拍S请求。输出及DONE在正常背压期间保持值和元数据。

错误采用协调reset S/T/E/helper并作废本轮在途状态；这是本地同钟域切片恢复，不是无reset排空或任意外部MEM晚响应隔离。S已经接受的写不回滚，host已接受的最终输出前缀也不回滚。done_words记录0..256个实际最终输出握手，done_partial=error且words非零。硬reset取消任务，不补造DONE。

work错误先保持work错误响应供消费，然后进入errorDONE；abort/reset可显式取消该通道。原生S没有error pin，TB通过force helper错误验证协调路径，不声称新增了真实S错误检测；E错误采用真实原生非法op14路径。

## 4. 实际验证与数据证据

[冻结TB合同](../work/Melodydt/151/atsp/atsp-tb-contract.json)绑定30个CASE严格顺序、TB及top SHA、9个编译输入和9dump映射。[独立golden](../work/Melodydt/151/atsp/fixture-contract.json)直接逐元素计算signed16饱和add，不复刻FSM：plain/dense无饱和，saturation含640个饱和元素。Python16个字面边界及65536个零恒等+65536个端点检查通过；不是模型量化质量测试。

| 已实际验证 | 范围 |
|---|---|
| 完整数据 | plain、dense、saturation各两行完整2048个S16元素；最后再完整dense无reset恢复 |
| 真实S覆盖 | plain帧通过work实际覆写S0..255并ACK；随后所有原残差回放/结果仍正确，未向RAM层次直接预填 |
| 实际流 | X只在in握手写dump，Wo只在wo握手原序写dump，输出只在out握手写dump；每份4096B，3×3=9份外部SHA核对，不重排Wo掩盖错序 |
| 时序/所有权 | 最后输入ACK前不start，work ACK/响应前不resume，S258 ACK前不E，E最后ACK前不release，同T两个lease串行，输出/DONE保持 |
| 故障/恢复 | 接单后多阶段abort/reset、旧X/坏Wo/坏T元数据、helper错误/原生E错误、输出前缀保留、DONE+abort+ready和正常无reset复用 |

正常每完整job实际计数断言：S请求=ACK=2048+work写数，S读1024、写1024+work；E256服务；T两BEGIN/两COMMIT/两RELEASE、512write/512take（raw256+输出256）。plain全覆盖时work256，所以S2304=1024读+1280写。不是所有fixture×所有故障组合的穷尽矩阵，也不是30次完整模型推理。

最终原始全局统计为 `cycles=118355 jobs=30 X=5640 Wo=1805 Sreq=21783 Sack=21782 E=1794 Ttake=2821 Trelease=11 host=1025 done=27`。其中混合早停、硬reset和注入错误，Sreq与Sack相差的一个请求是已取消在途，不能用该混合总数替代上述成功帧的严格对称计数；30接单中三次硬reset不产生DONE，其余27次DONE，和合同一致。

[实际服务器回执](../work/Melodydt/151/atsp/evidence/runs/r01/results/run-receipt.json)记录全部argv、版本、输入及输出SHA。[证据索引](../work/Melodydt/151/atsp/evidence/evidence-manifest.json)与本地实收核验了14份文本、13份源码输入和9actual流；原始生成数据/二进制/build留本人服务器，归档SHA为 `1b2b7b5407e5b1d52c13430a57aae772c5d4c84a23268fbd65a2f3677259fdec`。首轮r01即通过，没有提交失败仿真或被隐藏的重跑；本地下载脚本生成时有一次引号语法失败，修复后实收，不影响服务器输入或结果。

编译/仿真exit0，Verilator5.042、g++11.4.0、容器Python3.10.12；`--assert`启用，`-j8`构建/单线程仿真，Slurm8CPU。保留全部 `37` 条警告（`TIMESCALEMOD=8, WIDTHTRUNC=16, WIDTHEXPAND=13`）；只有-Wno-fatal，未关闭类别，非lint clean。新top除timescale提示无算术位宽警告；原T索引和TB整数比较/赋值警告保留，无本轮叶宏修改或物理重验。

## 5. 位置、复现与下一步

服务器yuzelu@10.129.166.172；任务 `/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/atsp-7aba36a-20261102`，输入input-r01、结果runs/r01/results、日志runs/r01/logs和slurm/zenanyan-atsp-95277.out/.err。源归档和实际submit-r01.sbatch/manifest都已留存，完整argv见回执；重新执行必须另建input/output与job，不覆盖r01。

本地仅Python静态/数学与证据检查，RTL只在服务器。仓库根运行 `python -B -X utf8 scripts/check_project.py`、`python -B -X utf8 project/experiments/block_v2/check_release.py`、`python -B -X utf8 scripts/check_w5_if.py` 与原模型准入检查；结果见[本轮交付检查](../work/Melodydt/151/atsp/final-checks.json)。叶宏交付仍六叶/R未完成，旧24真实目标保持GAP，旧运行锁保持原版本。

下一主攻 **L4-A-H2：H1024保持完整输入、D128一个KV头服务相邻两个Q头**，含Q/K逐头RMS、split-half64 RoPE真实gather、因果count1/2和PV；再KV8/Q16完整context/Wo、真实A→F。数值/官方框架/W8为独立待完成门；L5母控/通用storedACK、MEM、R/D/H/X和共同底座/M11永久绑定及物理均未完成。不能以本轮成功宣布整个L4退出。
