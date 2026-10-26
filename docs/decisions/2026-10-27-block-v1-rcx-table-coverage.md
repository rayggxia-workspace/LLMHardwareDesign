# 十二层拟合表的结构接收

Issue121，2026-10-27 CST。run026 六个完整场解分片均实际完成；run027
拟合后的全部常规电容上下文已有数据，但旧的“任何 DIST count 0 均拒绝”
断言拒绝了候选。原失败及输出保留。

固定 OpenROAD 提交 6ea4ca224f3589dd91809933f50f39af66053634 的
[extmeasure_res.cpp](https://github.com/The-OpenROAD-Project/OpenROAD/blob/6ea4ca224f3589dd91809933f50f39af66053634/src/rcx/src/extmeasure_res.cpp)
只查询 RESOVER 的上下文0；
[extBench.cpp](https://github.com/The-OpenROAD-Project/OpenROAD/blob/6ea4ca224f3589dd91809933f50f39af66053634/src/rcx/src/extBench.cpp)
的 linesDiagUnderBench 只生成相差1至4层的 DIAGUNDER。
[extModelGen.cpp](https://github.com/The-OpenROAD-Project/OpenROAD/blob/6ea4ca224f3589dd91809933f50f39af66053634/src/rcx/src/extModelGen.cpp)
依然打印所有层组合的空表。原生固定 ORFS 64939f3717ad7c694199ba04cb98924b98022868
的 Nangate45 rcx_patterns.rules 也有45个非零下层上下文的 RESOVER 空表和15个层差大于4的 DIAGUNDER 空表。

因此采用结构验证，而不修改模型数据：逐层检查全部普通/开放 OVER、UNDER、OVERUNDER
上下文及宽度、表计数、有限非负系数；RESOVER0 和层差1至4的 DIAGUNDER 必须有数据。
只允许上述两类工具约定空项，且不删除、复制、插值填充它们。提取使用 context_depth3，
不将该模型宣称为任意深度斜向耦合模型。

本地对原始 run027 模型实测2472表，2284个非空；188空表精确为132个非零
RESOVER上下文和56个远层DIAGUNDER。分别清空普通电容、必需电阻、M10/M11斜向
耦合表的三个负例均被拒绝。run029 重新执行拟合并记录结构回执；原始场解仍读取
不可变 run026。是否具备完整提取能力必须由另开的留出几何实验判断，结构接收不替代数值验证。
