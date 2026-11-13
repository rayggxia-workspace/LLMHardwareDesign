# Issue #149：E 宏 RTL 仿真流程验证

负责人 Melodydt（zenanyan，作业前缀 zny）；[任务 #149](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/149)。本任务只复用固定 E RTL 和原有测试，不修改七宏实现，不接管 #143 的物理作业。

## 已实际执行的结果

- GitHub 来源：rayggxia-workspace/LLMHardwareDesign，PR #144 固定提交 `5e787714362d957b79c2997141cf05eeebb85afc`；任务分支 `task/149-rtl-smoke`。
- 服务器代码目录：`/public/home/yuzelu/Melodydt/LLMHardwareDesign-issue149`。这是本任务独立、浅层、稀疏的 Git 工作副本，HEAD 固定为上述实验基线；78 个选定文件按原 Git blob 核验。Git 目录元数据用于正常稀疏 checkout，不读取或维护 ref-project 文件内容。
- 获取方式：本人 Melodydt GitHub 连接获取原始 Git 对象，SSH/scp 传到本人目录；物化 Git 对象时禁用网络 transport，没有使用服务器上任何其他成员的 GitHub 凭据。后续远端读取/上传继续使用本人连接；本任务没有配置服务器 GitHub CLI 认证，缺失的非稀疏对象不能假定可自动下载。
- 运行位置：Slurm Job **94188**，`zny-rtl-e`，c64/node1，分配16核，实际时间限制 UNLIMITED。
- 终态：COMPLETED，ExitCode=0:0，2026-10-31 15:01:22–15:02:07 CST，用时45秒（含容器启动、环境核验、lint、编译及运行）。
- 三组初态：(mode1,seed143)、(mode2,seed143)、(mode2,seed144)，每组107062检查、38030周期、1296个S32窄化包；合计321186检查，全部通过。seed 控制 Verilator 初态，不代表改变测试中固定143的随机数据序列。
- Verilator 5.042，Python3.10.12，GCC11.4.0；沿用现有 ORFS/Singularity 容器，镜像 SHA256=49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a。
- 登录节点直接调用 Verilator 曾出现 GLIBC 不兼容；在既有容器中实际运行成功。没有安装或修改共享工具。

## 启动方式与代码

原入口：`project/experiments/block_v2/run_rtl.py --model e --out <全新输出目录>`，由同版本 `remote_rtl.sh` 在计算节点容器中执行。本目录的 job.sh 是本次实际提交脚本；submission.json 记录精确 sbatch 命令和脚本SHA。再次运行必须换全新输出目录，并重新记录输入/脚本SHA，不直接重复提交已封存的 job.sh 路径。

服务器结果目录：

```text
/public/home/yuzelu/Melodydt/runs/issue-149/e-smoke-20261031-01/
  submission.json       实际提交命令/任务版本
  allocation.txt        实际节点、16核和UNLIMITED读回
  slurm-94188.out/.err  作业总日志
  tool-versions.log     容器内实际工具版本
  e-worker.log          Verilator工作进程日志
  e/lint.log            严格lint
  e/build.log           C++编译日志
  e/result-1-143.json   第一组结果
  e/result-2-143.json   第二组结果
  e/result-2-144.json   第三组结果
  e/receipt.json        总回执、源码SHA、三组passed
  result-summary.json  调度/结果/产物SHA摘要
  artifacts.sha256     封存轻量产物校验表
  e/obj/               编译产物，未纳入轻量证据包
```

## 在 MobaXterm 中追踪

先连接项目规定的服务器 yuzelu@10.129.166.172，然后执行：

```bash
RUN=/public/home/yuzelu/Melodydt/runs/issue-149/e-smoke-20261031-01
squeue -j 94188 -o "%.18i %.16j %.12T %.10M %R"
sacct -j 94188 --format=JobID,JobName,State,ExitCode,Elapsed,AllocCPUS,NodeList
tail -F "$RUN/slurm-94188.out" "$RUN/slurm-94188.err" "$RUN/e/build.log"
```

PENDING表示排队，RUNNING表示执行。作业结束后squeue不再显示是正常现象，用sacct查终态。tail遇文件尚未生成会等待/重试；Ctrl+C只停止查看日志，不取消仿真作业。未来新任务须替换实际job号和输出目录。

查看结果和校验：

```bash
python3 -m json.tool "$RUN/e/receipt.json"
python3 -m json.tool "$RUN/result-summary.json"
(cd "$RUN" && sha256sum -c artifacts.sha256)
```

验收同时核对主作业COMPLETED/0:0、receipt的passed=true、三组runs均passed、源码SHA/版本对应；仅看到进程结束或日志文件存在不足以认定通过。源测试没有启用波形追踪，因此本次未生成VCD/FST。

## 封存、验证与边界

原始结果/日志仍在上述个人目录。轻量包 `/public/home/yuzelu/Melodydt/runs/issue-149/e-smoke-20261031-01-evidence.tar.gz`，SHA256=`d447a183f6108b7bdbf62a1de7ca1287489b925927318fc2dcd2203fdc77d06b`，已下载本地并核验17个产物SHA和3个实际输入的上游绑定。包不含obj编译目录；仓库只提交必要轻量摘要。

现有D盘管理参考副本执行 `python -X utf8 scripts/check_project.py` PASS，不把它写成完整服务器稀疏副本上的管理检查，也不替代RTL验证。git-status.json 为服务器原生Git状态检查，返回0且输出为空。

本次仅验证E叶块功能仿真流程；没有运行R/M/N/G/S/T、综合、物理实现、宏间调度或整模型验证。physical_qualified=false。[PR150](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/150) 已上传，待独立审查/合并，不标done。

规则 rayggxia-project-collab1.0.0。登记沿用management-hub PR#5 pending；当前config无board.json且无Projects条目工具，看板unverified、同步pending；处理人待指定。服务器源HEAD仍固定在实验基线，远端任务分支后续的文档提交与该源HEAD分别记录。
