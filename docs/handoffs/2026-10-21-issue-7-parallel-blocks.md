# Issue #7 并发实验恢复与主线协调

## 最新恢复入口：第二轮（2026-10-21 19:25，UTC+08:00）

仓库、Issue／PR及工作树沿用下文；当前物理接续根为 **`parallel-blocks-wave2-06`**，实际runner **`05074e2`**。**89497／node7／48CPU** 的ACT裕量0/10/20均已COMPLETED0:0、批次6:00；**89498／node8／64CPU** 的GEMM10/20、MXU20、合并20继续运行，均每step16核、UNLIMITED。**89499** 一次性afterany审计已提交。仅ACT20通过后补的严格工具门槛，尚不是完整宏资格或签核。

**优先采用新根11的严格审计**：89510／node9／1CPU／afterany89499，后接89511；实际runner `f46deb0`。新根10的89508已对三路ACT各825源＋154输出条目校验全过，并发现10虽cap计数0、最差余量仍负，故0／10严格门槛false、20true。20面积比0增加0.321716%，选作后续视图检查候选。不要用06旧审计的计数条件覆盖该结果。根08首次容器缺sacct失败、根09未启动的89506／89507行政取消均保留回执，由10／11接替。

恢复第一步，在本专有工作树核对分支／最新规则后：

```powershell
python project/experiments/parallel_blocks/wave2/monitor.py --attempt parallel-blocks-wave2-06
python project/experiments/parallel_blocks/wave2/monitor.py --attempt parallel-blocks-wave2-11
```

然后读[第二轮实验记录](../experiments/issue-7-parallel-blocks-wave2.md)、[06提交回执](../../project/experiments/parallel_blocks/results/parallel-blocks-wave2-06-submission.json)及latest中的最近flow日志／修改时刻，不只看RUNNING。监视器取得计算节点SHA后才取回不可改写的completion。大文件留远程，不在登录节点重算哈希或运行EDA。

已完成：原openTPU RAM12组周期对照、包装逐bit连接／存储资源核对；原GEMM两种fusion各500例实际通过，首次采集器失败另存，89484在新根02核对原日志SHA／summary通过且未重跑模拟；C的89482导出旧结果基线视图，89487完成两个宏40端口／1662bit的接线与1670µm共同外边界准备。C初次8CPU，其余辅助任务1CPU，均已释放。**正式顶层PNR未执行**；旧宏仍电容失败，minimum_period缺失，arc／外部驱动负载／PG／功能及物理等价缺口显式保留。

故障及保存：首试01的7个ABC输出早已完成，却卡在持久ABC回执；长TMPDIR最小复现，默认临时目录的校正探针89493及真实ACT接续确认可继续。仅按[回执](../../project/experiments/parallel_blocks/results/parallel-blocks-wave2-stall-retirement.json)终止8个明确停滞step，非人工时限；不碰主线。原89480／89481／89491失败，89483／89492审计分别保留7／1项缺manifest失败。新根07的89501／89502封存原失败completion字节及SHA，监视器已验证取回；不要重写这些历史或将封存成功当成原实验通过。

本次代码已推送，文档与快照head以本PR／`git rev-parse HEAD`为准，后续commit不倒填到既有作业。恢复后检查89499及89510／89511终态、逐case计数与最差余量／时序及SHA，再决定合格宏和正式顶层；功能／物理验收不能由结构CI代替。草稿PR10／固定Issue回执继续更新；整体Issue本轮实际标签为status:in_review，由主线维护，不改回，本并发实验仍运行，审查人／优先级待指定。登记PR5仍OPEN、pending；无board.json／缺read:project，看板unverified、同步pending，管理员待指定。需要定时助手通知须从主线或普通聊天建立，本侧聊没有后台唤醒。

## 以下为首轮历史回执与18:05恢复说明

