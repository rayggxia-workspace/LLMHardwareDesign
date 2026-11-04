# Issue179：局部Block接续研究与协作欠项

## 2026-11-05 04:09 CST：第14步实际双局控控制门

Issue179／Draft PR180，负责人Melodydt，父dc23b38。实际母控＋2LC取指／全包任务返回，有限16KiB SRAM／ACK网络；10集成／4错误轨迹拒绝，R4有界门满足。97243／node27／debug／4核COMPLETED0:0、27秒，25局控回归通过；26母控回归来自97238且源／checker不变。两次失败与修正记录保留，106输入源／61日志／4编译SHA核验。无reset连续job、两端不同task_sequence再执行、READY传参、背压独立推进及RX不可关闭时隔离均有实际控制证据。存储／链路是有限peer，不是原生S、完整Block或物理。
原方案／同名PDF更新，PR176无变化；下一步R5五类candidate控制profile、分支循环、old-next与取消／协调复位。研究in_progress，PR Draft／未合并；登记pending，看板unverified／同步pending，审查／管理员待指定。全部仿真服务器执行，额度不足保存停止，不使用额外额度，无后台监测。

### 当前恢复入口（优先于下方历史）

仓库rayggxia-workspace/LLMHardwareDesign，Issue179／PR180，task/179-local-block-continuation，base task/175-local-block-design；PR父dc23b38，远端最终SHA见PR回执及外层remote-delivery-receipt.json。本地D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/control-rtl-network-dc23b38/delivery为无.git部分API副本，旧目录保留。控制DUT无改动，新增网络peer／日志交叉checker与观测器语义扩展，正式产物／进度见验证索引。
服务器yuzelu@10.129.166.172，/public/home/yuzelu/Melodydt/issue179-control-network-dc23b38/r003/source，实验commit738720d495eaf5ea53f123bfaacc67c19ef3ff68；包SHA1f9e442377e9bfd33650fc8c9e01e385ff87b9ca816e60f5cc1d8e4b5a4f83ee。97238 FAILED1:0（51原回归及9集成已过）、97239 FAILED1:0（观察器IREG取消语义）、97243 COMPLETED0:0，所有作业结束，无后台监测。均node27／debug／4核，最终results/network/network_report.json和slurm-97243.log；母控回归results/mother在r001，局控最终回归在r003。原始包evidence-97243.tar.gz，SHAee073ac145d7c7e21ee5db0313c9904d218e9f31725640e0fee2ffc33bea6c97，本地server-evidence为副本。

```bash
squeue -j 97238,97239,97243
sacct -j 97238,97239,97243 --format=JobID,JobName,State,ExitCode,Elapsed,NodeList
tail -n 40 /public/home/yuzelu/Melodydt/issue179-control-network-dc23b38/r003/slurm-97243.log
cat /public/home/yuzelu/Melodydt/issue179-control-network-dc23b38/r003/results/network/network_report.json
```

恢复第一步：Melodydt核周额度／PR176／PR180／Issue179和讨论／远端头，开始R5。R4有界门满足；母控／两个LC实际RTL，S／链路仍有限peer。R5需五类candidate资源／ABI profile、分支循环、非零old／next、消费者义务与提交／首错前缀、取消及协调复位；编码保持ISA v0.1，未知native不默认准入。R4网络参数MC/LC STALL4096、LC DRAIN128；真实RX不能close时隔离，不以peer凭空完成取消。R5／通用RTL／原生服务／数值／完整Block／物理未完成。每步更新原方案和PDF，额度不足停止；负责人Melodydt，审查／管理员待指定。


## 2026-11-05 03:46 CST：第13步母控协议RTL

Issue179／Draft PR180，负责人Melodydt，父2384c31。母控5指令、2目标／8token、实际PM装载／取指、CALL参数快照、READY／G_WAIT及首错取消／排空；97234／node27／debug／4核COMPLETED0:0，26场景／4突变拒绝。两个子端为有限协议peer，R4实际两个局控接入尚待，非完整Block。94源文件、日志／输出SHA和97230～97234失败／通过记录见control-mother-validation.json；173软件／128局控RTL源未变，复用既有证据。
原方案及同名PDF更新。下一步实际母控＋两个LC／有限SRAM链路，再R5；PR176无变化。研究in_progress，Draft／未合并，审查人待指定；登记pending，看板unverified／同步pending，管理员待指定，无后台监测。所有仿真服务器执行，周额度不足保存停止，不使用额外额度。

### 当前恢复入口（优先于下方历史）

仓库rayggxia-workspace/LLMHardwareDesign，Issue179／PR180，分支task/179-local-block-continuation，base task/175-local-block-design；PR父2384c31，远端最终SHA见PR回执／外层remote-delivery-receipt.json。本地D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/control-rtl-mother-2384c31/delivery为无.git部分API副本，旧目录保留。本轮新母控源码／轻量证据已整理，上传事实以回执为准。
服务器yuzelu@10.129.166.172，/public/home/yuzelu/Melodydt/issue179-control-mother-2384c31/r005/source，实验commit3b4ef844df72346271988ce33b5941cc3fa82aba，包SHA e215d4a38b9da476c686c0d5f2ded52c7081a5354d27f15262c47ab22cf08015；结果r005/results/mother/mother_report.json，日志r005/slurm-97234.log。97230／31／32／33 FAILED1:0，97234 COMPLETED0:0，所有作业已结束，均node27／debug／4核。原始证据evidence-97234.tar.gz，SHA06c5142f7094011bae7670714070ca19821cc0f298af060cea3b9dbd14194e5d，本地server-evidence为下载副本。

