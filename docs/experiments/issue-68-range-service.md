# Issue68：R范围/重定标与同资源V/R/S服务

2026-10-24 Asia/Shanghai；负责人Liangruizhi；[Issue68](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/68)，基于PR67@8bde3bf2309c2b41b68c081e9dbbe8be42d2ee19。当前为协议冻结/实现阶段，数值与服务尚未运行，不把计划写成验收。

## 问题与冻结的取舍

旧同范围S16/S32有184/193最终state饱和；新完整hidden RMS临时行超16KiB，V32 old/new占满R32KiB。只补仍改变物理边界的范围协议及同资源服务，不扩大模型品牌/长度矩阵。

R固定static_sat诊断、static_guard拒绝、guard_rescale因果候选：guard失败不能发布；仅对当前越界head的旧整数state做RNE重编码并coarsen exponent，完整重试同token，最多8次，单位/epoch/状态/输出共同提交。源S32上界仍32767<<16，不偷扩为任意INT32。所有原始clip/sat保留；adaptive改变数值合同，不能与static直接当placement收益。初始来自已编码的独立cal或旧初态迁移诊断，不看未来native或评价误差。

服务固定V16KiB/R32KiB/S8×32KiB/各1RW128bit，R/V总8个S8 lane（shared8或split2/6、4/4、6/2），唯一共享sqrt/div，单128bit bus/有限2KiB FIFO及有限EXT backing。旧新整state超scratch必须分页，不能赠双shadow。Rtile16本地old/new+aux与tile32+Sshadow作为候选；没有相同恢复语义的原位方案从主排名排除。两遍norm源读与aligned spill互斥、gamma流式、A8/Ae、scan/retry/rescale/epoch流量都入图。EXT/算术时延仅条件参数，待RTL校准。

norm32与旧R256属于不同真实捕获；同场比较只作为两个独立竞争流，不复制norm32冒充同一连续模型链。任何FFN/attention背景仅有界且完全相同的代理负载，不称整图。Phi封存、Issue55/63保持他人范围。

## 执行入口

根D:/Projects/LLMHardwareDesign-range-service/task/68-range-service；range/service/独立审计子树分别D:/Projects/LLMHardwareDesign-68-range、-68-service、-68-audit，仅各模块独立修改。服务器新根/public/home/yuzelu/RuizhiLiang/issue68-range-service-20261024；旧Issue66数据只读。初始只读盘点：c96有1344空闲核、共享盘约12TB空闲，本人旧批次已结束，其他成员89448/yzl-vec-resume在node3，未中断。数值代码冻结后通过Slurm lrz-i68-*并行，实际job及接收结果待回填。

登记沿用management-hub PR5 pending；无board.json及可验证Projects字段能力，看板unverified/同步pending待管理员；审查人待指定，未审查合并不done。