- 仓库：`rayggxia-workspace/LLMHardwareDesign`；project_id `llm-hardware-design`；操作者 YUZE-LU。
- Issue：[任务 #7](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7)。本批[草稿 PR #10](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/10)是主线 PR #8 的独立补充，不重复接管 VECTOR／供电修复。
- 分支／本地路径：`task/7-parallel-blocks`；`D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-7-parallel-blocks`。
- 执行 runner commit：`2568623f91f871e139c4b7544d00d0181ce4cb01`；监视／审计代码快照 `017a0a7e16c40e47a837e75101789c57b34625e6`。后续文档／监视器提交见本 PR head，不将其冒称为最初已执行代码；计算节点 SHA 索引绑定实际输入。
- 远程根：`yuzelu@10.129.166.172:/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7/parallel-blocks-01/`。仅此新目录写输出，源 repo／参考包只读。

## 已提交工作与边界

89458 `lyz-par4`：c64 node7，一个64 CPU allocation，四个独立 step 各16 CPU，实读 `UNLIMITED`。89458.0=MXU、.1=ACT、.2=GEMM、.3=ACT＋MXU。各case独立源归档／配置／日志／工作目录／退出码；一路失败不会取消其它路。**四路均已 COMPLETED0:0，批次41:33**，DRC／天线均0、setup／hold WS均正，但 GEMM／ACT／MXU／合并的 max-cap 为49／2／12／41，均未通过完整电气验收。

89460 `lyz-par-audit`：c64、1 CPU、afterany89458、`UNLIMITED`，**已COMPLETED0:0／21秒**。冻结 `observer-v1/` 已在计算节点核对438个输出条目全部通过并写 `completion.json`、`completion.sha256`、逐case校验日志和工具预算门槛。四路唯一失败的已列工具门槛均为 `max_cap_zero`，不是完整功能／系统验收。冻结终态已下载，字节SHA `4e6d7c24518f8ef55d45b57eb5325d0e7329dfc773273f8c339c4496fd885903`验证一致。它是一次性流水线后处理，没有后台助手循环通知。临时侧聊的 heartbeat 创建被工具明确拒绝为“不支持临时侧聊”，没有成功创建自动化。

89478 `lyz-cap-read`：node7、1CPU、UNLIMITED，已完成；只读当前同一镜像中的 ORFS 源码，确认 CAP_MARGIN 传入 repair_design -cap_margin。源包及SHA远程保留在 `parallel-blocks-cap-diagnostic-01/`，本地只有核对过SHA的摘录回执，不冒充原始源码包。本轮没有新PNR。

两项目源 commit／工具镜像、完整参数及模型限制在[实验记录](../experiments/issue-7-parallel-blocks.md)。openTPU 是原 small 的 synthetic fakeram 研究模型，不是真实 SRAM／GDS；物理阶段 LEC 显式关闭，不能套用主线证明。合并包装不加周期和缓存，原宽接口保持；分开宏尚未组成实际顶层。原始与本批 IO 时钟/hold预算不同，不做历史PPA的直接收益比较。

## 恢复第一步

确认分支和工作区，读取最新 AGENTS／远程规则后运行：

```powershell
python project/experiments/parallel_blocks/monitor.py --attempt parallel-blocks-01
```

该命令只读远程轻量报告，刷新本分支 `project/experiments/parallel_blocks/results/parallel-blocks-01-latest.json`；校验远程 SHA 后下载／核对不可改写的终态 JSON。现已打印每路校验和失败门槛，最新索引保存阶段电容数量、最终违例行、资源账单，`--verbose`显示明细。按实际sacct逐step状态、退出码、数据库＋收尾metrics、DRC、setup/hold、电气及PSM判读，不能只看批作业状态；新attempt不得覆盖旧输入。

继续物理工作的具体入口：先阅读实验文档的诊断表。建议只用ACT固定16线程先对照CAP_MARGIN10／20与0基线；新配置尚未执行，不要记录成修复完成。此后补齐包装回归／等价及边界驱动负载，再将分开ACT／MXU硬块重连到真实顶层，避免与主线PG实现重叠。另可测试小块4／8核与大块8／16核及空槽补位，账单22.1%不能直接证明减少线程不增加墙钟。线程与电容两因素分开对照，后续仍不设时限。

需要继续后台助手监视时，应从主线／普通聊天创建监视，而不是声称本临时侧聊可定时唤醒。一次性 Slurm 审计已提交，不因聊天关闭而取消。

## 同步和检查

本批只维护 `parallel_blocks/`、本实验文档、此交接和个人补充，不修改主线 `block_hierarchy/`、`docs/STATUS.md` 或 `progress/YUZE-LU/STATUS.md`。本地原工作区仍由主线管理，不切换它的分支、不合并或覆盖未提交内容。本分支仅新增专有路径，原工作区核对为干净；主线工作树的修改保留。

更新同一条[Issue #7并发回执](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7#issuecomment-6312241685)和本PR描述，避免刷重复评论或覆盖主线正文。代码／记录供主线审查后决定合入顺序，不自合并。尚在运行时保留草稿，整体 Issue 状态由主线据实际验收协调。

已过：`python scripts/check_project.py`、Python compileall、远程 Bash -n、Git diff whitespace；前一交付7908208的[Project structure CI](https://github.com/rayggxia-workspace/LLMHardwareDesign/actions/runs/39576683446) success。本轮实际运行增强监视器、核对终态／诊断源码包SHA及四路最终电气行数，均通过。当前提交CI以PR最新回执为准；未完成的独立功能／等价／物理／系统验收不能由管理CI代替。

登记沿用management-hub PR5（本轮读回仍OPEN／未合并，pending）；本项目无board.json、当前缺read:project，看板unverified／同步pending，由有权限管理员处理，具体人待指定。审查人与优先级待指定，无新增期限。
