# Issue32 GPU 证据交接

更新时间：2026-10-23（Asia/Shanghai，UTC+08:00）。仓库 [LLMHardwareDesign](https://github.com/rayggxia-workspace/LLMHardwareDesign)，project_id=`llm-hardware-design`；本人认证 YUZE-LU（与仓库owner分开核验）。

- Issue：[32](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/32)，负责人YUZE-LU。
- PR：[36](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/36)，分支 `task/32-gpu-model-evidence`，独立目录 `D:/Data/LLMHardwareDesign-gpu32`。待审查，不自行合并、不标done。
- 已同步主线 `0cc36f3238c7084d7126d94c314fe7d8bf0f9c5d`，保留并行H1/H2/个人记录。原工作区与他人工作树未改动。
- 正式测量源码 `82ad35dba0ea7e6d07079e83fe2b781de2ce4c5d`（Qwen3.5）、`e6a830ca22977756de3d5bf09bcf71164f8412cc`（Qwen2.5）；报告初次交付commit `06dffa906db58605e38ff95fa3b276926e539167`。每个运行的manifest记录实际文件SHA，PR最终HEAD为补充交接/检查回执的交付版本。

## 成果入口

1. [实验报告](../experiments/issue-32-gpu-model-evidence.md)：精度表、模型revision、短/长正确性、量化质量、失败和Block预算解释。
2. [代码与复跑说明](../../project/experiments/gpu_model_evidence/README.md)。结果位于同目录`results/issue-32/`，有summary.json、全部计时CSV、逐运行元数据ZIP、模型manifest和package-index.json。
3. `selected-qwen35-layer0/*.pt.gz`仅保存少量真实输入和状态，已随PR交付；`replay_capture.py`无需模型权重即可独立重放chunk/cached递推和错误初态负例。
4. 权重、完整验证logits和其它大trace留在 `D:/Data/llm-gpu32/models/` 与 `runs/`，结果包`local-artifacts.json`保留位置/大小/SHA；本人环境为同目录`.venv`。**本机路径不是团队共享链接**。完整共享存储待项目指定，处理人待指定；不要复制到公开服务。

## 审查时先看这些边界

- FP16短参考两模型均通过；BF16的Qwen3.5短参考失败，门槛未放宽。
- Qwen2.5长512/2048/4096一次与分块比较通过；8192仅分块执行完成。Qwen3.5分块执行到4096，但512/2048部分状态误差超阈值；8192OOM。
- 真INT8矩阵内核与INT32累加已执行，质量候选Qwen3.5为3/4、Qwen2.5为0/4，均未整体验收。浮点scale/反量化、非线性、KV和FP32递推仍存在。状态8/16bit结果为假量化敏感性，不能当整数更新通过。
- Qwen3.5实际固定状态48MiB FP32递推＋1.5MiB FP16卷积，另有32KiB/token KV；Qwen2.5为36KiB/token KV。INT32输出、FP32 scale及将来整数M/r宽乘移位均须单独进入容量/端口预算。
- 无实测物理流量；逻辑字节、去重storage、allocator峰值和WDDM共享显存分开。历史unbounded组有共享内存溢出，不得用于驻留GPU性能结论。正式CSV必须筛`performance_eligible=True`、`warmup=False`。

## 实际检查

`scripts/check_project.py`通过；5项协议测试通过。正式两模型参考/整数共四组artifact SHA读回通过；第一层真实INT8累加样本经独立INT64核对；Qwen3.5浮点递推独立重放及错误初态负例通过。参考四份验证logits实际复跑逐bit一致，candidate输出重新计算质量与保存记录一致。交付包`replay_capture.py`通过；源码语法、文档差异和包索引读回另在本任务辅助回执记录。检查通过不改变质量失败和OOM事实。

独立长观察器给出实际模块/SDPA形状及调用聚合；另一次128+1观察器记录每个ATen调用前后/调用内峰值PyTorch allocator，包括临时增量。此记录不包括allocator之外CUDA workspace，也不是性能运行。少量功能算子可能融合，依赖不是完整硬件DAG。

## 合同与协作待办

PR26@2cd9ca15仍OPEN，完整整数状态/非线性/scale/质量合同未发布；本地候选不是项目最终格式。请用户通知主研究线检查PR36，由主线审查真实捕获边界、先冻结精度合同，再用附带输入验证整数状态更新。审查人待指定，不主动给无关人员发通知，也不代主线跑划分/RTL。

规则：仓库[rayggxia-project-collab SKILL.md](../../.agents/skills/rayggxia-project-collab/SKILL.md) v1.0.0。登记：management-hub [PR5](https://github.com/rayggxia-workspace/management-hub/pull/5)本轮读回仍OPEN，`pending`。看板：无`config/board.json`，已读status-mapping；候选[组织Project1](https://github.com/orgs/rayggxia-workspace/projects/1)本轮GraphQL明确缺`read:project`，条目/字段无法核验，`unverified`、同步`pending`。未扩大凭据权限。由有权限管理员核验本Issue条目及Project ID/Status/Priority，管理员待指定。

恢复第一步：读最新AGENTS、Skill、Issue32/PR36/PR26与本交接；核对PR HEAD及package-index，然后运行README的一条不需权重重放命令。之后按已冻结合同决定校准/更大验证集和整数递推；不要将旧失败、历史running状态文件或本地未共享路径解释为通过/在线作业/共享交付。
