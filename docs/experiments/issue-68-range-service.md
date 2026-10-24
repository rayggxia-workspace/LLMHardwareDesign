# Issue68：R范围/重定标与同资源V/R/S服务

2026-10-24 Asia/Shanghai；负责人Liangruizhi；[Issue68](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/68)，基于PR67@8bde3bf2309c2b41b68c081e9dbbe8be42d2ee19。R范围双轮/独立接收、checkpoint、V/R/S双轮完整服务及全量独立检查已实际完成；归档与远端交付状态按最后回执区分。

## 问题与冻结的取舍

旧同范围S16/S32有184/193最终state饱和；新完整hidden RMS临时行超16KiB，V32 old/new占满R32KiB。只补仍改变物理边界的范围协议及同资源服务，不扩大模型品牌/长度矩阵。

R固定static_sat诊断、static_guard拒绝、guard_rescale因果候选：guard失败不能发布；仅对当前越界head的旧整数state做RNE重编码并coarsen exponent，完整重试同token，最多8次，单位/epoch/状态/输出共同提交。源S32上界仍32767<<16，不偷扩为任意INT32。所有原始clip/sat保留；adaptive改变数值合同，不能与static直接当placement收益。初始来自已编码的独立cal或旧初态迁移诊断，不看未来native或评价误差。

服务固定V16KiB/R32KiB/S8×32KiB/各1RW128bit，R/V总8个S8 lane（shared8或split2/6、4/4、6/2），唯一共享sqrt/div，单128bit bus/有限2KiB FIFO及有限EXT backing。旧新整state超scratch必须分页，不能赠双shadow。Rtile16本地old/new+aux与tile32+Sshadow作为候选；没有相同恢复语义的原位方案从主排名排除。两遍norm源读与aligned spill互斥、gamma流式、A8/Ae、scan/retry/rescale/epoch流量都入图。EXT/算术时延仅条件参数，待RTL校准。

norm32与旧R256属于不同真实捕获；同场比较只作为两个独立竞争流，不复制norm32冒充同一连续模型链。任何FFN/attention背景仅有界且完全相同的代理负载，不称整图。Phi封存、Issue55/63保持他人范围。

## 执行入口

根D:/Projects/LLMHardwareDesign-range-service/task/68-range-service；range/service/独立审计子树分别D:/Projects/LLMHardwareDesign-68-range、-68-service、-68-audit，仅各模块独立修改。服务器新根/public/home/yuzelu/RuizhiLiang/issue68-range-service-20261024；旧Issue66数据只读。初始只读盘点：c96有1344空闲核、共享盘约12TB空闲，本人旧批次已结束，其他成员89448/yzl-vec-resume在node3，未中断。数值代码冻结后通过Slurm lrz-i68-*并行，实际job及接收结果待回填。

登记沿用management-hub PR5 pending；无board.json及可验证Projects字段能力，看板unverified/同步pending待管理员；审查人待指定，未审查合并不done。

## R阶段实际结果（服务阶段前）

90083输入接收脚本启动因else193词法错误失败，未读入数据/启动数值。修正源后90090完成输入接收；只修改本人pending数值作业的afterok依赖，保留原失败。90084/85 native各12条件、90087/88 legacy各72条件双轮全部COMPLETED0:0；90086/89独立接收各6条件全数学与实际重写SHA负例PASS，其他case核两轮科学文件SHA。90091 checkpoint四条件8/16及真实rescale边界接续PASS；它是同producer接续资格，与独立数学接收分列。

六个原256步窗×四格式=24源条件，每源比较三种policy。static_sat仍完整复现原1508次state饱和；static_guard在8个源条件停止、仅16完整，不把零已发布sat误称全完成；guard_rescale全部24完整、零已发布sat，16次重编码波次，合计新增状态重编码读写1,572,864B（不含其余retry/备份成本）。

接收前固定的layer0/end8192 S32/D31：static193sat、guard第4token拒绝；adaptive两波、单位[-27,-33]→[-27,-31]、epoch2，完整256步且0sat。输出局部RMSE约0.04821%→0.04724%，final state对FP64约0.07255%→0.06317%，重编码自身额外读写262144B/RNE32768cell，完整重试/代际shadow另需服务计价。S16同窗adaptive输出约1.01663%，并未因消除sat就变成应用质量通过。所有样本仍是既有观察诊断，非新独立质量集合或通用生命周期证明。

补充软件checkpoint携state/units/epoch/version/position/sequence，实际chunk接续逐码/事件一致；unkeyed checksum只表软件完整性，不声称认证或硬件SHA引擎。原range计算源83ef2b0...及运行commit7ea68a4保留，兼容resume扩展源db92865...单独phase5；未覆写原数值结果。

## 同资源服务分阶段执行记录（中间状态）

冻结service源0fa2cc07aa192d746db34ebbb96ca512dcd52c99ff940c98ec0a98a85769d59c@ae9d26b，4个单配置producer pilot90092/93/95/96完成。接收器先因只允许双策略而拒绝显式fifo子集；两版原失败及一次root接收路径误填均保留，未重新运行数值或producer掩盖失败。当时phase9读取原pilot01/02，90102 native已PASS、90103 legacy仍在接收；现两者均已PASS。