```bash
squeue -j 97230,97231,97232,97233,97234
sacct -j 97230,97231,97232,97233,97234 --format=JobID,JobName,State,ExitCode,Elapsed,NodeList
tail -n 40 /public/home/yuzelu/Melodydt/issue179-control-mother-2384c31/r005/slurm-97234.log
cat /public/home/yuzelu/Melodydt/issue179-control-mother-2384c31/r005/results/mother/mother_report.json
```

恢复第一步：Melodydt核额度、PR176／PR180／Issue179与讨论／远端头，连接实际两个LC RTL。先消费者READY再生产者，有限16KiB SRAM／ACK，两个job无reset、返回与取消独立推进；真实RX不能完成时应隔离，不能照搬本步peer可总是闭合取消的假设。之后R5五类控制profile／old-next／分支循环／协调复位。R4整体及R5未完成；G_PARAM／算术／循环分支、通用服务／原生S／RX-close／provider复位／flit串行化／完整Block／物理未验收。每步更新同一方案及PDF；额度不足停止，不启用额外额度。处理人Melodydt，审查／看板管理员待指定。


## 2026-11-05 02:44 CST：第12步P／RAW16控制门

Issue179／Draft PR180，负责人Melodydt，父76fc765。9类局控指令的受限P／RAW16控制profile已具备进入R4证据：寄存器值读回、有限16KiB SRAM／16B接收槽、RX写后ACK、TX收到ACK后完成、对象valid／DROP、两任务新payload及取消／隔离。存储与链路仍为行为peer，不是原生S、通用控制器或完整Block。
173既有检查＋103原RTL来自97227（后续新TB编译位宽失败）；最终97229／node27／debug／4核COMPLETED0:0，25新场景／4轨迹突变拒绝。DUT与旧回归源SHA一致，三份新测试文件修正，失败日志均保留。原方案／同名PDF补进展；下一步R4母控二进制取指与两个局控，之后R5。研究仍in_progress；登记PR5 pending，看板unverified／同步pending，审查人／管理员待指定，无后台监测。

### 当前恢复入口（优先于下方历史）

仓库rayggxia-workspace/LLMHardwareDesign，Issue179／PR180；task/179-local-block-continuation，base task/175-local-block-design，PR父76fc765，最终远端SHA见PR回执。本地D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/control-rtl-transfer-76fc765/delivery为无.git部分API副本，旧目录保留；外层remote-delivery-receipt.json上传核验后记录远端状态。
服务器yuzelu@10.129.166.172，/public/home/yuzelu/Melodydt/issue179-control-transfer-76fc765/r003/source，实验commit7d8790967e46314a37e27428e5346fd209d956a9；输入包SHA107d34286632b7122300596751898f7c26d25c8e3763e184016ad10c5584265e。97227 FAILED1:0、45秒（173软件＋103旧RTL已通过，新TB位宽）；97228 FAILED1:0、15秒（负向测试先命中未声明输出）；97229 COMPLETED0:0、14秒，均node27／debug／4核。控制RTL／旧回归源未变，最终只改三份新测试源。没有未结束作业。
启动sbatch --parsable job-r003.sh；日志slurm-97229.log；结果results/transfer/report.json。旧回归在r001/results/{baseline,cancel,fault,adapter,object}，不得把97227整体写为通过。证据包在任务根evidence-97229.tar.gz，SHA897532b981eb46a55fde97909ce908d8c9a7fe11f60da34c0d0c56de660435ee；本地server-evidence为下载副本。84最终源、128当前场景日志与8编译日志SHA核验；部分重复／失败日志额外保留。

```bash
squeue -j 97227,97228,97229
sacct -j 97227,97228,97229 --format=JobID,JobName,State,ExitCode,Elapsed,NodeList
tail -n 40 /public/home/yuzelu/Melodydt/issue179-control-transfer-76fc765/r003/slurm-97229.log
cat /public/home/yuzelu/Melodydt/issue179-control-transfer-76fc765/r003/results/transfer/report.json
```

受限P控制门已满足：九局控指令、128当前RTL场景／173软件和寄存器、对象、ACK、背压／错误／两任务证据。仍未测试原生S口、flit串行化、RX-close、真实provider协调复位、完整Block／母控／物理。恢复第一步由Melodydt核额度、最新PR176／PR180／Issue179／评论及远端头，开始R4母控二进制取指与两个局控；完成后继续R5五类profile／状态。每步只增补原方案和同名PDF，额度不足停止。


## 2026-11-05 02:06 CST：第11步对象生命周期

Issue179／Draft PR180，负责人Melodydt，父ddac1c8。单RAW16对象预约／DROP、错误／取消清理及范围互锁通过，执行／对象描述符使用显式loaded位拒绝整记录全零。服务器97225／97226均node27／debug／4核COMPLETED0:0；173既有检查＋76原控制／适配器RTL＋27对象场景通过，3新轨迹突变拒绝。r003只改runner新增全零执行描述符测试，DUT／其他仿真源与r002 SHA一致，因此旧回归有效关联且不重复计数。
现有总方案及PDF继续原位补充；下一步有限RAW16存储／RX/TX／ACK／READY报告，再R4／R5。当前仅逻辑预约；无S数据有效性与寄存器值读回、完整Block／母控／物理证据，R3整体未完成。登记PR5 pending，看板unverified／同步pending，审查人／管理员待指定。研究in_progress，未配置后台监测。

