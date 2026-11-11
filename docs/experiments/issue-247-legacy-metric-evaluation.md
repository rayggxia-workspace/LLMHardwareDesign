# 沿用 PR241 / Issue247 评价体系的吞吐复评

关联 [Issue247](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/247) / [PR243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)，负责人 Melodydt；2026-11-10T00:50+08:00（Asia/Shanghai）。复用当前任务分支，未改生产RTL、未实装SRAM扩容。

本轮使用此前研究的冻结模型重新评价；不同实现约束的原生串行转换模型不参与本轮分母或百分比。旧体系中的主要W8 decode结果仍是 **3.063655 → 3.230811 / 3.496169 token/s**：前者是八组部分和且保持共享口的机制投影，后者还需要理想独立读写端口。**4.467001 / 4.547434 属于48/64KiB的prefill2参考。**

固定K256、switch1、reuse_A1、端口q4、U16KiB和4向量lane。W8沿用adaptive_prefix_pair_combine，W16沿用adaptive；每个四因子组内部配方完全相同，主矩阵policy0，容量参考policy16。消费者优先仲裁在旧模型中没有独立参数，本轮不给它单列增益；已有预取/前缀/成对供数/写合并收益也不重复计算为新增RTL收益。

本表读取已完成的21项SystemC回执，沿用旧S32/S96模型、300MHz、2P/1U和总DDR 17.1GB/s。共享端口ctx8属于机制投影；独立读写端口属于理想目标；48/64KiB属于未实装容量参考。

源码 commit：`3e62b85c8da19caca31784cb380c40d323295157`。结果 SHA-256：`31213ac812866f463c8bd6e32a97d41e74e570b5310b6689f15e1e8fc6727cbc`。

## 四个workload的条件吞吐（token/s）

| 场景 | 16KiB共享口/ctx1 基线 | 共享口/ctx8 机制投影 | 理想独立读写/ctx1 | 理想独立读写/ctx8 联合目标 |
| --- | ---: | ---: | ---: | ---: |
| Decode context512 / W8 | 3.063655 | 3.230811 | 3.301099 | 3.496169 |
| Decode context512 / W16 | 1.871684 | 1.835579 | 2.027523 | 2.116659 |
| Decode context2048 / W8 | 2.306810 | 2.400318 | 2.447213 | 2.552804 |
| Prefill 2 tokens / W8 | 3.107254 | 3.107254 | 3.696697 | 3.696697 |

## 同一workload内的直接配对变化

吞吐变化 = `(基线耗时 / 候选耗时 - 1) × 100%`；下列百分比各有自己的分母，不相加。

| 场景 | ctx8/shared 对基线 | 理想读写/ctx1 对基线 | 理想读写/ctx8 对基线 | ctx8 对ctx1（理想读写内） | 理想读写对共享口（ctx8内） |
| --- | ---: | ---: | ---: | ---: | ---: |
| Decode context512 / W8 | +5.456% | +7.750% | +14.118% | +5.909% | +8.213% |
| Decode context512 / W16 | -1.929% | +8.326% | +13.088% | +4.396% | +15.313% |
| Decode context2048 / W8 | +4.054% | +6.086% | +10.664% | +4.315% | +6.353% |
| Prefill 2 tokens / W8 | +0.000% | +18.970% | +18.970% | +0.000% | +18.970% |

## 未实装容量参考

这些行均采用ctx1、理想独立读写和固定16KiB预取判定。对16KiB ctx1是容量对照；对16KiB ctx8是整路线比较，不能称为纯容量增量。

| 场景 | 每P容量 | 条件token/s | 对16KiB理想读写/ctx1 | 对16KiB理想读写/ctx8整路线 |
| --- | ---: | ---: | ---: | ---: |
| decode512 / W8 | 48KiB | 3.541567 | +7.284% | +1.299% |
| decode512 / W8 | 64KiB | 3.543921 | +7.356% | +1.366% |
| prefill2 / W8 | 48KiB | 4.467001 | +20.838% | +20.838% |
| prefill2 / W8 | 64KiB | 4.547434 | +23.013% | +23.013% |

48/64KiB容量参考在prefill2中分别为 4.467001/4.547434 token/s，在decode512中分别为 3.541567/3.543921 token/s。Prefill2计入两个输入token的摊销，不能把这一吞吐直接当作decode生成速度。

## 原observe参考

W8/decode512 observe为 2.714625 token/s；同硬件ctx1/shared下已有调度组合直接提升 +12.857%。理想端口ctx8联合目标相对observe的直接比值为 +28.790%，不是分阶段百分比相加。

## 证据边界

