# A8源码与真实服务器证据交叉审阅

以下代理仅独立读源码/数学及根任务实际执行证据，未自行启动仿真，不等于外部PR批准。审阅中的server-evidence/c02映射到正式work/Melodydt/151/a8-rtl-evidence。完整98条warning逐项说明另见a8-warning-review.md/json，功能通过仍非lint clean。

# L4 A8服务器Verilator证据独立复核

结论：r04在精确绑定的源码和声明的有限测试范围内，N29、F8 25、A8 26，共80个场景均有实际服务器Verilator通过证据。本代理只读取下载回执、日志、输入manifest与本地对应源码，执行Python证据检查；没有启动本地/远端RTL仿真、提交Slurm或修改服务器。这是项目内部独立证据复核，不是外部PR批准，不关闭整个Issue151、L4或完整Attention验收。

## 1. 实际作业、环境与证据

作业95116，名称`zenanyan-a8-all`，node1/c64，8CPU，1仿真线程；`sacct`文本为`COMPLETED|0:0|00:01:51`。服务器工作根为`/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/a8-1d72247-20261102/`，本轮结果在`runs/r04/`。执行位置符合Melodydt个人目录规则。本地下载证据为`server-evidence/c02/`。

回执记录Verilator5.042、Ubuntu C++11.4.0、Make4.3；完整runner/build/sim位于容器`orfs-26Q1-repacked.sif`，容器SHA `c742bf99ea498fb4da5135bc83fd1677abcebe0e64470e6a115f2baecb3905df`。三套build均实际使用`--binary --timing --assert`，build与simulate退出码均0。本代理逐SHA核对下载manifest内55个文本证据文件，核对日志与run-receipt的fingerprint，并独立检查场景集合、源码绑定、计数及告警，总242项读回断言通过。该数字是证据读回检查，不是新增RTL测试数。

| 对象 | SHA256 |
|---|---|
| r04/results/run-receipt.json | 251ffbf24ea5bdd20bb08ef5fdeebf0efbbb44f192f9155b1b64258b3fa0eb0c |
| simulate-n.log | d979bce05f6fe4fb770f48abb05df02d7898bb9e6b3dec90f3bd6a94b89c7bd3 |
| simulate-f8.log | 33d17f4f39aeb5feed79f2f36f4e2998547d0bf09791e4aee5559996a4a96521 |
| simulate-a8.log | bcb69c12f5ada5a9b1cd1efe09796d4016c8aa86ff55470b7557dc273cbf4bbb |

旧失败attempt没有被覆盖：c02仍保存r02的`verilator-version exit1`、r03的`build-n exit1`及相关环境/部署/调度文本。只有r04被本报告列为本次三套RTL通过；旧ModelSim回执只作为历史与独立CASE集合来源，没有被改写成Verilator结果。

## 2. 80个场景完整性与故障覆盖

| suite | 独立预期来源 | 实际唯一CASE/周期 | 最终摘要 |
|---|---|---|---|
| N | 已冻结W4 n-r01原完整29CASE回执 | 29 / 20336 | PASS_W4_N |
| F8 | 已冻结W4 f8-r01原完整25CASE回执 | 25 / 16323 | PASS_W4_F8_FFN8 |
| A8 | 实施前声明的a8-tb-contract.json完整26CASE | 26 / 9687 | PASS_W4_A8 |

本代理分别按顺序比对三份实际日志的CASE_PASS与独立预期：缺失、额外、重复均为零；并核对唯一最终PASS、最终cases数、无FAIL/断言失败以及真实退出码。三套合计80个不同CASE_ID，并非把多个日志里的重复标签累加。完整80项及其故障/生命周期子集列在同名JSON报告，预期没有从待测日志动态定义。

N仍保留真实非法opcode、helper读响应error、第二目的写ACK错误保留已存前缀、poison及协调reset恢复、257末项新max/tail、EXP原码回放、count/地址/重叠准入等场景。F8仍保留M/E/G/N真实错误，G所有已接受pair退休后才报错，以及原来的abort/reset/DONE同拍、N474写ACK门等场景。原故障用例未因Verilator迁移而删除。