### 当前恢复入口（优先于下方历史）

仓库rayggxia-workspace/LLMHardwareDesign，Issue179／PR180；task/179-local-block-continuation，base task/175-local-block-design，PR父ddac1c8，最终远端SHA见PR回执。本地D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/control-rtl-object-ddac1c8/delivery为无.git部分API副本；旧目录保留。外层remote-delivery-receipt.json于上传后记录远端核验。
服务器yuzelu@10.129.166.172，/public/home/yuzelu/Melodydt/issue179-control-object-ddac1c8/r003/source，实验commit6df461bc7b4429fb83975bdae0e3ce8337b834ba；输入包SHA724d0c3958442204e8eb468abe1b9d1340695874a9158c8005e5a59aa94f7c61。97225／r002为173软件＋76旧RTL＋26对象；97226／r003为新增全零执行记录后的27对象，仅runner变化，DUT SHA完全一致。两作业均COMPLETED0:0，node27／debug／4核，44秒／10秒，无未结束作业。
启动sbatch --parsable job-r003.sh；日志slurm-97226.log，结果results/object/report.json；旧回归在r002/results/{baseline,cancel,fault,adapter}。两份完整启动脚本均已收仓。证据包位于任务根evidence-97226.tar.gz，SHA2d9ff3ef33d1bb197258b360c5924156cdfbce54709eed523de401774f3c7dfb；本地server-evidence为下载副本。79最终源文件、103当前场景日志及6编译日志SHA已核验；原26对象日志额外保留，未重复计数。

```bash
squeue -j 97225,97226
sacct -j 97225,97226 --format=JobID,JobName,State,ExitCode,Elapsed,NodeList
tail -n 40 /public/home/yuzelu/Melodydt/issue179-control-object-ddac1c8/r003/slurm-97226.log
cat /public/home/yuzelu/Melodydt/issue179-control-object-ddac1c8/r003/results/object/report.json
```

成功判据已满足：27对象／3错误轨迹、旧76RTL／173软件，0:0；只有逻辑对象预约／释放及MOVI退休，没有S数据或寄存器值读回证明。恢复第一步由Melodydt核额度、最新PR176／PR180／Issue179／评论及PR头，再补RAW16有限存储peer、RX/TX／ACK／READY及寄存器观测，然后R4／R5；每步维护原方案与同名PDF，额度不足停止。


## 2026-11-05 01:45 CST：第10步M服务适配器

Issue179／Draft PR180，Melodydt，父af680f3。严格M_CLEAR_ALL_VALID适配器已接现有未改block_v2_m（blob d91ffdf904bc77c19d5d0ecfd4cd11560b44a417）；服务器97224／node27／debug／4核COMPLETED0:0，173既有检查＋61原RTL＋15适配器场景通过。5场景接真实M RTL、5命令／5响应逐次关联，10协议peer场景及3轨迹突变拒绝；clear不含GEMM数值或完整Block资格。源码实验commit944648b45efcf962091b3ca13c0d6dfd35501d5b，输入包SHA7222db6feced886a58f28819a4610551059b0853587fe8fa00aad89ac5248f20。
现有总方案及PDF补进展；下一步对象窗口／寄存器／收发事件，再R4／R5。研究in_progress，R3整体未完成；真实provider协调复位、其他宏服务与物理尚待。登记PR5 pending；看板unverified／同步pending，管理员／独立审查人待指定；未配置后台监测。

### 当前恢复入口（优先于下方历史）

仓库rayggxia-workspace/LLMHardwareDesign，Issue179／PR180；task/179-local-block-continuation，base task/175-local-block-design，PR父af680f3，最终SHA见PR回执。本地D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/control-rtl-adapter-af680f3/delivery，无.git部分API副本；旧目录保留。外层remote-delivery-receipt.json在上传核验后记录远端状态。
服务器yuzelu@10.129.166.172，/public/home/yuzelu/Melodydt/issue179-control-adapter-af680f3/r002/source，实验commit944648b45efcf962091b3ca13c0d6dfd35501d5b。97223 FAILED1:0（日志cycle编号），97224 COMPLETED0:0、36秒，均node27／debug／4核；没有未结束作业。实际启动sbatch --parsable job-r002.sh，日志slurm-97224.log，结果results/{baseline,cancel,fault,adapter}/report.json。证据包在任务根evidence-97224.tar.gz，SHA c06023e89191302b67f587c2d637023d1993335d60fc459e35364a30f69bf201；75源文件、76场景及5编译日志SHA核验，本地server-evidence为下载副本。

```bash
squeue -j 97224
sacct -j 97224 --format=JobID,JobName,State,ExitCode,Elapsed,NodeList
tail -n 40 /public/home/yuzelu/Melodydt/issue179-control-adapter-af680f3/r002/slurm-97224.log
cat /public/home/yuzelu/Melodydt/issue179-control-adapter-af680f3/r002/results/adapter/report.json
```

成功判据已满足：15适配场景及3错误轨迹拒绝、旧61控制场景与173检查、Slurm0:0；只验证独占M clear，不扩张为GEMM、S或完整Block。provider_released由外部保证已复位且无旧响应；真实cohort协调器未实现。未提交宏变化、ref-project、原始大包或凭据。
恢复第一步由Melodydt核额度、最新PR176／PR180／Issue179／评论及工作区，确认PR头后研究对象窗口／寄存器及收发事件，再R4／R5。每步维护原方案及PDF；不启用额外额度。


## 2026-11-05 01:25 CST：第9步故障RTL

