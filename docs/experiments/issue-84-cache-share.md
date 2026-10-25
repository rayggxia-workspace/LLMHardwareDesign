# Issue84：同容量 A 缓存与重定标乘法器共享

2026-10-25 UTC+08；负责人Liangruizhi，身份182389313。[Issue84](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/84)，PR链接以最终回执为准。依赖[PR83](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/83)@7e9ec409d90478a05547b555071d21c22ba260d7；成员55/63、PR58/79无新变化，不重复开发。所有实际pack、矩阵/整数接收、RTL、综合和完整比对只在本人CPU服务器c96/node13经lrz-i84-*；PC仅源码、8个小边界、metadata与字节接收，无新模型/软件/其他机器/Phi解封。

## 结论和证据范围

在本次完整Granite down-M整数消费者中，优先候选是**既有4KiB区域A缓存＋M/RQ与Norm共享一个S32乘法器**。原精度、16KiB单1RW及128bit五beat读协议不变，缓存使安静周期减少34.6801%、三资源背压减少33.0681%，线传输减少49.1987%；合并共享后logic-only面积相对本轮基线减少10.3752%。它是有条件的电路候选，尚不是制造边界或整模型收益验收。

关键反例：每次片内操作增加8拍授予等待时缓存已无周期优势，12拍时反而慢17.38%。应保留可选择/旁路能力并约束端口服务，不能把cache always-on写入普遍最优结论。当前CACHE/SHARE是编译期制造变体，**运行时旁路尚未实现**。

原始精度/质量失败、BF16/FP32参考不改写。这里只证明相同整数函数的结构、资源和逐周期实现；当前MoE入口midA8、选择ID/gate、W8及残差已编码，router/SiLU/前置编码和完整模型质量仍在cut外。

## 冻结函数与实验矩阵

复用Granite-3.1-3B-A800M-Instruct revision a02780686e08a03fe0d2679a293b5c74a90efa89的既有74/82数据：层0/13、token0/64/71，六个不同真实输入，每个完整8expert×K512×H1536。共四变体×两背压×六输入=48命令，加SHARE1下缓存开/关×三固定端口等待×六输入=36命令；总84条，不说成84个模型样本。

W8A8→INT32全K→S32 mantQ31乘积S64→按`31-expS16-A_deltaS16`RNE→I32Q12→U16gateQ15乘积及八项S64前缀和→一次RNE15→coefficientQ20乘法/RNE20→残差I32Q12→完整精确RMSNorm/gammaQ20→I32Q12。scale单位减法18bit硬件、有界大右移clamp64、RNE、错误检查、epsilon/coefficient命令锁存保持82合同；命令接收后驱动清零，不能偷读host中间计算。所有乘法、宽加/移位/比较、128bit恢复除法和整数开方均是真实RTL资源，无FP或LUT近似。K512最坏8,388,608安全；八项gate前缀绝对界小于2^50，保持S64。候选不等于只用INT8乘法器。

四方案统一一步SFU。独立/共享均使用有限ready/valid服务，每client一个S64响应槽，不能给独立方案保留旧无握手快速路径。故本轮基线9061831与82原未包装基线9035719不作同一控制开销比较。算术数量有差别，不能称同面积/同算术库存；相同精度、容量、端口下测面积代价。

| 方案 | A缓存 | S32乘法器数 | 安静cycles | 背压cycles | logic-only面积 µm² | generic寄存器bit | 映射DFF_X1 |
|---|---|---:|---:|---:|---:|---:|---:|
| v0 | 关 | 2 | 9,061,831 | 10,690,375 | 57,603.630 | 4,083 | 3,582 |
| v1 | 关 | 1共享 | 9,061,831 | 10,690,375 | 50,130.626 | 4,084 | 3,583 |
| v2 | 开 | 2 | 5,919,175 | 7,155,270 | 58,961.028 | 4,211 | 3,744 |
| v3 | 开 | 1共享 | 5,919,175 | 7,155,270 | 51,627.142 | 4,212 | 3,745 |

六输入的固定工作计数与周期一致；逐元素acc/down/join/norm全部跨变体、背压相等，并逐一等于物理payload独立NumPy/bigint参考和旧原始codes。每次6,291,456实际S8 MAC、12,288条acc/down、1,536条joined/norm，不能以捕获acc替代矩阵。8次实际改acc、重新SHA的语义负例被拒；端口36条也独立全函数接收。新RTL不是参考llaccel/opentpu数值规范的逐位复现。

