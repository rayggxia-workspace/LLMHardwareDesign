# Issue106 实际唯一服务银行（预登记 v1）

负责人 Liangruizhi；仅本人服务器新 issue106-shared-services-20261025 / lrz-i106-*。基线102 PR105 a62cffbf、99 PR103 8c51f5df；合并0eaa695。98物理与104 GDN独立，GDN未接入。当前仅源实现，尚未验证。

## 数学、输入与采样

保持97原始Granite gate/up I32Q12→SiLU→完整512最小δ→A8→8专家/K512/H1536实际M→merge/residual→流式norm；保持102完整8Q/1KV/d128三遍materialized Q8/KV16→QK/score/exp/sum/P15→PV32；保持99 Falcon单head D128×N256旧函数、全head guard/retry与RNE、72步合同。均不改精度，不给host中间结果。

首批固定97六原输入中的第0和第5（L0/t0、L13/t71，具体名由原cases绑定）；102固定真实prefix128 full position0与实际cached position128（由原cases匹配，不用full伪替）；R99 head0原输入从INIT、STEP0、STEP1连续跨lease，后续真实position27 checkpoint需RESTORE另分资格。主序列 INIT→M0→Afull→Rstep0→Acached→M5→Rstep1。不是同一模型端到端数据链。输入SHA/旧manifest/准确名称在首次运行前输入清单绑定。两模式无等待/有界端口与外部及结果背压；无按结果选有利case。

## 唯一资源与有限库存

shared106唯一实例store82 1024×128bit（16KiB，1RW），共享8×有符号8×8组合乘法、mul84 SHARE=1单S32乘法/两个64bit有限响应槽、一个128bit SFU、一个128bit半双工memory_link（每逻辑事务5beat）。m/a/r均仅controller新变体；所有局部line/vacc/状态/宽RNE/地址/选择器真实综合，不把静态不活跃等同无面积。norm106不再内藏SFU。S memory行为wrapper非真实宏；C0 128KiB外部只读LUT，不是免费片内ROM。环境最多2个(128data+32tag)响应槽320bit+控制单列，非core mapped area。新D配置、export索引/基址/owner/phase/counters/选择器全计入。唯一资源综合必须从实际层级及flatten算术/存储验证，不以名称证明。

M每次Vprep重建A4KiB；A覆盖自己的score/P/KVtile/output区域；R每STEP重载系数/行，持久状态只在外部双bank/root，不能依赖S跨lease保留。D配置仅空闲，单response，所有输入参数通过各controller实际锁存。M/A/R原S布局保留且互斥。结果从同一S端口实际读出：M384行、A256行、R candidate32行，背压稳定且全部ACK后才能结束/决定commit。R INIT/RESTORE无候选导出。

地址不混叠：M原GU0x04000000、records0x04100000、gamma0x04800000，界限0x04c00000；A K0x05000000/V0x05100000，界限0x05200000；R将原1MiB数据原字节重定位至0x06000000..0x06100000，偏移和descriptor不变。LUT仍0x02000000..0x02020000且含102新增exp对象。未来GDN独立窗口未在本实现接入。不得host替换R/缩小head或把物理库存按并发相加省略。

## lease、排空与提交

全局D互斥owner lease从cmd接受至完整result导出和DONE ACK；lease内唯一transport epoch32，命令接受+1，max拒新cmd，绝不回卷。abort不改变当前tag，防旧已接受事务丢失。不同旧epoch迟到丢弃；external必须每已接受事务恰一response、写在ACK前effect-once，epoch不是每事务ID，不承诺检测同epoch恶意重复。终止空闲同tag迟到排空；硬reset必须协调fabric，不能当无损恢复。

M/A abort优先于新内部service接受及新result握手，D停止请求并吸收已接受S/S32/SFU/link全部响应，只有全drain后才局部reset。已进入bridge的请求在abort之后仍可发到外部，必须完成；本合同并非旧立即flush。A registry只硬reset清除，跨lease/softabort保留单owner、正向version不回卷、同version的K/V地址/scale固定和长度非减；length仍caller已提交前缀，不证明KV append。

R保持99 abort排空及原子root写义务；candidate完整export后才允许accept/reject。accept进入COMMIT即不可取消，直到128bit根写ACK并更新mirror。export期间abort可撤销未提交候选并排空D读；reject胜accept；abort胜可取消accept。R发布state/Y/position/unit/epoch跨其他owner保持。DONE要求同资源drain，不响应假cfg/cmd握手。

## 验收与失败保留

先服务器build/pilot；正式同core混合、两等待、参数忙时扰动、export背压、M/A各服务在途abort、R不可取消commit/abort/reject、registry A→其他lease→A负例、迟到tag、32bit末值边界和协调reset恢复。实际RTL边界注入须明示，mapped gate禁止top输出赋值冒充DFF注入。门级只选无注入真实完整M/8头A/完整R消费者，和同driver RTL逐字段比较。

独立oracle从97原参考、102原捕获编码/数学、99原bigint重放完整state/Y，每种结果必须全值比较；旧结果可配对但不能独自充当独立真值。改真实文件且重SHA的数值/owner/协议/库存负例应被完整receiver拒绝。记录实际服务接受/响应/导出/换手、R root每次发布及不可变旧bank；所有源码commit、输入/manifest/SHA、binary/log、失败和取消均存档。分别报告compute/调度/export/abort成本；独立三核面积之和是库存不同的参考，不当同资源性能对照。相同数学/容量/端口的顺序切换基线和共享开销分列。logic area非宏/STA/PPA；通用V ISA/GEMM、KV append/online、完整GDN、全模型及制造后定制未覆盖。

## 首轮审查修订（首次正式统一版前）

根审查发现cfg_pending响应遇soft_abort时公开valid为0而原内部take仍可消费，已修复为同资格门控；service_accept在硬reset时亦屏蔽。旧phase1/2保留为原型，正式混合和恢复重跑同一修订RTL。新增读/写ACK各4拍冲突、保持响应恢复唯一握手，完整后继命令确认。32位末值通过实际top epoch Q边界注入，资格仅RTL，不传播到门级。

正式phase3两路7命令混合、两路23命令恢复已独立通过；补充phase5再验证M已接受S32响应、A已接受内部store ACK取消，恢复扩为27命令/6abort。RTL和正常sim driver字节不变；build/run/receiver只校验实际编译依赖（所有RTL+sim，qualification二进制另加qualification），不把未被编译的旁支driver变更当成原二进制变化。`compute_cycles`是继承的controller active计数，R包含OFFER等待导出/决定，不能与export_cycles相加；统一端到端本切片使用D cycles，非模型端到端。

生命周期补充：INIT继承99的破坏性空白状态配置语义，INIT中止不保证已有published bank；本批只在授权空白image INIT一次，后继STEP/reject/abort保全，硬reset后RESTORE。资格driver从full源切实际cached源显式提升version3，再回full源version4，不假定两来源快照已有KV字节恒同；正常混合full1→cached2原已正确。原阶段保持，最终27命令在修订driver上重跑，RTL不变。

交付说明（不改冻结实验）：M/A导出前缀在status0 DONE前为provisional，abort时sink必须丢弃该lease前缀；R为candidate再accept。当前测试sink完整向量M6144B/A4096B/R512B是环境存储，最大6144B不计作额外片内容量或core面积。未来真实下游事务buffer/commit或可撤销流式机制未实现、未物理计价；本任务不宣称外部下一消费者硬件闭包。该说明对应已有部分导出可取消接口，不修改任何数值或服务账本。
