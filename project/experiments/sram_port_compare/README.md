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

首次服务器执行结果待真实回执补充。任务入口[Issue247](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/247)，沿[PR243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)交付；负责人Melodydt，未审查合并不done。
