# Issue76 Granite 有限 expert→merge 服务

本实现固定Issue74已独立接收的layer0/13、R16、evaluation72整数函数，只比较输出/merge物化窗口128/256/1536、M/V驻留和split/shared零差标签，共24条件。此处记录实现和合同；实际服务器执行、独立接收另由主任务留证，不把源码或小测试称为服务验收。

## 输入与执行

真实数组/服务仅授权服务器Slurm，本机仅小合成、源码和JSON。current norm/router/ID/Q15已发布是显式external cut；post-attention norm/router计算在此服务外，所有消费的入口IO计价。离线72row的前64/后8位置分组不代表真实cached-decode或跨token免费batch。

~~~sh
python -B project/experiments/granite_ports/service.py pack --compiled COMPILED74 --layer 0 --binding PHASE.json --out NEW_PACK
python -B project/experiments/granite_ports/service.py run --compiled COMPILED74 --result R16_EVAL74 --receipt NUMERIC_PASS.json --packed PACK76 --packed-receipt PACK_PASS.json --calibration MICRO76 --calibration-receipt MICRO_PASS.json --tile 1536 --placement shared_v --label split --binding PHASE.json --out NEW_SERVICE
~~~

binding包含真实commit和service_sha256。pack/run可绑定不同冻结源码，原phase2 pack不因后续日历修改重做。输出拒覆盖。

run要求原granite-independent-receipt74-v1/PASS、43stage/72token/576真实路径及3个实际重SHA负例；pack要求PASS_PACK_CODES与同层/compiled；micro要求PASS_MICRO_CAUSAL_BYTE_AND_ROM、18typed/service_all_keys_qualified及实际manifest/cost_table SHA。未知op/格式/shift、错误源、SiLU域外、错误ROM或缺独立资格均拒绝。

## 唯一静态布局与M矩阵

packed[e,ob,kb,k,o] = original[e,16*ob+o,16*kb+k]，形状[E,O/16,K/16,16,16]。实际服务器编译重排并全量逆变换，原S8码不变。每层完整40专家唯一packed副本94,371,840B及Q31/I16 scale共614,400B在EXT；scientific原NPZ不再部署第二份raw94MB。

每O16/K512块8192B连续逐packet EXT→M。M每K16读A16B保留，再16次读weight16B/执行16有效PE；B1不将总MAC除256。8192B权重、1536B输入、64B accumulator registers、A/W各16B寄存、64B返回镜像和RQ工作区均计容量。完整K1536/512后才RQ，INT32绝对界24,774,144/8,258,048。没有免费在线transpose或隐含8KiB寄存。

pack是另记时间/源SHA的离线整数布局步骤。每token真实weight/activation/scale访问仍收费。

## 三phase与完整消费者

每macro的meta.token=0..71、meta.phase=front/down/norm。同token严格front→down→norm，完整nextnorm结束后才下一token。

1. front：currentnorm全1536扫描/最小RNE shift/A8；读取真实8路ID/gate；完整gate/up1024→SiLU LUT→门乘midQ12→整512 absmax barrier/最小shift/A8。8份midA8共4096B及I16 delta16B在S0；S64控制cache另收费。
2. down：front gateup4096/silu2048/mid2048/normA81536释放后初始化当前window的S64 merge。逐rank重读mid512/真实descriptor，完整K512 down，O16先RQ共同Q12→U16Q15 gate乘→S64 prefix；8路齐后RNE15、0.22 Q20乘/RNE20、真实residual add/I32guard，O16直接EXT写回。
3. norm：1536layeroutput写齐barrier后释放merge，完整U128平方和→floor/H1536+epsilonQ24(17)→radicand左移40→isqrt→全1536 gamma乘/分子左移12/任意除数RNE/I32guard→EXT nextnorm。保守归约显式多付0+首square一次padding，U128加1536次，函数不变。

allocation的token_phase生命周期允许不同phase同offset复用，接收须由实际macro区间证明。down只留O16返回，不把整6144B output与fullmerge强制并存；完整8路S32返回49152B驻V仍拒绝，不能与12288B full-H S64 accumulator混淆。

当前静态分配峰值（字节，包含40B固定VR8 operand寄存和512B Vframe）：

|window/owner|M|V|S0|EXT|ROM reserved|
|---|---:|---:|---:|---:|---:|
|128/M|11344|11184|4304|96766256|131072|
|128/V|10320|11184|4304|96766256|131072|
|256/M|12368|11184|4304|96766256|131072|
|256/V|10320|11184|4304|96766256|131072|
|1536/M|22608|11184|4304|96766256|131072|
|1536/V|10320|14224|4304|96766256|131072|

