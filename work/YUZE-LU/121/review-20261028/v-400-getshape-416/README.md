# 旧 V400 选定网络的形状 API 对照

Refs #121 / PR #122。416 在已有 R404/93555/node21 的空闲 16–31 CPU 只读运行，COMPLETED/0，原始 route ODB SHA 不变。9 份原始文件及源/脚本/helper/ODB 绑定见 index.json。

对 415 选定的四个报告网络，同时导出 dbWirePathItr 与 dbWire.getShape 的实际 wire/via 矩形。539 行逐行完全相同，差异 0。它排除了这四个网络当前这两种读取方式不一致的假设，不能推广到所有网络、所有 API 或解释全部 DRC。

不修改数据库，不作为 DRC、RCX 或最终物理资格。该结果与旧 V380 的提取后时钟宽度异常分别保存，不作相同根因推断。
