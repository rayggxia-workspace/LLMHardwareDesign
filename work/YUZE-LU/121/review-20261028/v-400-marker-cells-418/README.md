# 旧 V400 四标记的单元几何补查

Refs #121 / PR #122。2026-10-30 04:21 CST。418 使用 R404/93555/node21 现有 allocation 的空闲16–31 CPU，内存 guard 与固定 SIF SHA 检查后只读原始 V400 route ODB，正常 COMPLETED/0；原 ODB 前后 SHA 相同并与原400输出回执绑定。

10 份原始文件及 index.json 记录：遍历492544个实例，按415同四个标记的扩展窗口与实例 bbox 相交筛出4个实例，检查45个 pin geometry box、32个 master obstruction box；完整应用实例 transform 后，同层窗口内命中0。实例 bbox 作为筛选范围，不能解释为任意窗外引脚或全体433项覆盖；OBS是障碍而非导体。未修改原数据库、当前 V410/R404 或任何规则。

原始 odb_geometry.tcl 与启动commit Git blob逐字节一致；有限 marker_cells.tcl 为本诊断捕获脚本，按 launch.tool_inputs SHA核验，并非声称已存在于启动commit的正式源。初次本地准备因 Python 字符串转义检查失败，发生于远端创建前；修正为保留 Tcl 字面转义后只启动一次。此次零命中仅补全先前415未扫描单元几何的局部信息，根因仍未确认，不构成物理接收或误报判定。
