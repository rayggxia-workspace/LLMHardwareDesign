# 跨 PR token/s 研究工具

[Issue #244](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/244) / [PR #243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)。用户指定继续在 `task/242-r-load-bounds` 分支研究；不接管 PR220/241 的工作树或作业，不修改生产 RTL。结论见[研究报告](../../../docs/experiments/issue-244-token-throughput-study.md)。

## 输入与方法

- `study.json` 固定 PR220/241、补充的 PR237/239 版本及共享输入 SHA；`references.json` 保存实际读取的文档 Git blob / SHA-256。`qwen2.5-3b-config.json` 原字节来自 PR237 的固定 Qwen 配置，原官方 revision 为 `3aab1f1954e9cc14eb9509a215f9e5ca08227a9b`，本轮未重新下载模型或权重。
- `analyse.py` 只用标准库，按 SHA 拒绝输入漂移。由实际 IR 的依赖、选中绑定及容量为 1 的资源顺序重建完整 DAG；其序列化必须逐字节等于 PR241 的 `tasks.txt`。暂不支持的 offset/shard 合同直接拒绝，不近似成独立资源。
- 每个情景将指定算子**整个服务时长**乘以假设因子，重新求完整 DAG 最长路径。它包括搬运/转换，未分离纯计算或 DDR 等待。结果仅是固定绑定与资源顺序下的敏感性；没有生成可执行优化配方，不证明新命令成本、资源释放或真实吞吐。
- decode 工具从模型配置独立推导每 token 密集投影/LM-head 的 MAC 数，再使用上游报告的驻留命令间隔求理想计算上限。S8、混合、S16 以及现有/候选硬件分开；不是带 KV 的生成速度。权重载荷/理想 GQA KV 读量不含完整事务、元数据、重复读取或能量。
- `systemc-evidence.json`另固定最新PR220迭代15与PR241的34组架构结果。`assess_systemc.py`核对这些已发表记录并计算达到4/5/10 token/s的必要条件，不重新运行SystemC。该版只激活2P/1U、候选原生S32宏、S32激活/KV；不能混用上面3颗原M的数位乘法上限。
- 描述符只复算 PR241 给出的 `64×20` 与 `287` 两个端点；不拟合未校准的完整 DDR 模型。

## 检查与服务器复跑

本地小例检查：

```powershell
python -B scripts/check_project.py
python -B project/experiments/token_throughput_study/check.py
python -B project/experiments/token_throughput_study/check_assessment.py
# 使用全新的输出文件名：
python -B project/experiments/token_throughput_study/preview.py --out /新的目录/preview.json
python -B project/experiments/token_throughput_study/assess_systemc.py --results work/Melodydt/244/upstream241-results.json --out /新的目录/assessment.json
```

`check.py` 用独立全路径枚举验证 900 个 DAG 情景，检查关键路径切换，并拒绝四种非法图和一次真实源 SHA 篡改。首轮 Windows 检查因默认 TEMP 无写权限中止；改为本人实验目录的单个临时文件后通过，未放宽判据。

`check_assessment.py`另用40位Decimal独立复算三个目标的必要字节/带宽条件，验证吞吐上限，并实际拒绝四种损坏的上游记录。它只验证算术和拒绝路径，不授予新的SystemC数值/时序资格。

完整 707 MiB IR 的计算只在获授权的服务器 Slurm 资源内执行。先读 [REMOTE_RULES](../../../docs/REMOTE_RULES.md)，使用本人目录和全新尝试名。以下从具有已提交源码的 checkout 打包；代码 commit 及真实命令以[证据索引](../../../work/Melodydt/244/README.md)为准：

```bash
run=/public/home/yuzelu/Melodydt/issue244-token-throughput/run04
mkdir "$run"
mkdir "$run/source"
git archive --format=tar 81dfbd0e6e6d1432447750d5b2d4a106e2d786b7 \
  project/experiments/token_throughput_study > "$run/source.tar"
tar -xf "$run/source.tar" -C "$run/source"
cp "$run/source/project/experiments/token_throughput_study/job.sh" "$run/job.sh"
cd "$run/source"
find project/experiments/token_throughput_study -type f -print0 | sort -z | xargs -0 sha256sum > "$run/source-files.sha256"
printf '{"source_commit":"81dfbd0e6e6d1432447750d5b2d4a106e2d786b7"}\n' > "$run/inputs.json"
cd "$run"
sbatch --parsable job.sh
```

c64配置 `RealMemory=1 MiB`，不能据此请求真实GB内存；脚本分配4核，并以 `ulimit -v` 将每个分析进程的虚拟内存限制为12GiB。首轮16G请求未被受理、无JobID；101601随后因Windows清单CRLF导致文件名含回车，读取源码前失败。保持六个源码不变，生成LF清单并在新run03先执行 `sha256sum -c` 后提交101608，已在c96/node13用22秒COMPLETED0:0，实际Python3.10.12。失败原件保留，未取消在跑作业或跳过检查。

Windows打包时必须将source-files.sha256写成ASCII/LF字节，不能使用默认CRLF的文本写入。上面的Linux命令自然生成LF；提交前应在source目录运行 `sha256sum -c ../source-files.sha256`，全部通过后再sbatch。

容器此前核验SHA为 `49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a`；本作业未额外记录运行时镜像哈希，待核实。研究结果记录真实Python版本与输入/输出SHA，没有新增SystemC、RTL、物理或能耗验收。

运行器对原共享目录只读，不使用其他成员的 Python 环境；输出 graph.json/result.json 留在本人目录。graph.json 是完整可审计 DAG，仓库保存轻量结果、来源及 SHA 索引。若输入不可访问或 SHA 不符，先恢复对应冻结版本，不删校验。
