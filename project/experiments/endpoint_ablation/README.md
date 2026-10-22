# 端点限制的配对消融（Issue13）

本目录依赖[Issue11模型](../frozen_routing/)，不修改其源码或原始记录。目标是把限制本身与路由搜索失败区分开，不提出新路由算法，不验证物理H2/PPA。

## 冻结内容与四条件

每组先生成一个最大**合成**库存master：所有导线、tap、Block、有源输出、可选连接及最大容量固定。overlay仅限制允许连接与wire-tap容量。保存master、overlay及materialized有效配置三个独立SHA-256；不同有效配置不是相同的完整物理底座。

| 条件 | 引脚可选连接数 | wire-tap容量 |
|---|---|---|
| restricted | 原始2/4 | 3 |
| access | 扩展4/8 | 3 |
| capacity | 原始2/4 | max(3, 扩展库存中该tap的degree) |
| joint | 扩展4/8 | 与capacity完全相同 |

所有条件pin容量均为1，导线不可拆，不加内点、选择器或buffer，定制连接总预算160不变。放宽容量只是反事实上界，不是可制造接点数；新增可选pin接线也不等于工艺上已获许可。

8组库存×4图×3seed×4条件，共384例。四条件固定同一映射、net顺序、multi_order实现、seed与14次尝试。之前的design/held_out标签保留为来源信息；这些图已经观察过，本轮不是新盲测。

结果区分路由器找到、其他条件提供合法witness、固定映射已有闭合cut证明无路径、未知。witness仅重绑定目标有效配置hash并全局重验，保留来源，不篡改原始搜索记录。约束放宽后启发式可能未找到已有合法解，不能说可行性下降。仅capacity搜索成功变化不足以证明容量导致原实例不可行。restricted的无路径证明加access的合法解可证明该白名单约束对当前映射的影响；joint对应联合放宽，不称access单因素收益。

六类手工微例分别隔离白名单、容量、联合限制、多驱动、正例、总预算；每个最大5个连接，全子集精确检查。大例不声称全局最优或不可行。

## 执行与复查

在项目根目录，先为进程设置TEMP/TMP/TMPDIR/PYTHONPYCACHEPREFIX/MPLCONFIGDIR到 `D:/Projects/Codex/issue-13-endpoint-ablation/` 内对应子目录，不改系统变量。已有D盘Python／项目venv、NumPy；图表需要Matplotlib。

```powershell
python scripts/check_project.py
python scripts/check_research.py
python project/experiments/endpoint_ablation/run_ablation.py --out project/experiments/endpoint_ablation/local_runs/<新目录>
python project/experiments/endpoint_ablation/verify_ablation.py <运行目录> --replay
python project/experiments/endpoint_ablation/report_ablation.py <运行目录> --out D:/Projects/Codex/issue-13-endpoint-ablation/<新图表子目录>
python project/experiments/frozen_routing/package.py --run <运行目录> --figures D:/Projects/Codex/issue-13-endpoint-ablation/<图表子目录> --out <新归档目录>
```

正式运行拒绝dirty源码与已有输出目录。开发例必须显式allow-dirty，不能提升为正式证据。只在清洁真实commit上跑正式实验，输出与输入逐字节hash；verify还从声明的Git commit读回每个源码文件。

真实LEF视图可访问但宏资格仍不完整；本轮不混入其几何、负载或RC，也不把矩形存在当可合法引出。接入条件见[宏端点合同](../../../docs/MACRO_ENDPOINT_CONTRACT.md)。
