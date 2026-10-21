# YUZE-LU 的进度

## 当前任务：Issue #7

- 更新时间：2026-10-21（中国标准时间，UTC+08:00）。
- Issue：[候选 Block 边界及分层布线流程](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7)，负责人 YUZE-LU，当前 `in_progress`；审查人和优先级待指定。
- 已完成：读取两个项目的接口／RTL／报告和已有 ACT—MXU 实验；形成 [候选划分及对照矩阵](../../docs/experiments/openTPU-llaccel-block-plan.md)；核实用户授权的集群工程与工具可访问；在独立分支 `task/7-block-routing` 增加正式实验运行器，原参考包和原工作区改动保留。
- 实验：完整 16-lane VECTOR 的 screening 89442 通过；89443 在 45 分钟人工上限超时，89447 的恢复 dry-run 失败，均保留。89448 已验证从 checkpoint 接续 CTS、不重综合；89449 等待其成功后做顶层。两者实际 `TimeLimit=UNLIMITED`。终态以[试验记录](../../docs/experiments/issue-7-vector-pilot.md)和[轻量索引](../../project/experiments/block_hierarchy/results/issue-7.json)为准。
- 运行约束：用户明确要求不设时限；后续作业取消人工有限时长，实读 c64/c96 `MaxTime=UNLIMITED`，每次提交后核验实际 `TimeLimit`。早期超时与恢复预检查失败保留，不通过删除历史制造成功。
- 新增验证：独立 RTL 回归 89455 已通过，VECTOR 1,203 例／数学 12,000 组／舍入 16,384 组；测试副本唯一 `1u << 31` 兼容修正有 diff/hash，原 RTL 与参考不改。89453／89454 是另开的 `LEC_CHECK=0` 物理路线，89448／89449 默认检查路线保持运行；不混用二者证明。
- 实际物理结果：89453 `COMPLETED 0:0`、33:03、`UNLIMITED`，DRT 错误 0；最终 setup WS −4.16659 ns／287 违例、最大电容 59 违例，时序／电气未验收通过。最终 SPEF 抽象和活跃 pin 时序弧已独立审读。89454 因 PG 接入被全层 OBS 阻断而失败；89456 完成 DRT（错误 0），但最终 PSM 发现 M8／M9 短接并失败，顶层未验收。
- 验证：`python scripts/check_project.py`、Python 脚本语法编译、远程 Bash 语法检查和 `git diff --check` 通过；镜像阶段门级 LEC 已调用、尚未得结论。完整 core 回归、原 RTL 到物理网表的完整形式比较、多计算图、受限定制和系统签核未执行。
- 下一步：在新 attempt 修复顶层 PG via 接入，显式审计供电连通，再验最终宏位置／信号接口；保留内部时序、电容及缺少宏功耗模型的限制，再准备 F0/H1 对照和 H2 冻结资源规则。
- PR：[草稿 PR #8](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/8)；脚本快照 `7e9bde5b763b19591dcbe4f49ade7b08ef093843`，运行时实际文件由每个 attempt 的 SHA-256 标识；未合并或验收前不标 `done`。
- 接入：管理中心 [登记 PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5) 本轮读回仍 `OPEN`，登记 `pending`；Projects 缺 `read:project`，无 `config/board.json`，看板 `unverified`、同步 `pending`，由具备权限的管理员处理（待指定），见[持久交接](../../docs/handoffs/2026-10-21-issue-7-projects.md)。

## 历史记录：2026-10-19

- 更新时间：2026-10-19（中国标准时间，UTC+08:00）
- 当前任务：[Issue #1：初始化项目并导入初期资料](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/1)
- 已完成：初期研究资料已进入 `main`；PR #2 已合并。本次按用户要求直接在 `main` 提交并推送更新后的研究资料导读与用户提供的 `ref-project/` 改动；成果提交为 `695587d`、`5c86109`。
- 下一步：完成[管理中心登记 PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5) 的审查；由具备 Projects 权限的管理员核验或配置项目看板。`ref-project/` 不纳入 Agent 的主动或例行维护，用户更新后可按要求提交；无需逐项审查或做哈希检查。
- 阻塞：物理实现原始代码、数据库与工具环境未包含在当前资料包；共享存储位置和实际可访问性待核实。
- 本次验证：`python scripts/check_project.py` 通过；导读的 6 个本地相对链接存在；变更文档的 `git diff --check` 通过。未检查参考包内部改动或哈希，未执行业务构建／仿真。本地未配置 `config/board.json`，看板仍待管理员处理。