Issue179／Draft PR180，Melodydt；父96b8280。当前M clear子集新增CALL身份准入、运行错误、native错误优先、有界无进展隔离；服务器97222／node27／debug／4核COMPLETED0:0，173既有＋10原RTL＋22取消＋29故障通过，两类各6项轨迹突变拒绝。源码实验commit f41158211ef69bb74a9252bd1790e53572e095e0，输入包SHA cac75c8d153b5afac4f04569326901d1e080dfc158eb866d8027cb0e3e71761e。
原TWO_LEVEL_CONTROL_PLAN.md及同名PDF补充进展；下一步服务适配器／对象／收发，再进入R4／R5。研究仍in_progress，未完成R3整体或真实Block；真实provider协调复位、母控、数值／物理未验收。登记PR5 pending；看板unverified／同步pending，管理员／审查人待指定；无后台监测。

### 当前恢复入口（优先于下方历史）

仓库rayggxia-workspace/LLMHardwareDesign，Issue179／PR180，task/179-local-block-continuation，base task/175-local-block-design，PR父96b8280，最终PR commit见PR回执。本地D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/control-rtl-fault-96b8280/delivery为无.git部分API副本；当前成果及提交范围见同目录外层remote-delivery-receipt.json（上传后生成），旧目录保留。
服务器yuzelu@10.129.166.172，/public/home/yuzelu/Melodydt/issue179-control-fault-96b8280/r005/source，实验commit f41158211ef69bb74a9252bd1790e53572e095e0。97219／97220／97221 FAILED1:0（位宽、观察器边沿、突变取样）；97222 COMPLETED0:0，node27／debug／4核，25秒，无未结束作业。实际启动sbatch --parsable job-r005.sh，结果results/{baseline,cancel,fault}/report.json，日志slurm-97222.log。证据包位于任务根evidence-97222.tar.gz，SHA feb885a9993b6948780ead04ae20551a5bf5bbb3343c3756eede4d3bc5269a25；本地server-evidence为已核验下载副本，66源文件、61场景日志及三份编译日志SHA一致。镜像容器完整SHA待核实。

```bash
squeue -j 97222
sacct -j 97222 --format=JobID,JobName,State,ExitCode,Elapsed,NodeList
tail -n 40 /public/home/yuzelu/Melodydt/issue179-control-fault-96b8280/r005/slurm-97222.log
cat /public/home/yuzelu/Melodydt/issue179-control-fault-96b8280/r005/results/fault/report.json
```

成功判据已满足：29故障场景＋6轨迹突变、22取消＋6突变、10原RTL、173软件检查和0:0。有限peer同时复位／全镜像重装只证明本控制切片；真实无tag provider复位与系统协调仍待，不能据此接入未验证宏。
恢复第一步：由Melodydt检查额度和最新PR176／PR180／Issue179／评论，确认目录及远端头，再研究服务适配器、对象／收发；用户授权继续到R5且每步只更新现有总方案及PDF。未配置后台监测。


2026-11-04，Asia/Shanghai。仓库rayggxia-workspace/LLMHardwareDesign，project_id=llm-hardware-design；[Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179)，负责人Melodydt。优先级/审查人/Projects处理管理员待指定。

## 2026-11-05 01:00 CST 第8步（优先恢复此段）

Issue179／PR180，负责人Melodydt；分支task/179-local-block-continuation，base task/175-local-block-design，PR父a54cbc4，最终SHA见PR回执。本地独立部分API目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/control-rtl-cancel-a54cbc4/delivery，无.git；旧目录保留。服务器/public/home/yuzelu/Melodydt/issue179-control-cancel-a54cbc4/r003，独立实验commit6950be60082c1e5320843c2dce144410cfb3633d。

97216／97217 FAILED1:0（testbench终态分支收尾），97218 COMPLETED0:0，均node27／debug／4核。最后启动sbatch --parsable job-r003.sh；日志slurm-97218.log，结果results/baseline/report.json及results/cancel/report.json。原始证据包evidence-97218.tar.gz位于该任务服务器根，SHA15d755f0b90aecff38a3395cf11f4aa5ee185d03b03197613f87f760001c4594。源码包SHA7cd7e49939c2fc01734ab49c96cf1517075527d4ccf79fe9d6f9fef83e409446，62源文件核验；仿真均在服务器，文档在本地渲染。

```bash
squeue -j 97218
sacct -j 97218 --format=JobID,State,ExitCode,Elapsed,NodeList
tail -n 60 /public/home/yuzelu/Melodydt/issue179-control-cancel-a54cbc4/r003/slurm-97218.log
cat /public/home/yuzelu/Melodydt/issue179-control-cancel-a54cbc4/r003/results/cancel/report.json
```

173既有检查、10原RTL、22取消场景通过；19安全结束、3预期隔离和6项轨迹破坏拒绝。M／PM仍为peer，不具备真实cohort复位证明；超时保留资源义务，不产生完成任务的假终态。
用户授权自动继续至R5，每步增补现有TWO_LEVEL_CONTROL_PLAN.md和同名PDF；周额度接近耗尽前保存并停止，不使用额外额度或重置。下一步先检查额度、PR176和当前Issue／PR，再研究运行异常／故障与取消竞态，之后继续R3适配器／对象／收发、R4与R5。没有聊天结束后的自动监测。登记PR5 pending，看板unverified／同步pending，管理员／独立审查人待指定。

## 23:47 CST 第7步最小功能局控（历史记录）

