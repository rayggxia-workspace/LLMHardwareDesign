# S补片阶段验证说明

Refs #121 / PR #122。

- 277三stage定位、278实际API、279补片试验均由Slurm实际运行，完成证据27份原始文件/19条receipt输出SHA绑定通过；27份Git blob逐字节一致。
- 280/92987/node17已经提交；全DEF非目标字节SHA完全相同，目标net仅新增声明RECT的token检查通过，fresh fill/route别名/finish正在运行，四最终门按真实依赖补位。不是已取得最终资格。
- Python编译与check_project.py通过，后者只检查管理结构。
- 原始工具日志存在工具自身尾空格/EOF空行，必须保留SHA。差分检查除沿用timing.rpt/prove.log/load-sta.log外，新增明确排除s-patch-0330和0335捕获中的localize.log、wire-api.log、patch.log；只排除这些原始工具日志，代码、JSON、文档仍检查。
- 280复用258的已过序列化小电路参照原文件/receipt；物理门读取时继续核对工具二进制、库、控制脚本及预算SHA。未转移任何旧S物理/DRC/功能/LEC资格。
