# R范围与V/R/S同资源服务

Issue68 / PR69；[正式记录](../../../docs/experiments/issue-68-range-service.md)。

- [RANGE.md](RANGE.md)：因果guard、旧state逐次RNE重编码、重试与原子发布。
- [SERVICE.md](SERVICE.md)：同精度/任务/恢复语义及有限1RW、8总S8 lane、SFU、FIFO和外部后备，完整条件DAG调度。
- [AUDIT.md](AUDIT.md)：独立Python整数参考、逐witness服务核验和实际重写SHA负例。
- aggregate.py：7个不可变分片组成56配置/112witness逻辑run，不执行模型或数值算术。

先运行`python -B scripts/check_project.py`，再在已有NumPy环境执行`python -B -m unittest discover -s project/experiments/range_service -p "test_*.py"`。临时目录指向D盘任务目录。数值与服务实际任务均经本人CPU服务器Slurm，不新增权重或其他机器。

当前R实际双轮已完成；服务28分片与聚合/全量接收进行中。不能将软件整数、条件服务周期写成全模型质量、RTL/PPA或制造边界验收。
