# Issue98：实际整合核布局、时钟树、布线与严格电气验证

2026-10-25，负责人 Liangruizhi，实验继续进行。**97整合核已在本次Nangate研究库、整store82切口及固定I/O约束下完成布局/CTS/详细布线/真实RCX/全端点时序与严格电气验收，并通过精确最终网表4×2正常消费者链门级。93最终详细物理检查也已通过，精确51×2门级仍在原作业中运行。** 这是有限研究逻辑岛资格；真实SRAM、供电网、目标工艺制造验收仍未具备，不能写成完整芯片或固定层底座已验收。

## checkpoint3：97研究物理资格已闭合，93等待最终门级

| 最终候选 |93 joint9302 → detail9303|97 joint9701 → detail9702|
|---|---:|---:|
|实际单元面积µm²|59619.910|76964.174|
|原79600.5µm²预算余额|19980.590|2636.326|
|真实RCX最差setup ns|+3.488219|+3.680569|
|真实RCX最差hold ns（双load取最小）|+0.037797|+0.036780|
|完整setup/hold端点|5826|7465|
|完整cap / slew检查（每种负载）|45136 /45147|58346 /58359|
|严格cap / slew超限|0 /0|0 /0|
|实际DRC迭代终态|7700→…→0|13977→…→0|
|原图相同/全部FF函数/端口/RCX读回|通过|通过|
|精确最终gate|51×2正在运行；尚未接收|4×2正常完整链PASS|
|physical_stage_accepted|false，仅缺该网表完整gate|true，在声明的研究切口范围内|

97候选6只对实际RCX残余 `_73496_/ZN` 增加1枚X4，后续固定50ps增量hold实际再加15枚CLKBUF_X1：总增加13.832µm²，未放宽原10ns/min0、全部端口和容量。独立中间图证明旧driver仅驱新BUF输入、新输出承接全部且仅原sinks；18dirty批次、208唯一网、16新网完整计账。详细route固定seed42/8迭代，实际7m14s，DRC序列13977/4983/4083/321/64/5/5/0；无resize/repair/antenna插入，最终电气图与新gate绑定网表相同。实际7,465端点双loads全检，未解释未约束端点0，58346cap和58359slew全表均严格无超限；无fanout限制仍明确未限定。

97实际最终gate接收[原收据](../../project/experiments/integrated_physical/results/issue-98/checkpoint3/final97-gate-receipt.json) SHA `ade8d55632682139c5fd7a438ee474be33a2ea16e91cee7b378b09e8be0db452`；[完整物理接收](../../project/experiments/integrated_physical/results/issue-98/checkpoint3/final97-detail-receipt.json) SHA `465bf3e283ddb47e2c0b4ac54db39691d544c904f1db3c8158be00fcc8ab13d6`。接收器 `receive_detail.py` + `gate_dependency.py` 强制精确stage/final.v/所有cell-pin等价类、全端点及实际SPEF读回、电气全表和postgate；旧raw或旧网表gate不可替代。97 gate范围仍仅4×2正常消费者，不扩大为RTL50命令内部注入/恢复或全状态formal证明。

最终层账：93实际876835.685µm中心线/289659via，42118完整RC网；97为1223763.660µm/383536via、54427完整RC网。93本候选最高signal至M7，97仍用M8/M9/M10（3583.2/802.4/203.2µm），全clock/signal/PG及各via层对见收据。两者PG均缺失，边界仍M5/M6且没有按55/63要求引到M8，不能移植成固定M1–M8/后定制M9–M10资格。93与97功能不同，面积差不是同功能Block划分收益，10ns下slack也不等于签核Fmax。

错误拒绝能力补齐：known incremental候选不得用1/False/缺字段跳过入口审计，所有前序SHA/status/prepared必须匹配冻结合同；joint5/6接收器独立限制BUF_X4。真实 `receive_route` 入口四种重SHA破坏均已在服务器拒绝，见[原负例收据](../../project/experiments/integrated_physical/results/issue-98/checkpoint3/entry-negative-receipt.json)。这修复接收代码漏洞，未发现先前真实结果被错误放行；先前native小cap失败仍完整保留。