Issue179／Draft PR180，负责人Melodydt；分支task/179-local-block-continuation，base task/175-local-block-design；PR父41777f1d，最终远端SHA／上传核验见PR180回执。
本地D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/control-rtl-min-41777f1/delivery为无.git的部分API副本，旧目录不覆盖；实验快照位于snapshot-r001～r005，服务器源码另有独立Git commit，不能混称PR分支HEAD。

服务器yuzelu@10.129.166.172；最终工作目录/public/home/yuzelu/Melodydt/issue179-control-rtl-41777f1/r005，独立实验commit d880b56ee06414d6f3e344b20e19ce6badc00feb，源码包SHA 2b683442febe31c0872b7af5a55b3daba0af0f9423a4cd5d225bfcb2e0f56b03；源码37文件已与本地逐项核对。
Verilator5.042在宿主因GLIBC不兼容，使用Singularity4.3.4和既有ORFS26Q1容器，G++11.4／Python3.10.12；安装和安全设置未改。认证通过本人已有公钥，凭据不入成果包。
97211 FAILED1:0（位宽），97212 FAILED1:0（peer信用保持），97213 FAILED1:0（execution ABI偏移），97214 COMPLETED0:0（7场景），97215 COMPLETED0:0（10场景），均node27／debug／4核，当前无运行中作业。

```bash
squeue -j 97215
sacct -j 97215 --format=JobID,State,ExitCode,Elapsed,NodeList
tail -n 60 /public/home/yuzelu/Melodydt/issue179-control-rtl-41777f1/r005/slurm-97215.log
cat /public/home/yuzelu/Melodydt/issue179-control-rtl-41777f1/r005/results/report.json
```

源码source/、实际启动脚本job-r005.sh、日志slurm-97215.log、结果results/均持久保存；证据包/public/home/yuzelu/Melodydt/issue179-control-rtl-41777f1/evidence-97215.tar.gz，SHA 977ed2f099e4947b0cbbcf7b2b258027f7caf5d8ffbc5030a439d07f99e1fc08。本地server-evidence为下载副本，仓库只收轻量报告／索引和复核脚本。
成功判据已满足：最终作业0:0，10个RTL场景PASS，5实际执行轨迹独立checker通过；本地37源码SHA、日志SHA、6完整终态包和旧173检查核验。未执行四态、综合、真实M／S／完整Block、母控RTL、LLM数值或物理，不代表R3整体完成。
下一步负责人Melodydt先核最新Issue／评论、PR180和PR176及同步历史，运行ARCHITECTURE所列检查，再补取消／异常排空和服务适配器；随后扩RAW16／RX/TX。每轮更新总方案。
研究in_progress，PR Draft／未合并；登记PR5 pending，看板unverified／同步pending，处理管理员和独立审查人待指定。聊天结束后没有自动监测。

## 21:54 CST 第6步局控RTL合同（历史记录）

仓库／负责人／Issue／PR同上；分支task/179-local-block-continuation，base task/175-local-block-design，父e079924c7956c1fddf0994db5ba7cc67fede691a；独立部分API目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/control-rtl-contract-e079924/delivery，无.git／HEAD／index，仅上传白名单，旧包不覆盖。本地发布前资料不等于Git提交；最终远端commit／原文／CI见PR180。

恢复先读规则、Issue／评论、PR180、PR176 head／正文／评论／review／逐行评论并核pr176-sync.json；有差异先同步，上传前再核，每轮进展继续直接补总方案。

[第6步合同](../local-blocks/LOCAL_CONTROL_RTL_CONTRACT_V0_1.md)与project/control_rtl_contract_v0_1交付92逻辑信号／状态机候选、单PM端口／装载准入／信用／RX关闭、SystemVerilog声明与36组边界检查，累计173组。4份人工期望时序不是DUT轨迹，HDL编译／lint／仿真未执行；本机PATH未发现iverilog/verilator/yosys。来源／实际验证见work/Melodydt/179/control-rtl-sources.json及control-rtl-validation.json。

先运行管理检查、七套单测、声明／示例--check及既有两campaign重建；下一步实现配置／单口仲裁、CALL／FETCH、空任务和M clear的EXEC/WAIT/END功能局控RTL，再扩RX/TX／取消。逻辑端口不等于宏原生pin或物理冻结；内部tag不解决无tag迟到响应。真实provider复位、SRAM/CDC和完整Block仍为外部接入门，未授予控制RTL或物理资格。

负责人Melodydt继续；无服务器作业／节点／日志／结果或自动监测；研究in_progress、PR Draft／未合并；登记PR5 pending，看板unverified／同步pending（缺board.json／Projects工具），管理员／审查人待指定。

## 20:58 CST 第5步恢复研究（历史记录）

仓库／负责人／Issue／PR同上；分支task/179-local-block-continuation，base task/175-local-block-design，父c22dde6972e0f86600ecdc4060409e6947b19fb8；独立部分API目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/control-recovery-c22dde6/delivery，无.git／HEAD／index，仅上传白名单，旧包不覆盖。本地发布前文件不等于Git提交，最终远端commit／原文／CI见PR180。

恢复先读规则、Issue／评论、PR180和PR176 head／正文／评论／review／逐行评论，比较pr176-sync.json；有变化先同步合同，上传前再核。每轮目标、上游、产物、实际验证、限制及下一步仍须直接补总方案。

