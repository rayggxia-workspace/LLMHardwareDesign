# Issue247：容量与读写并发两路线比较

用户要求研究两个P各48/64KiB＋读写并发，与各16KiB＋读写并发＋8组部分和。两P/一U、U16KiB及原端口、N8、4向量lane、17.1GB/s及参考时钟保持。SRAM扩容只在隔离条件模型中研究，不实装生产RTL。

本目录复用原封不动的area_speed_study/p_dma_study功能源，生成同一份容量/端口/context可参数化的C++模型。source.json锁源、8份原输入及246/247四轮真实结果与对应源码清单。先完整重跑历史容量/端口基准，再接受新联合结果；运行前必须核验输入/源码SHA。

新完整CLI为：`model TRACE PROFILE VARIANT CTX SWITCH REUSE P_KiB DUAL P_QUARTER_CYCLES`。本轮P_KiB取16/48/64，CTX取1/8，DUAL取0/1；端口占用取4/5/6/8个四分之一拍，即每64B服务1/1.25/1.5/2拍。它是端口占用敏感性，不是整个芯片降频，也不模拟真实宏同址冲突。保留旧默认CLI用于完整回归。

在获授权Slurm计算节点、全新run目录执行：

```bash
sbatch --parsable job.sh
# job.sh使用4核，校验冻结清单后调用：
python3 -B source/project/experiments/sram_port_compare/run.py \
  --inputs /absolute/new-run/inputs --out /absolute/new-run/results \
  --capacity /absolute/new-run/capacity-result.json \
  --stage1 /absolute/new-run/stage1-result.json \
  --stage2 /absolute/new-run/stage2-result.json \
  --stage3 /absolute/new-run/stage3-result.json
```

各前置结果同目录须有对应capacity/stage1/stage2/stage3-inputs.json；当前run根须有inputs.json真实source_commit。前置SHA、passed与源码关系不符时拒绝；结果目录已存在时拒绝，不能覆盖旧实验。旧外部SystemC/容器依赖见job.sh，不声称仅凭仓库能重建全部环境。

独立compare_audit从trace重推分片、驻留、A/B流量及每个P的本地读/写服务；另核对真实旧U状态与工作不变。模型不执行真实张量数据，既有数值oracle不等于新RTL/宏资格。含U的私有S预算分别48/112/144KiB；16KiB路线的8组单行部分和另加672B/P数据寄存器及控制，不能把不同资源当同面积比较。

首轮run04/101665已COMPLETED0:0，8分02秒，57完整trace＋6尾块＋4非法CLI通过，149回收输出SHA一致。W8/context512默认策略B为3.496169，A48/64为3.412179/3.413514；prefill2大容量路线更快。完整结果SHA966729e962ecde76f755a9da873f3fb7ac566e4dd454f45e7d4b6f8f76c73cce。

发现adaptive判定随容量切换，新增独立policy扩展作控制实验；已测run.py/generate_compare.py/compare_audit.py及source.json保持。generate_policy.py仅改变adaptive预取判定阈值，实际驻留/容量/分片仍保持。新增第11参数ADAPT_POLICY_KIB取0（按实际容量）或16（固定16KiB判定），默认去policy_study后必须完整回归run04。source-policy.json锁该扩展及真实run04-result.json/run04-inputs.json；policy_audit要求相同硬件的流量、M工作、每端口服务/预约与U实际工作不变，只允许时序/等待变化。

run05/101672源49b3938ce8b55734520c56a79a7d5d7933af9cdc，3:58 COMPLETED0:0，30完整case（先12默认回放）及2非法CLI通过，81回收SHA一致。固定判定后A48/A64 W8/context512为3.541567/3.543921，比B3.496169仅高1.30%/1.37%；prefill2分别高20.84%/23.01%。完整结果SHA4dcb0f01357e2f71fcf9f90deeab1d1dd50101b3d928b3e9866473c91c133777。[报告](../../../docs/experiments/issue-247-capacity-port-compare.md)和[证据](../../../work/Melodydt/247/compare/README.md)列出所有退化、端口代价与资格边界。两轮无活动作业、未配置自动监测。

```bash
# 另建全新run；根内放真实run04-result.json/run04-inputs.json及冻结清单。
# 将源目录的job_policy.sh复制为该run根的job.sh，再从run根提交：
sbatch --parsable job.sh
python3 -B source/project/experiments/sram_port_compare/run_policy.py \
  --inputs /absolute/new-policy-run/inputs --out /absolute/new-policy-run/results \
  --prior /absolute/new-policy-run/run04-result.json
```

任务入口[Issue247](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/247)，沿[PR243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)交付；负责人Melodydt，未审查合并不done。
