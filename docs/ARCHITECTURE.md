# 架构与运行

本仓库保存研究资料、参考结果和本项目的初步实验工具。本分支的冻结连接模型位于 `project/experiments/frozen_routing/`；其他成员的物理Block工程见Issue #7关联PR #8/#10，未合并文件须从对应任务分支读取。最终工艺、硬件库与系统实现工具链仍未冻结。[项目说明 v1.0](../预制计算底座项目说明_v1.0.md)中的候选架构不等于已实现硬件。

## 研究系统边界

拟研究的流程是：目标计算图与需求 → 预制 Block 资源映射及调度 → 预埋资源选择和受限布线 → 定制互联与成本／性能／能耗评估。预制内容、制造时定制内容和运行时状态必须分别建模；工艺堆栈、端点电气合法性、存储供给与时钟网络不能省略。

## 目录约定

| 路径 | 用途 |
| --- | --- |
| `README.md`、`研究资料导读.md`、`预制计算底座项目说明_v1.0.md` | 项目入口、阅读导引与初版研究定义 |
| `docs/` | 当前项目简介、架构、状态，以及专题研究文档和重要决策 |
| `sources/` | 手写笔记、讨论澄清和原始研究资料 |
| `ref-project/llm-routing/` | 参考布线结果；Agent 不主动或例行维护，用户更新可按要求提交 |
| `progress/<github-handle>/`、`work/<github-handle>/<issue-number>/` | 个人进度和任务辅助资料，不作为正式研究成果的默认目录 |
| `.github/`、`config/`、`scripts/` | 协作模板、状态配置和管理结构检查 |
| `project/experiments/frozen_routing/` | 本项目抽象冻结连接模型、路由基线、独立验证、配置和轻量结果 |

Issue #11将本轮Python研究工具正式放入 `project/experiments/frozen_routing/`。未来硬件／映射与物理实现目录仍由相关Issue明确，不将全部业务代码放个人 `work/`。

## 本地阅读与验证

- 阅读：从仓库根目录直接打开 `ref-project/llm-routing/总报告.html` 或 `ref-project/llm-routing/线长报告.html`；其图片和下载链接使用包内相对路径。
- 管理结构检查：`python scripts/check_project.py`（Python 3.9+，无第三方包）。
- 本次用户授权的报告更新检查：`python work/YUZE-LU/3/sync_reports.py`（Python 3.9+，需要 `beautifulsoup4`）；只读核验两份报告的资源、锚点、清单及图片展示状态。该任务脚本不是例行维护入口；再次同步需用户明确要求，并传入 `--sync --source <源报告目录>`。
- 初次接入的来源记录见 `docs/DATA_PROVENANCE.md`；后续例行检查不覆盖 `ref-project/`。
- 本机业务检查：`.\.venv\Scripts\python.exe -m unittest discover -s project/experiments/frozen_routing -p "test_*.py" -v`。
- 冻结源码后的本机实验：`.\.venv\Scripts\python.exe project/experiments/frozen_routing/run.py --out project/experiments/frozen_routing/local_runs/<新尝试名>`。默认拒绝dirty source和已存在输出目录。
- 证据核对及确定性重放：`.\.venv\Scripts\python.exe project/experiments/frozen_routing/verify.py <运行目录> --replay`；图表：`.\.venv\Scripts\python.exe project/experiments/frozen_routing/report.py <运行目录> --out <新图表目录>`。
- 现有D盘Python创建项目内venv，复用已安装包的环境事实写manifest；需要NumPy，绘图需要Matplotlib。核心连接算法只用标准库。
- 本实验没有RTL／周期仿真或物理PPA校准。本机尚无经验证可用的EDA工具链；Issue7的集群实验与限制以对应PR/记录为准，不能由当前结构或软件测试代替验收。

## 数据与外部依赖

新增实验应记录代码 commit、工具和配置版本、输入数据版本、输出位置及 SHA-256。大体积物理数据库、原始日志和工具环境应使用项目约定且有权限控制的共享存储，并在仓库中保留可核对的索引；具体共享位置和访问权限尚待确定。不得将凭据写入仓库。
