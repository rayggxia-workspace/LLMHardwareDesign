# Issue117：全项目研究教程与证据交付

负责人Liangruizhi（182389313）；[Issue117](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/117)。独立目录 `D:/Projects/liangruizhi/.worktrees/issue117-handbook`，分支 `task/117-research-handbook`；主线基线 `2113afef4afc1f16391e0ed929158bdfc3f70b94`。本任务不修改或继续主会话的代码、服务器任务、原结果及其他成员116图册归档。

正式成果在 [docs/research-handbook](../../../docs/research-handbook/README.md)。全文与11章从同一源生成。保留每个模型的输入、执行阶段、关键数值、失败/限制、划分推理和下一步；其他任务在全项目总账逐一说明。

本目录包含：

- `source-documents.zip`：164份冻结来源原字节（105个Git来源、59个Issue正文快照），约0.91MB；无权重、大张量或凭据。SHA/大小/逐成员归属见正式 `source-index.json`。
- `task-snapshot.json`：59个Issue/58个PR的读取快照，工作流与执行范围分开；以后恢复须重读在线状态。
- `build_handbook.py`：离线生成证据目录、任务总账和完整全文，不改手写章节。
- `audit_handbook.py`：独立核zip/Git blob/SHA、章节/链接/显式锚点、83组来源片段、12格CSV聚合和教学数例，不执行模型/RTL/EDA。
- `validation.json`：最终实际文档检查回执；不是原模型实验复现。
- `collaboration-readback.json`：本次账号/仓库、登记PR5和看板权限的真实核验。
- `remote-readback.json`：上传后固定commit的实际字节回读（发布后补齐）。

命令从仓库根执行：

```powershell
python -B scripts/check_project.py
python -B work/Liangruizhi/117/build_handbook.py
python -B work/Liangruizhi/117/audit_handbook.py
```

首次管理检查因独立副本未检出 `.github/` 而失败；补齐原有稀疏检出后原检查通过，没有新增假管理文件或改校验器。原报告读取在标准库/现有解释器完成；本次未安装软件、未运行模型/整数生产或原接收、RTL/gate/SAT/综合/STA/物理，也未查询服务器新终态。

当前登记management-hub PR5仍open/unmerged，pending。无 `config/board.json`；本账号实际GraphQL查询Issue117 Project Items返回 `INSUFFICIENT_SCOPES`（read:project），条目事实unverified、同步pending，管理员待指定。不扩大token权限、不切换账号。本任务通过独立PR审查，不自行merge/done；发布事实见交接和在线回执。