## 有限容量、打包和端口账

同一个store82共1024×128bit=16,384B单1RW：X/join/Y原地6,144B（行0..383），gamma6,144B（384..767），A缓存4,096B（768..1023）；cache-on无剩余容量。A缓存不是新bank，不使用此前候选M32KiB作为免费容量。复位保留存储，active M中止与done/status保持实际检查通过；独立fabric复位/CDC仍未验。额外A行128bit、W行/oline、乘法响应、FSM与诊断计数器均包含映射逻辑/寄存器，generic寄存器数不重复加存储131072bit。

初始装载8×512个A8，全H复用；每个W128先取一个A128再做两次8laneMAC。缓存使用与M joined、Norm、cfg相同端口；无预取、额外DMA lane、完整多行acc/merge缓冲或第二端口。每份A逐行复用关系在pack时检查，cache格式重构旧格式所有字节完全一致后才运行。

| 实际开销/一次完整命令 | cache-off | cache-on |
|---|---:|---:|
| W8 payload | 6,291,456B | 6,291,456B |
| A8外部payload | 6,291,456B | 4,096B（冷装载） |
| 16B头/元数据/残差/保留位 | 196,608B | 196,608B |
| 总payload/16B事务 | 12,779,520B /798,720 | 6,492,160B /405,760 |
| 双头请求/双头响应/数据五beat线传输 | 63,897,600B /3,993,600beat | 32,460,800B /2,028,800beat |
| 片内128bit操作 | 1,920 | 395,392 |
| 新A缓存读/写 | 0/0 | 393,216/256 |

1,920共同片内操作含M写384、Norm读1152/写384；外部caller gamma配置384写/768edges和结果384读/768edges另计，cmd接收1edge、donehold+ack4edge另计。缓存冷装载256外部事务/写均在active cycles内。command epsilon/coefficient共8B控制字段、rank/row计数和scale解码在RTL内；expert gather/输入流构建及在线调度在cut外，其时间不得当成零系统成本。打包未按FP32字节除四，未把payload当真实DRAM峰值带宽。

## 乘法器、仲裁和缓冲

M每命令26,112个S32乘法请求（两次/专家坐标＋一次/坐标），Norm3,072次，2个有限64bit响应槽；SHARE1增加输入选择与RR控制。当前M→Norm整阶段串行，实际同时eligible次数0，安静时wait0/wait1均0；背压明确为26,112/3,072拍授予等待，v0/v1与v2/v3周期相同。共享的零额外周期仅对此调度成立。

独立mul84 RTL压力每版本接收4096请求（合计8192），包括INT32端点、符号、持有响应、双请求、授予阻塞、20edge有界服务及active reset。各231个双请求edge；独立/共享denied edge300/530，held-response28358/28128；源码保证未接收的操作数稳定。证明仲裁接口有限且可运行，不证明重叠M/Norm或多context仍零代价。逻辑测得cache增加2.3564%面积；共享使cache版本减少12.4385%，缓存加共享净减少10.3752%。通用双client端口每个传64bit操作数、64bit结果及req/ready/valid/take；跨Block长线、扇出、寄存切片和STA尚未资格化，不能据此强制物理合宏。

## SRAM压力反例与边界

保持外部响应和乘法授予安静，两方案同一端口、每操作相同额外等待：

| 额外等待/128bit操作 | 无缓存共享cycles | 有缓存共享cycles | 缓存周期减少 |
|---:|---:|---:|---:|
| 0 | 9,061,831 | 5,919,175 | 34.6801% |
| 4 | 9,069,511 | 7,500,743 | 17.2972% |
| 8 | 9,077,191 | 9,082,311 | -0.0564% |
| 12 | 9,084,871 | 10,663,879 | -17.3806% |

新增393,472片内操作的静态break-even为3,142,656/393,472=7.98699额外授予edge/操作，与实测跨越一致。这是人为可复现的端口可用性压力，不是已观测的真实NoC争用轨迹或SRAM宏延迟。若另加独立bank避免争用，必须单列容量/宏面积/互联/调度，不能混入本对照。H2560仅X+gamma就超16KiB；Llama/Qwen不能直接继承本缓存占用成立结论。当前版本无context shadow/下一命令预装空间。

## 逻辑面积资格、工具恢复与未完成项

