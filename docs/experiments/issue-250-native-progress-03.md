# Issue250：实际程序与有限数据链

2026-11-11 CST；Refs #250 / PR #251。接续 `issue-250-native-progress-02.md`。总任务继续实施；以下分项通过不能代替原300MHz系统验收。

## 实际执行的闭环

| 范围 | 证据 | 仍不覆盖 |
| --- | --- | --- |
| typed scope/range → 真M短口 → A → S | 102270，6seed×3初态：8组K128/256、ordinary/head、1/2输出组；315真实W64B请求/返回，192 A-S128读，18 record、24结果S128写ACK，独立Fraction/RNE oracle | full-K11008流式输入、任意RESTORE/SPILL、整模型 |
| 真MC PM → LC PM → descriptor → M/S | 102292，18次；MC400B/33指令、LC352B；每CALL23次LC PM读、2次64B参数读取及124周期CRC；8CALL/8RETURN、21184确认读字节、384结果写字节 | 三P并发、系统物理与性能 |
| 寿命/取消 | 102295，两套各18次；缩小namespace强制至少17次真M FENCE，坏cookie不得释放。K256取消后CTX_ABANDON真ACK，再用同context重跑数值 | 全部错误组合、整芯片复位物理资格 |
| MC/LC/M与全局DMA | 102312，18次；6个64B返回槽，331真实backend请求/返回（315 W+16参数），启动purge真实完成；末尾两channel credit/descriptor归零 | 新M切链版本、三P饱和吞吐、整模型 |
| 量化 → 两个缩放头 → 三P真S → 三份A各两用 | 102284，36次（6seed×3初态×2背压）；每case源S读16、三P写48、A读48，第二次A使用无新S读取；头与数据共用128根数据线 | MC/LC程序、M算术、适配器300MHz |
| S暂存释放后真实覆盖 | 102335，36次；72次A使用，576个实际S128覆盖写，旧A载荷/shift仍正确、无新S读取 | 两槽并存、M执行 |
| 同key两K/两份A并存 | 102342，36次；同一S窗真实覆盖、两A槽各两用；COPY progress绑定实际start的generation16/K元素偏移16/session32/ticket32，加原key128；旧prefix期间禁止新S读 | 真MC/LC/M联合、generation重用/rearm、最终物理 |
| 真S32交错复制 | 102294，36次；每次28合法+2拒绝，真实8bank；验证三路N8交错、256值环绕、tail、大列号、未触及字保持、未释放窗口不得启动 | 真G消费者释放与整个FFN outer |
| 两次真G64 → 量化K128 → 三P/A链 | 102319，36次；每case G读64/写32/ACK96、64个两lane G包；两段shift与整128值独立最大值一致；12组历史模型向量、72次A使用 | 上游真M、outer程序、完整新模型质量 |

离线审计入口：`project/experiments/block_local_native/audit_quant_copy_a.py`、`audit_s32_stripe.py`；source/日志/SHA在 `work/YUZE-LU/250/native-services/{copy-a,scatter,gcopy-a,copywin,copylook}`。102278/279/281、102290、102313/314、102328/336等失败保留。102339是仅generation/K的中间通过版本，最终身份扩充以102342为准。102319的 `total_cycle` 包含两段G，`quant_copy_a_cycle` 仅后半段，不能混用。

动态S32 Dot另有真M/LOCAL_S_PACK64/真S/digit packer/80bit merge回归。采用3×5=15个有符号partial，full-K最后只RNE一次，不能沿用理想8partial或免费动态Dot费用；详见 `work/YUZE-LU/250/dynamic-s32/RESULTS.md`。这不是完整decode512数值/性能验收。两种布局K128/N8均实测1256周期/partial，15次即18840周期，尚不含上游输入和最终写回。完整费用回放正修复重复DDR→S预约后重跑；不能继续把8.136179条件行当作真实动态Dot整模型速度。原生有限S128、full-K一次RNE的S32 Dot另立硬件Issue #252，不归纯DP优化收益。

## 物理、带宽与真实费用

G32独立叶宏已通过最终原约束TT300MHz，沿用上一回执。M旧RF-only/prepare候选GPL最差路径仍约5.47ns/5.25ns；新命令回复/transport诊断切开、真实DMA请求输出寄存器虽有18次产品回归，最终物理仍未通过。

