# 本地完整搜索异常摘要（非原始stderr）

2026-11-09 CST，Issue219。以下依据工具返回文本记录，不冒称保存了原始进程stderr。
本地小例/134项检查通过；独立服务器当前生产源100813完整通过，异常根因仍未确定。

| 本地运行 | 观察 |
| --- | --- |
| Windows Python3.12.4，初次完整column_slice | exit1，无stderr；未确定原因 |
| Windows，完整column_slice retry | 排名出现 `list_iterator + int` TypeError |
| Windows，column_resume | 读取C0.E.write出现KeyError；事后不可变输入中该键存在 |
| WSL Ubuntu22.04/Python3.10.12，冻结源245 | static_rejections累加出现`itertools.product + int` TypeError |
| WSL，冻结源246，已将retention product物化为tuple | evaluate_transition返回值下标处出现`int is not subscriptable` |

没有找到这些值合法变型的源码路径。内存压力、解释器、宿主环境和共享历史释放仅为未证实假设。
不能将这些现象归因为芯片硬件，也没有据此新建硬件PR。没有放宽检查或用默认值吞掉错误。
当前增加整数时间断言、明确排名步骤及缺网诊断，**不宣称已修复根因**。
服务器采用冻结生产源码，输入/源SHA见results/column-dynamic-nine/receipt.json与input.sha256，130项及完整两预算通过。
本地大IR/计划/源245、246快照在本任务忽略目录inputs/results/raw中保留；新故障须保存真正stdout/stderr及进程环境再定位。