[第5步合同](../local-blocks/CONTROL_RECOVERY_PLAN_V0_1.md)与project/control_exec_v0_1新增恢复模型／独立检查器。9取消／poison＋9恢复、168退休、2模型复位cohort；30新增、累计137组。旧9执行报告、镜像与人工参考不改；来源／实际验证在work/Melodydt/179/control-recovery-sources.json及control-recovery-validation.json。运行管理检查、六套单测、两种campaign逐字重建后，冻结局控RTL周期级接口／状态机／写口互锁与真实provider确认清单。

重要边界：无tag旧响应在新上下文中可能无法识别；隔离只在provider静默／复位合同下成立，观察标签不是native tag。RX关闭及RESET_ACK是模型合同；7／11参与者不含尚未建模的G／feeder／仲裁，真实Block复位范围需另核。S写不回滚，poison保留义务；完整重新装载和新epoch后才解除门控。未执行控制／宏／S RTL、完整Block、LLM数值或物理。

负责人Melodydt继续；无服务器作业／节点／日志／结果和自动监测；研究in_progress、PR Draft／未合并，登记PR5 pending，看板unverified／同步pending（缺board.json／Projects工具），管理员／审查人待指定。

## 19:46 CST 第4步二进制执行（历史记录）

仓库／负责人／Issue／PR同上；分支task/179-local-block-continuation，base task/175-local-block-design，父8cb31090ed936906f4cf5a7a9a5ce4fa8ce7f864。新独立部分API目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/control-exec-8cb3109/delivery，无.git／HEAD／index，旧包不覆盖；本地发布前文件不是Git提交。最终远端commit、原文读回和CI见PR180回执。

先重新读取规则、Issue／评论、PR180和PR176 head／正文／评论／review／逐行评论，核pr176-sync.json；有差异先同步合同，上传前再核。每轮研究仍须把目标／上游／产物／实际验证／限制／下一步直接补总方案。

[第4步说明](../local-blocks/CONTROL_EXECUTION_MODEL_V0_1.md)和project/control_exec_v0_1交付按二进制PC执行的母控／局控与有限peer；9次实验100退休／193观察，新增26、累计107组测试。来源与验证为work/Melodydt/179/control-exec-sources.json／control-exec-validation.json。运行端不读人工案例，compare仅做观察映射／独立检查，既有镜像和参考未改。

恢复核来源后运行管理检查、五套单测、run_campaign重建；下一步补运行取消／排空／poison、provider协同复位确认和迟到响应，随后冻结RTL接口。当前仅14类直线指令、M op6／RAW16；无控制RTL／完整Block、原生宏／S RTL或物理／LLM数值执行。ModelBound不是架构错误终态或死锁证明；失败实验的loader失效不代表已实现协同复位。

负责人Melodydt继续控制研究；无本轮服务器作业／节点／日志／结果和自动监测。研究in_progress、PR Draft／未审查未合并；登记PR5 pending，看板unverified／同步pending（缺board.json／Projects工具），管理员／审查人待指定，需核实际条目／字段后读回。

## 19:14 CST 第3步镜像／装载（历史记录）

仓库／负责人／Issue／PR同上；分支task/179-local-block-continuation，base task/175-local-block-design，父add63270a2faf707fac035898dd13028ceb1135f。新独立部分API目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/control-images-add6327/delivery，无.git／HEAD／index，本地发布前文件不是Git提交；只上传本轮白名单，旧目录保留。最终远端版本、原文核验及CI见PR180在线回执。

恢复第一步：重新读取规则、Issue179／评论、PR180及PR176 head／正文／评论／review／逐行评论，比较pr176-sync.json；上游有变化先同步合同，上传前再核。每轮目标／上游／产物／验证／限制／下一步仍须直接补进总方案。

[第3步合同](../local-blocks/CONTROL_IMAGE_LOADING_V0_1.md)和project/control_image_v0_1交付7份完整镜像、manifest／SHA与配置状态模型；[来源](../../work/Melodydt/179/control-image-sources.json)及[验证](../../work/Melodydt/179/control-image-validation.json)记录实际版本／命令／产物SHA。修正旧参考CALL arg0=1；累计81组检查，START仅准入，未执行PC／RTL。运行管理检查和四套单测，再开始独立二进制执行器；不得用cases.json给运行端排程，它只给oracle。

未完成：PC执行、真实配置总线／互锁RTL、provider复位确认实现；完整Block／模型数值／物理为外部门。负责人Melodydt继续控制研究；没有本轮服务器作业／节点／日志／结果或自动监测。研究in_progress、PR Draft／未合并，登记PR5 pending；缺board.json与Projects工具，看板unverified／同步pending，管理员／审查人待指定，需管理员核实际条目及字段后读回。

## 18:21 CST 第2步用例与参考轨迹（历史记录）

每次恢复先核PR176最新head／说明／评论／review／逐行评论，比较pr176-sync.json并同步受影响合同；上传前再核。用户新增要求：每轮目标、上游差异、产物、实际验证、结论／限制和下一步必须补入总方案，不能只记聊天或个人进度。

[第2步](../local-blocks/CONTROL_REFERENCE_CASES_V0_1.md)交付project/control_cases_v0_1的3组程序／29指令／分离记录、4条人工轨迹和27组检查；不执行PC，不验证RTL或实际S写。源TX必须收到ACK才释放，接收token本用例在写确认＋ACK发送接受后完成；M错误轨迹为peer非正常注入。

父afd96b359c369c7ea039cca2c642677b0ab5f665，任务分支／PR base不变；新目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/control-traces-afd96b3/delivery，无.git／HEAD／index，只上传白名单，旧包不覆盖。最终commit／原文／CI见PR180；[来源](../../work/Melodydt/179/control-case-sources.json)及[验证](../../work/Melodydt/179/control-case-validation.json)记录实际命令。

