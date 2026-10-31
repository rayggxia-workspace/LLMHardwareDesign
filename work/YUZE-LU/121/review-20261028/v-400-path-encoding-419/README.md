# 旧 V400 普通路径编码对照：未修复

Refs #121 / PR #122。2026-10-30 04:32 CST。419 在 R404/93555/node21 已有 allocation 的16–31、32–47空闲CPU并行两项副本对照，均正常 COMPLETED/0；原 route ODB 前后 SHA不变，源回执与当前保存的400原始回执绑定，未新增 allocation或取消EDA。

clock/ns各在原同网短线中心线追加一条普通双点路径，不含通孔或RECT；完整DEF差异各仅单条NEW路径及原末尾分号移位，完整Verilog前后SHA相同。计划bbox由415已捕获wire矩形及140DBU宽度构造，新增端点见各probe/DEF diff；本次未单独从probe ODB导出默认宽度，因此不将该计划bbox当作完整导体并集等价证明。

两项原生全芯片报告均仍与原始433项报告逐字节相同，普通路径编码对照也不支持修复，hypothesis_supported=false、physical_qualified=false。不向当前410/R404注入改动，不推断误报或屏蔽规则。17原始文件与SHA/字节、启动/inspect脚本SHA、原始ODB与回执和完整网表/DEF差异核验见index.json；10大文件保留服务器索引。

index.passed只表示有限诊断执行和证据核验完成。当前V410仍须自己的最终时序、独立完整DRC、功能与LEC和接口资格；旧400保持拒收。
