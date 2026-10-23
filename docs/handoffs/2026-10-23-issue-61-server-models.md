# Issue61服务器批次交接

仓库 https://github.com/rayggxia-workspace/LLMHardwareDesign；[Issue61](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/61)/[PR62](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/62)；负责人Liangruizhi。task/61-server-models，D:/Projects/LLMHardwareDesign-servermodels，基于task/59-down-scale/PR60（fb4f42e01d9474c7c92676c72d363e643272a035）。交付commit以PR62 head为准；运行源码分别固定在8a1fe4b/a96eef6/3f17910/0ff14d7/7fdd2c2/4ca7214/8211803，完整SHA见报告/index/binding，不把文档commit冒充实验源码。工作区后续改动先用git status核对，不覆盖别人的目录。

## 实际完成

Gemma3-4B-it、Qwen2.5-3B、Qwen3.5-4B、Phi4-mini已在本人服务器目录 /public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023 的lrz-* Slurm跑完本轮CPU协议。主测420线性/56注意力格式、5185严格来源张量（含Phi）、全PV32 1474560输出匹配I64；Phi仅参考/来源/封存，禁止用于调参。Qwen旧GPU长轨迹复用PR36，两轮独立partial/state重放，不重复CUDA矩阵。完整模型reference是原BF16权重转CPUFP32，非INT8执行速度或全整数状态。

全部作业与失败见work61/execution-ledger.tsv及final-execution-ledger.log；最终90044–90047均COMPLETED0:0。90017现代字典状态适配失败、Gemma坏分片、89995 DNS失败和旧strict01混入cached norm的错误均保留。strict02为正式导出，不能使用strict01。SSH传输不是Slurm，占用短作业结束后不会留在squeue；sacct/log是执行证据。

## 数据接收

正式index：project/experiments/server_models/results/issue-61/index.json；报告docs/experiments/issue-61-server-models.md；逐模型表work/Liangruizhi/61/model-acceptance.json。

服务器primary-model-data01.zip：569140969B，SHA256 2f03daf778c6667aae49d2edd40f3397227514e59c6342d367a552cac6ff7730；包含三主测raw/编码/strict02，无完整权重。phi-reserved02-sealed.zip：30232659B，373a030cc3f4087664d69d20bb13a9ed504e9753972c8a52cf1d5edaa4c668ed，只在冻结后使用。

仓库batch-metadata01.zip：7269991B，b2e94f70861d92debf71d5f0055a7006c6c1731db688e46c0473d0786b9530fa；117索引成员+索引自身、27源文件逐原Gitcommit比对通过，内含review-samples01.zip。后者只重放4GQA/6整数case，不能代替全420条件/全部浮点校准输入。bounds02/cost01单列完整SHA，分别绑定phase16/17；01保留不覆盖。源码/环境和恢复命令见server_models/README。

## 未完成、阻塞、交接责任

本轮CPU执行和数据接收已结束；后续科学研究的E2b完整attention端口/非线性实现、E3公平整数状态、E4物理和整图收益尚未执行。局部误差失败/饱和不能称已接受W8A8；Psum有条件32位核不证明未归一化online算法或所有未来scale安全。无GPU，CUDA/显存/4bit专属指标未执行，不能靠CPU补出。Phi冻结后验证未执行。

PR62待审查/合并，审查人待指定；Issue61交付后in_review，非done。不自行合并PR60/62或更改Issue32/55。最新另有huangpingyang04-lgtm负责Issue63工作负载通信适配器，明确不接管本Issue；保持独立，不另写重复适配器。登记management-hub PR5 pending。当前无config/board.json和Projects读写工具，看板状态unverified、同步pending；管理员待指定需确认Issue61条目/Project ID=llm-hardware-design/Status=In review/Priority=p1并读回。旧GPU原始大包仍有生产方D:/Data共享待项，不因本次新CPU包可访问而称旧所有原始数据都已同步。

## 恢复第一步

先以Liangruizhi/182389313核认证，再读最新AGENTS/Skill、Issue61/PR62与Issue32/55的评论、未合并交接和成员进度。查看squeue/sacct及冻结phase目录，不重启本轮已完成作业。先按README在新D盘目录校验仓库精选包并重放，再按需要读取已有权限服务器主包验证全量；禁止解封Phi调参。根据决策记录选择一个能改变D1–D6的下一阶段Issue，不盲增模型或把CPU计时换算芯片PPA。大文件/权重保留已有授权目录，临时文件仍放D:/Projects/Codex当前任务文件夹。
