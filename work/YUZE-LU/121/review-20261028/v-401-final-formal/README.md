# V401 对旧 V400 最终网表的独立严格等价

Refs #121 / PR #122。401/93578/node23 的独立严格 LEC PASSED：51206 common inputs、51195 common outputs，四组 diff 输入/输出均 0，UNSAT/IDENTICAL。

原始小文件及源 Git blobs、回执输入/收录输出 SHA 和最终来源绑定见 index.json。源 62e3e5776c891a83f8665d0b86a99fb6aa36f188，308 个源 Git blobs 已核验。来源回执 SHA 与已核验的三初态最终功能所用最终来源相同，绑定旧 V400 实际最终 V/ODB。

这是旧 V400 的最终网表严格 LEC；其负 setup/hold 和 433 项原生全芯片 DRC 违规仍拒收。完整未修改 GDS deck 尚在运行，新 V410 需重新完成自己的全部最终门，不继承本结果。
