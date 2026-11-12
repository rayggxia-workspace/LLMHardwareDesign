# Issue #255 控制章节交接

- 更新日期 2026-11-12（Asia/Shanghai，UTC+08:00）。仓库 `rayggxia-workspace/LLMHardwareDesign`，项目 ID `llm-hardware-design`。[Issue #255](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/255) 负责人 Melodydt。
- [任务分支](https://github.com/rayggxia-workspace/LLMHardwareDesign/tree/task/255-dac-control-paper) 基于 [PR #251](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/251) 的 `9abd46f5cbb4534bcfc614571ccd6d402ad11882`。以 `task/250-w8a16-base-contract` 为堆叠 PR 的基分支。最新提交与审查状态见 [草稿 PR #256](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/256)。
- 本地独立目录 `D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/255/authoring` 为文稿目录。线上分支是完整 Git 历史，本地文稿经 GitHub 连接器发布。PNG 预览及生成器检查副本保存在本任务本地目录。
- [论文控制图文与固定版本证据](../papers/dac-control/README.md)。图 1 保留 NoPool 九个实例与 C 局控，用蓝色接口表示固定 SRAM 访问，用与图 1(a) 对应的橙色横带表示 C 内后制路径。已验证 G→E 接入横带，S/R 端点仍属候选。图 2 先介绍四类指令的总体作用，再用 Llama 3.2-3B 与 Qwen3-4B 的 Q/K 前处理说明插入逐头 RMSNorm 如何改变张量路径和调用顺序。图中模型算子级映射为候选。图 3 展开三 P FFN 的母控循环、同一局控内核及 DDR 描述符表，并注明夹具验证范围。三张可编辑图、中文说明和英文正文同目录，PR #180 证据另列。

## 已执行检查

- 在本地管理副本执行 `python -X utf8 scripts/check_project.py`，通过。
- 四个固定版本汇编、循环展开、LC 内核和 FFN 镜像生成文件的 Git blob 与远端一致。用 Python 3.12 运行本地 `verification/check_paper.py`，检查 diagrams.net 对象和连线样式、公共 ISA、FFN 镜像与 192 次调用。模型步骤对照固定版本源码及配置，C 连线对照固定 RTL 与独立夹具验收。两段程序以基线汇编器核对目标、依赖、调用顺序、掩码和 U0/U1 复用。图 3 的记录地址、等待掩码、镜像与描述符大小均与生成结果核对。新增图已渲染并目视核验。
- 本轮无新增服务器作业，未执行 RTL 仿真、SystemC 或物理测试。

## 恢复步骤

1. 读回 Issue #255、任务 PR 和 PR #251 的当前状态。核对变更后再决定是否更新论文基线，按文稿证据表逐项检查图文引用。
2. 以二级调度图、拓扑映射图和英文正文为起点，核对术语与已绑定服务的范围。若论文需要量化收益或真实时序，补充可回查的 CALL、描述符取回、写 ACK 与终态日志。由 Melodydt 推进，独立审查人待指定。
3. 如需补实验，按 `docs/REMOTE_RULES.md` 登录项目 Slurm 集群，在本人目录 `/public/home/yuzelu/Melodydt/issue255-dac-control/<attempt>` 使用独立的源码、日志和结果目录。固定提交、输入/配置、工具及校验和，沿用经核验的工具或容器，采用 `sbatch --parsable` 和 `mdt-<任务缩写>`。用 `squeue` 区分排队和运行，用 `sacct`、日志及输出 SHA-256 核验终态。每次提交提供实际作业号、分区、核数、命令和位置，长作业单独保留恢复入口。
4. 登记沿用 [management-hub PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5)，待合并。仓库无 `config/board.json`，当前 GitHub 工具无 Projects 条目接口。看板事实为 `unverified`，同步为 `pending`。管理员待指定，先核对 [候选看板 #1](https://github.com/orgs/rayggxia-workspace/projects/1) 的受众与配置，再查 Issue #255 条目、状态和 Project ID，并记录读回证据。
