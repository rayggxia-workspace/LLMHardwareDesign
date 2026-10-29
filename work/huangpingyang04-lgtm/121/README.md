# Issue #121：负载与位宽讨论文档

关联：[Issue #121](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/121)。本次整理负责人huangpingyang04-lgtm；Issue整体实施负责人保持YUZE-LU。

正式成果：[M11/M12宽线负载与M数据位宽](../../../docs/experiments/issue-121-load-and-width-review.md)。

提交：[PR #134](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/134)，OPEN、非草稿、待独立审查。初始提交dfea826a47ebc24e974bca3c78feb1781ae45426；本地与上传树精确一致，最新commit/CI以PR读回为准。

## 范围与实际结果

整理宽线负载/冻结阶段约束、既有run287电容失败、openTPU small和llaccel接口、128bit供数推导、256/512bit候选及联合评估步骤。来源清单见[load-width-sources.json](load-width-sources.json)。

本次仅文档；未修改RTL/服务器/参考包，未执行EDA或接口候选。不是对Issue #121、PR #122或未来系统的最终验收。

## 检查

- 修改前、修改后执行 `python -B scripts/check_project.py`。
- `git diff --check`。
- 对本文引用的小型输入核对固定Git字节、SHA、端口声明与参数。
- 复核128/256/512bit的300MHz理论带宽、S8 tile的72B有效/80B容器/5次接受，以及T high超限差值。
- 核对本次文档相对文件链接和固定提交链接。
- 实际结果：管理结构、diff空白检查、10份来源Git字节/身份、6个相对文件链接与条件算术均通过；业务仿真/综合/物理未执行，因为没有实现变更。CI实际状态另记在PR提交回执。

## 协作与恢复

- 从main 6a681d6632e7f7be537ff96eae1827df834bcfe8创建独立分支 `task/121-load-bandwidth-review`，不改写PR #122实施分支。
- 当前来源的c048b5c属于PR #122快照；不得假定相应路径已经在main。
- 审查者待指定；候选取舍待实施负责人/独立审查，不自批准、合并或关闭Issue。
- 已读回项目登记management-hub PR #5：OPEN、未合并，登记pending。
- 本分支无config/board.json；现有工具未提供Projects条目能力，看板unverified、同步pending。待管理员明确看板/授权并核验Issue121实际条目；不另建看板。
- 下一步：审阅讨论文档；若批准实施，在原Issue下明确范围并按文档步骤固定基线、做有限候选和全路径验收。