A8的26项保留8组数值输入及逐阶段score/EXP/prob/output、M四S32容器、A128/B512布局、普通S及loader计数；另包含partial与末字未ACK的start门、held start、M命令/响应/loader/N服务/output反压、复用、输入/score/EXP的abort、held N/M响应及T stall reset、原生N opcode15/QK EXEC0x988c/PV EXEC0x988d错误及恢复、已有DONE遇abort+ready只消费一次、prob目的ACK后才允许PV。所用`force/release`路径在本次Verilator5.042的这些精确场景中实际走通；这不构成任意force形式或四态/X行为与其他仿真器等价的证明。

## 3. 源码与数学预期绑定

研究parent `1d722477564e14f7dc93e39ce8e28b8e2d150cb0`、native `707878621b2add4ed218b8c43df2e95c9a56e2ba`。新A8文件在运行时尚未提交，回执明确用输入精确SHA绑定；source_ref是基线，不虚称已存在交付commit。

| A8输入 | 本地formal、draft与r04输入回执一致的SHA256 |
|---|---|
| top | f6e52569b6a675caf781b7c5a917073127edcabc06cf14d80d539fb787581fc1 |
| TB | 0b5e03853d57cc25113ae3f1aafaf6aa960aa9789598ef10add853270134dce7 |
| 八组vector JSON | e75b09db507196fd7db5f9d0c9f38ed478aef28169647e3c12bafecc7644bdb0 |
| 独立整数参考 | 12af038fa7f4c642ebaca7a7826bb0d9b9ff9deb7e1230b2b6ef4af056c77398 |
| literal SVH | c96657f5fd3f09c6ed799b7364496e7d712a803ea03beb935c8b2126a2e9e84c |
| 独立26CASE合同 | 5040c3a15fbbcdef59b17c0238dac69cc16c2d1d0ea0742cc9d22bfaf76cf738 |

本地source-r04-manifest与服务器导出的input-r04/source-manifest完全一致；manifest每项与正式集成文件逐SHA一致，run-receipt的输入SHA也逐项核对。本次下载主要是文本证据及manifest，没有把未下载的可执行文件或波形描述为本代理已检查。服务器runner回执记录其source snapshot与编译/执行信息。

与前W4包逐字节比较，32份继承SV/SVH全部不变，包括原叶、已有控制器和原N/F8 TB；完整清单及SHA在JSON。这个32是代码不变证明，不表示所有32条路径都获得了本次独立功能资格。N/F8 selected路径具有本次29/25场景的服务器回归证据，其余资格仍按原边界维护。

八组vector保持非恒定/非对称、equal-score、zeroQ、末key极值新max、交替符号极值、稀疏identity、负Q混合K、常值V通道。EXP数学表由独立math/Decimal重建，RNE/Fraction及QK/PV公式已在前置Python检查中验证；本次没有从DUT抓输出生成expected。QK factor11585/RNE19→Fin10，prob Q14×V Fin7经RNE11→Fin10。K token-major与V channel-major分别检查。当前S8/D8输入不会触及S16夹限，八组done_saturated=false不能被描述为饱和路径全覆盖。

## 4. A8全局计数差额的精确解释

正常成功帧单独断言：12入口，S23请求/ACK=19写+4读，M10cmd/rsp、2loader、N6cmd/rsp、T一字take后release。suite里25个正常成功帧，另有13项额外事务小计：其中一项在T字已被消费后abort，另外12项为取消或故障事务。按固定TB步骤逐项重算，得到与日志完全相同的：

`input424, Sreq741, Sack738, Mcmd302, Mrsp301, Ncmd180, Nrsp180, Ttake26`。

| 额外事务 | input | Sreq/ACK | Mcmd/rsp | Ncmd/rsp | Ttake |
|---|---:|---:|---:|---:|---:|
| 已消费T前缀后abort | 12 | 23/23 | 10/10 | 6/6 | 1 |
| 捕获入口但S未接受即abort | 1 | 0/0 | 0/0 | 0/0 | 0 |
| 入口写ACK待回abort | 1 | 1/0 | 0/0 | 0/0 | 0 |
| 完整输入但未RUN即abort | 12 | 12/12 | 0/0 | 0/0 | 0 |
| score460写ACK待回abort | 12 | 13/12 | 5/5 | 0/0 | 0 |
| 两入口beat后reset | 2 | 1/1 | 0/0 | 0/0 | 0 |
| N服务完成响应保持时reset | 12 | 18/18 | 5/5 | 6/6 | 0 |
| committed T尚未take时reset | 12 | 23/23 | 10/10 | 6/6 | 0 |
| 原生N非法opcode错误 | 12 | 14/14 | 5/5 | 2/2 | 0 |
| QK EXEC错误 | 12 | 12/12 | 3/3 | 0/0 | 0 |
| PV EXEC错误 | 12 | 21/21 | 8/8 | 6/6 | 0 |
| EXP461写ACK待回abort | 12 | 16/15 | 5/5 | 4/4 | 0 |
| M CLEAR响应保持时reset | 12 | 12/12 | 1/0 | 0/0 | 0 |

