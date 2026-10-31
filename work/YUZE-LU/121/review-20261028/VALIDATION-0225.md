# 本轮验证

49份捕获文件大小/SHA及25条现存receipt输出绑定通过；六份测量报告的bench/数值参考/RTL逐一对应实际执行source_commit的Git blob，旧基线对应ad3c2b3；两初始化原报告一致。V264原始日志可由base64逐字恢复并匹配原receipt输出；S严格LEC所有检查通过。

实际268四测量/两比较、269两扩展测量均PASSED。Python编译、python scripts/check_project.py通过；结构检查不代替行为。新增文件代码/文档差分检查及提交后Git字节检查随后核验。此前原始timing.rpt/prove.log/load-sta.log空白与SHA保留，对全范围diff --check按明确三个文件名模式排除；本轮捕获没有修改物理证据以消除空白。V/R内部分时资源占用、实际S执行、模型/系统性能、P3/P4余项尚未执行。