[checkpoint3字节收据](../../project/experiments/integrated_physical/results/issue-98/checkpoint3/independent-byte-receipt.json)：7份原始文件共5042877B已跨机SHA接收；另有74服务器phase、3650原Git引用、224独立blob共1774531B通过原Git字节核验。全量最终archive待93终态后保存。93当前完整门级保留原10500s child/10800s作业上限；实测6941s完成119884912/194658699与128494926/230528560周期，保守估总11270/12453s，存在预算超时风险。若真实超时仅按已批准的同源网表/binary/完整51driver/input一次延长新out执行，原失败保留；不可缩减记录或直接升级accepted。

## checkpoint2历史有界结果（失败及当时状态原样保留）

- 93唯一50ps增量hold消除原6条保持失败，面积59611.664。后续只固定4个cap driver各加X4、再一次50ps hold，最终增加4X4+1CLKBUF_X1=8.246µm²，总59619.910；完整5826端点setup+3.316442ns/hold+0.050006ns、双load全cap/slew严格0。中间四driver分别只驱新X4且全旧sink保留；原全部FF/函数/接口、几何和全RC证书通过。该精确新网表完整51×2门级与DRT正在执行，尚未最终accepted。
- 97唯一50ps增量hold面积76950.342，7465端点setup+3.546201ns/hold+0.039329ns，58330 cap/58343 slew检查严格0，精确4×2正常门级已独立PASS。随后实际DRT耗6m28s，DRC依次13258/4525/4047/269/39/3/0，全部DEF/RCX/SPEF读回通过；实际setup+3.665755ns/hold+0.034158ns，但 `_73496_/ZN` cap26.169408798>26.054399490fF，**仍失败**，不能用1fF原生过滤容差放行。
- 97此driver为OAI21_X1，仅驱1个AOI21_X1/A，原0.80选集源ratio0.7711所以未选；最新GRT总cap22.03515625，详细RCX变26.169408798。电气连接、完整final.v逐字节相同，RCX网电容24.5431fF包含ground9.173904和coupling15.369152；不将跨RC模型差异全部归因单一线长。原失败及只读诊断留存，尚未自动追加修复。

增量独立账：93/97分别321/463 dirty批次、1046/1835唯一网；新320/461网全部覆盖。工具按grid pin位置选择更新，93/97有7/15个换sink但主段不变的网，全部要求真实新SPEF pin RC变化且全图连通；97一个实际空批留存，不把空批改写成漏记录。4种实际重SHA破坏（删新网dirty、追加full reroute、bool类型伪造、复用旧pin RC）均拒绝。93四网联合最终仅5新网、12移动cell、16原网主段变化。

四网联合首次91377因直接routed insert_buffer未初始化DPL grid而Signal8，失败保留；精确源证实先check_placement可importDb/initGrid且不回写cell。恢复新out前后COMPONENTS/PINS/NETS必须逐块一致，再执行同一候选，不增加优化步骤或放宽限制。

[checkpoint2](../../project/experiments/integrated_physical/results/issue-98/checkpoint2/independent-byte-receipt.json)的8原文件共6126541B已服务器与PC独立字节SHA接收；精确gate、负例、诊断与精选阶段指标可复查。全量最终归档仍进行中。

## 研究对象和约束

对象为 Issue93 `chain93`（真实M→merge/residual→gamma-stream norm）与 Issue97 `chain97`（真实V→M→norm）。各自源commit、映射、输入、独立整数oracle与原RTL/gate收据分别冻结，不能继承旧84或另一核的时序。

| 固定条件 | 本次实际口径 |
|---|---|
| 库/工具 | 已有 Nangate45 typical 1.1V/25°C；OpenROAD26Q1-1961-g63ed2e0fe5，OpenSTA83e1f9b；工具库/LEF/RC规则逐文件SHA |
| 几何/面积 | core399×399=159201µm²，die448×448；285行×2100sites=598500；单元面积上限79600.5µm²，含CTS/repair |
| 时序 | 10ns，uncertainty0；输入slew0.05ns，I/O max0.1ns/min0，全部输出分别1/10fF；不删endpoint/不加false path |
| 存储 | 整个store82 wrapper显式cut：16KiB、128bit、1RW；store_reset保留真实reset或soft_abort；宏本体、宏时钟/供电/阻挡未验 |
| 库存 | 原8S8+1S32以及U128 SFU；97新增实际V/控制独立计价；无隐含额外存储端口 |
| 金属/接口 | signal M2–M10，clock trunk M4–M10；实际M1via/M2/M3 clock pin access计入；M5/M6边界pin全部保留 |
| 资源 | 仅本人服务器lrz-i98-*，8CPU、默认20min/1100s；51记录门级每精确条件一次180min上限；无安装/其他机器/成员55/63目录改动 |

