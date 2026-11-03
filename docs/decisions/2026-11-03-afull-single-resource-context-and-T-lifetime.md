# AFULL单资源整合与T生命周期

Issue151/PR152，Melodydt；源08e674a272a74810e761fadd2d047285e0b1e0ff，实跑95793。将AH2与ATSP机制合为新局部FSM，保留一套M/N/E/S/T，不复制验证top；原X交错T lease，全部context在S真实形成后才Wo，逐字T capture→S258 ACK→E→目的ACK，最后原T RELEASE后再输出lease。8A padding真实写零一次并保活，减少197624次写；512context ACK计数是进入Wo的必要条件。源/T metadata与padding写保护提供有限错误终态，不能替代全系统late-response隔离。

所选Fin10/W7/eps1 profile让S16KiB/T4096B构造成立，已用独立完整整数golden和32CASE/9实流验证；若扩大seq、精度或增加cache，须重新接收容量/数值/接口。下一L4-AF1024接真实Y到F，L5一般控制网络及M11产品物理另验。固定算法程序与参数流分离，未实现启动装载控制程序或产品ROM永久绑定。
