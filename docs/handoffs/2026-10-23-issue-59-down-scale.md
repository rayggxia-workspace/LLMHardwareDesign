# Issue59接续：Llama down_proj

2026-10-23（Asia/Shanghai），Liangruizhi/2663955430@qq.com/182389313。
仓库rayggxia-workspace/LLMHardwareDesign，project_id=llm-hardware-design。
[Issue59](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/59)/[PR60](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/60)，
task/59-down-scale，base task/56-llama-cross-model@2fd3e858f87e7a1bbb95adcd07395243a2334d89。
工作目录D:/Projects/LLMHardwareDesign-downscale；当前交付head与dirty先git/PR读回，不把未审查PR写成已合并。
源：采集1ef1197/f025806；正式数值与服务6d2d6603fde7e2372bd399c1cee511e33e6c2781；分析/打包/重放e5bca383e79ad076aceac76c235b830fdebc5b14。

实际所有本机计算已结束：2次新文本捕获、24候选/144条件、1152服务配置两轮、全量独立数值/4 witness/144包络、7合同检查。
13科学文件相同；完整与精选包安全解包/packet重放及数值/依赖负例通过。
报告docs/experiments/issue-59-llama-down-scale.md；决策docs/decisions/2026-10-23-down-proj-scale-granularity.md；
成果project/experiments/down_scale/results/issue-59-run04/，辅助work/Liangruizhi/59/。
完整原始数据只在D:/Projects/Codex/llama-downscale-20261023，完整索引在精选包local-data-index.json，共享pending。
精选包只含24代表条件编码、全部144/1152摘要/4轨迹；不能冒充全量浮点校准重放。

结论：最佳K128/W128仍5.39%局部误差；粗35bit界不表示实测溢出，固定实际W与所见scale最紧界约1.62e9可用32bit。
需继续对guard/metadata成本与portable64比较；输出格式/RQ误差是下一个最小分叉。近M服务差约1.4%/2.3%，无最终硬件收益结论。
未执行：全层/全模型质量、长序列、硬件周期/RTL/PPA及E2b/E3/E4/E5。不要扩大解释0饱和或producer PASS。

用户随后把兄方批次交由本会话用服务器并行，已另开Issue61，不混入本机实验事实。
服务器REMOTE_RULES已读，身份与现有Slurm任务已查；只本人RuizhiLiang目录，不中断其他成员。

恢复第一步：重新认证Liangruizhi，核Issue59/PR60/61及成员进度；检查包SHA，运行work/Liangruizhi/59/verify.py。
再按最小分叉冻结下一协议，不为所有模型盲扩交叉矩阵；师兄现有PR36先接收核SHA，避免重复。

协作回执rayggxia-project-collab1.0.0：文件/PR已交付状态以线上读回为准；审查人待指定，不自合并/不done。
management-hub PR5本轮读回open/unmerged，登记pending。
无config/board.json与Projects条目能力，已读status-mapping，看板unverified、同步pending；
具能力管理员待指定核Issue59、Project ID、In review/P1/assignee并读回；原始数据共享处理人待指定。