因此S差3正是入口写、score460写、EXP461写的三个已接受但ACK被协调abort取消的事务；M差1正是held CLEAR(op6)响应被hard reset取消。N180/180完整退休。两个入口beat后reset时，第二beat仅由顶层捕获，还未被原生S接受，故该项是input2但S1/1，不能凭input数补造S丢响应。Ttake26比正常成功帧25多1来自已消费前缀后abort，不代表回滚。

继承N的全局差额也保留同样语义：S715+288=1003对ACK1002是一次待回EXP写ACK reset，N624/623是一次held BEGIN响应reset；21成功+8准入错+3poison错=32完成，两取消服务不造完成。F8 S1224/1221来自入口、原X466、N474三处ACK待回abort，M413/413；正常成功帧仍逐次39/39。没有将含reset的全suite写成无条件请求/响应守恒证明。

## 5. 告警及尚未接收的范围

三套编译保留98条告警：N33、F8 29、A8 36，类别合计TIMESCALEMOD54、WIDTHEXPAND37、WIDTHTRUNC7。runner明确使用`-Wno-fatal`，未按category屏蔽告警；报告保留完整warning header、类别和日志，`lint_clean_claim=false`。本代理逐log重算告警数量/类别与回执一致。功能通过不能替代width/timescale处理、lint清零、综合、STA或物理验收。

本报告接受的是声明的有限QK→Softmax→PV与N/F8回归证据。未完成完整A_plain/QKV与output投影、Norm、RoPE/GQA、mask、KV-cache、残差、多head/多组、真实模型shape/容量/量化质量、MEM、完整产品程序/永久金属绑定或PPA。没有因本次结果擅自转入L5、关闭全部L4、批准PR或提升Issue状态；根任务负责正式整合、上传与要求的外部审查。


---

# A8设计、独立数学与TB静态交叉检查

检查对象为本目录A8 top、根A8_ABI、另一作者的 `a8_integer_reference.py`、冻结向量及 `block_w4_a8_tb.sv` / `a8-tb-contract.json`。本检查只读源码；没有执行RTL compile/simulation或外部PR批准。A8 top由本审阅者编写，数学/TB为另一作者，不能把作者对自身RTL自审写成独立外部审查。

发现并已由root采纳的两项ABI纠偏：PV A base原拟462不满足native loader四字对齐，改为prob464/pad465..467/output468；native M CLEAR为op6，MC_CLEAR=0只是本地阶段编号。当前ABI已修正，RTL不需要迁就错误opcode。其余本次检查未发现阻断问题。

数学oracle按独立公式重建1025项EXP，只解析native表作版本一致性检查，不以DUT输出作为期望。QK整数dot乘11585后RNE19、Softmax全组max/EXP/floor factor/RNE30和PV prob×V后RNE11与所选native路径相符。特别地，native EXP执行lo+RNE(delta*fraction,4)，oracle没有误用对lo+fraction合计的另一种tie parity。EXP32768保留U16位模式；PV的概率按非负S16 Fin14解释。两次op5的4×S32 carrier按低16抽取、first-half低4/second-half高4顺序正确。

TB预先声明8个数值向量及26个CASE，不从DUT日志抽取来定义预期覆盖。已静态检查：K key-major与V channel-major512-bit完整拼接；Q A128及prob A128；S loader配置与两个M投影格式/scale/descriptor；23普通S/19W4R、M10/N6/load2/T1；score/EXP/prob/padding/output逐stage实际写数据与ACK；N op3取score/op6取exact EXP；N响应保留时禁止PV提前启动；最后prob目的ACK与PV之间的门；真实native N op15、QK988c、PV988d错误与新帧恢复；abort/reset/held output/DONE+abort+ready和T release。

