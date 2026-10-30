# Issue121 继续入口（2026-10-31 07:31 CST）

Refs #121 / PR122；负责人YUZE-LU。

2026-10-31 07:31 CST：801/94054六个6×16候选均自然PASS，全片native均0，全部562494网络/目标header/原路径/其他RECT/非NET几何精确核对；803封存48原始/12实际服务器大文件SHA及363归档Git源、receipt输入/稳定输出。只选择case1（RECT右边497.800µm）继续，原wire/via/PG保持；原767完整GDS失败保留。准备804 fresh RCX/最终报告→805全部新验收门与完整信号几何→806全端口/有限RC，由只监视这三队列的新控制器按真实前置补位。V总accepted=false，R原404继续，M/S/T保持。

选择case1仅缩短原RECT右边：原metal2(995340,145880,996180,145950)，新(995340,145880,995600,145950)，DBU2000/µm，实际制造网格10。实际GDS/ODB定位见797/798，错误网格前置失败见800；六个候选的成功不转移完整GDS或最终资格。原始源和失败完全保留。实际几何图[802](actual767-metal2-marker-802.png)已查看，仅标记原失败及候选，不是假定修复结果。

新finish policy2严格绑定801 case1原receipt/报告/单RECT编辑、767 source f06b8e14…与630→629祖先和原RTL，不接受外部源；复制后只做ordinary do-6_report/RCX，不reroute/fill/优化，原NETS和非NET几何必须精确不变、复查native0。805 signal connectivity新导出并检查完整网络，新接收门强制同源证明；旧776失败复核分支仍只允许旧767源，不能拿782旧结果接收805。

待实际提交804/805/806及部署807后核对jobID、PID/CPU掩码、源归档与回执。6×16动态补位，本Issue最多8allocation含旧/PENDING/UNKNOWN，其他Issue不计；真实依赖未就绪不制造复制任务。原R404/93555及634/769控制器均保持，原767needs_attention/768未提交。

当前线上commit89c4aecc，PR122draft、Issue121in_progress，head/body均精确读回。登记PR5 pending，board未配置unverified/同步pending，管理员/独立审查人待指定。目标active，五宏最终未齐。