恢复核源与测试后，下一步完整镜像／配置装载合同和半装载有效互锁，再实现二进制执行器来产生独立实际轨迹。完整Block、模型数值和系统物理仍是外部门。无本轮服务器作业／节点／日志／结果或自动监测；研究in_progress、PR Draft／未合并，登记PR5 pending，board.json／Projects工具欠缺，看板unverified／同步pending，管理员／审查人待指定。

## 17:39 CST 第1步接口合同（历史记录）

用户要求每次研究先看PR176更新并及时同步。恢复第一步：用本人连接读取PR176 head、状态／说明、评论／review／逐行评论，和work/Melodydt/179/pr176-sync.json比对；有变化先读diff，更新受影响接口／profile／来源和兼容版本。上传前再查一次；不是后台监测。本轮开始head08f2ea20未变且评论／review空，最终检查见同步记录。

[接口合同](../local-blocks/CONTROL_INTERFACE_CONTRACT_V0_1.md)与project/control_contract_v0_1现有6模块149原生端口、12个P服务、2个16KiB研究profile及15组静态检查；不是控制RTL／Block实现或R2执行器。M上下文、G包与S真实ACK必须分别推进。查[来源](../../work/Melodydt/179/control-interface-sources.json)／[验证](../../work/Melodydt/179/control-interface-validation.json)后，先运行管理和两套编码／字段单测，再按空任务／单服务写独立预期轨迹及镜像／配置装载合同。

发布父提交df3e7a2657a96bf0e5031a958d48155010bd7380；任务分支／PR base不变。新工作目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/control-interfaces-df3e7a2/delivery，无.git／HEAD／index；修改仅白名单，旧包保留，最终commit和远端原文核验见PR180。源RTL仅只读绑定，未上传／修改PR178原模块，没有新服务器作业／节点／日志／结果或自动监测。

负责人Melodydt继续控制研究。第1步为P接口基线，R1整体／R2未完成，完整Block与系统物理仍为外部依赖。登记PR5 pending；缺board.json／Projects工具，看板unverified／同步pending；管理员／审查人待指定。研究in_progress、PR Draft／未合并。

## 17:05 CST 控制研究范围（历史记录）

用户明确本分支只研究母控／局控，不负责完整 Block 实现。最新[方案第0、9节](../local-blocks/TWO_LEVEL_CONTROL_PLAN.md)改为接口合同、镜像与装载、二进制控制模型、局控 RTL＋有限协议 peer、母控多局控协同及控制程序生成。基础宏／S／完整 Block 数据通路与系统物理／模型质量由外部任务负责；真实集成验收要求保留，任务／负责人待指定。

发布前基线614cdab41cfde66ee31c92fc3e44a9e1733a338a，任务分支／PR base不变；最新目录 D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/control-scope-614cdab/delivery，无 .git／HEAD／index。修改仅本轮白名单，旧资料包不覆盖，最终 commit和读回见PR180。没有本轮服务器作业／日志／结果目录或自动监测。

恢复第一步：核 Issue179／PR180 最新版本和本范围约束，读[文档验证](../../work/Melodydt/179/control-scope-validation.json)，运行管理检查，然后开始 R1 控制接口／profile及装载准入。用协议 peer 可启动研究，明确假设和有限资源，不把 peer 写成真实 Block。登记PR5 pending；看板unverified／同步pending，管理员待指定；研究in_progress、Draft／未合并。

## 16:25 CST 综合方案交接（历史记录）

当前发布前源码基线 d6429607d5e0f607c321ab6372e78d5f53ec96ba，tree f7a1826fee23c24ed8d939f2325961e059e44257；任务 task/179-local-block-continuation / PR180，base 仍 task/175-local-block-design。最终新增 commit／CI／原文核验由在线 Issue／PR 回执记录，不伪填自引用 SHA。

本轮成果为[综合方案 v0.2](../local-blocks/TWO_LEVEL_CONTROL_PLAN.md)：Block 组成、四类连接、ISA／程序装载执行、最新进度及下一步；ISA v0.1 编码和代码未变。局控到宏固定预连、主机统一装载器仍为 proposed；宏级断电暂缓。

工作目录为 D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/control-summary-d642960/delivery，是新独立部分 API 快照，无 .git／HEAD／index，不能称本地 Git 已提交。发布前改动仅本轮白名单；旧 control-plan-1f3e916/delivery、179/delivery、151 包保留。远端基于固定父树仅更新本任务文件；上传／原文核验结果以 PR180 回执为准。

实际检查和摘要见[control-summary-validation.json](../../work/Melodydt/179/control-summary-validation.json)，在线 PR 元数据／说明快照及固定文件版本见[control-summary-sources.json](../../work/Melodydt/179/control-summary-sources.json)。PR178／163 的最新状态仅按核验时的报告记录，不是服务器实时作业读回；没有新增服务器作业、节点、日志／结果目录或自动监测，没有停止原任务。

恢复第一步：Melodydt先核 Issue179／PR180 最新 HEAD、评论及分支，核本轮来源／产物 SHA，再在上述 delivery 运行管理结构、容量 --check 和 codec 的现有 8 项测试。随后 R1 交付资源／原生 ABI 注册、固定控制网与后制端点清单、镜像与配置装载接口、16／32KiB 对象生存期；再 R2 有限二进制解释器。

