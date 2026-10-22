# Issue16：普通LEF几何库存交接

- 仓库：`rayggxia-workspace/LLMHardwareDesign`（private）；[Issue16](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/16)，主要负责人Liangruizhi；[PR18](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/18)，待指定审查人，未合并，Issue交付后in_review而非done。
- 分支：`task/16-macro-endpoints`，工作目录`D:/Projects/LLMHardwareDesign-lef`；基分支`task/13-endpoint-ablation`，依赖PR14/12。捕获/解析/导出/后处理清洁源码commit `23040b0459cd32297b6562e22f48af5ae812ed25`；成果/文档交付commit见PR18最新head。通过Liangruizhi已核验GitHub插件提交Git对象并核对本地tree；CLI Git认证没有配置，没有声称执行CLI push。
- 并行工作：解析器会话独立`D:/Projects/LLMHardwareDesign-lef-review`／`task/16-lef-parser-review`，仅两份辅助源文件未提交，已原字节纳入主任务；其他审阅不修改项目。保留现有Issue11/13及其他成员worktree和文件，不覆盖。

## 已有成果与实际检查

- [正式记录](../experiments/issue-16-macro-endpoints.md)、[工具与运行步骤](../../project/experiments/macro_endpoints/README.md)。仅三份普通LEF只读捕获，无服务器写入、Slurm或EDA操作；原始路径及上游record/runner commit在inputs.json。
- 原始LEF、配置、capture manifest及四业务输出/运行manifest无损保存`project/experiments/macro_endpoints/results/issue-16-run01/evidence.zip`；502980bytes，SHA256 `42555df9e5ba32b405b2bc124722d4aea5fec94ef8a874adc37aeaf4020f5bcf`。图表/摘要/逐文件及ZIP成员索引在同目录。
- 6791PIN／6785SIGNAL／6956PIN RECT／30OBS RECT，完整保留PORT、PG及原始坐标/DBU/行号。三宏qualification均false。
- check_project PASS；三业务套件67项PASS；四业务输出逐字节重导出一致；归档10成员与外层交叉校验PASS。PNG人工视觉检查通过。独立全量解析54,598行，394,774字段/条件检查0差异；脚本/报告在`work/Liangruizhi/16/audit/`，限制与SHA见正式记录。
- 本机原始捕获位于`D:/Projects/Codex/lef-endpoint-export-20261022/frozen-inputs-01`；忽略的正式运行目录`project/experiments/macro_endpoints/local_runs/issue-16-run01`。这些仍供审查使用；D盘figures-01/independent-audit为已归档中间副本，最终交付后可清理。可指定缓存均在同任务D盘目录，没有C盘临时工作目录或系统环境变量修改。
- 已实际将归档解压至D盘新目录offline-replay-01并离线逐字节重放通过。之后对offline-replay-01、figures-01、pycache、matplotlib四目录的原生PowerShell清理被自动审批拒绝，原因为`blocked by policy`；目标绝对路径事前已核对位于本任务D盘目录，未执行删除、未绕过。四目录暂保留，维护者待指定，不影响成果正确性；不要把本地清理写成已完成。
- 上传范围限本任务新增工具/结果、本人work/progress和直接相关docs/README/check_research；不包括ref-project、大数据库、凭据或他人资料。最终工作区和远端head核验见PR回执，不能把未上传文件说成已上传。

## 未完成与处理人

1. PR12/14/18审查及依赖合并：审查人待指定；禁止自合并或提前标done。Issue15/PR17由YUZE-LU继续同资源ACT/MXU物理对照，本任务不接管其作业、时序修复或个人记录。
2. 底层RTL commit、完整OpenROAD/ORFS版本、镜像SHA及上游逐文件预期SHA待核实；本次哈希是捕获实测，没有上游逐文件预期对照。后续实施负责人待指定。
3. 下一独立Issue先核对ACT—MXU实际端口逐bit与RTL/Lib对应、DEF安装方向和工艺via/spacing/enclosure/OBS访问，再定义合法access候选。尚无这些证据不能称合法访问；minimum_period/arc/边界driver-load、PG、等价和合格宏仍待闭合。下一实施负责人待指定，不以这批几何推断H2/PPA收益。
4. 登记pending：管理中心默认registry只有team-workspace；[管理中心PR5](https://github.com/rayggxia-workspace/management-hub/pull/5)于本轮仍OPEN、未合并。管理员待指定，复用原登记PR，不另建重复登记。
5. 看板unverified／同步pending：本仓库无config/board.json，当前连接无Projects工具，账号在线权限未知；[组织项目1](https://github.com/orgs/rayggxia-workspace/projects/1)仅候选入口。具备工具与权限的管理员待指定，需核对受众、Issue16是否已有条目并加入/同步`Project ID=llm-hardware-design`、`Status=In review`；Priority未指定不得编造，完成后读回条目ID/字段/时间。不要根据其他会话缺scope记录断言Liangruizhi无权限。
6. 本会话误建后停用的空远端`task/15-macro-endpoints`待清理：当时head为a2769bf9fc6409816c16d5cbea1e5c8c45bc2d58，没有本任务提交/PR；插件没有删除分支能力、CLI未认证。维护者待指定，重新核对无新提交/PR后才删除；此分支不是Issue15工程分支。实际任务一直使用16。
7. Issue13被自动审批拒绝的旧缓存清理仍沿原交接保留，不绕过或再次操作旧目标；与本轮实验结果无关。

## 恢复第一步

认证查询确认Liangruizhi／2663955430@qq.com／ID182389313；读最新AGENTS/Skill、Issue16、PR18评论/审查、本人进度与Issue15/PR17最新交接。核对origin、当前branch/head、git status和worktree，确认没有重复任务。先验证归档SHA并离线重放，再根据缺项创建或认领下一独立Issue；如需新服务器数据，重读REMOTE_RULES，保存新输入版本，不覆盖本轮。