新M回复状态约11bit，registered request约68bit新增地址/通道等寄存器，旧地址寄存器复用游标。ALLOC EOP到首请求实测由3变4拍；首次offer多1拍/record必须计入模型。单record后续17/18 beat连续II1；双record轮转实际II2，不能记作连续II1。算术INPUT11/CONTINUE16/FINAL18、serial guard II21不得用未验证gap代替。参考 `M_APERTURE.json`、`REGISTERED_REQUEST_COST.json` 与实际CSV。

DMA原4×64B返回缓冲在相同OOO/三个单返回口压力下约87.2%标称服务。共享6槽（384B总，相比原多128B寄存器）36次原压力达到每channel严格rolling3的4/3 beat/cycle门；8槽也过，4槽共享仍失败。新增128B归MC缓冲面积，**私有S没有扩容，整机存储增量不是零**。每channel32个在途entry只放元数据，不是32份数据缓冲。102315另有真正旧DDR包在途时reset/purge隔离；组合系统仍须重验。

已发布条件性SystemC 8.136179 token/s低于旧9.21564723269门，动态Dot、outer和新M尚未全部回校。硬件变化、费用修正与纯DP收益分开；不宣称达标。

## 原16KiB内的FFN生命周期候选

下表适用于Qwen2.5-3B的hidden2048/intermediate11008候选，不是七模型通用静态切分。KV、残差、外部张量须另在真实资源里计账。

| 每P S128 word窗口 | 用途 | 字节 |
| --- | --- | --- |
| 0–255 | Gate/Up的A16 X；该阶段结束后释放给Down结果 | 4096 |
| 256–719 | Mid A16 tile，t归P[t mod3]，地址256+16 floor(t/3)，每P最多29 tile | 7424 |
| 720–783 | P0的256值gate环；P1/P2可用子窗口放64值片段 | 1024 |
| 784–847 | up环/片段 | 1024 |
| 848–879 | 两次G64形成一个128值Mid S32 | 512 |
| 880–895 | A16 K128复制/LOAD暂存 | 256 |
| 896–1023 | 未分配余量，不能当作新增独立存储 | 2048 |

两个256B A lease、W4×1152B、RF512B、目录/保持寄存器、MC/LC PM仍各计面积。每P32项stride3目录登记本地最多29个Mid tile；不能让每个接收P免费登记全部86项。复制携带当前tile的key/K元素偏移/shift/session/ticket，A两槽各捕获自己的shift。

预期流程：

1. Gate/Up每192列，每P8个N8组×2way恰为16个RF context。完整K逐片供数，真完成后scatter到P0，不把全部11008个Mid32堆进P0。
2. G按64值消费环，集齐128个真实写ACK后量化，tile按t mod3存回现有三份S。环覆盖须等相应G读取/写回和Mid保存的真实释放事件。
3. 86个Mid tile全完成后释放X和gate/up环。Down每次384输出列（每P16个N8 context），遍历86个Mid tile，从owner S真实复制/LOAD到三个P；2048输出列共6个stripe，无需把Mid重算6次或增加全量RF。
4. 每P最多688个最终S32结果占2752B，放进已释放的4096B X窗口；Mid保留到最后Down stripe完成消费。

当前实际P provider仅注册LOCAL_CONTIG完整K128/256、bias0；STREAM_PROJECT_ITER service2在真实LOAD/记录/生命周期接入前继续拒绝。流式S地址是当前tile staging，不是 `base+16*(global_K/128)`；M/A的K128 index与目录/header的K元素偏移显式转换。

单S暂存窗口在最后一次真实S读取完成、匹配LOAD回执与COPY写方排空后可释放；102335/342已用真实覆盖旧S证明，A内部载荷仍可继续使用。`A quiescent` 不是槽FREE，必须另查 `live_slots`；释放S窗使用 `source_reads_drained` 与匹配的成功LOAD身份，不能仅凭COPY写ACK或A命令接收。

同key不同K会保留旧COPY prefix=16；新LOAD必须将progress与当前window的generation/K/session/ticket逐项匹配。`early_copy_epoch_3p` 在真正COPY start握手时绑定身份，与底层ACK prefix清零同边发生，113bit显式身份寄存器计入LC面积，不增加payload SRAM。目前generation16耗尽只允许系统reset，尚无经过全链排空验证的namespace rearm，不能宣称可无界循环。

## 后续

继续实际S窗口复用、service2/outer及新M+全局DMA，回校时间/带宽/动态Dot，补足性能并迭代最终物理。五类Block保持独立叶宏、局控/适配器的控制归属；不把新服务封成五个大硬框。真实能力与状态转移供DP/greedy共用。上传PR、分项PASS不结束目标。
