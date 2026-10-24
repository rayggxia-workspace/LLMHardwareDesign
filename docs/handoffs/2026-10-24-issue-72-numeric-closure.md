# Issue72交接：路由、连续整数R与同资源边界

2026-10-24 UTC+08；负责人Liangruizhi，审查人待指定。
仓库https://github.com/rayggxia-workspace/LLMHardwareDesign；[Issue72](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/72) / [PR73](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/73)。
分支task/72-numeric-closure，base task/70-moe-hybrid@f4d2c4643ef683336bf583739bf117cca8013118。文档前checkpoint55cfbdf；最终交付取PR73最新head。归档/配对执行源844825b1cfd1e00d6a297705977f3a1b3386951e；各run按15phase/43源SHA，不将文档HEAD冒充执行源。
工作目录D:/Projects/LLMHardwareDesign-numeric-closure；三子worktree分工见work/Liangruizhi/72/README。最终提交仅Issue72及关联公共状态，未覆盖成员55/63/ref-project/其他目录；交付后读回git status，后续新改动先识别归属。

## 实际完成

- Granite native32旧chunk FAIL复现，router64移至cached FAIL；新model64显式eager原门自洽/独立PASS，内部FP32 cast明示。
- 768整数路由/gate及192选择性profile独立通过；评价动态W8集合变720/6912，W16 6/6912；全部选择性行宽回退。
- Falcon全32head整数R分支12条件、6conv+R共同续接独立通过；full S16/S32 GU72步零发布sat、51head事件/25epoch，nextnorm约3.03%局部L2，Attention/MLP在外。
- 固定同一gatedinput的whole/K512/K256三条件独立通过；nextnorm L2约3.03/1.87/1.67%，部分maxabs变坏，partial wire1/8/16倍，宽对齐/metadata非免费。
- 20完整算术服务及10个label零差；Dpage/bank实际变化差小于0.02%，不足以定独立R/合宏。grouped函数不能套whole-row时隙。
- 103本人Slurm作业100完成、3FAIL保留；另一次依赖提交拒绝无job。结束核对本批无活跃任务，成员89448未中断。
- 本机89新测试、80旧模块、check_project、diffcheck通过。实际模型/张量/服务只服务器，无其他机器任务。

## 数据、SHA与实际验证

索引project/experiments/closure/results/issue-72/index.json。
服务器根/public/home/yuzelu/RuizhiLiang/issue72-numeric-closure-20261024。
完整delivery01/full-results.zip：9,898,974,561B/1096成员，SHA80e0b598039256f576bc6280d1f677713df5d5b36b8ff8ec1e22f35ee7c60197。
精选selected.zip：2,480,138B/286 metadata成员，SHA165d57d6050e0ef0e8775d7d081175d35e8bb85fffcc163db3f08d6bb547c883。
两包服务器逐成员接收，精选本机再验。原Issue70完整包SHA4c221db36ee3f756a284cda25dfabd6d9376ca4d7b95341c97d53a2be4d74f8b及原权重为明确外部输入，不可省略。
全部数学/端口/负例和原日志已封存；collector/验包后续收据另列索引，不能伪称在自身快照。复跑按closure/README和work72/slurm实际原command，用绑定旧源到全新out；精选metadata不足以重算数学。

## 未完成、处理人及恢复第一步

1. Liangruizhi后续研究：先校准真实wide/SFU/ROM/guard/RQ微实现及grouped-RQ同资源服务，再联合M合法prefill复用/分页。不盲扩模型或换机器。
2. Granite全整数gate→expert down/merge/应用质量预算未闭合；Falcon整模型/长窗和全码域读出保证未验收。当前路由差和局部L2不是质量PASS。
3. 工艺/库/RTL/布线/时序/PPA处理人待指定；成员55/63物理工程不接管。
4. 审查人待指定：PR73及依赖PR71等未合并，不自行批准/合并或Issue done。
5. 管理员待指定：management-hub登记PR5 pending；无config/board.json及Projects能力，实际看板unverified/同步pending。需核候选组织看板适用性、Issue72条目/ProjectID/Status/Priority并读回；当前不报告synced。

恢复第一步：核本人Liangruizhi/182389313认证、最新AGENTS/Skill、Issue72/PR73/基PR/评论、成员55/63和服务器活跃作业，验新成果SHA，再选真正改变边界的最小实验，避免重跑本批。保留原失败/浮点证据边界和本人账号，常规步骤在既有授权内推进。
