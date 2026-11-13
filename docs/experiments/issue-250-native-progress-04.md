# Issue250：完整费用失败与真实流式窗口

2026-11-11 CST，Refs #250 / PR #251 / 硬件 #252。此页接续progress03；目标继续实施，不以组件PASS、上传或条件仿真结束。

## 当前决定

保持五类控制分组、独立叶宏与实际端点；私有S仍16KiB，无新增共享payload池。先把真实服务、窗口寿命和程序接通，再优化通用DP。新增寄存器、MAC、DMA缓冲及其面积独立计账，不将硬件改进或错误费用修正记为算法收益。

完整decode512历史trace的15-partial动态点积费用回校已暴露重大缺口：3P理想601548755周期、0.498712693745 token/s；观测组件压力0.433671633137。旧8.136179行使用未资格动态占位费用，只作历史对照。此为完整scope的SystemC时间诊断，**不是完整模型数值推理、全原生控制/物理或能耗验收**，E/N、源loader/PM等仍有缺项。原工作量/权重/精度/300MHz不降，重复预约DDR→S的失败102340也保留。详见[FULL_DYNAMIC_FAILURE](../../work/YUZE-LU/250/native-service/FULL_DYNAMIC_FAILURE.md)。

该缺口不能靠DP去掉15条实际record；#252 / [draft PR253](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/253)独立开发有限S128原生S32 full-K点积，对4/8/16计算lane及多query复用做真实存储/面积/供数Pareto，最终只选一种provider。核心正确不等于S前端、完整token/s或物理通过。

## 新的实际证据

| 范围 | 实际结果 | 界限 |
| --- | --- | --- |
| 新epoch COPY与S覆盖 | 102368，36PASS；同key不同K、两个live A槽，旧S真实覆盖，全部A值/shift保持 | 无M/实际LC外层 |
| 86 Mid tile分散三P | 102366，36PASS；29/29/28本地目录项，六次遍历共516 COPY，258对双A槽，3096 A use，24768 S覆盖写，最后1376个Mid word逐字保留 | host提供A16输入；无上游M/G/量化、Down算术或控制程序 |
| 实际U量化→Header/COPY→P/M→S | 102353，18PASS；315 W64返回、192 COPY源读/目的写ACK、12真LOAD proof、24结果ACK，独立整数oracle | 旧7d1f预取配置；新a424的102370另18PASS/315返回/24SACK，均只一P |
| 真COPY中止与重用 | 102359，18PASS；prefix4 halt、held请求排空、错误LOAD proof、真M CANCEL/DRAIN/CTX_DROP、RX cancel释放，然后同owner重跑K256逐位正确 | 一P；新a424配置102371另18PASS，原始回执均保留 |
| service2的类型/范围 | 102373，18PASS；完整K11008、单256B S窗，132范围case、六票、七tail、30拒绝 | decoder/实际range iterator，未注册实际typed2 provider/外层 |
| 老service1兼容 | 102374，18PASS；默认仍拒绝service2，没有把新服务偷偷授予旧provider | 原类型/范围证据，不是M物理 |

102373只通过默认关闭的`ALLOW_STREAM_A16`显式optin；实际provider还须独立开关及真实LOAD/ACK接入。完整scope的service2不支持partial RESTORE/SPILL或非零bias。输入空间检查按当前K128窗，不能错误要求完整11008个A16一直驻留同一S。

## 同S复制是实际资源限制

102361无背压完整通过，但背压第一个tile死锁：本地源预取读响应排在上一笔目的写ACK前，copier载荷保持等待ACK，形成有序响应环。a424fd244为STREAM的epoch copier关闭下一word预取，直到所有目的ACK清空payload hold才发下一源读；没有加16B FIFO或隐藏读口。102366/368分别重验PP/UP；旧独立U源的legacy实例默认预取行为保留。

新COPY配置的UP实际M联合102370/371各18PASS，source/全部原始回执已按字节分片入库并锁SHA；资格仍为一P实际组件，不自动转为typed2或整个外层。实测seed1正向4997→5285周期（12tile多288），取消1055→1103，不能沿用旧COPY费用。可以继续研究跳过本地自复制，但必须改变真实LOAD地址/写完成合同并另验，当前未采用。

## 物理与候选

G32仍仅独立叶宏最终原TT300MHz通过。M f08同原约束P&R未闭合；新good-CANCEL控制切链保持数值/费用、映射726068.280平方微米，较f08多2.926，尚不是最终面积或时序资格。M2两owner候选明确新增121.625B逻辑metadata，原Lib映射735299.278平方微米（较f08 +1.272%）、外pin同为1330，叶级可观测II14；未将其替换成默认系统II。两候选独立做原约束P&R/guard/存储联合，均未冻结。

主控共享六返回槽比旧四槽多128B寄存器，仍须面积/物理计账；局部S不扩容不等于整芯片存储增量零。时钟/复位/PG/最终网表/全原版DRC/电气/300MHz与M10接入按实际源版本逐项验收。

## 复核与恢复

小source与逐项SHA随Git，较大原始bank日志按项目存储规范保留在已授权拥有者集群及C盘同字节镜像；`distmid/index.json`记录精确archive URI/字节/SHA。不能拿索引冒充离线全审计。详见该目录README，审计必须显式提供raw镜像：

```powershell
python project/experiments/block_local_native/audit_quant_copy_a.py --root work/YUZE-LU/250/native-services/distmid --receipt-cache CACHE
python project/experiments/block_local_native/audit_quant_copy_a.py --root work/YUZE-LU/250/native-services/copylook
python project/experiments/block_local_native/audit_p_scope.py --root work/YUZE-LU/250/native-services/scope-stream
python project/experiments/block_local_native/audit_p_scope.py --root work/YUZE-LU/250/native-services/scope-default-regression
python project/experiments/native_s_calibration/analyze_dynamic.py --run work/YUZE-LU/250/native-service/run-23
```

上述均已对实际原始包运行通过；check_project只查管理结构，不替代业务验收。102357/360 strict失败、102361死锁及no-Slurm部署目录冲突全部保留。下一步是实际typed2 outer、三P并发/M2、native S32、剩余E/N/程序和原物理，随后用同一能力/状态/费用模型调整DP/greedy并做独立数值/性能/能耗对照。Issue250继续in_progress，PR251 draft，登记PR5 pending、Projects未验证/同步pending，独立审查人待指定。
