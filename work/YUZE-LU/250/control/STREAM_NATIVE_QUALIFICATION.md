# 固定 staging 窗口与真实 COPY 的原生闭环

Refs #250。`p_native_stream_record_executor.sv` 是独立候选，保留已验收的 contig executor、原 A frontend 和 serial guard。typed provider 仍拒绝 service2；本回执没有把 K128/256 的 record 发生器写成 whole projection/FFN 外层已实现。

| Slurm | 真实覆盖 | 结果 / c64 6×10分配的实耗 |
|---|---|---|
| 102343 | 固定256B S窗口；完整key/gen16/K/session/ticket隔离旧prefix；LOAD背压、覆写S、真实M数值 | 18 PASS；9s elapsed，20.612 CPU-s |
| 102346 | 加入 early-cancel 后同正例回归 | 18 PASS；9s，20.675 CPU-s |
| 102347 | COPY只提供4个S128字时取消；真M CANCEL/DRAIN/DROP，然后同上下文重做K256 | 18 PASS；8s，20.546 CPU-s |
| 102353 | 真实U/P四银行S、fallback量化、128bit Header/RX、版本化COPY、A→M→S | 18 PASS；9s，22.470 CPU-s |
| 102359 | 真COPY在prefix4处halt，源/link/S/A/M排空，RX取消释放，再同owner/context数值复用 | 18 PASS；8s，22.000 CPU-s |

102353 每 trial 有八个限定范围、18个 M record、315次W64请求和返回、24个真实结果S128 ACK。十二个K128输入由U的S32源经真实量化器计算 max/shift/RNE，16个真实写ACK后才能形成Header。Header和COPY共用原128根数据线；总24个Header flit、192次COPY源读、192个目的写ACK。P目录的shift来自实际RX，A读取受对应COPY的真实ACK prefix约束。

数值输入构造明确：整数oracle原来使用 `Aold × scale × 2^8`；本回归给U真实S写入 `S32=Aold×256`，量化器实际选择shift0，输出A16=`Aold×256`。两者表达同一数值，M按真实shift0运行，与独立Fraction/RNE整数oracle逐位一致。shift不是host直接宣告就绪；完整模型的真实上游producer仍要另验。

LOAD证明由真实16次S响应形成，携带完整key、COPY gen16/session/ticket/K以及独立A slot/gen/shift。它是现有前端的一份有限保持回执，没有新增FIFO。成功回执和COPY/link/S排空后，RX释放S窗口，此时A内部槽仍live。随后真实覆写192个staging S字，原A仍能正确完成所有M消费；`source_reads_drained`与A FREE始终区分。

102359 中，COPY halt后仍保持已offer的VALID直到接受，真实返回与目的ACK排空；未形成完整A的前端返回匹配的error LOAD terminal。P正常取消让当前唯一W record完成FILL（最多1088/1152B），再用真实bank/gen/record发CANCEL与DRAIN，清理真实RF上下文。没有虚构EXEC/INPUT/ABORT或SACK。然后相同Akey/RFowner/context重做K256正确。每trial合计51个W64请求和返回、36次A读（取消4+重做32）、2个最终S ACK、4个range票退役。当前正常取消会继续取完这一个W record，成本明确保留；未注册partial W截断和其字节计数。

接口及位宽见 `project/experiments/shared_x_control/p_native_stream_contract.json`。额外current-window元数据86bit，early-cancel会话/标志67bit；无新增私有SRAM、A payload或结果FIFO。量化器、Header TX/RX、COPY113bit身份、原有每P16B保持和S仲裁都要另计实际有源面积。宽身份只是局控内部总线，不能直接扩成宏或母控大量pin。

完整源/向量/日志/CSV/银行模型存于run61–68原SHA的≤1MiB exact parts，所有失败保留（102341脚本误名、102350/352严格测试端告警，未绕过）。`followup-*.json`记录实际CPU及原始路径，`sacct-61-68.txt`记录完整accounting。功能时钟10ns，不是300MHz物理验收。

