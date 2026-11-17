# 七模型速度仿真与512-token Prefill估算

负责人 Melodydt；[Issue #291](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/291)；[PR #292](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/292)。独立分支 `task/291-seven-model-prefill-estimate`，基分支 `task/280-seven-model-energy` 的 `89b02b0424e3ab923fca320509a4058692bd5f97`。不修改 #280 的代码/工件/作业。

阅读 `seven-model-speed-report.html`；机器结果 `seven-model-speed-results.json`；每模型原回执 `inputs/`，局部采样和估算 `results/<model>/`。

**512-token Prefill全为条件预测，非完整仿真实测。** 16/32-token独立验证按用户要求暂缓。Phi和Falcon注意力局部样本与两端直线最大偏差分别10.72%和10.16%，按用户要求保留线性估算并显眼标注。Granite未新增专家路由扫描；Qwen3.5/Falcon没有中间真实递推状态快照，只有固定大小服务的零态/真实512末态敏感性采样。

## 数据与方法

- 原速度来自 #274 全层三P/512-bit PR272 combined短程，并经 #280 窗口复跑保留。所有原短P和Decode值未更改。
- 第1输入位置的原时间保留启动一次；第2位置增量和第2步Decode的主体时间（可见KV为2和514）建立端点直线，显式求和至512，最终词表头只加一次。
- 330个注意力局部采样覆盖1/2/4/7/8/9/16/32/64/65/128/129/256/257/512。每模型3个代表层，Gemma4个。固定合成query和真实KV前缀，冻结原服务与实际DRAMsim3/S128，不冒充中间位置完整模型数值执行。
- 混合模型共8个递推探针；实际参数、固定合成激活输入、零态/真实512末态，真实DDR读写，循环规模固定。不从末态截取中间态。
- 原CALL累计忙时不能直接相加为全层时间，因为三P并行。全层估算继续锚定原整体时长。
- Qwen3采样plan SHA与原速度回执不同；保存 `inputs/qwen3-sampling-baseline.json`，验证全部其他结果字段相等，分别保留散列。
- 模型计时仍 `timing_calibrated=false` / `rtl_qualified=false`。不提供物理签核或硬件采样器延迟。

## 运行与复算

```powershell
python -B work/Melodydt/291/build_speed_report.py --all
python -B work/Melodydt/291/verify_report.py
python -B scripts/check_project.py
```

Windows主目录为无 `.git` 的管理文件副本；本任务只在 `work/Melodydt/291` 内写入。GitHub分支通过Melodydt连接维护；公共文档的拟提交版本在 `publication/` 内隔离准备，不覆盖主线程本地文件。

## 服务器回执

登录 `t6s011227@BSCC-T6@ssh.cn-zhongwei-1.paracloud.com`。服务器代码目录 `~/LLMHardware/zenanyan/issue-291-prefill-01`；软件沿用 `~/LLMHardware/opt/orfs-current-repacked.rootfs`。提交 `sbatch --parsable --time=0 run_context_samples.sbatch`，7个任务各1核，单节点，原输入只读挂载。

| 作业 | 源码提交 | 状态 | 说明 |
| --- | --- | --- | --- |
| 38826673 | d01ba717b2387e149c6be3bdfc78f22471a18747 | FAILED 127:0 | 容器只读挂载格式错误，仿真未开始 |
| 38826697 | 618a8b1e3c0a6fdc6e8387b807dd451eb4b01343 | FAILED 1:0 | 只读样本没有零值writes字段，计数检查报错 |
| 38826721 | 395fe768ceaed45ef2b822d9ce288e1f98f0fe0f | COMPLETED 0:0，30秒 | 330 ATT＋8递推样本；v6_384/m3ca0801，7核，UNLIMITED |

```bash
R=~/LLMHardware/zenanyan/issue-291-prefill-01
squeue -j 38826721
sacct -j 38826673,38826697,38826721 -X --format=JobID,State,ExitCode,Elapsed,NodeList,Timelimit
tail -n 20 "$R/slurm-38826721.log"
tail -n 20 "$R/run-38826721/qwen3.log"
cat "$R/run-38826721/qwen3/samples.json"
cd "$R/run-38826721" && sha256sum -c results.sha256
```

所有作业终态，无自动后台监测。原始DDR统计与各样本输出持久保存在服务器 `run-38826721/`。各 `samples.json` 记录实际导入源码、实际读取KV/参数、描述符、输出的SHA及Python版本；本地回收样本与服务器清单核验。

## 交付边界

本轮报告/算术/流量/散列检查不等于用户暂缓的独立序列验证。审查人待指定，PR不自合并，Issue不标done。规则 `rayggxia-project-collab 1.0.0`；登记沿用management-hub PR #5 pending；缺 `config/board.json` 和Projects工具，看板条目unverified/同步pending，待具权限维护者处理。

恢复第一步：读取PR #292与本目录报告，核验样本散列，再按用户后续指令开展独立序列验证或更细粒度非线性建模。


## 论文 Word 双表

追加[一页可编辑Word双表](../../../docs/experiments/seven-model-dac-tables.docx)：七模型短Prefill/估计512-token Prefill/Decode速度（token/s），片上/片上＋DDR的Decode/短Prefill能耗（J/token）。原稿风格、跨双栏三线表，保留区间和证据边界。[生成、验证与接续](WORD_TABLES.md)；源数据未更改。


## 七模型合并Word表（2026-11-18）

新增[合并表](../../../docs/experiments/seven-model-dac-combined-table.docx)，七模型各Prefill/Decode两列、三个指标；Prefill速度用512-token估计，能耗用短P2/Decode标定区间下限。加粗表注区分窗口，旧双表保留。[构建和接续](MERGED_WORD_TABLE.md)。