28分片90104–90131，每分片独立目录、1CPU/1线程、7组织×2源任务×2轮，默认2tile×2norm route×2EXT×2strategy，预计每轮每源56配置/112witness。4逻辑聚合90132/33/35/36及全量独立接收90134/37已afterok排队，未提前称完成。label-only sharedX_Y/splitX_Y保持逐节点相同资源，shared8是不同发射粒度，不归为纯物理归属收益。

## 同资源服务最终结果

全部28个分片90104–90131实际COMPLETED0:0，native每分片约48s，legacy约5min。每套7组织×2tile×2norm×2EXT=56配置，每配置两种预声明策略；各做两轮，合计448份调度文件。native和legacy各自的两轮科学文件逐字节一致。native90134独立核112份witness；legacy90140–90146并行各核16份，90148只合并回执及全量SHA/覆盖证明，不假称再次重放日历。每套48对label-only共享/拆分的逐节点签名、内存、lane、路由及周期精确相同。90137原串行legacy接收尚pending时经本人job名/owner核实取消，由7个并行接收替代；其命令与取消原因保留。

固定shared4_4、critical策略、reread、EXT-II1，所有数值与提交合同一致：

| 真实R任务（另有32行norm及相同有界代理） | tile16/本地shadow条件周期 | tile32/S4 shadow条件周期 | tile16总线上字节 | tile32总线上字节 |
| --- | ---: | ---: | ---: | ---: |
| native32 | 257428454 | 258322870 | 29714176 | 33981440 |
| legacy256/2次rescale | 2071815382 | 2079045254 | 212500224 | 246909952 |

tile32在同R容量下额外占S4 16384B，并增加S↔R传输；这同时改变tile和shadow放置，不能独立归因为纯tile大小或纯placement。tile16在本有限网格及两个EXT参数下作为下一轮工作基线，保留其他候选，不冻结硬宏。

shared8整池粗粒度最低native为135091774/143937894（EXT-II1/16），legacy为1060774102/1157113942；分配V2/R6的partitioned最低native173698710/185804310、legacy1397796118/1494135958。各自只是在两策略/已声明图内优化。shared8改变lane发射粒度及池化，不能把这组差值当合宏收益；同后缀shared/split对照才是纯标签检查，其差值为0。

norm spill比reread多512000B总线流量（32行、每行16000B，含打包头），各配置分别从fifo/critical取最小值后，legacy全部reread/spill配对完成周期相同；固定某一策略并非全部相同，native优化后也有小差异或相同。不把省字节直接写成省周期。保守固定slot分配中，V常驻15552B、R24576B，S0=27648B、S1=30720B，EXT=52078848B；FIFO各2KiB另计，未赠整state SRAM。reread仍保留同样容量槽位，未宣称已做最优生命周期回收。

### 重定标的完整代价及瓶颈

实际legacy shared4_4/tile16/reread/EXT1的独立分解核回原整数事件：256次commit、2次abort；decay/prediction/outer各8454144次产品，output8388608、beta66048；不是忽略失败尝试的256步计数。两次重编码本身外部读131072B/写131072B；首次重试必须保留全双head，因此fulltrial clone还要外部读262144B/写262144B。源编码RW与经过S/R的总线流量分列：rescale线上534528B，fulltrial clone线上534528B；失败attempt线上1069056B，接受的retry线上1608704B。后者包含本来就需要的成功执行，不全部称额外增量；这些分量也不能和外部RW混加成同一种字节。

在这个S8 digit+受检I64合并实现假设下，legacy的4条R lane占用约97.60%，另4条V lane约0.64%；BUS约0.64%、R端口约0.84%。这说明当前冻结图的时间由宽算术lowering/反馈链主导，不能据此说真实硬件端口不重要或应该制造独立R。M只执行相同有界代理，没有把R宽点积映射到空闲矩阵阵列；改用适用宽单元/M复用可能改变瓶颈和宏边界，必须是下一轮公平基线。norm32:R256是独立流人为配比，非整模型层间比例；一次性初态布局也在周期里，不能直接除256当稳态token延迟。

## 可复查交付与边界

[统一索引](../../project/experiments/range_service/results/issue-68/index.json)记录逐phase源码commit/SHA、原输入版本、四逻辑run及独立接收、精选与服务器全量位置。2.42MB portable-r.zip保留真实t[2,14)完整双head输入/状态/单位/epoch，覆盖两次rescale；服务器及本机各独立重放PASS，不能证明省略的前两步、剩余242步或原FP编译。四份服务精选保留原gzip和独立回执，可离线核日历/容量/元数据及实际重哈希epoch负例，不重做原NPZ算术。

本批69项新增边界/接收/聚合/分析测试及管理结构检查通过；原164项研究业务回归本轮通过。实际命令/日志和SHA在work68。原失败、静态饱和、S16退化、FP桥保留，不解封Phi、不新增模型、不修改成员Issue55/63。全部整数软件、条件调度、RTL与物理/模型质量严格分层。PR69交付待审查合并，非done；登记pending、看板unverified/同步pending，待指定审查人与管理员。

归档90151实际COMPLETED0:0/245s：完整8024664381B、SHA745968df14258e0984028a3d6d5626753196f4082dea1591719c9235ee51b8ea，1919成员逐SHA/大小读回及ZIP CRC通过；自身最后日志外置。精选数据18170182B（不含统一索引），未将8GB复制到本机。最终69个本人Slurm job中61完成、7原启动/接收失败、1本人pending取消替代；数值/服务与所有最终接收均完成，未抹掉原失败或中断他人作业。