仍未覆盖：typed service2与完整outer、fullK11008流式执行、三P吞吐、流式输入与真实MC/全局DMA同次联合、五类provider、COPY16bit通用rearm、紧急raw ABORT恢复、布局布线、能耗/token/s。COPY wire generation仍是16bit，不能靠改名32bit掩盖ABA；耗尽须先真实namespace协调排空与rearm。

后续固定 stream COPY 为不预取下一源字的配置（源737784597，root a424fd244 等价）：P也是COPY源时，原预取会让下一源读响应堵住旧目的写ACK，形成同S有序响应环。现在只有16B hold空闲才offer下一源读，无新增payload。旧单元参数默认1保持历史资格，stream epoch wrapper显式0。102370实际量化/Header/COPY/M/S 18 PASS（9s，22.586 CPU-s），102371实际中途halt/取消/复用18 PASS（9s，22.026 CPU-s）。seed1正例4997→5285周期，取消1055→1103，费用如实保留。run69–70完整源/日志/CSV/向量以原SHA≤1MiB分片保留；没有将原配置的吞吐或物理资格移交给新配置。

后续 typed2 与真实程序（run71–85）：`NATIVE_STREAM_A16` 只接受service2，使用root已验收的 decoder `ALLOW_STREAM_A16` 明确选择；默认及contig仍拒绝2。102385八个K128/256范围通过真实量化/Header/COPY/A/M/四银行S。102390及修复后102395各18 PASS，从真MC16KiB SRAM PM（400B/33条）到真LC1KiB PM（352B/3条），实际128B DDR取参、内联CRC、typed2、真源数据链和同一global DMA（6个64B返路槽）联合。每trial8 scope/18 record、315个W64+16个取参64=331个真实外存请求与返回、24个结果S ACK、seed1 7618周期。外存器件由有限peer模拟，源S32由显式fixture写入，只有1P；不把这条回执外推为模型吞吐或五类全覆盖。

真实长K功能：102391发现executor会在S staging已凭真实LOAD证明释放后再次查询已释放的RX shift，旧持久目录短测未暴露。195575ee7让已有6bit LOAD shift随A lease保留，JOIN、EXEC和A replay校验不依赖旧RX窗口。102392 18 PASS：单scope K11008/N8、同256B staging复用86次、真实quant/Header/COPY/LOAD/M/S，目的只消费当前匹配RX metadata、无86项目录。每trial有86量化、172 Header flit、1376 COPY源读与目标ACK、86 LOAD证明、1376覆写字、1376 A读、1462 W64请求与返回、2最终S ACK；独立合成W8/F16/RNE oracle一致（seed1 32381周期）。这一项不是完整checkpoint、三P流水、整FFN外层或目标性能。

M2候选独立于旧串行：102405 18 PASS实际四银行S，响应为M peer；INPUT EOP后可发第二条，仍持两完成身份/原2×32B结果。RF2先到可保留但按首命令顺序写S；只取消第二条不阻第一条FINAL双SACK；early RF error保留owner直到真实INPUT或ABORT+drain；error ABORT只有零cursor、不能恢复。`m_dual_exec_issue.sv`从两份guard metadata直接形成真实2-flit EXEC，侧命令仲裁保留已offer帧，无新增payload。102407 18 PASS已接实际M2 V2（21fac77）与真实P/COPY/S，8范围/18 record/315W64/24S ACK，seed1 5281周期；该P fixture仍只有一份准备中的record，没有测出双发收益。双prep与三P外层仍未完成。

run71–85保留首轮严格width/launcher错误、长K metadata寿命失败、实际MC mixed-reset fixture原策略以及所有后续通过源和波形文本，按远端原SHA分片；完整作业accounting见 `sacct-71-85.txt`。功能10ns，不是300MHz物理、能耗或token/s结论。

## 两份有界准备与 K2048 Gate/Up（run86–92）

