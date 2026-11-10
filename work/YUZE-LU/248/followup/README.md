# Issue248 后续讨论与全部追加实验

统一入口：[主台账D01–D24](../../../../docs/experiments/issue-248-followup-design-ledger.md) · [完整配置附表](../../../../docs/experiments/issue-248-followup-all-cases.md) · [Issue248/PR249](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/249)。

用户确定总51.2 GB/s、新生产profile不用S128并尽量避免持续S64；其他资源/组织方案均未默认定案。这里保留所有追加实验和候选，不只推荐或成功结果。

## 包与覆盖

`inventory.json`为授权目录的metadata快照：服务器53个Issue248根目录，分别为PR249原有41个run、公开模型输入根和本次11个追加run；逐根对应仓库入口。它不扫描无关项目或校验全部模型/参考工程文件。旧证据保持原处，不重写。

`index.json`保存11个新包、584成员的SHA-256及真实Slurm状态；包为`bundles/*.tar.gz.b64`。包含实际执行源、原source.sha256、工具/输入引用、原结果、日志、生成代码、部署回执、失败和取消材料。原有evidence.tar.gz也按原字节保留，离线核对其回收SHA。`early-extra-sha256.json`补回早期24种计时的完整日志/生成源，以及两个取消质量任务的部分日志；它们不获得质量通过资格。

执行时脚本为基于bf02ab63的隔离未提交文件；准确字节由原source.sha256固定。**本次发布commit不是历史执行commit。** 根目录的某些聚合/阅读副本不是执行入口，原RESULTS与source清单继续区分。公开模型、完整checkpoint和大build保留授权服务器，不因有归档索引而宣称已上传这些raw。

追加覆盖：四实际FFN的28种对照、六组36层部分语料质量、24种位宽/RNE/Mid时间消融、六种G表（65项质量失败）、20组流式/银行/X配置的20次micro及41次完整decode trace、256种提议布局合成整数检查（12组重复同一固定集合）。所有完整trace读写字节/M命令数与基线一致。

`summary.json`从归档确定性生成，带FIFO预约/等待、FFN时间/链路和X预算。完整原始指标仍在包内，不删去未展示到Markdown的通道/端口等字段。

## 离线核验与生成

只用Python标准库，不连接服务器，不执行ML、RTL、SystemC或EDA：

```sh
python -B project/experiments/stream_quant_synthesis/followup_report.py --root work/YUZE-LU/248/followup
```

重新生成派生summary和完整配置附表：

```sh
python -B project/experiments/stream_quant_synthesis/followup_report.py --root work/YUZE-LU/248/followup --write-summary
```

重跑实际试验必须从指定包恢复真正执行源、保留原工具/模型revision/输入SHA，并在**全新的空运行根**提交Slurm，按6×10或8×12策略。不要直接在已有输出目录运行driver，或覆盖旧包/旧source.sha256。历史narrow01/02的4核记录及两次取消按事实保存，不改写成后来策略。

## 证据与交接边界

S32和小表是含浮点路径的质量筛查；新流式时间不承载整模型数值。header-first提议与真实W8/M RTL的lane排列兼容尚待验证；20次micro和256种合成布局不替代整模型整数RTL。

旧研究S128/M/G/bank RTL是历史参考。新S32、缩表、流式、X-in-S、地址窗和控制/MC联合RTL、物理资格、能耗、10 token/s及公平FPGA/ASIC对照均未完成。G表/X位置/FIFO/上下文等未决项见D01–D24。

Issue248保留in_review，PR249未合并、不done。登记沿用management-hub PR5 pending；config/board.json缺失，当前Issue没有Projects条目，目标看板unverified/同步pending，管理员和审查人待指定。旧PR251宽格式合同待后续修订，不能作为新profile的直接执行合同。