统一Nangate45研究Liberty SHA256 8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1，非目标可制造工艺。实际generic netlist逐层核一个1024×128逻辑1RW memory、8个S8乘法、一个/两个S32乘法，无隐藏原生div/mod/pow；映射实例直方图等于Yosys stat，按原Liberty Decimal独立求和等于面积。**整个共同store82 wrapper黑盒排除面积**，容量/操作数另报，不能称总芯片面积。控制/line/response/诊断寄存器均计；计数器可否移除另任务，不事后从某一方案减费用。

首批四build缺mul_request观察端口而失败，原输出保留；仅取消本人16个不可能满足的依赖。默认Yosys/ABC重复服务器接口在8个map01/02中等待，进程/系统调用证据为父读子输出、ABC select等stdin；进一步根因未证实。未接受面积，取消仅此8作业及3待分析。依据[安装版本ABC源](https://github.com/YosysHQ/yosys/blob/70a11c6bf/passes/techmap/abc.cc)和[synth源](https://github.com/YosysHQ/yosys/blob/70a11c6bf/techlibs/common/synth.cc)，同一ABC二进制改为文件调用、显式abc-fast/opt-fast，四map03约20s完成；恢复配方一致、日志实时保存/300s上限。未安装/替换工具，原失败保留，不把旧任务面积当完全同配方对照。

尚未验收：SRAM/ROM宏的面积、延迟、功耗/读写能量；目标PVT、STA、布局/金属接入/长线、映射门级等价；运行时cache旁路；M/Norm并发、多context与更大H/K；一般18函数V/ROM、完整M阵列/在线MoE dispatcher、整模型质量与真实DMA。安静cache等时间最低频率比0.6532只是周期比，未做STA不称实际时间加速。

## 来源、接收与协作

整数执行phase2=d031510，端口phase5=7a01ef6，正式仲裁phase4=87b87a9，四map/全分析phase6=049a8a6；完整SHA在binding/execution。统一结果索引在`project/experiments/cache_share/results/issue-84/index.json`，完整输入/日志/网表/失败留授权服务器/public/home/yuzelu/RuizhiLiang/issue84-cache-share-20261025，精选/精确源码SHA按最终接收回执。分析report SHA256 873fbd5b435ffbb93e73e782ee62d72407053143553a4be8dd7f577ff56cc0cc；不是以脚本存在或作业提交代表通过。

按协作Skill1.0.0通过Issue/独立task/84-cache-share和PR交付；未审查合并不done。登记management-hub PR5仍pending，board.json404，实际Projects查询缺read:project，状态unverified/同步pending；有权限管理员和审查人待指定，不改用他人身份。

## 交付前独立审查

正常84条算术/缓存结果未发现反例。修复接收器空协议/漏字段/非布尔真值可过，以及目录名代替profile/stall绑定的缺口；新增元数据负例并仅服务器重跑14份接收和完整分析，不重复正确RTL。Issue85接续正式cmd_ready/accepted、缓存模式锁存和多阶段中止后完整重启；Issue86接续门级/受限STA。当前cfg pending时busy=0但cmd不接收，因此84仅适用驱动等待cfg完成的调用合同，不称通用命令ABI合格。

## 最终证据接收

严格接收/分析phase7=302f18a2c719e37f49716d43c78de6ed19067e75，analysis05与analysis04的数值报告字节一致（接收算法收紧，原输出未改变）。14份正式接收各含1个实际重SHA改码负例，共14个；8份主对照＋6份端口压力。93个Slurm作业62COMPLETED、4FAILED、27CANCELLED，归档/接收作业90729—90731均完成。原90个实验作业逐项终态见精选slurm90.json，另外3个归档/接收终态见工作目录归档回执。

完整包delivery01/full-results.zip：279763633B、799成员，SHA256 290113c6ed0b35ce801fbbc3a417b743a55934cea0ebef1754a00b6326603f69；精选selected.zip：2900792B、300成员，SHA256 1af3d45efe541e15dbe116089eb32281d9bec4252ab3661d82315716c1001e4a。服务器两包、PC精选逐成员字节及7phase126份原Git源绑定通过。PC没有重跑实际张量或RTL。恢复命令、限制和审查状态见交接。

远端交付：[PR87](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/87)已上传，Issue84为in_review；待指定独立审查与合并，未done。已按不可变commit读回报告/交接/个人进度，与原Git blob逐字节相同；后续仅文档同步，不改变实验源码和结果SHA。
