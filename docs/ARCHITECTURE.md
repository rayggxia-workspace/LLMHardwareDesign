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
| `project/experiments/endpoint_ablation/` | Issue13固定最大库存、端点约束overlay、配对消融与独立证据分类 |
| `project/experiments/macro_endpoints/` | Issue16真实普通LEF只读捕获、保留PORT/PG/OBS的原始几何、哈希索引和离线重放 |

Issue #11将本轮Python研究工具正式放入 `project/experiments/frozen_routing/`。未来硬件／映射与物理实现目录仍由相关Issue明确，不将全部业务代码放个人 `work/`。

## 本地阅读与验证

- 阅读：从仓库根目录直接打开 `ref-project/llm-routing/总报告.html` 或 `ref-project/llm-routing/线长报告.html`；其图片和下载链接使用包内相对路径。
- 管理结构检查：`python scripts/check_project.py`（Python 3.9+，无第三方包）。
- 本次用户授权的报告更新检查：`python work/YUZE-LU/3/sync_reports.py`（Python 3.9+，需要 `beautifulsoup4`）；只读核验两份报告的资源、锚点、清单及图片展示状态。该任务脚本不是例行维护入口；再次同步需用户明确要求，并传入 `--sync --source <源报告目录>`。
- 初次接入的来源记录见 `docs/DATA_PROVENANCE.md`；后续例行检查不覆盖 `ref-project/`。
- 本机业务检查：`.\.venv\Scripts\python.exe scripts/check_research.py`，运行frozen_routing、endpoint_ablation、macro_endpoints和interface_contract四套检查。
- 冻结源码后的本机实验：`.\.venv\Scripts\python.exe project/experiments/frozen_routing/run.py --out project/experiments/frozen_routing/local_runs/<新尝试名>`。默认拒绝dirty source和已存在输出目录。
- 证据核对及确定性重放：`.\.venv\Scripts\python.exe project/experiments/frozen_routing/verify.py <运行目录> --replay`；图表：`.\.venv\Scripts\python.exe project/experiments/frozen_routing/report.py <运行目录> --out <新图表目录>`。
- 现有D盘Python创建项目内venv，复用已安装包的环境事实写manifest；需要NumPy，绘图需要Matplotlib。核心连接算法只用标准库。
- Issue13配对消融：`python project/experiments/endpoint_ablation/run_ablation.py --out project/experiments/endpoint_ablation/local_runs/<新尝试名>`；读回：`python project/experiments/endpoint_ablation/verify_ablation.py <运行目录> --replay`。方法和归档命令见该目录README。
- Issue16真实LEF捕获及端点导出：先提交清洁源码，运行`macro_endpoints/capture.py`、`export.py`、`verify.py --replay`、`report.py`及`archive.py`；完整参数、D盘缓存和离线恢复命令见[工具说明](../project/experiments/macro_endpoints/README.md)。数据保存原始微米与精确DBU，PORT、PG、OBS均不省略；并不代表已验证合法接入点。
- 本用户任务的临时文件与可指定缓存，按进程将TEMP/TMP/TMPDIR/PYTHONPYCACHEPREFIX/MPLCONFIGDIR设至`D:/Projects/Codex/issue-13-endpoint-ablation/`对应子目录；正式成果保留项目目录，不改系统变量。其他平台按实际用户规则选择目录。
- 本实验没有RTL／周期仿真或物理PPA校准。本机尚无经验证可用的EDA工具链；Issue7的集群实验与限制以对应PR/记录为准，不能由当前结构或软件测试代替验收。

## 数据与外部依赖

新增实验应记录代码 commit、工具和配置版本、输入数据版本、输出位置及 SHA-256。大体积物理数据库、原始日志和工具环境应使用项目约定且有权限控制的共享存储，并在仓库中保留可核对的索引；具体共享位置和访问权限尚待确定。不得将凭据写入仓库。

## Issue19 三视图接口与既有合同

`project/experiments/interface_contract/` 以固定Yosys/Liberty/LEF名字、位宽、方向关联ACT/MXU逐bit边界，复用已有合同。运行 `python project/experiments/interface_contract/verify.py <解压的证据根目录>` 检查源码、哈希及重放；捕获、运行、归档参数见[工具说明](../project/experiments/interface_contract/README.md)。不替代RTL等价、时序、PG或合法接入验证。

## Issue21 模型驱动划分

正式目录project/experiments/operator_partition/。运行python scripts/check_research.py覆盖五套业务测试；新实验命令与D盘缓存规则见该目录README。归档核验：`python project/experiments/operator_partition/verify.py project/experiments/operator_partition/results/issue-21-run01/evidence.zip --sha256 f85b1f120065f91d13df95cdf343d35eb48640d9a56d2755b46da5c6ed82306d`。本工具是逻辑张量资源账本和合成数值核，不提供cycle/物理/质量测量。

## Issue23 固定真实权重轨迹

project/experiments/qwen3_trace/使用独立D盘环境（torch2.10.0+cpu、transformers4.57.6），正式命令与输入/误差合同见该目录README与experiment.json。先运行该目录test_numeric.py协议检查和work/Liangruizhi/23/check_observer.py集成，再从清洁commit调用run.py，输出到D盘独立新目录。原有check_research五套测试仍用其指定环境；新模型依赖不强加给全局Python。

## Issue27 状态与端口服务模型

`project/experiments/state_ports/`包含固定slot/scratch、原子服务资源、四种启发式与小规模精确oracle。先运行`python -B scripts/check_project.py`；再在Issue23的独立环境运行`python -B -m unittest discover -s project/experiments/state_ports -p 'test_*.py'`（25项）。进程TEMP/TMP指定D:/Projects/Codex/state-port-study-20261022/process-temp。

从干净commit执行`python -B project/experiments/state_ports/run.py --output <D盘新目录>`；真实head捕获用该目录capture.py的`--weights`与`--output`，具体锁定环境/模型及完整命令见[工具说明](../project/experiments/state_ports/README.md)。不将真实tensor数值验证或服务模型cycle描述为RTL/PPA。归档/图表脚本在work/Liangruizhi/27，正式资源/采集输出与独立审计位置见[实验报告](experiments/issue-27-state-port-model.md)。
