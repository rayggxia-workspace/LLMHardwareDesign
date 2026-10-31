# 旧 V400 重复 RECT 编码对照：未修复违规

Refs #121 / PR #122。417 的 clock/ns 两项在 R404/93555/node21 已有 allocation 的 16–31、32–47 空闲 CPU 并行运行，均正常 COMPLETED/0，原始 route ODB 前后 SHA 不变。启动固定 SIF SHA 和节点内内存 guard；没有新增 allocation 或取消任何 EDA。

每项只在内存副本向一个报告网络追加一块 RECT：clock 为 M3 的 60×140 DBU，ns 为 M2 的 80×2 DBU。对应 bbox 均被 415 捕获的该网络已有 wire 完整包含；416 对同批网络的两种几何读取一致。副本实际完整 Verilog 前后 SHA 相同，完整 DEF diff 只有该 RECT 和原记录末尾分号的移位。原始数据库没有改写。

**两项检查后的原生全芯片 DRC 报告都与原始 433 项报告逐字节相同。** 因此重复覆盖 RECT 的假设未得到支持，不采用为修复，不向新 V410 注入此改动。index.json 的 passed 表示诊断执行和核验完成，明确 hypothesis_supported=false、physical_qualified=false。

17 份原始小文件及 SHA/字节见 index.json；10 份大 DEF/V/ODB 留在服务器，索引复用节点内 inspect.py 实际生成的 SHA，采集时再核对实际大小。没有将这些副本作为最终交付物，没有豁免任何规则。初次本地收集核验假设 DEF 分号位置不变而拒绝；按实际 diff 修正为原末尾分号移到新增 RECT，所有已捕获字节保持，未重跑 EDA。
