# Issue #255 控制章节交接

- 日期 2026-11-11（Asia/Shanghai，UTC+08:00）。仓库 `rayggxia-workspace/LLMHardwareDesign`，项目 ID `llm-hardware-design`。[Issue #255](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/255) 负责人 Melodydt。
- [任务分支](https://github.com/rayggxia-workspace/LLMHardwareDesign/tree/task/255-dac-control-paper) 基于 [PR #251](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/251) 的 `9abd46f5cbb4534bcfc614571ccd6d402ad11882`。以 `task/250-w8a16-base-contract` 为堆叠 PR 的基分支。最新提交与审查状态见 [草稿 PR #256](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/256)。
- 本地独立目录 `D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/255/authoring` 为文稿目录。线上分支是完整 Git 历史，本地文稿经 GitHub 连接器发布。PNG 预览及生成器检查副本保存在本任务本地目录。
- [论文控制图文与固定版本证据](../papers/dac-control/README.md)。五类九实例是 NoPool 候选合同清单。图 2 局控栏限于 native P 的三指令内核。基线三 P FFN 的实现和 PR #180 的覆盖证据各有独立出处。

## 已执行检查

- 在本地管理副本执行 `python -X utf8 scripts/check_project.py`，通过。
- 四个固定版本汇编、循环展开、LC 内核和 FFN 镜像生成文件的 Git blob 与远端一致。用 Python 3.12 运行本地 `verification/check_paper.py`，核对实例清单、ISA 分类、FFN 镜像与 192 次调用，并汇编验证两种逻辑拓扑例子的指令编码、描述符地址、依赖与 wait 掩码。两张 SVG 已渲染并目视核验。
- 本轮无新增服务器作业，未执行 RTL 仿真、SystemC 或物理测试。

## 恢复步骤

1. 读回 Issue #255、任务 PR 和 PR #251 的当前状态。核对变更后再决定是否更新论文基线，按文稿证据表逐项检查图文引用。
2. 以二级调度图、拓扑映射图和英文正文为起点，核对术语与已绑定服务的范围。若论文需要量化收益或真实时序，补充可回查的 CALL、描述符取回、写 ACK 与终态日志。由 Melodydt 推进，独立审查人待指定。
3. 如需补实验，按 `docs/REMOTE_RULES.md` 登录项目 Slurm 集群，在本人目录 `/public/home/yuzelu/Melodydt/issue255-dac-control/<attempt>` 使用独立的源码、日志和结果目录。固定提交、输入/配置、工具及校验和，沿用经核验的工具或容器，采用 `sbatch --parsable` 和 `mdt-<任务缩写>`。用 `squeue` 区分排队和运行，用 `sacct`、日志及输出 SHA-256 核验终态。每次提交提供实际作业号、分区、核数、命令和位置，长作业单独保留恢复入口。
4. 登记沿用 [management-hub PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5)，待合并。仓库无 `config/board.json`，当前 GitHub 工具无 Projects 条目接口。看板事实为 `unverified`，同步为 `pending`。管理员待指定，先核对 [候选看板 #1](https://github.com/orgs/rayggxia-workspace/projects/1) 的受众与配置，再查 Issue #255 条目、状态和 Project ID，并记录读回证据。
