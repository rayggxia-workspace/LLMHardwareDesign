# Issue247 S16桥接与E流水化交接

2026-11-10 Asia/Shanghai；负责人Melodydt。仓库rayggxia-workspace/LLMHardwareDesign，Issue247，PR243，分支task/242-r-load-bounds，PR base main，尚未合并。
工作目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/242/r-load-bounds/repo（非Git完整快照，通过GitHub连接的tree/commit及expected_sha提交；不将其描述为已暂存Git工作树）。外层与他人worktree未动。
生产RTL/最终测试源78c57285d206355cbcb5ae9f5cd51249964306cc，模型源2d7aec50cbee93ad19d11a52b96459b194a45b5b；文档/PDF提交另见PR最新head，源码版本不能替换为文档提交号。
备份task/247-before-s16-vector8@ddc12651e35035a25a206d2bdfe46d154864f2d8。当前新能力NEXP_S16/E_PIPELINE默认关闭，独立审查后按配置启用。

## 真实作业状态

服务器yuzelu@10.129.166.172；下列目录均在/public/home/yuzelu/Melodydt/issue247-area-speed。作业全部c64/node1/4核且已经结束。

| run / job | 源码commit前缀 | 结果 | 实际阶段 |
| --- | --- | --- | --- |
| 38 / 102049 | 39cc71b6 | FAILED1:0，1秒 | 启动目录错误，未运行EDA |
| 39 / 102050 | 411fc3a5 | FAILED1:0，1秒 | 清单CRLF，未运行EDA |
| 40 / 102051 | 411fc3a5 | FAILED1:0，30秒 | 默认回归通过，争用测试握手采样错误 |
| 41 / 102052 | f5e8ce54 | COMPLETED0:0，1:30 | 原生21运行＋4面积，模型校准来源 |
| 42 / 102053 | 2d7aec50 | COMPLETED0:0，5:18 | 32条件模型场景 |
| 43 / 102054 | 78c57285 | COMPLETED0:0，1:32 | 补充自然参数覆盖后的原生21运行＋4面积 |

每个目录源码source/、根job.sh/inputs.json/SHA清单、日志slurm-JOB.log、输出results/result.json。最终三项均有receipts.tar、collection.json、output-files.sha256；原始日志/网表持久保留。实际启动命令为在对应run目录执行sbatch --parsable job.sh，内层srun/singularity/argv见job.sh及result.json。102053名称mdt-s16-model，另两项mdt-s16-vector。

在已授权服务器上可复制：

```bash
cd /public/home/yuzelu/Melodydt/issue247-area-speed
squeue -j 102052,102053,102054
sacct -j 102052,102053,102054 -X   --format=JobID,JobName,State,ExitCode,Elapsed,Partition,AllocCPUS,NodeList
tail -n 30 run42/slurm-102053.log
tail -n 30 run43/slurm-102054.log
cat run42/results/result.json
cat run43/results/result.json
```

成功判据为Slurm0:0并且result.passed=true，21原生运行/4面积通过、8基线精确/32模型/160负控通过、源码输入和输出SHA相符；不以进程退出替代RTL通过。三个成功run本地209文件复核通过。没有自动监测，后续由用户再次唤起查看。

## 成果与继续执行

正式报告docs/experiments/issue-247-s16-vector-native.md，PDF docs/experiments/pdf/issue-247-s16-vector-native.pdf，下载副本外层output/pdf同名。辅助证据work/Melodydt/247/s16-vector-native；源码project/experiments/s16_vector_native和s16_vector_model；生产变更4个RTL文件。
外层work/Melodydt/247内打包/导出脚本、run38至run43载荷/回收属于本任务辅助文件，不上传原始二进制构建。除显式交付清单外不覆盖或暂存其他文件。生产源已上传，文档/PDF以PR最新commit核对；main真实状态仍是未合并本阶段。
已验证：默认三组事件精确、桥接1..8/非法/别名/尾部/reset/第二ACK、NExp全S16域合同、E独立oracle/有限流水、完整U128项、同库局部面积；本地管理结构通过。未执行：原生整图、全U综合、STA/布局布线。
建议：优先集成S16桥接，随后研究U读/执行/写重叠、FIFO/scoreboard和真实位宽供数。E核心II=1不是完整U吞吐证据，当前合法自然参数988到984拍。5.112600为条件目标，局部桥接校准prefill4.216864/4.815109。
恢复第一步：读最新Issue/PR及本交接，核对实际分支head和部署SHA；再审查NX16描述符及真实区域数值尺度。重跑要新建授权个人run目录，不能覆盖现有results。负责人Melodydt，正式审查人待指定。

## 待同步/管理限制

当前交付待审查，不done。登记management-hub PR5 pending；无board配置与Projects工具，看板unverified、同步pending，管理员待指定。CI在源码78c57285上run42841550005 failure，validate无steps/logs，原因待管理员核实，最终文档提交CI另从PR刷新。不绕过检查；旧run24/25原包上传阻塞保留。
