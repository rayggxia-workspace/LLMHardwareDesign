# Issue #226：综合到布线接口

基于 PR #220 `f23a6d93448849b6f7b15edccce7e996d1092e7d`，隔离工作树实现。
规则 rayggxia-project-collab 1.0.0；项目 llm-hardware-design；认证账号 YUZE-LU。

- 正式实现：`project/experiments/block_synthesis/route_contract.py`、`route_feedback.py`。
- 自动接入：`full_plan.py`；合同/CLI：同目录 `ROUTE_CONTRACT.md`。
- `two-u-route-requirements.json` 来自已提交的 #220 真实双U连接需求。
  306位=284传输+22预约；311项unresolved=306个未绑定member+5个缺接口模板需求
  （四个E读写束和MC/LC控制依赖）。没有物理pin、via、几何、RC/STA通过声明。
- 单元测试包含合成pin目录，仅用于验证schema、别名冲突和输入哈希，不能继承物理资格。
- 40项相关测试通过：19个新增合同用例、11个DP回归、10个缓存回归。
- 完整3B重编译/全量原生RTL/EDA未执行；此任务没有改变原语、搜索或缓存实现。
- 需求重构检查共享展开代码，并另查端点覆盖；不冒称独立物理检查器。

复跑：见正式合同。源文件、输入及生成需求SHA见 `receipt.json`。
工程实现待独立审查，不自批准或合并。登记沿用management-hub PR5 pending；
本仓库缺config/board.json，Projects unverified/同步pending，沿用接入交接Issue7。
