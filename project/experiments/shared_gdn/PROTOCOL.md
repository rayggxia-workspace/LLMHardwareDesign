# Issue109 四profile同一服务银行预登记 v1

负责人 Liangruizhi；task/109-shared-gdn；独立本机 D:/Projects/LLMHardwareDesign-shared-gdn；服务器 issue109-shared-gdn-20261025 / lrz-i109-*。基线106 PR108@7a9fece合104 PR107@03ab900；原源/数据只读，成员55/63及物理98不接管。

## 固定数学和真实范围

M/A/Falcon原106数学及数据不变；GDN完整两个128×128 head，复用104严格checked-I64/非对称S32状态、宽乘三块exact后一次RNE、全head重标、两头group epoch与原子root。position64/version64独立；每头units I8和group numeric_epoch不与D transport epoch混同。新priority参考先任何shift>62拒绝，再任何shift<-32宽度重标。不改已有真实32/12输入或精度以取性能。首轮主序列预登记R INIT→G native RESTORE→M0→G native step0→Afull→R step0→G native step1→Acached→M5→R step1→G native step2；连续native三步跨其他profile无host状态替换。随后同instance空闲时显式切换至104已验真实legacy rescale checkpoint，RESTORE→G完整重标一步。外部checkpoint替换是明确已释放lease的导入，不当连续轨迹。两等待模式；门级选择上述完整M/A/R/G native首步及真实重标一步，预先有界pilot，非全模型数据链。

## 实际唯一库存与地址

shared109唯一store82 16KiB/128bit/1RW、8S8组合乘法、mul84单S32/两有限响应槽、128bit SFU和memory_link半双工5×128bit/txn。gdn109仅控制器和wide104 lowering状态，不含额外store/link/mul。新增owner mux、context与导出控制全综合计费；没有通用V ISA、额外SRAM宏或免费128bit乘法。

M04000000..04c00000；A05000000..05200000；Falcon06000000..06100000；GDN06200000..06300000。GDN104 image内容除metadata word3的实际COEFF/state/Y指针加02200000外原字节保留，重定位收据逐处核对；绝不把所有碰巧匹配数字替换。元数据context104保留其源身份。GDN有效mutable659600B、32slots50176B，共709776B，窗口1MiB；32slot限制不称256步容量。完整数据与状态外存，不计作片内16KiB。S所有controller按互斥lease使用；M每次重建A、G每step重载系数及decay，不依赖跨lease S旧内容。

## GDN导出、发布及排空

profile0=M，1=A，2=Falcon，3=GDN。统一D generation32只在命令接受递增，不回卷。GDN自己的generation寄存器抽除，沿D当前值。G context独立持久，其他profile不改其published寄存或外存root；同profile新context须先RESTORE。

G OFFER在完整proposal/两头guard/shadow/Y/四metadata写ACK完成后出现。D在OFFER锁定inactive Y基址，通过同一外部桥实际读取128行×16B=2048B；每行保持到result_take，最多单行桥response，没有新增2048B片内buffer。结果携带owner3/result_candidate/index；g_position+1、g_version+1、g_candidate_units、g_candidate_epoch、!g_bank、g_owner_saved、g_context_saved形成完整稳定候选身份，消费者须在同lease锁存。完整128行ACK后candidate_ready才有效。环境sink最大仍6KiB（M），G占2048B；此sink非core、真实下游事务缓冲/提交/撤销未实现，不冒充完整下游消费者。

accept进入G原COMMIT不可撤销，即使root请求尚未fabric接受；root128原子写ACK后才更新镜像/DONE。reject或可取消abort不得改变当前published root/state/Y/meta。双bank lease要求DONE ACK表示前一代所有引用已释放；禁止外部并发读写，不能永久immutable snapshot。current和候选二者分别比较。

新增export_pending追踪D自己的外部读；在导出中abort时停止新请求，消费已接受bridge响应，G本owner运算排空后DONE，等待所有公共服务drained才释放。不能把G OFFER无请求等同D没有在途导出。M/A原abort排空、不reset公共银行，R/G原commit-drain保持。cfg与命令冲突仍cfg优先；全部busy配置扰动取锁存值。硬reset仅协调fabric/公共服务，恢复读真实root；终止tag注入仅RTL，门级不Qpoke。

## 验收和成本口径

新顶层执行两模式完整四profile序列，独立97/102/99/104 bigint全值及G全stage/state/Y/metadata接收；重标checkpoint原SHA、原前序state与非零Y绑定。补G外部/S/S32/wide/candidate读取在途abort、heldresponse、reject、不可取消root、cfg冲突、旧tag/末值/协调reset-restore；每次失败保留实际文件，语义负例重SHA后完整receiver拒绝。唯一库存通过generic层级/flatten乘法数量和实际mapped库计价；selected raw gate逐字段/周期/IO同driver RTL并独立oracle。实际CPU/日志/sourceSHA/输入版本/工具/有限fabric队列独立记录。

G每成功候选额外128外部读、640×128bit线拍=10240B（payload2048B），另request/response32bitgeneration sideband；cfg128物理协议另列。G计算debug cycles包含OFFER等待，不能与D export_cycles直接相加；命令accept至DONE使用D cycles。旧独立核面积之和非同资源对照；本轮logic mapping不代表宏/STA/布局布线/制造后定制通过。
