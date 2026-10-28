# 本次证据核验

Issue #121 / PR #122。目录时刻是快照名称，真实UTC时间见各index.json。

- run282：15份捕获/12条输出绑定；run283：31/24；run284：21/16。每个index的大小/SHA及所有本地存在的receipt输出逐字核验，两初态原始JSON一致。
- 三个不可变源码archive分别绑定1a1a11e、45604422、f93ab12e；全部286/288/288份归档文件与其Git blob原字节逐项比较。receipt非缓存输入与archive逐项比较。远程运行生成的`__pycache__/*.pyc`仅保留原回执记录，不作为Git源码字节一致声明；未把它们加入源码归档。
- M原始bench、形状spec、实际RTL与生成bench SHA核验。9份config快照与当前Git原始config字节/解析值一致。1024/3072的16条continuous_supply/resident_reuse原始计数与255完全相同；255报告额外的两项派生速率先按MAC/周期公式核验，再去除派生字段作原始记录比较。
- S/V全部RTL、查表、wrapper、独立数值参考、原bench与生成bench SHA核验。只改变长度列表，不改变硬件/控制流程。
- 实际M/T固定路径图由原始回读图形生成；两PNG已查看。原始probe.log尾部空格不修改，以保持receipt输出SHA。
- S280原生流程及新物理门通过，native-0420是尚未完成DRC/最终功能的运行快照，不能作为S最终交付。后继严格LEC依最终功能补位。V270/R236仍运行，281尚未分配。

代码/文档差分检查明确排除已有原始timing.rpt/prove.log/load-sta.log、s-patch-033*的localize.log/wire-api.log/patch.log，以及此次preconnect-0400下两个实际probe.log的原始空白。排除只用于Git文本空白检查，不排除任何业务验证或SHA核验。

S280 native最初沿用了32GiB只读探针预估，遗漏fresh finish内置LEC，预估错误。实际采样进程树峰值132908896256B（约123.78GiB，500ms采样；共享页可能重复计），单进程HWM约122.29GiB；当时只有此依赖任务在本任务节点运行，没有OOM。不可变280 queue保留原值；未来同类S finish须按至少160GiB预估再加1.2倍准入和16GiB guard，严格LEC192GiB预留不降。不能把32GiB当作已证明足够的并发依据。
