# Issue230：通用布线的九组产品输入交接

仓库 https://github.com/rayggxia-workspace/LLMHardwareDesign；
任务 https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/230；
分支 `task/230-backend-router`，前置提交 `f0273848e1872d9b2d9488981eaf279a902218a5`
（PR229，叠加PR227/220）。负责人/操作账号YUZE-LU，独立审查人待指定。
本次源码与证据提交见分支历史及[草稿PR231](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/231)，尚未获整产品验收。

## 可以继续使用的成果

`project/experiments/upper_router/BACKEND.md` 是真实ODB索引、通用路线输出、
DEF/ODB/GDS读回和几何核验入口。`work/YUZE-LU/230/README.md` 保存输入版本、
作业、失败修改、RC证据边界。29项算法/后端测试与两项实际物理负对照通过；
五类晚接接口362网实际读回、上层研究几何及全部原生层XOR通过。
这不是#220完整静态网，也不是九组共同底座的物理资格。

原版完整DRC为作业100406（五项，每项10核），收集作业100458及最终100471依赖其结束。
精确结果以远程原始报告及任务证据索引为准；无报告不得推断通过。
所有新增运行均在本人目录
`/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-230-backend-router/`，
attempt01–12不可覆盖。最终29项测试在attempt11；早期收集器100458采用attempt09的26项，
最终100471采用attempt11并增加实际上层ODB/GDS。应同时保留两个版本，不改写旧报告。

## 待明确由谁提供的产品输入

1. 九组共同放置的原生ODB/网表/GDS，而不是九个组合硬框。独立叶宏、局控和必要
   适配器各自计入。固定预连逐条登记；PG/CTS及局控PM应有明确实现与验收范围。
2. #220原生服务到真实信号的完整catalog。实际五类夹具仅部分端口在M10，不能
   把其余M5/M6端口凭空视作可从M11接入，也不能由逻辑束名猜出数据及握手线。
3. 当前母控两驻留目标到九组的实际分发方案，及替代虚拟外存服务的memory gateway。
   这些是硬件集成输入，布线本身无法产生缺失的存储/控制功能。

本对话已向用户说明缺项并询问：纳入本任务补齐硬件，还是由另一任务提供底座。
截至本交接写入时尚无答复；处理人待指定。不可将这一范围问题当作用户已批准新硬件。

## 恢复工作的第一步

先读AGENTS和协作Skill，核对上述PR最新头与当前Issue。取得明确的产品输入归属后，
冻结一份共同base/catalog并验证#220全部binding都能逐位展开；再生成完整静态网，
经通用布线、原生网stitch、上下层耦合RC、原Liberty电气与TT300MHz setup/hold验收。
路线变化须重新提取；#202/#216/#218/#225的旧版图数据不能转移为新底座资格。

登记沿用management-hub PR5 pending；无config/board.json，Projects unverified、
同步pending，沿用Issue7。待有权限维护者补配置并读回，不新建或猜测看板。