平台自身明确为nonmanufacturable研究库。缺少真实目标PVT/SRAM宏、PG/tap/fill、LVS、上游驱动阻抗和固定底座制造条件；任何本报告的研究验证都不能替代这些资格。

## 最重要的验收修正

完整非过滤电容表发现：93详细RCX与97当前GRT各20条actual cap>maxcap，而工具`-violators`摘要仅7/3条。已核同版本OpenSTA：摘要用`fuzzyLess(slack,0)`，零比较容差1e-15F，即1fF，会省略小超限。**1fF不是本项目允许的设计裕量。** 新接收器必须核完整max slew/cap/fanout表和全部有界输出driver，最终接受还要求严格actual≤limit。历史“零违例”数据仅表示当时native摘要，尚未完整重查的阶段不升级为严格闭合。详见[决策与原始源码SHA](../decisions/2026-10-25-issue-98-strict-electrical-maxima.md)。

实际完整检查（两个负载）：93 cap44584个check/20超限，slew44595/0；97 cap57367/20，slew57380/0。库和SDC无fanout上限，0条fanout检查表示没有这种约束，不能说fanout已闭合。外部输入固定波形仍不等于上游驱动阻抗验证。

## 实际阶段数据

面积单位µm²，slack单位ns；全部保留失败，无无限追频或放宽10ns/min0。native cap列属于历史工具过滤口径；严格电容最终以完整表为准。

| 核/阶段 | 单元面积 | 最差setup | 最差hold | native cap | 严格资格说明 |
|---|---:|---:|---:|---:|---|
|93原映射+2tie|54811.694|-224.910370|-0.002434|196|控制树超载，非算术固有Fmax|
|93布局修复|56325.500|+3.427134|+0.013908|0|理想时钟/估计RC；严格cap待独立完整重查|
|93 CTS基线|56766.794|+3.414859|-0.208368|0|1057个hold失败|
|93 C1：5ps/1端点预算|57918.840|+3.414859|-0.111598|0|238个hold失败|
|93 C2：125ps/1预算|59390.352|+3.414858|-0.111598|0|237个hold失败|
|93 C3：5ps/4096累计预算|58659.384|+3.414859|+0.001866|0|CTS阶段native通过，非最终route|
|93首次GRT|58659.384|+3.222259|-0.006039|42|12个hold失败|
|93有限route repair|58898.518|+3.222326|+0.011129|12|cap失败保留|
|93 cap候选2：12BUF_X4|58920.862|+3.238300|+0.011564|0|GRT native0，不能据此跳过严格完整表|
|93实际DRT+RCX|58920.862|+3.413180|+0.005351|7|**完整表20cap失败**；精确该网表gate现已PASS，但严格cap失败保留|
|93批量0.80裕量|59356.304|+3.316442|-0.012740|1|**完整表4cap失败、6hold失败**|
|97原映射+2tie|70104.034|-528.77|-0.002429|未在此表摘录|独立实际网表|
|97布局修复|72580.494|+3.645788|+0.008617|0|理想时钟/估计RC|
|97 CTS基线|73167.024|+3.657456|-0.214280|0|1162hold失败|
|97 C1|74539.850|+3.657456|-0.099040|0|294hold失败|
|97 C2|76498.674|+3.657456|-0.099040|0|293hold失败|
|97 C3|75270.020|+3.657172|-0.000489|0|1hold失败，不以舍入通过|
|97 C4：20ps修复目标|75477.500|+3.657172|+0.012626|0|精确post-gate正常范围已PASS|
|97首次GRT|75477.500|+3.489845|+0.002318|46|cap失败|
|97有限route repair|75608.904|+3.485171|+0.016043|5|cap失败|
|97 cap候选2：5BUF_X4|75618.214|+3.486056|+0.016718|1|原5条消除后真实重布线新增失败|
|97 cap候选3：再1BUF_X4|75620.076|+3.484627|+0.016695|3|**完整表20cap失败**；停止逐网追补|
|97批量0.80裕量|76581.932|+3.546201|-0.043177|0|完整cap/slew0，但**68hold失败**|

