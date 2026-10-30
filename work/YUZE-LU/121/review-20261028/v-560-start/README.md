# V560 副本编码诊断已提交

Refs #121 / PR #122。93748/node20实际RUNNING，使用Issue统一8allocation锁，PENDING/UNKNOWN/旧任务均计入。源5b6359bfc1db39d1a5a8adf763c7a2dd0e298d63，归档3c9ee22faaa219c8470b2a8c6a8133ec0b6177e7a8cfda3a0afce6f92beda6ec，313源Git/远端SHA、实际run/argv及前置557 receipt核验。c96六个16CPU动态槽，只有一项真实ready诊断，内存64GiB×1.2+16GiB保护/实际RSS；不造占位任务。

只在旧523 ODB内存副本中显式编码445个已有同网wire/via并集完全覆盖的RECT。必须核对原矩形全部保留且只新增精确预期445矩形，并运行不修改的原生全片DRC。原ODB不写回，失败原样保留。即使诊断通过，也不能授予任何宏物理资格：完整全网几何/XOR、连通、fresh final/RCX/STA/电气、完整未改GDS deck、最终功能和严格LEC仍需在同一最终源完成。旧源setup/cap拒收保持。
