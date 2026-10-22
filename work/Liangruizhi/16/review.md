# 独立审阅与真实数据审计

方法审阅在独立会话执行，只读检查本任务capture/common/export/verify/archive，不运行服务器EDA或触及他人物理工程。在正式源码冻结前发现并修复四项问题：

1. 图表可能来自旧run或覆盖归档sidecar：现在核对report-manifest文件集合/哈希、当前导出manifest和plotter源码。
2. 外层来源commit/摘要可能与ZIP内不同：现在交叉比对commit及sidecar原字节。
3. load_snapshot没有重验捕获stat/路径/身份：现在复用统一观察记录检查。
4. 宏边界touch可能误计无限延长线：现在同时检查另一轴与有限边界范围相交。

同时记录后处理代码的清洁源码commit和SHA。捕获/export核心链、PORT分组、PG原形状、ORIGIN未声明状态和资格边界经审阅未发现夸大。正式运行源码23040b0已经包含上述修复；34项本模块测试在该版本通过。

另一独立会话用标准库按行解析真实LEF全部54,598行，没有导入项目模块，394,774检查0差异。原始报告和脚本在audit/；本目录只是从D盘任务临时目录逐字节复制，不改变SHA。脚本的SNAP/REPO/RUN为本次实际绝对路径，运行会在脚本所在目录写audit.json/SHA256SUMS；若需重跑先复制到新的D盘临时目录，不在此处覆盖历史审计。离线数据从正式evidence.zip恢复后调整临时副本的路径，新增报告保留修改后脚本SHA。

审计不是团队GitHub批准，PR18仍待指定审查人；历史服务器stat与整工作区clean只来自当时捕获记录，本地审计无法重建。合法via/OBS访问、RTL/Lib逐bit匹配、PG连通、时序、等价与宏资格尚未执行或未闭合。