| Slurm | 实际功能证据 | 结果 / c64 6×10分配的实耗 |
|---|---|---|
| 102412 | 同一 K128 tile 的两个真实W准备、M2独立完成、量化/COPY/四银行S | 18 PASS；10s，23.265 CPU-s |
| 102417 | 两W已满、未EXEC即取消；首INPUT后只取消第二条；同owner数值重做 | 36 PASS；12s，25.660 CPU-s |
| 102423 | 连续K128、两上下文前缀和FINAL、实际S ACK | 18 PASS；11s，23.319 CPU-s |
| 102424 | 第二K tile取消、保留已成功K进度，真实drain后同owner复用 | 36 PASS；12s，26.036 CPU-s |
| 102429 | 实际MC/LC PM、scope DDR/CRC、全局DMA、M2与真数据通路 | 18 PASS；20s，64.834 CPU-s |
| 102431 | 首版K2048测试的Verilog字面量分词错误，未运行仿真 | FAILED；3s，0.415 CPU-s |
| 102433 | 合成K2048 Gate/Up、2RF、16个实际流式输入tile | 18 PASS；11s，23.743 CPU-s |

连续K候选只提前准备两条同tile记录。首条INPUT EOP后可独立发第二条，首条仍持完成身份/结果槽直到自身RF响应、若FINAL则真实双S128 ACK。102423 seed1两条head EXEC间距17拍，第二条早于首RF帧结束1拍。首条CONTINUE只更新真实RF，不伪造S写；在第二tile取消时未执行记录按原K游标终结。额外local控制状态355bit，另计M2/guard metadata，不增加W/A/结果payload或SRAM。取消前若已接受W仍等有界FILL和真实CANCEL/DRAIN，不假造传输取消。

102429在上述实现上真取指、真取参、真DDR credit及S；8范围/18记录/315个W64+16个scope64/24个结果S ACK。seed1范围总fixture为7386拍，旧单记录程序fixture为7618拍；两个版本的输入metadata接线也不同，差值不能全归于M2。当前仍一个P、实际global fabric及有限DDR peer，不作整模型吞吐推论。

102433用ordinary W8让独立Gate/Up owner各跨满16个K128分片。每trial 32个记录、544次真实64B W请求和返回、16次真实量化和LOAD、32个Header flit、256次COPY读和目标写ACK、256次A读，及stage释放后256次真实覆写；两路结果共4次S128 ACK后分别回读并与独立Fraction/RNE整数oracle逐位比对。每tile均实际detach一次，峰值2 RF。范围端到端6077–6085拍：U fixture真实源写1536、量化1520、Header128、COPY1840、COPY后剩余LOAD等待48–56拍。各阶段和W可能重叠，不能从总延迟直接扣除所有阶段。测试用合成数据及有限DDR peer、仅一P、未接MC PM；覆盖Gate/Up投影，不覆盖门乘、Down、整FFN或checkpoint质量。

因此为同一token上多输出条带复用X，值得独立验收把4096B A16放入**已有**16KiB S的常驻窗口。它仍要支付真实首次写入/量化、S128重读及租约，须核对其他live窗口不重叠；不增私有SRAM，也不恢复独立4KiB寄存器。102433没有测出该方案的净速度。所有源、日志、CSV、向量、真银行模型和失败记录见原SHA的run86–92 exact parts与完整sacct。功能10ns，不是300MHz物理。


## 同一 X 两条带的常驻对照（run93–99）

102461 在相同 K2048、两条不同的 N8 Gate + N8 Up 输出条带和相同 M2 资源下测三种模式，各 6 seed × 3 初态。各模式均使用真实 U/P 四银行 S、实际动态量化、128bit Header/COPY、A lease、实际 M2 和有限 DDR peer；均完成 64 ordinary records、1088 W64 请求及返回、512 次 A 的真实 S 读取、8 个结果 S128 ACK，并逐位回读独立整数oracle。

| 输入寿命 | 首次独立准备拍数 | 两条带总拍数（含首次准备） | COPY 目标真 ACK |
|---|---:|---:|---:|
| 每条带重新源写/量化/搬运 | 0，随各范围执行 | 10454–10488 | 512 |
| 首次放入已有 P.S 的 4096B 窗口 | 5075 | 10438–10899 | 256 |
| 首次量化，放在已有 U.S，再按条带 COPY | 3073 | 8581–8987 | 512 |

