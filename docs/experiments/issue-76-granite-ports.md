# Issue76：Granite有限expert到merge与宽算术成本

2026-10-24 UTC+08；负责人Liangruizhi；[Issue76](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/76)/[PR77](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/77)，task/76-granite-ports，base PR75@ce2d08f。本批实际模型数据、pack、微程序/RTL、服务和完整接收全部由本人CPU服务器Slurm并行执行；PC只源码、微合成、JSON和字节接收。

**24个同函数同资源配置全部通过独立有限服务接收。完整H1536的S64 merge可以合法驻V16KiB，峰14,224B；近M驻留仅节省约0.00084%的条件服务时隙，不能据此冻结M/V物理融合。** 宽算术字节frame的公共银行/BUS成本主导当前保守实现，下一步应优先校准其内部暂存与预连线，而非继续盲扫merge tile或增加模型。

## 1. 冻结范围和真实执行

[执行协议](../../project/experiments/granite_ports/PROTOCOL.md)、[服务合同](../../project/experiments/granite_ports/SERVICE.md)、[微核](../../project/experiments/granite_ports/MICRO.md)、[独立接收](../../project/experiments/granite_ports/AUDIT.md)与[统一索引](../../project/experiments/granite_ports/results/issue-76/index.json)给出精确来源/命令/哈希。服务器/public/home/yuzelu/RuizhiLiang/issue76-granite-ports-20261024，lrz-i76-*，旧70/72/74原输入只读；无新下载、其他机器任务、Phi解封或成员55/63接管，其他成员89448作业未动。

复用Issue74已独立PASS的Granite-3.1-3B-A800M-Instruct官方rev a02780686e08a03fe0d2679a293b5c74a90efa89：层0/13、R16、evaluation72。起点是已发布currentnorm/router/ID/Q15的外部cut，其消费IO计费、计算在cut外；完整8expert gate/up→SiLU/门乘→512全行scan/A8→down→共同Q12/S64 merge→0.22残差→1536完整nextnorm。原43stage逐码轨迹不变，数值质量仍沿用原局部误差与失败限制。

两层×merge128/256/1536×nearM/sharedV×split/shared标签=24。物理M16×16、B1有效16PE、O16/K512；VR8、共享SFU1/ROM1、M32KiB/V16KiB/R32KiB/S8×32KiB/EXT128MiB、128bit1RW/单BUS/2KiB FIFO均不变。预先加入fullH控制，是因为完整acc与完整输出不必共存；并非看到有利结果后删条件。离线72行的前64/末8位置标签不是本批新cached-decode执行。

|对象|实际结果|证据边界|
|---|---|---|
|两层W8静态pack|producer/独立接收PASS|每层94,371,840个码及地址完整逆变换；实际改码重SHA负例拒绝|
|正式micro03|807case、1,082,106个byte RTL动作独立PASS|18typed key、132真实Granite码样本、69单ROM请求；不代表完整wide FSM|
|正式服务03|24 producer/24 receiver Slurm COMPLETED，全部PASS|完整43stage绑定、生命周期、有限端口/FIFO、全宽收费；每项6类实际重SHA负例，合计144|
|配对比较|90445 COMPLETED/PASS|6个同层同窗口M/V对、12标签逐字节零差、4窗口对照；全03单一费用版|
|全模型质量/端到端/STA/PPA|未执行/未验收|条件服务时隙不能换算GHz、GPU速度或芯片面积能耗|

## 2. 容量结论修正：完整merge可以放下

每层只有一个静态packed W8部署副本94,371,840B，scale614,400B；科学原NPZ不当第二份硬件权重。已有完整8路S32输出49,152B驻V方案仍实质拒绝。S64 merge只有12,288B：先将8份midA8共4,096B缓存S0，front临时释放后进入down，只保留O16返回/RQ，8路完整prefix后分片写EXT；全部1536结果齐后释放merge再nextnorm。各token串行，nextnorm结束才复用。

|merge window/owner|M峰B|V峰B|S0峰B|EXT峰B|
|---|---:|---:|---:|---:|
|128/M|11,344|11,184|4,304|96,766,256|
|128/V|10,320|11,184|4,304|96,766,256|
|256/M|12,368|11,184|4,304|96,766,256|
|256/V|10,320|11,184|4,304|96,766,256|
|1536/M|22,608|11,184|4,304|96,766,256|
|1536/V|10,320|14,224|4,304|96,766,256|