loader命令accept先把loads计数推进，后续真实A/B握手据此选择QK或PV期望，当前比较的边沿顺序正确。故障例关闭strict_native descriptor逐项断言但保留错误后无发布、存储及恢复断言，避免把故意非法命令当正常命令接受。normal_counts只用于完整成功帧，全suite取消事务不要求无条件计数相等。

限制：8向量/26CASE仍是待服务器Verilator执行的有限计划，不是RTL通过、全部输入或参数空间覆盖。该A8合法S8数值范围下score与最终值通常均在S16内，done_saturated检查不代表新增clip边界穷举。两状态/X、层级force、timing/reset注入和数组访问的实际Verilator兼容性须由root服务器真实compile/run及具体guard日志证明，不从旧ModelSim证据转移。无完整A、掩码/causal、RoPE/GQA、真实模型尺寸、外存或PPA资格。


---

# 正式服务器脚本只读复核

复核对象为当前`integrated/work/Melodydt/151/run_a8_verilator.py`与`prepare_a8_sbatch.py`，未覆盖正式文件，也未执行HDL/SSH/sbatch。执行`check_server_final.py --root <integrated> --output <本目录/server-final-static-checks.json>`：两脚本AST/Python编译、正式源及独立authority校验、N29/F8 25/A8 26共80项完整集合、24项合成日志正反例、两次本地preparer输出和三种非法配置拒绝均通过。所有正式输入SHA在检查前后相同；具体SHA和本地仅供检查的输出脚本在JSON记录，不能提交这些REVIEW_ONLY脚本。

## ROOT诊断

已读回`server-evidence/c01/runs/r02`及r03真实receipt和version日志。两次CLI请求及receipt解析后工具路径均为`/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator`，wrapper都是28119B、SHA`deaac572105cb908ace4f66b845e68905f162aa3e364df964f707172f4693462`；镜像SHA也相同。r02的container.VERILATOR_ROOT是手设prefix，version退出1并报inconsistent path；r03该字段null，version退出0、识别Verilator5.042，继续进入N编译。

官方wrapper用FindBin的RealBin及安装时替换的pkgdatadir相对路径计算真实ROOT，并用realpath检查手设ROOT是否相等。安装prefix不能凭目录名假定为ROOT，具体包的计算值应由实际安装配置证明；本审阅不猜其目录。见[官方源码](https://github.com/verilator/verilator/blob/master/bin/verilator)。由于r02/r03请求路径与Path.resolve后的路径没有变化，没有证据把该错误归因于Python.resolve；Perl本身也采用RealBin。回执未保存lstat/readlink，因此不能仅据此证明文件绝非symlink，但已排除本次可观察的执行路径改写。保留requested/resolved/is_symlink/readlink元数据可进一步增强追溯，不是此次恢复的前置条件。

## 正式改动审阅

preparer和make_job移除了VERILATOR_ROOT参数/env注入，HOME改为个人bootstrap的`--home`，shared runtime由make_job显式传`/public/software/singularity-ce-4.3.4/bin/singularity`。cache/tmp/Slurm资源/目录/新输出保护仍在。r03实际version成功支持此环境修正；该成功不等于RTL仿真通过。

runner新增的`--nonfatal-warnings`默认为false、需显式opt-in；只追加`-Wno-fatal`，不移除任何warning类别、assert、timing或故障用例。实际warning完整log、每suite类别计数和header保留，回执明确不是lint clean。r03默认fatal的33项warning证据保留；warning逐项是否接受仍由源码审阅负责，不能用flag取代判断。新runner还记录同目录verilator_bin指纹，并在全部suite成功后核对wrapper/core前后SHA；若运行提前失败，当前代码保留其before信息和失败日志，不应把缺少after字段写成已经完成前后核验。

完整CASE/精确PASS/summary/非零退出/显式FAIL的判据保持原样，A8仍用独立CASE合同的SHA、module和TB SHA复核；不能只数marker或因兼容性删除fault。只读复核未见这些正式流程改动的阻断。真实Verilator是否覆盖80项、工具是否稳定和全部warning结论，仍以主任务实际新run回执及独立源码审阅为准，不由本地Python检查代替。
