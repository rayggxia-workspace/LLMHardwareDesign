# 旧 V400 完整 DRC 终态：仍拒收

Refs #121 / PR #122。2026-10-30 04:21 CST。93578 自然 FAILED/1:0；final-source、三初态最终网表功能和严格 LEC 已通过，但最终时序与独立原生 DRC 失败，因此 delivery/geometry 被真实前置拦截。

本目录保存 12 份原始文件及 index.json：完整未修改 FreePDK45 GDS deck 为 **0 项**，report 23965 bytes/SHA d20fedb88f546ca06eae9b3bd7af3a8d15878fee889e1ed863fbd3b053c3cd37；独立原生全芯片检查仍 **433 项**（432 Metal Spacing、1 NS Metal）。原生报告与先前快照逐字节相同。两门不能互相代替，不推断工具误报或授予豁免。

实际 final-source 回执 SHA 与最终功能记录一致，deck SHA 与旧375完整 deck 一致。稳定输出均匹配原任务 receipt。node-queue-child.log 在 receipt 封存空日志后追加 worker 的 assert result['passed'] 失败堆栈：索引保留原空日志哈希和捕获哈希，未伪装为 receipt 稳定输出匹配。初次本地收集因这一追加日志拒绝；保留已捕获字节，核实追加内容后补全索引，无 EDA 重跑或原文件修改。

GDS 大文件留获授权服务器，路径/大小/实际检查使用的 SHA 见索引。index.passed 仅表示收集与绑定核验通过，actual_drc_passed=false；不能给当前 V410 转移任何物理资格。