C3的4096是工具跨端点累计修复预算，不是4096轮全设计优化；C1一次预算不足解释了提高margin仍无改善。C4的20ps是内部修复目标，验收hold始终≥0。这些是受限电路实现机制，不是Block划分收益。[修复预算证据](../decisions/2026-10-25-issue-98-cts-repair-budget.md)。

97新cap失败有直接几何证据：`_50541_/ZN→wire604:A`连接和10个via不变，但GRT长度219.45→247.95µm，实际负载32.064598>28.991697fF。继续补该一网后又出现新失败，说明须一次性设置容量裕量，不能无限逐条修补。

## 真实DRT、RCX和金属成本

93固定seed42、最多8次迭代、20min pilot实际约2m58s，DRC依次7638/1949/1612/10/1/0；真实最终DRC报告为空、工具routed=1、天线0。没有resize/repair/antenna单元，最终Verilog与cap候选2逐字节相同。仅预先证明空GROUND标签`zero_`没有ITerm/BTerm/wire/SWire后移除；全部实际功能pin等价类保持。

独立详细SPEF接收：41566个多端点网完整覆盖，174940电阻、216506 ground cap、909698对称coupling记录（454849唯一对）；PF/OHM单位明确。逐net D_NET与ground+coupling总量仅允许实际`%g`六有效位的写出舍入界；全部RC图连通。3580未注释driver逐个证实仅为无sink/port的输出，未解释/部分未注释均0。独立新进程读回实际SPEF得到同5826端点与数值；这证明绑定与工具一致性，不是独立电磁求解。

完整DEF层账独立通过：45146电气类，41566有线nets含238 clock，3580无负载单输出；29个无端点、无几何的名字元数据逐个列入收据。873242.54µm真实中心线、286850via，与工具逐层整数报告相符；2371个显式零end-extension和CTS_NDR_0记录计入。

| 层 | signal中心线µm | clock中心线µm |
|---|---:|---:|
|M1|0|0|
|M2|216414.575|10060.420|
|M3|274626.550|8657.580|
|M4|174872.040|3405.080|
|M5|113746.835|2872.800|
|M6|64212.600|48.580|
|M7|4189.480|0|
|M8|4.800|0|
|M9|131.200|0|
|M10|0|0|

PG真实缺失，没有预留供电拥塞成本。该历史stage的M5/M6 pin未按团队55/63方案引出M8，且signal实际用到M9；不能把本研究logic island当作M1–M8固定/M9–M10后定制的同底座资格。

## GRT SPEF不是完整RC传输格式

同版本OpenROAD GRT writer的D_NET包含整网cap，但CAP只写非pin节点，pin-access wire分配到pin节点的部分会遗漏。93 cap候选2 D_NET总105598.4639696fF，而CAP写出97022.79163620fF，差8575.67233340fF。没有人为补cap或调大守恒容差；GRT STA继续用原segments的实际内存估计。

独立目录从原ODB/segments/SDC/同库重新估计可逐字节复现全部GRT SPEF并独立执行检查。实际正cap篡改、擦除cap违例章节或整份报告并重算SHA均被拒绝。此接收称工具一致性，不能称独立RC数值复算。详细RCX采用另一完整提取格式并实际读回，不混两种口径。

## 已执行批量裕量候选及联合修复依据

以下对全部非clock内部driver、当前真实RC和双load取最差比值；93采用真实详细RCX，97采用当前GRT。下表是执行前冻结选择的依据。新增BUF_X4面积1.862µm²/输入max3.401892fF/maxcap242.31fF。

| actual/maxcap阈值 |93缓冲数|93新增面积|97缓冲数|97新增面积|
|---|---:|---:|---:|---:|
|0.75|317|590.254|645|1200.990|
|0.80|227|422.674|502|934.724|
|0.85|163|303.506|365|679.630|
|0.90|105|195.510|248|461.776|