V持久区1,456B、down fullacc12,288B、O16临时480B；前段峰11,184B与fullacc峰不同时live，故fullacc相对全任务V高水只增3,040B，剩2,160B。不能将原74中acc+完整6,144B输出的静态相加义务升级为“必须小tile”的结论；本批生命周期证据修正了这种排除理由，旧产物原条件保留。它仍是固定资源候选的合法布局，不是工艺SRAM宏/真实线长验证。

最大实际FIFO2,016B<=2,048B。每packet源读→BUS→目的RMW/写完成后才下一packet，以完整共享资源envelope证明聚合leaf可等时重排；8192B先全读入再全发不能视为有限FIFO证明。银行不假定byte mask，部分写付读旧128bit行+写两拍，旧行暂存在既有FIFO。

## 3. 宽算术、SFU和ROM究竟校准了什么

实际8个S8/byte lane只含8×8乘法与byte加减、carry、shift/logic/CMP/MUX；每个wide调用由固定、覆盖全部有限shift域的微程序构造，独立live-store逐动作消费RTL返回值。未用CPU原生宽乘/除/开方推目标周期，也未无条件将scalar carry除8。候选SFU借VR8 lane0，同时占VR/SFU，不赠宽ALU。active操作数5B/lane、共40B从V扣除，512B microframe和caller临时均有限。

下表读写包含初始化/结果提取；ALU列不包含另付的1/action候选controller dispatch、frame/调用者IO和端口：

|typed op|byte ALU动作|frame读B|frame写B|scratch峰B|
|---|---:|---:|---:|---:|
|mul_s32_s32|2033|1768|1553|57|
|mul_s64_s32|6665|6004|5033|97|
|mul_s32_u16|1231|1096|943|53|
|rne_s64_i32|197|223|172|59|
|rne_s128_i32|389|447|332|107|
|udiv_u128|21078|24932|16376|139|
|isqrt_u128|19161|19209|13610|107|
|div_rne_s128_u64_i32|21463|25382|16709|195|

32×32/64×32/32×U16分别25/45/15个S8乘积，还需全部digit、carry、符号、sticky/tie/even、guard和控制；不是只按乘法个数计时。完整18key包含S16符号扩展、S64/U128加减/比较/对齐等，费用原表在精选包。

ROM真实候选为32,768×32bit、单口，预留131,072B，其中SiLU65,540B+router exp2 8,196B有效，padding57,336B；全局池4,260,100B另列。实际69请求核latency2/II1，服务中每个SiLU独立word读取、总294,912次；不能按128bit返回免费并成一拍。router计算在cut外，但表占用保留。

已有Verilator5.042/只读ORFS镜像执行，无安装。镜像SHA c742bf99ea498fb4da5135bc83fd1677abcebe0e64470e6a115f2baecb3905df，verilator_bin SHA f98f160dc1ba1b2b660621ab654e916541a8c6a7504d7841822a016fa5d7a1bd。byte核心/ROM功能仿真已执行；宽循环/地址controller、512B byte-store实现及其1/action dispatch仍是软件/候选，完整wide FSM、RF银行、宏时序、STA/PPA未验收。ROM仿真latency不等于工艺ROM时钟。

## 4. 保留并修复的实际控制域失败

旧02 L13全12通过，但L0全12producer因真实RQ shift超0..128而失败，其未启动依赖receiver核验后取消，未用跳过层0冒充全通过。只读90396诊断完整2,949,120输出：L0 gate/up589,824输出中32处s130/131（10/22处），原S64 product非零，raw>=64共3,976处；其余L0down27..36、L13gateup27..34/down26..37，无负shift。

原有S64对称RNE在s>=64恒0，包括最负码在s64的半数tie-even。正式03用已校准cmp/sub/max/sub实现非负guard与128-max(128-s,0)，逐项核原RNE、译码后RNE和原发布Q12均为0，不改原exp/delta、43stage或模型数学。所有1,474,560输出/配置一律支付4op、guard flags真实读写和1,474,560候选controller测试槽；128常数部署原96B区+64，无新容量。负shift需新左移/溢出合同，本次未遇且不免费clamp。

rq_decoder.json保存原/译码范围、hist、全数组/72×8逐路径SHA及全部32位置。3,976是全部大右移零码检查数，32才是改变控制值的数量。正式版本NONNEGATIVE_MIN128_FOUR_TYPED_PLUS_FLAG_TEST76_V1统一24配置；旧L13/02不混排名。每项独立负例覆盖port/capacity/numeric/widthfee/ROM/rq_decoder，实际改artifact并重写SHA后由语义层拒绝；数值绑定继承原74独立完整数学，本服务接收不是再次全NPZ数学求值。