- 共享端口ctx8是旧S32/S96体系中的机制投影；原生8xS64实现未因此获得S32/S96资格。
- 理想1R1W按独立64B/拍读和64B/拍写计时；当前四1RW bank实现不等于这个目标。
- 理想端口结果是条件目标参考，不是数学上界，也不是原生RTL实测速度。
- 48/64KiB仅保留为未实装容量参考；其对ctx8方案的比较同时改变容量和context策略。
- Prefill2是两个输入token的摊销吞吐；decode是单次生成token，不跨场景比较百分比。
- 每项提升均直接比较同workload/profile的两次结果；不将各项百分比相加。

全部21项通过独立审计、U参考核对及历史字段复核；生成器产物与run12完全相同。输入、旧结果和生成源码SHA保存在配套analysis.json；本分析不执行新仿真。

## 服务器运行与证据

本轮实际作业 **101800 / mdt-legacy-metric**，c64 / node1 / 4核，耗时 **00:03:22**，**COMPLETED 0:0**。源码 commit `3e62b85c8da19caca31784cb380c40d323295157`；源目录及输入以部署清单绑定。Python 3.10.12、g++ (Ubuntu 11.4.0-1ubuntu1~22.04.3) 11.4.0、SystemC 3.0.2，C++17/O2/Wall/Wextra/Werror。运行在既有 ORFS 容器中，容器和 libsystemc 的 SHA 见 `tools.sha256`。

登录 `yuzelu@10.129.166.172`；目录 `/public/home/yuzelu/Melodydt/issue247-area-speed/run15`，源码 `source/`、日志 `slurm-101800.log`、结果 `results/result.json`。实际启动命令为目录内 `sbatch --parsable job.sh`，4核上最多4个并发case。没有本地或登录节点 EDA 仿真。

```bash
cd /public/home/yuzelu/Melodydt/issue247-area-speed/run15
squeue -j 101800
sacct -j 101800 --format=JobID,State,ExitCode,Elapsed,NodeList
tail -n 40 slurm-101800.log
cat results/result.json
sha256sum -c output-files.sha256
```

- 21个完整场景全部执行；逐场景独立工作/流量/容量/端口审计及U参考通过。
- 原有225个kernel数值、4个validation、5个smoke通过；7个回执篡改、2个非法CLI、源码及历史结果SHA漂移均被拒绝。
- 新生成5个C++文件与run12 SHA完全一致；全部旧模型源、输入冻结。run05和run12适用场景全RESULT精确相等；run04仅新增policy元数据；run01所有原字段递归零容差核对，新增资源元数据另行审计。21个场景都有历史参考，不只比较token/s。
- 63份当前源码、16份部署输入绑定；75个服务器输出SHA、63个回收结果SHA、74份轻量原件。大二进制/生成源码保留本人服务器，仓库采用可逆压缩并同时记录原文和存储SHA。
- 主结果 SHA-256：`31213ac812866f463c8bd6e32a97d41e74e570b5310b6689f15e1e8fc6727cbc`。
- 管理结构检查通过只代表管理结构；完整原生RTL大模型、真实权重生成、模型质量、面积/STA/P&R均未在本次执行。

## 复现和交付

部署包中的16份原输入另行归档在证据目录的 `run15/frozen-inputs/`，包括四份历史结果及其源码输入清单。本地核验逐项比对SHA，并再次执行独立的21场景历史字段和资源审计；74份回收原件与16份输入档案分别计数。

[场景计划与运行器](../../project/experiments/legacy_metric_eval/README.md)、[全部对照分析](../../work/Melodydt/247/legacy-metric-eval/analysis.md)、[证据索引](../../work/Melodydt/247/legacy-metric-eval/index.json)、[接续记录](../handoffs/2026-11-10-issue-247-legacy-metric.md)。本地只读核验：`python -B work/Melodydt/247/legacy-metric-eval/verify.py`。服务器原始run01/04/05/12结果作为历史输入，路径/SHA均保存在部署及结果清单；主模型无需改写。

结论用于旧候选架构内部的方向选择。八组部分和对W8 decode有效、对W16共享口略慢、对多行prefill没有单独增益；理想端口收益取决于真实并发访问能力。16KiB联合目标已接近大容量方案的decode结果，扩容在prefill参考中更明显。当前四个1RW bank允许部分读写并发，但不等于模型中同时64B读和64B写；原生S64也不等于旧S96，所以本报告不能替代当前生产RTL的完整模型实测。

规则 rayggxia-project-collab 1.0.0；本地与远端任务分支交付分别核验，PR待独立审查/合并，Issue保持in_review，不done。登记PR5 pending；缺board.json/Projects能力，看板unverified、同步pending，管理员待指定。CI以最终head的在线回执为准。作业已终态，无活动仿真，无自动监测。
