# 当前 V410 / R404 完成 CTS 的阶段证据

Refs #121 / PR #122。2026-10-30 03:26 CST 捕获 30 份原始文件，大小/SHA 见 index.json。二者均完成 synth/floorplan/place/CTS，进入 route；**不是最终 300MHz 验收**。

| 项目 | V410 / 93585 / node16 | R404 / 93555 / node21 |
| --- | --- | --- |
| 源 commit | 33bb0916943a72f5b07860d89a24d088cf6e893c | d1aadb3ed41a1f6fe9c79280c6f0358c358dec0d |
| 源归档 SHA | ec978042c42931a8b15527588ea9dfa2f1c95683108d26111345158b6c27da26 | f9b9db75983acffbe2edf5a3e3f1dfcea9a3fa34024a3a80ffc820daf2fcedf9 |
| 已核验源 Git blobs / 远端实际源 SHA | 309 / 309 | 308 / 308 |
| CTS setup WS / TNS ns | −0.0163065 / −0.103482 | −0.00195399 / −0.00195399 |
| CTS hold WS / TNS ns | −0.235032 / −3.78777 | −0.0930063 / −0.279496 |
| 实际所有时钟网 NDR none | 4984 | 27414 |
| CTS 修复内部 LEC common inputs / outputs | 51206 / 51195 | 292950 / 292936 |

内部 LEC 均 UNSAT/IDENTICAL，四组 diff 边界均 0；不得转写为独立最终 LEC 通过。V 的实际修复命令 `-hold_margin 0.08`，R 为 `0.02`；两份日志均保留未修复全部 hold 的警告，V 另有 setup 警告。配置中后面的 HOLD_SLACK_MARGIN 覆盖前值，实际命令读回与策略相符，未放宽最终时序门。

300MHz、全部数值/状态/周期不变。继续原生 route/finish、独立最终时序/电气/RC/PG/连接、完整原生及未修改 GDS DRC、三初态最终网表功能、严格 LEC、六文件/完整几何和接口验收；不存在旧 V400 或旧 R 的物理资格转移。
