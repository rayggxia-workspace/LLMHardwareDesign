# Issue68：R范围/重定标与同资源V/R/S服务

2026-10-24 Asia/Shanghai；负责人Liangruizhi；[Issue68](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/68)，基于PR67@8bde3bf2309c2b41b68c081e9dbbe8be42d2ee19。R数值双轮/独立接收及checkpoint已实际完成，V/R/S服务尚未执行；两者状态分开记录。

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

## 同资源服务实际执行中

冻结service源0fa2cc07aa192d746db34ebbb96ca512dcd52c99ff940c98ec0a98a85769d59c@ae9d26b，4个单配置producer pilot90092/93/95/96完成。接收器先因只允许双策略而拒绝显式fifo子集；两版原失败及一次root接收路径误填均保留，未重新运行数值或producer掩盖失败。最新phase9读取原pilot01/02，90102 native已PASS、90103 legacy实际仍在接收。

28分片90104–90131，每分片独立目录、1CPU/1线程、7组织×2源任务×2轮，默认2tile×2norm route×2EXT×2strategy，预计每轮每源56配置/112witness。4逻辑聚合90132/33/35/36及全量独立接收90134/37已afterok排队，未提前称完成。label-only sharedX_Y/splitX_Y保持逐节点相同资源，shared8是不同发射粒度，不归为纯物理归属收益。