P 常驻只增加 240 bit 的有界目录状态（128b对象key、10b基址、16×6b shift、5b计数、1b有效），另有2个错误脉冲寄存器。原16KiB S内部占4096B，不加SRAM，也不恢复4KiB X寄存器。目标只有 Header/COPY完全一致的 key/gen/K/session/ticket、正确的 S基址和16个真实写ACK 才接受下一tile；第16个才封存并允许 P 调用。错误ticket不能提前封存；活跃范围和未排空时拒绝重配。测试中的其它 S 写遵守范围隔离；完整外层仍须实现该所有权，不能拿软件约定代替。

与实际较强的U常驻对照逐seed/初态比较，P常驻稳态每个小条带省45–72.5拍，但独立首次准备多2002拍。把同一对照每次的稳态差线性外推，估计约28–45个同宽条带才摊平。这是估计，实测只有2个条带和每P N8/way；真实每P N64/way可能更容易把 COPY 藏在 W 服务里，需要更宽条带的实际对照。当前两次复用优先 U.S 常驻；P.S 常驻留作有足够长寿命和空间时的候选。该样本的 S32 起点来自fixture写，不声称真实Norm producer、全FFN或整机速度。

服务接线：scope采用独立 NATIVE_RESIDENT_X_K2048，service1、K2048、完整K、zero bias；p_native_resident_x_candidate 和 resident_x16_directory 接现有 M2 与普通 S128。已有typed2流式资格保持独立。真实 scope 元数据在接收后保留至 terminal 被接受；最后一次 INPUT 不能代替所有结果写 ACK。硬件合成时不应同时复制两个完整的 P 执行器以支持两种输入寿命；组合时只增加输入地址/租约选择，共用后续状态。

run93–97保留 launcher、严格lint、索引和错误脉冲testbench缺陷的原记录；run98 36 PASS，run99 54 PASS。全部严格源、日志、CSV、向量、银行模型、原SHA和实耗完整保留；102461 26s elapsed、73.491 CPU-s（c64 6×10）。paired JSON保留18对逐次时序。不作目标300MHz、能耗或token/s结论。


## 宽条带与同一 P 两种输入寿命（run100–102）

102470 对每P的实际64列Gate +64列Up运行K2048，连续两条带。每trial 512 ordinary records、8704实际64B DDR W请求和返回、512次A真实S128读、64结果写ACK、256次pair detach，峰值16RF。独立整数参考逐位匹配。三种原模式及单执行器依次跑resident/stream都通过，共72次。NATIVE_DUAL_A16 provider 使用一套M/A/guard/RF票据，依据当前持有的typed scope选地址和来源；两种profile各自的底层S路径仍独立计费。Service1限定封存的完整K2048、零bias；service2全K stream、零bias，目录与Header匹配由各自真实来源提供。不能用该试验宣称三P、整体G/Down或者全模型。

| 模式 | 两条真实宽条带总拍数（包含首次准备） |
|---|---:|
| 逐条带流水量化及传输 | 39398–40983 |
| 预先封存P.S常驻4096B | 43977–45575 |
| 预先完整量化到U.S，再逐条带传输 | 42087–43672 |
| 首条带逐片量化并在U.S保留，第二条带复用 | 39207–40792 |

最后一项由102474另18次证明；相比同seed/初态的逐条带量化，只省191–196拍（0.466–0.487%）。P.S常驻的稳态第二条带仅再省43–56拍，首次准备多约五千拍。W和P执行已覆盖了大部分输入工作，不宜按COPY次数推算等比例加速。U常驻4KiB在已有16KiB U.S内，目录为已存在的有界格式；P无需新加X存储。全FFN和三P路径需要真实层级调度验证，不能直接套用本fixture的拍数。

实际双profile入口是 project/experiments/shared_x_control/rtl/p_native_a16_dual_profile.sv 与 NATIVE_DUAL_A16=1；外层须只在共享执行器scope_ready时送同一份已验CRC descriptor/owner，保留到service_done_valid && service_done_ready；该terminal已包含自身真实FINAL的全部S ACK。外层跨P汇合还须独立等待每组scatter完成。目录/当前RX的shift选择见同目录的tb_p_resident_x_compare.sv模式3。run100脚本失败保留；102470 36s /118.636 CPU-s，102474 12s /29.634 CPU-s，c64各6×10。


