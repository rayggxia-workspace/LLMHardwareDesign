# 本轮验证与提交回执

- 规则：rayggxia-project-collab 1.0.0；Issue121/PR122，账号YUZE-LU。
- `python scripts/check_project.py`：通过，只验证管理结构。
- `python -m py_compile`：delivery/escape/escape_gds/worker及本地stage生成脚本通过。
- P2纯Python正例/重分割正例及六种真实几何改变负例通过；实际KLayout/OpenROAD须以远端报告为准。
- 新M255的128输入位符号等价及三初态数值/溢出保护/映射/两组性能实际通过，详细布线运行。T新四门、最终文件、完整原生几何实际通过；其余未完成项见状态与交接。
- 本轮不可变小证据分别76与10份；index记录逐字节SHA和大小，receipt输出绑定按实际捕获项核验。原始timing.rpt末尾空行保留以保持原证据SHA，代码/文档另外执行diff --check。
- 本轮提交为进展，未验收五宏整体；PR保持草稿、Issue in_progress，不关闭/合并。管理中心登记PR5仍pending；缺board.json/Projects工具，看板unverified/同步pending，管理员与独立审查人待指定。未将本地摘要等同看板已同步。
