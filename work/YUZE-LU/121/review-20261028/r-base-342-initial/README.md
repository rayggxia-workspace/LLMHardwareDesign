# R342 新旧状态预取验证与被拒绝采样

Refs #121 / PR #122。源76f8db5758ecefdd72d45b0544ecb9a79ed6bced/archive01b5022856…，93189六项独立16CPU任务启动。三初态数值/事务各379979检查、178456拍；公共24及卷积9案例各两初态通过，映射继续运行。

两项占用任务FAILED，原因是策略仍指向309公共回执、当前RTL已变；revision300_lane_occupancy.py的精确RTL SHA同源保护正确拒绝。失败未删除、不复用旧采样；后续343将绑定342新公共测量重新执行，两项源/参考SHA校验保持。

所有捕获原始SHA、307份源Git blobs/receipt输入已核验。失败receipt在wrapper写入Traceback前记录child.log为空，其后实际原日志已有Traceback；两份原字节均保留，这两项后写日志差异见verification.json，不宣称失败回执全部输出稳定或科学任务通过。其余稳定输出按原SHA核对。新状态预取未获得物理资格，311原流程正常运行。