## 三个P动态S32准备口共用DMA（run103–105）

typed P候选不改旧 mc_dma_fabric.sv。P0–2 每个客户端默认128B scope，可在自身所有已接收描述符、beat、skid和局控terminal全部排空后选择单64B native；其它scope和W的类型不变。native地址64B对齐、通道按地址bit11、tag最低位0；同客户端native serial31单调，mode切换不重置，只有精确本客户端真实FENCE回执或全局复位后的实际transport purge才可重新开始。坏请求的同拍 p_req_rejected 明确表示没有保留资源、不会返回数据；stage据此给自己的匹配terminal。每通道32 beat/32 descriptor、总6×64B skid及任意3拍每通道最多4次真实DDR issue均保留。fabric新增99 bit控制状态，0 payload；联合命令准入还需要每P 1bit已注册标记和2bit本地owner数，合法源保持地址和身份至握手；没有另加96bit地址缓冲或512bit本地payload。实际独立stage有2份元数据owner，见其原证据。

102475独立fabric 18 PASS；102487实际typed fabric +三份精确 b37acf762 stage +三份真实四银行S也18 PASS（c64 6×10，19s elapsed /48.753 CPU-s）。每trial 435实际动态64B返回，其中1个早取消仍真排空但不写S；5个真fabric拒绝不产生raw或写ACK；共440真实stage terminal，三个P均达到两owner。6次真实SRAM读取验证最终写回。旧128B、W17/18、跨通道重复identity、真实启动purge、保留VALID、reserved取消和实际FENCE回归仍跑。stage真实DONE背压时，即使fabric已空也不允许切换mode。独立读trace证明 5542合法reserve=5541真DDR return+1真实reserved取消。

同一pressure测试2/4个S128字的最短真实时间：DDR landing到可见raw1拍，raw到首S请求1拍，raw到末S ACK4/6拍，末ACK后1拍才释放raw，再至少1拍消费DONE。两种路径raw到末S ACK中位数5/8拍；完整分位数见 dma-stage-three-p-audit-102487.json。三P的432个混合压力动态请求跨2081–2135拍，包含同一fabric上的W/legacy竞争、真实S反压和有限DDR peer，不能当整个动态Dot或整模型速度。联合fixture不是已部署的动态运算完整程序。run104定时模型初次构建错误完整保留，102487严格检查未豁免这些错误。

## M2 scope 代号实际回绕（run106–112）

M2 的16位 scope generation 与 COPY generation 是独立的名字空间。M2 的同一 handle 到达 `FFFF` 后，只有晚于该次 `BEGIN_SCOPE` 的真实 FENCE 完成才准许下一次使用 generation 0；启动时的 purge 或更早的 FENCE 都不算。LC 在确认 `BEGIN_SCOPE(FFFF)` 时清除旧授权，匹配后续真实 FENCE 后再授权；执行票据内部 bit240 表示 LC 已有匹配的、仍活跃的 generation 0 context。旧票据其余保留位继续拒绝。bit240 不出现在 M 的128bit wire frame，无新增存储或物理 pin。M 仍独立检查自己的 handle、epoch、generation 与 frame 身份。

基线102506在 `FFFF` 后完成真实 purge，但旧guard挡住合法 generation 0 EXEC；102515仅恢复旧的过期授权清除逻辑，在进入 `FFFF` 前有一次真实 purge，却试图直接回绕，真实 M 拒绝，未执行该记录。修复102507和含提前 purge 的102516各18次通过；每次确实接受一个 generation 0 EXEC，测试真实MC/LC程序存储、scope获取、DMA FENCE/后台 purge、M2与S，完整运行八个数值范围。分别观察到两次/三次后台 purge（均含启动）；每trial 315个真实W64请求和返回、18个完成记录、192个A读取、24个结果S128 ACK，独立参考逐位一致。102517未加速计数的普通程序亦18次通过。近回绕fixture只通过单独保存的源视图调整 reset 计数初值 `FFFE`，含早 purge 的测试还设定初始会话计数靠近耗尽；这些初值不进入生产候选。源、原始失败、log、CSV、向量、银行、SHA及实际 Slurm 用量见 run106–112 exact parts 与 `sacct-106-112.txt`。真实 COPY 名字空间的回绕仍需自己的连接排空/重置证据；本试验不提供其资格，也不提供300MHz物理资格。