0.80集合中93有8个、97有17个原负载超过193.848fF，全部X4不能提供20%新输出余量。已有X8面积3.458、输入max6.585178、maxcap484.009；若仅该子集X8，其余X4，预计总新增435.442/961.856，单元总面积59356.304/76581.932，原预算余额20244.196/3018.568。**插入前数值不能替代重新legalize/route后的全约束检查。** 实际已按此唯一0.80候选插入并独立核库存、原FF/所有pin函数及新BUF输入加载：面积与上述预估一致，但93仍4cap/6hold、97为0cap/68hold，未进入DRT。原失败保留，不扩大阈值。

全部6/68失败均input→FF。97最差store_dout[49]路径数据到达281.402→210.993ps（快70.409ps），clock arrival237.083→237.335ps（仅+0.252ps）：新X4隔离负载使旧hold2019 CLKBUF_X1负载49.383→4.040fF，原延时148.786→41.049ps，新X4只补45.480ps。因此主要是数据加速，不宜全部归因clock漂移。93前值是RCX、后值GRT，不能混作纯几何归因。

只读实测：93/97仍各237/315 clock cells、238/316 clock nets，均159网主段变化，93无clock cell移动，97仅3叶cell≤一行/1.33µm。50ps内部hold目标影响396/592端点，而非仅6/68违例；以25ps小负载buffer为说明性估算，面积约390.222/683.088µm²（不含共享/真实工具选择，非保证）。已冻结唯一incremental hold候选：从当前margin网表，50ps内部目标、4096累计预算、10%新buffer、原79600.5面积，只一次hold+legalize+增量route，不追加full reroute。全部dirty批次/实际改动网、邻网、pin-access、完整RC/端点/严格cap与精确新gate继续验；没有放宽10ns/min0。

## 完整性、门级与范围

93全部4019FF、5826setup/hold端点、11恒定输出位；97全部5344FF、7465端点、13恒定位。所有功能/时钟/常量pin连接、原非buffercell函数和FF拓扑独立保持；新增buffer全部计价。未解释未约束端点0。

93仪器化接口2369bit（551in/1818out），纯观测1468out占80.75%；原单侧1818输出超过796槽位失败保留。四边完整pin候选通过，M5左/右600/569、M6下/上600/600。97独立2799bit（665/2134）。不能把观测膨胀当算术Block必然不可布，未来CSR/串行观测须另立实际硬件计成本。

93原映射完整门级51记录×quiet/heldreply已独立PASS（90940/90941分别1h34m37s/1h52m31s，91304接收）；每路67条接受命令。收据SHA78e43e09196115d943f92ec746e70e104751e2ae55fd6ed6154e767a506ae613，见[已校验原收据](../../project/experiments/integrated_physical/results/issue-98/checkpoint1/raw93-gate-receipt.json)。精确布局修复repair9302的双条件post-gate已PASS（90990/90991耗1h33m37s/1h50m49s，91305接收）；更晚CTS/route/joint网表独立长跑继续，不能移植。唯一预登记驱动适配是末次直接epoch寄存器注入替换为`gate-last-normal-command`；门级不把top输出赋值冒充FF注入，不宣称覆盖该terminal边界。97各精确已验布局/C3/C4网表是4运行/8正常完整输出，来自原74整数oracle和原RTL/gate；50-command RTL错误恢复/内部注入另列，不扩大gate范围。

## 成果和接续

- Issue https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/98；branch `task/98-integrated-physical`；PC `D:/Projects/LLMHardwareDesign-integrated-physical`。
- 服务器 `/public/home/yuzelu/RuizhiLiang/issue98-integrated-physical-20261025`；实际每phase的binding、每job argv/log、manifest与输入/库/结果SHA均保存；结果目录不可覆盖。
- 当前完整层账`detail-ledger9303`，严格全表`strict-electrical9302/strict-electrical9702`，RCX独立读回`detail-readback9301`；完整联合接收`detail-receive9303`实际通过数据接收并保持physical_stage_accepted=false；`negative-detail01`四种实际重SHA的RC/几何破坏均拒绝。
- 阶段checkpoint1已对7份真实收据完成服务器SHA与本机独立字节接收，精选指标/原raw gate收据可审查；全量最终归档、剩余数据跨机器接收、任务PR发布/看板读回仍未完成。根会话统一交付，不自合并或标done。成员55/63保持独立。
- 恢复第一步：核本人Slurm活动jobs和已有receipt，不重复长跑；优先完成唯一增量hold候选、全严格电气/图/RC/精确gate，再冻结最终证据包。