登记 PR5 已读回 open／未合并，pending；本任务头 config/board.json 仍 404，status-mapping 已读，但无 Projects 条目／字段工具，条目 unverified／同步 pending。管理员待指定，需核实际卡片、Project ID、Status=In progress、Priority 待指定并读回；未因本轮结束聊天而标 done。审查人待指定，PR Draft／open，研究 in_progress。

下方早前两级控制／容量交接为历史记录；路径和当时进展保留，不代表当前本轮工作目录。

## 本轮更新：两级控制与指令编码优先

用户明确主要负责母控/局控研究，并要求后续模型编译能使用的指令种类与编码。现交付[方案/研究步骤](../local-blocks/TWO_LEVEL_CONTROL_PLAN.md)、[ISA v0.1](../local-blocks/CONTROL_ISA_V0_1.md)及[参考工具](../../project/control_isa_v0_1/README.md)。24操作码/9类记录和软件编码工具已形成；完整镜像装配、native参数注册、语义编译、执行解释器及新RTL/物理未完成。R1–R7仍待执行，不因文档/编码通过标done。

本轮基线commit1f3e916ed5c40fc54a0e7af90c675017c87317e4/tree0beb612ccc0dacc350e1ab5765b583efdf1fe324，仍通过PR180和task/179-local-block-continuation交付。新的独立本地API目录为D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/control-plan-1f3e916/delivery，无.git/HEAD/index，修改均为发布前工作文件而非本地Git提交；最终远端SHA见PR/Issue回执。旧179/delivery与151包保留。

恢复先读取Issue179/PR180最新HEAD和评论，核本轮来源/验证索引，再在新目录运行管理结构检查和project/control_isa_v0_1/test_codec.py。随后开展R1：真实宏/私有S端口与native字注册、程序/描述符容量及地址/资源/拓扑检查。容量下界旧研究继续约束S布局。没有新服务器作业、节点、运行日志或结果目录；这些项目为未启动，不取消其他任务，无自动监测。后续服务器实验先读远程规则并按启动/RUNNING/终态回执交付。

[本轮来源](../../work/Melodydt/179/control-plan-sources.json)及[实际验证](../../work/Melodydt/179/control-plan-validation.json)随白名单提交；没有重验PR178/167/163大包。登记PR5仍open/unmerged，pending；缺board.json/Projects工具，看板unverified/同步pending，管理员待指定。下方为原容量交付的历史恢复入口，和本段一起保留。

## 分支、版本与位置

- 来源PR176未合并，固定设计commit `08f2ea20a11dfdd09892a67599163e32b7237edb`、tree `70d56e60b162ce3ef17e6f0ffdd55b570ec5d4d7`。
- 新任务分支`task/179-local-block-continuation`，[Draft PR180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)以`task/175-local-block-design`为base；首交付commit `8513c23d70ac6156a9735f04da271cf6764a1f7c`，最终HEAD在Issue179/PR180在线回执读回。PR176合并后先核差异再考虑改base，不自动合并。
- 独立本地API包`D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/delivery`，管理/来源快照与本任务白名单文件；无.git/HEAD/index/暂存，因此无“本地已提交”状态，未提交资料指发布前本目录的新文件。远端通过Git tree API继承固定父树，仅上传白名单。
- 根参考资料副本和work/Melodydt/151旧包不覆盖；main仍为`4b1df2c7cbdaa0fa6f9f468f2b5b854cec875609`（本轮读回）。本任务未改服务器或原作业。

## 成果与验证

[研究报告](../local-blocks/CONTINUATION_RESEARCH.md)、[8项容量下界](../local-blocks/continuation-capacity.json)、[核算输入/程序/来源和验证入口](../../work/Melodydt/179/README.md)、[个人进度](../../progress/Melodydt/STATUS.md)。实际发布SHA和验证结果见Issue/PR回执与work/Melodydt/179/validation.json；本地资料与远端每个上传blob逐字核验后才报告上传完成。

管理结构不是业务验收；容量算术不是完整生存期/调度证明。没有新增RTL/模型/EDA/服务器实验；作业号、节点、日志、服务器结果目录均不适用（未启动），没有自动监测。

## 未完成项与恢复第一步

负责人Melodydt先读取Issue179及PR最新头、PR176和PR178/167/152/163最新状态，确认无并行更新；保留其他任务及其作业。然后在本目录运行：

```powershell
python -X utf8 -B scripts/check_project.py
python -X utf8 -B work/Melodydt/179/analyze_capacity.py --check
```

接着从Qwen dense FFN起，给出16/32KiB候选的对象地址、紧凑打包、bank、M单上下文、down端完整Mid重放位置与成本及真实ACK/释放顺序。先形成可检查合同/轨迹，再落地新仿真；Falcon数值、系数表、Granite质量和最后同资源物理对照仍待接续。完整三模型能力未验收，不标done。

## 登记与看板交接

本轮读回management-hub PR5 open/unmerged，登记pending；复用该登记不重复建PR。PR176基线config/board.json返回404，status-mapping.json已读取；当前连接器没有Projects条目/字段读写工具，因此本任务实际看板/条目ID/status未核验，并非已证明Melodydt缺read:project权限。状态unverified、同步pending。

管理员待指定：确认正确看板及受众，补配置，查Issue179是否已有卡片，复用或添加；同步Project ID=llm-hardware-design、Status=In progress，Priority待指定不猜测；读回条目ID、字段及时间并写回本Issue/PR。未完成前不报告synced，不修改权限或另建看板。