## 四个既有 W 银行并行填充（run113–120）

此前宽条带的限制有两层：同组第二个记录要等第一笔 W 填完才发 ALLOC；下一组又等上一组完成。实际上旧实现可持有两个 W 银行，但任意时刻最多一个银行有 W64 请求仍在途。新 `p_native_weight_prefill` 先用各自真实 ALLOC/FILL 身份重叠两笔；`FOUR_BANK_LOOKAHEAD=1` 再最多接收两张后续 range ticket，通过同一 M aperture 发真实 ALLOC。只前取同一 K128、已有 RF context 的记录，首 tile 仍受真实 context 建立约束。每项仍等匹配真实 W FILL、A lease、guard credit 才 EXEC；已准备记录回放给同一执行器，不重复 ALLOC。四银行数据还在 M 原有 4×1152B 内。相对原 P 增加已分配较旧 W 的33 bit，加两项有界 range/ACK 元数据和索引506 bit，共539 bit控制状态的 RTL 上界；没有新 W/A/result payload 或 SRAM，没有面积/300MHz验收结论。

下表各模式与对照用相同 P、真实 U/P 四银行 S、N64 Gate+N64 Up、K2048、同一输入寿命策略、同一批向量与两条带。每次比较均有512实际 M record、8704次64B W读请求/返回、512次 A 的真实S读、64次结果S128 ACK并逐位读回。早前有限直接DDR peer整体最多每两拍返回一个64B；第二组使用实际两通道、每通道32beat/32desc、共六个返回暂存的global DMA RTL，但外部DDR仍为有界fixture，只连接一个P的W源，无其它客户端竞争。

| 路径 | 旧实现拍数 | 双银行拍数 | 四银行拍数 | 配对四银行减少 |
|---|---:|---:|---:|---:|
| 相同直接 DDR peer，102524/102530 | 39207–40792 | 33593–34342 | 25387–25952 | 35.17–36.38% |
| 相同真实 global DMA，102544 | 34221–34950 | 未测 | 18323–18624 | 45.89–46.71% |

独立CSV审计以真实 W64 tag 逐笔核对发出/返回，比较三方案实际地址多重集合，检查 `range accept → ALLOC → FILL EOP → EXEC → complete` 的每条身份并核实峰值在途银行1/2/4；global比较独立检查每通道任意3拍最多4个真实DDR issue。直接peer每scope的返回间隙，超过原有两拍每beat下限的累计额外时间从10704–11496拍降到3793–4077拍。该减少是同一个计算图下 P 控制/搬运调度改进，不应记成综合DP、整模型、实际DDR或token/s的收益。

102535在同时拥有四个真实W银行且有未完成传输时取消，260–274拍收到匹配范围terminal。四个 M bank 逐一匹配实际 CANCEL/DRAIN；未发 EXEC、未产生新结果S ACK；已发的W读正常排空，未制造成功。范围中另有一个已offer但还未分配W的记录按错误退役。相同地址/银行重试前先毒化输出窗口，实际重算256记录、4352 W64和32结果ACK，再读回对照。102551把测试会话阈值暂设96，在真实DMA中经18次实际后台 purge（含启动）重复验证，取消到真实terminal203–206拍，实际13396 W64 req==return。任何排空时仍存活的 W 银行、guard 或result owner 都会触发fixture断言。生产阈值未变；生产范围只在没有前取 owner 时开始 FENCE。证据为 `wide-weight-prefill-102524-102535.json`、`wide-weight-global-102544-102551.json` 和 run113–120 exact parts；启动/fixture失误亦保存。复用 `P_STREAM_FOUR_W_SOURCE_LOCK.json` 的精确RTL，不可把这里一个P的性能复制为三P共享DDR的吞吐。