另保留micro01首ALU后注入中间输入的实质拒绝、micro02仅17key不具正式服务资格；服务01缺逐packet FIFO证明仅diagnostic。90348虽写出PASS收据却末尾CLI打印KeyError、Slurm FAILED，未算正式验收；90349新out/修正print后COMPLETED。所有来源/失败均在归档，不静默覆盖。

## 5. 同精度同资源比较与瓶颈

|层|merge window|near M条件slots|shared V条件slots|近M节省占V|少wire B|
|---|---:|---:|---:|---:|---:|
|0|128|92,108,771,216|92,109,545,360|0.00084046%|5,308,416|
|0|256|92,108,384,144|92,109,158,288|0.00084046%|5,308,416|
|0|1536|92,108,061,584|92,108,835,728|0.00084047%|5,308,416|
|13|128|92,104,239,602|92,105,013,746|0.00084050%|5,308,416|
|13|256|92,103,852,530|92,104,626,674|0.00084051%|5,308,416|
|13|1536|92,103,529,970|92,104,304,114|0.00084051%|5,308,416|

每对精确少55,296个64B partial复制：payload3,538,944B、含包头wire5,308,416B、774,144slots；数学、18key运算、ROM和库存完全相同。不是硬件连线缩短或融合后的时序证据。窗口1536相对128少709,632slots，来自少11次窗口重读mid/descriptor；256相对1536多322,560slots。V的fullacc只增全任务高水3,040B且仍在原16KiB内，但如此微小的slot差不支持无条件固定fullacc优于小window的物理设计。

当前microframe每byte read=1bank拍+48B BUS=4slot；无mask写=2bank拍+48B BUS=5slot，故micro子集时间=ALU+dispatch+4r+5w，wire=48(r+w)。这是有意暴露费用的保守BUS-attached策略，不是优化过的宽算术设计：

|层/fullH共享V|总wire B|frame wire占比|micro服务slots占比|
|---|---:|---:|---:|
|0|794,908,724,160|99.7510%|99.4611%|
|13|794,868,655,152|99.7511%|99.4611%|

micro wire已经包含于total，不能再加。约99.75%的wire和99.46%的slots都在公共microframe策略，足以掩盖当前M/V驻留差；不能把这些巨大字节数称真实LLM模型通信、最优硬件需求或把极小百分比外推到另一种RF实现。相对旧74也不能跨费用版排序。

## 6. Block划分结论与下一步

继续M/V/A/R/S/D六个逻辑模板。制造前候选固定：M局部S8 MAC→同单位INT32 fullK反馈/完成标记；V宽运算的有限临时与读改写接口、RNE/guard/scale控制、单ROM请求/返回仲裁；S银行/缓冲owner与显式phase屏障、D信用/完成控制。动态expert ID/top8 fanout、M↔V宽旁路、merge窗口/owner与S/backing端点保留产品配置，不固化当前所见expert连接。

容量/端口层面已排除全8输出驻V，保留M或V fullacc合法候选；此批没有连续R更新，不覆盖或替代Qwen/Falcon的range/epoch闭包。逻辑完整归约需要共同单位，不要求同一制造宏。见[Block v2第14节](../BLOCK_PARTITION_V2.md)与[决策](../decisions/2026-10-24-granite-finite-ports-and-micro-cost.md)。

下一真正影响物理取舍的最小分叉是：在相同8byte lane、512B有限存储、端口/寄存/ROM预算下，实际实现并校准宽microframe局部访问/控制器，保留既有BUS基线，比较完整同精度消费者链。不能把局部frame访问免费化或只扣packet后声称收益。随后用真实宽FSM/RF、布局/STA与并发资源证明判断V/RQ/S的宏边界和预连线；更长连续状态/整模型质量仍按既有独立任务，不为此盲加模型或扫更多merge窗口。

## 7. 可复查交付

[统一索引](../../project/experiments/granite_ports/results/issue-76/index.json)列完整/精选大小、SHA、19phase原Git源、实际命令/Slurm、失败与接收；[work76](../../work/Liangruizhi/76/README.md)和[交接](../handoffs/2026-10-24-issue-76-granite-ports.md)给恢复第一步。新69项微合成及相关74的63项回归、管理结构通过；归档与源字节接收分别记录，不能替代数学/硬件验收。

仅提交本人任务文件，PR77待审查合并，Issue in_review而非done；登记PR5 pending，board.json404/Projects缺能力，看板unverified、同步pending，管理员和审查人待指定。上传/CI/远端原字节读回以最终回执为准。
