102196严格编译及量化95/60、copy133独立检查全部通过并打印TRACE_MATCH。
自检提前返回分支漏设原模型`passed`状态，导致sc_main返回1，driver正确拒绝。
在所有断言通过后明确设置passed=true，保持未通过时异常/非零退出。
