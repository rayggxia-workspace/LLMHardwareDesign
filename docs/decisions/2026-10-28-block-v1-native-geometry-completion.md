# 完整原生占用和 M10 底部几何交付

2026-10-28 03:11 CST，Refs #121。实现计划第7项及五宏规格要求接点形状、OBS和未来via10所需enclosure；本工作只读导出最终积木，不增加宏版本、上层路由或通用层次模型任务。

216/217原生迭代器导出及底部几何检查通过，但不能单凭其原scope称完整：安装版dbWirePathItr漏DEF RECT，M205有已由GDS精确证明的M2补铜。218实际API探针确认Tcl没有dbWireShapeItr；其进程返回0但语义探针失败，保留记录。

219/220在新文件中补全原生DEF全部普通NETS的RECT，保持原net身份并核精确多重集；遇不支持的RECT语法直接拒绝，不漏过。M恰1处[282460,530600,282650,531160]DBU，T无此类RECT。完整占用包含wire/via、PG、BPin/ITerm、实例master OBS和block OBS；OBS必须作为禁布信息，不作为电气导体。原ODB哈希保持。旧导出与报告保留，并以coverage-status明确其完整性未合格。

M/T新数据见[完整M几何](../../work/YUZE-LU/121/delivery/M/native-geometry/README.md)、[完整T几何](../../work/YUZE-LU/121/delivery/T/native-geometry/README.md)。M10合同包含实际signal pin/net/DBU和0.6µm cut+0.1µm bottom enclosure；只证明容纳于固定M10矩形，不签发上层route或via电气资格。candidate.lef只读生成，abstract coverage/Lib/M11-M12系统仍false。

[216–220实际step证据](../../work/YUZE-LU/121/results/native-geometry-030826/index.json)：只复用既有215/92511的80–95核。不可变215 DAG最大反链5个16CPU任务，且已封存生产调度器始终选择最低空闲CPU，故该16CPU子集在将来补位时仍独立；一次仅一项有硬时限的只读诊断，不重启或取消EDA。Slurm step96CPU是既有allocation的可选cpuset envelope，实际taskset限16，不是增加96CPU。M/T导出约63/153秒，MaxRSS460744K/1790104K；补全约23/42秒，前者0 MaxRSS为采样缺失而非零内存。

221源2278615已部署暂存且Linux验证通过，但三个leaf-delivery均未就绪，dispatch-state.tasks={}，没有提交。后续待S/R/V各自同源四门和delivery通过后，按八allocation上限和6×16即完即补导出。引用真实子回执，不把会park/排空的父Slurm终态当逻辑子任务失败。
