# Issue19：接口证据与输入缺陷交接

- 仓库rayggxia-workspace/LLMHardwareDesign（private），project_id=llm-hardware-design；[Issue19](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/19)／[PR20](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/20)，负责人Liangruizhi。按rayggxia-project-collab1.0.0交付，待指定审查人，未合并／未标done。
- 主目录D:/Projects/LLMHardwareDesign-interface，分支task/19-interface-contract；PR base task/16-macro-endpoints，依赖PR18/14/12。capture清洁commit16be20bfe644e51158279ad69a8983270e81cc00；正式run清洁commitc3916f4f457fcf72fc96f2b2f53ad706e50012e2。成果交付commit以PR20最新head为准。
- 通过已核验Liangruizhi／2663955430@qq.com／ID182389313的GitHub插件上传Git对象，远端tree与本地暂存tree比较后导入真实commit；CLI Git认证未配置，没有声称执行CLI push。
- 并行解析器目录D:/Projects/LLMHardwareDesign-interface-review／task/19-liberty-review；连接图目录D:/Projects/LLMHardwareDesign-interface-graph／task/19-graph-review；各只留下本任务两个未跟踪实现/测试文件，已复制纳入主任务。其他成员worktree、作业及进度未改。

## 成果及实际检查

[实验记录](../experiments/issue-19-interface-contract.md)；正式目录project/experiments/interface_contract/results/issue-19-run03。ZIP1585317bytes，SHA256 2d2047b761323ba22e3c209d83a25a89fc77e901beae166103908df72de986d7。原始十文件、两LEF、逐bit表、边界图和manifest均可离线恢复；辅助审计与失败记录在work/Liangruizhi/19/。

管理结构PASS，148项业务检查PASS，独立205390项比较PASS，六个自洽manifest篡改负例均拒绝；离线恢复23成员和逐字节重放PASS。3032 signal、685连接、2346网；两处缺分号、四处PG方向差异显式保留，不能把接口一致性称宏资格/完整Lib合法/PG或时序通过。

本轮只读获授权服务器10文件7559708bytes；无服务器写入、Slurm或EDA作业。原始捕获在D:/Projects/Codex/interface-contract-20261022/frozen-inputs-01；运行目录project/experiments/interface_contract/local_runs/issue-19-run03被忽略。临时和可指定缓存都在D盘任务目录，未改系统环境。最终上传仅本任务目录、本人work/progress、直接相关文档及业务检查入口；不含ref-project或他人资料。

## 待办与责任边界

1. PR20及依赖审查/合并：审查人待指定。登记pending，management-hub PR5于本轮读回OPEN／未合并，不重复登记。
2. 看板unverified／同步pending：本项目无config/board.json，当前连接没有Projects工具；Liangruizhi在线权限未知，不能引用其他会话缺scope来推断。管理员待指定，核对候选组织Projects1受众及Issue19条目，按config/status-mapping同步Project ID=llm-hardware-design、Status=In review，读回条目ID/字段/时间；优先级未指定不得编造。
3. 两份旧Liberty缺分号及四处PG方向差异：本轮仅记录和显式兼容提取，未改服务器原文件；后续模型维护负责人待指定。Issue15/PR17由YUZE-LU推进新M9 matched宏/父层，须检查新数据是否同样存在，不能套用旧结论或接管其工作。
4. 新视图、DEF朝向、技术via/enclosure/OBS、完整arc/内部时钟、PG连通、RTL等价与宏资格仍待核实；原实验配置外部driver/load未指定。已有图不证明物理H2/PPA；后续任务按最新Issue认领。
5. 自动审批拒绝删除本轮D:/Projects/Codex/interface-contract-20261022/independent-audit/mutation-copy-01，理由“blocked by policy”。删除前已核对路径；未删除、未重试或绕过。该副本已恢复与原始运行一致，保留供审查，清理待指定维护者处理。旧Issue13/16被拒绝目录及旧空远端分支task/15-macro-endpoints沿既有交接保留，未操作。

## 恢复第一步

先核验指定GitHub身份，读最新AGENTS/Skill、Issue19/PR20评论和审查、个人进度及Issue15/PR17最新记录，确认origin/branch/head/worktree和git status。按工具README核对ZIP SHA并离线重放；核对上述输入缺陷，明确新matched视图版本后再选择下一独立Issue，不重复创建PR或覆盖既有尝试。待审查的交付保持in_review；只有要求的审查/合并和验收均有证据才done。
