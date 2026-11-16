# Issue250 联合底座：执行和协作交接

仓库 rayggxia-workspace/LLMHardwareDesign；[Issue250](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/250) / [PR251](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/251)。2026-11-10 Asia/Shanghai，实际身份YUZE-LU。

正式入口 [修订合同](../plans/w8a16-next-base-contract.md) 与 [工作索引](../../work/YUZE-LU/250/README.md)。原PR251 `a237a6fa366fda7c48d7b4fda56c555d469a7d29` S128草稿保留历史，不可直接执行；PR249 `85fe7989b` 与PR243 `63089fb9`证据按各自范围继承。

根分支 `task/250-contract-integration` 在原PR251准确commit上修改；三个准备分支与所有权见工作索引。未覆盖旧PR220未提交实验、PR249归档、peer分支或共享main。未来提交commit以PR在线回执为准，不在未提交文件中编造当前SHA。

恢复第一步：读AGENTS/skill/REMOTE_RULES和在线Issue250、PR251，检查各分支实际状态；先完成R0复现与R1/R2有限资源模型，达成至少9.21564723269 token/s同条件性能后冻结方案。不要跳过性能门直接宣称共享容量或300 MHz成立。

未完成：联合评估、新数值/记录与服务合同冻结、宏RTL与物理、控制/五类组联合验收、RTL校准/通用DP、完整整数质量/能耗/公平FPGA对照。后续执行仍由本任务推进，交接不代表暂停或完成。

已做：本地管理检查PASS；当前main/PR249/PR243/原PR251基点核验，原合同重写。未做业务仿真或新EDA验收，不把文本/协议审计当RTL证据。

接入：management-hub PR5 pending；本地无`config/board.json`，当前工具无Projects字段能力，实际条目/字段unverified、同步pending，待项目管理员（待指定）恢复配置/权限后核验Issue250加卡与状态。审查人待指定；不自行批准或合并。
