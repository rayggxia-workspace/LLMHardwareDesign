# Issue13 端点消融交接

- 2026-10-22，UTC+08:00；负责人Liangruizhi／2663955430@qq.com，GitHub ID182389313。
- 仓库rayggxia-workspace/LLMHardwareDesign，project_id=llm-hardware-design；[Issue13](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/13)／[PR14](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/14)，task/13-endpoint-ablation；待审查，未合并／未标done。
- 主工作目录D:/Projects/LLMHardwareDesign-endpoints；原D:/Projects/liangruizhi和D:/Projects/LLMHardwareDesign-dac保留原分支，未切换或修改。正式运行源码dc294114a6758b6baa1e4f6085630971a8f11fcc，后处理提交以PR当前head读回，不改写运行输入。
- PR基分支task/11-frozen-routing-pilot，起点47d134411775e25a0c43f9818bfbd95e69e69734，依赖PR12未合并。不要重开向main重复整套先前代码的PR；先核对PR12的合并方式／最终base，必要时有审查地调整PR14基线并处理实际差异，不force覆盖。
- 正式代码project/experiments/endpoint_ablation/；成果results/issue-13-run01/；原始/开发/绘图副本local_runs/忽略保留；docs/experiments/issue-13-endpoint-ablation.md记录实际结果与命令。
- 384例／96配对；restricted44/96、access71/96、capacity44/96、joint71/96。230成功配置全部合法与数值通过；248份cut读回；24精确状态9可行15不可行。access有9个原no-path→合法的固定映射，不外推真实PPA；容量放宽未新增本轮成功不能说容量永远无关。
- 管理结构、33项业务检查、全量来源/成果hash读回、Git源码字节与确定性连接重放、ZIP原字节及图表检查通过。source_dirty=false。物理构建／STA／LEC／真实LLM／H2/PPA未执行。
- 原manifest SHA256 6ad74db7b00fbfe2d5421f9f9bca526b0a164994fe11b20b77a4f98230174a91；ZIP da9f18282acbeaaa1e09de53fc5e9bcc0b989ff871f148a39b2de22695d8bb2a。后续新增结果另建attempt并记录真实新commit。

## 恢复第一步

1. 先用本人Liangruizhi认证核对最新README/AGENTS/Skill、Issue13/PR14和依赖PR12、Issue7/PR8/PR10评论及交接，确认其他成员范围。核对git status、worktree和远端head，不覆盖新改动。
2. 执行package.py --verify核对归档；临时解压到D:/Projects/Codex/issue-13-endpoint-ablation下全新子目录后verify_ablation.py --replay。不要改写旧dirty开发尝试或运行源码。
3. 审查overlay反事实边界与cut归因。后续任务按docs/MACRO_ENDPOINT_CONTRACT.md冻结真实普通LEF、版本/SHA与端口几何/层，再补工艺、driver/load和宏资格。数据实际可访问但未作为本轮输入，不写成已校准。处理人／审查人待指定。
4. 该本地仓库是API建立的浅层稀疏副本加worktree，未取ref-project/sources大内容与早期历史；CLI本人认证未接通，上传使用核验后的本人GitHub插件。不要借用其他凭据或说普通CLI push已执行。
5. 登记沿用management-hub PR5，当前OPEN/pending，默认registry未含本项目。待有权限审查者处理，不重复开登记PR。
6. Projects事实unverified、同步pending：没有工具/board.json，未核验本人权限或Issue13条目。管理员待指定，需核对组织看板1及受众、查/复用或加入Issue13，按status-mapping读回Project ID=llm-hardware-design和Status=In review、条目链接/ID/核验时间；未确定Priority或日期不猜填。
7. 临时/缓存仅D:/Projects/Codex/issue-13-endpoint-ablation内本任务子目录，进程级TEMP/TMP/TMPDIR/PYTHONPYCACHEPREFIX/MPLCONFIGDIR，不改系统变量。保留项目成果与仍有用途的开发记录，清理仅本任务无用缓存；不删除其他任务数据。

## 临时清理待办

归档字节及审查脚本/回执副本均已核对一致。自动审批两次拒绝本任务缓存目录的递归删除（一次批量脚本、一次核验后的明确LiteralPath），仅返回blocked by policy，未给更具体理由；未绕过该限制，目录保留。待具备可用操作方式的本机用户／处理人（待指定）清理D:/Projects/Codex/issue-13-endpoint-ablation，以及项目local_runs下development-figures-01、issue-13-figures01这两个已逐字节归档的图表中间副本。正式results、原始issue-13-run01和dirty开发记录保留。

独立微例审查worktree D:/Projects/LLMHardwareDesign-endpoint-review仍保留供PR待审查阶段复查；不是并发修改主任务目录的入口。后续不再需要时先核对未提交文件与正式副本，再用Git感知方式处理该worktree，不盲删其他工作树。
