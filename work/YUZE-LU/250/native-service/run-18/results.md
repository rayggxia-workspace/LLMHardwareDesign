#102203 下游提前广播与权重布局负对照

同一完整trace/总线读取/3,028,352 M记录，八任务各12CPU，独立服务微时间线和
全图资源审计全部通过。4/6票、纯调度与layout co-design分开。

| 条件 | token/s |
|---|---:|
|102172旧pipeline/192条带参考|8.507946|
|任一P触发下一个Mid广播，下一copy仍等三P完成LOAD|8.510610|
|K-major权重部署布局，仅co-design|8.477164|
|K-major布局+提前广播|8.477423|
|102202新三stage scale/RF profile|8.228410|
|新profile+提前广播|8.228485|
|旧profile提前广播但4票|8.501668|
|旧profile提前广播但不平衡尾context|8.486307|

提前广播纯调度收益只有约0.03%，新pipeline下更小，不能夸大。K-major部署
在该DDR模型反而变慢，保留负例且不投入真实packer，不从布局收益冒称DP20%。
新profile对应root/Wagent102202、source31846aad1：ordinary RF晚2拍；head
RF晚16拍，INPUT晚8拍，A实际在+1/2/3/4/7/10/13/16接受。W晚8拍早释、
A lease保持更久均计入。尚无300MHz物理资格；E/N/dynamic服务仍未绑定。