库存M32KiB/V16KiB/R32KiB/S8×32KiB/EXT128MiB不增加。fullmerge在V或M均可合法部署，不能用acc+整output超容量推出必须小tile。

## 宽成本、转换与ROM

全部宽乘/S8 digit重组/byte carry/shift/guard/RNE与U128除法/isqrt绑定micro03正式18key/独立receipt。S16 exp真实走signextend_s16_i64，S32→S64走align_s32_i64(0)。delta由真实当前row scan的S64 counter产生，I16发布及S64cache均存储/收费。逐output shift=31-exp-delta实际计算，不用未来参考选scale。

SIMD8未资格化，每scalar按ALU依赖+软件controller dispatch收费，不把carry总量除8。单SFU controller借既有VR8 lane0，同时占SFU/VR8，无新增宽ALU。固定8lane×5B=40B寄存从V预算让出，scalar active5B；微frame512B在V，所有初始化、每byte读写、结果/valid提取及caller IO均付bank/BUS。

微leaf证书：每byte指令读≤3 frame bytes→1byte ALU→写≤2bytes→1dispatch，有限5B active regs、512B source-bound frame、完整初始化/live/全shift域。全leaf保守预留V/BUS/VR8(+SFU)，全局串行允许内部合法逐动作retiming，不解释成先读全部到无限RF。

ROM有效SiLU65540+exp2 8196=73736B，实际32768×32核131072B，padding57336B明确分配；全局池4260100B不变。单word32口latency2/II1，每实际SiLU index独立request/read/response/写回，不能把四个返回当免费一拍128bit。router是cut外计算，但其表保留有限占用。

byte核心RTL重放、软件宽微程序、1/action候选dispatch与未实现完整wide/address FSM、byte-store/STA/PPA分开。M16发射、DMA/bank/BUS为声明的候选基础时隙，不声称完整加速器实现或工艺时钟。

## 128bit物理拍与部分写

银行128bit1RW、单BUS128、header32、payload≤1984、16B pad，逐packet按真实leading offset计拍。未假定SRAM byte mask；partial目的beat先读旧16B行再写，旧行保留于已计FIFO，不增端口。

微frame每byte read=1bank拍+48B BUS=4slot；write=旧行read+write两bank拍+48B BUS=5slot。因此总micro时间=ALU+dispatch+4reads+5writes，bank拍=reads+2writes，wire=48(reads+writes)。ROM4B/I16/小flag写同样RMW，完整对齐16B写不额外读。

transfer叶采用唯一source-bank/BUS/destination-bank全窗口资源envelope，并给出可逐packet独立展开的serial_packet_retiming_certificate：明确真实src/dst offset、payload、源读→BUS→目的RMW/写的子区间；不能将8192B聚合源读→BUS→目的写当有限FIFO日历。总时隙和计数不变，实际每次只驻一包。FIFO峰取max(32+16×源physical read拍数，32+16ceil(payload/16)+16×partial目的beat数)，同时覆盖源非对齐汇集与目的old-line shadow的互斥阶段。1984B非对齐最多两edge，2016+32=2048恰好；40B寄存不能再永久挤入。caller暂存≤512B，micro整体FIFO保守1024B。M/V均经同bank-select BUS-attached VR8，nearM不赠ALU或物理locality。

## Witness与范围

summary.json schema=granite-service76-v1：task绑定numeric/compiled/receipt/pack/micro source和SHA，config/库存/allocation/phase峰值/counts/end_slot。manifest schema=granite-service-run76-v1，状态EXECUTED_CONDITIONAL_SERVICE。row_hashes.json绑定原43stage数组及逐token row SHA；observer hash不收为目标硬件算术，目标完整当前row scan则已收费。

witness.jsonl.gz每行macro含id/start/end/deps/meta/body；loop body时间相对iteration原点，end=start+count×period。access.index_strides对loop索引右对齐；offset/range/leading拍独立重建。micro地址class仅绑定已核512B程序和全shift域，LUT class回链原silu_lut_index。label不进入builder，同配置split/shared应witness逐字节零差；同层所有tile/placement数值rowhash相同。

接收另核完整8mid持久barrier、全K/8prefix/共同单位、真实consumer、phase实liveness、ROM/widthfee/port/FIFO及48KiB拒例。当前源码不能替代实际接收。工具交付时本机10项小合成及项目结构检查通过，未加载真实NPZ/运行模型或真实服务。无整模型质量、实际INT8速度、最终物理边界或PPA结论。
