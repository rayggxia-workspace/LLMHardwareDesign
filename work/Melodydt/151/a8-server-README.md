# A8服务器Verilator运行准备

Issue151，研究父提交`1d722477564e14f7dc93e39ce8e28b8e2d150cb0`，native源锁`707878621b2add4ed218b8c43df2e95c9a56e2ba`。本目录保存初版脚本/合同、历史备选及纯Python检查；作者未执行本地RTL仿真、SSH修改或sbatch。主任务维护当前`integrated/work/Melodydt/151/`正式脚本、实际上传和服务器作业。本目录旧脚本不覆盖已归档字节，不能替代当前正式副本；当前只读核验见`server-final-static-checks.json`和`server-final-review.md`。

## 当前冻结交付

- `run_a8_verilator.py`：在一个Slurm task内依次编译/运行selected suite；全部source/build/tmp/log/results限制`/public/home/yuzelu/Melodydt/`。
- `prepare_a8_sbatch.py`：只生成作业脚本，不提交。`--name-initials`必填；本任务用户已确认`zenanyan`，不从GitHub handle猜姓名。debug最多30分钟。
- `a8-verilator-baseline-contract.json`：保留原N29/F8 25完整集合、原生14份源及旧helper/W3/W4字节锁；CASE来自已留存完整旧回执，不是现场从候选TB推导。
- `a8-verilator-profile-contract.json`：绑定独立`work/Melodydt/151/a8-tb-contract.json`的SHA、top/TB SHA和26项完整CASE；绑定新RTL与数值参考。实际运行再核对独立合同，不能删故障用例绕过兼容问题。
- `zenanyan-a8-all-c64-01..03.sbatch`：旧准备稿，仅作历史输入保留；实际作业使用主任务为每个新run生成的独立submit脚本，不能重新提交旧准备稿冒充当前配置。
- `server-runner-static-checks.json`：纯Python准备检查，三份TB共80项声明、源/独立合同匹配、24个合成日志解析正反例。没有调用HDL工具。

## 容器执行与资源

主任务的真实compute预检证明node1直接启动opt下Verilator5.042缺所需glibc，host g++8.5；不能把mgt01登录节点工具路径转移为compute事实。compute可用runtime为`/public/software/singularity-ce-4.3.4/bin/singularity`，而非旧默认`/usr/bin/singularity`。生成实际作业时必须显式`--container-runtime /public/software/singularity-ce-4.3.4/bin/singularity`。现有`/public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif`提供容器g++11.4.0/Python3.10.12，正式job仍重新核对实际tool version/SHA。

当前正式作业脚本用`exec --cleanenv --no-home`及`--home "$TASK_BOOTSTRAP_DIR/home"`启动整个Python runner，禁止用Singularity不接受的`--env HOME=...`覆盖方式。所有version、Verilation/C++构建和模拟均在同一容器；个人目录rw、opt目录ro，host/runtime cache/tmp及container home均在个人bootstrap内，宿主HOME变量不改。镜像约1.5GB的SHA只在Slurm分配内计算。无安装、无系统PATH修改、不读license/凭据。

不要手设`VERILATOR_ROOT`为安装prefix。Verilator wrapper按自身实际安装位置和安装时配置的pkgdatadir相对路径计算ROOT；错误的手设值会直接被一致性检查拒绝，见[官方wrapper实现](https://github.com/verilator/verilator/blob/master/bin/verilator)。实际r02同一wrapper在手设prefix时version退出1；r03不设该变量后version退出0并进入N编译。正式preparer和make_job已移除该required参数及env注入，不采用旧示例。wrapper/核心二进制指纹及前后检查与镜像指纹一起记录。

runner要求真实`SLURM_JOB_ID`、单task、job-name以必填姓名缩写开头，`-j`不超过实际`SLURM_CPUS_PER_TASK`和CPU affinity。模拟固定`--threads 1`，各suite顺序执行；没有无界并发。CLI还记录声明node class及wall time，debug不得超过30分钟，并预留30秒保存回执；调度节点/分区归属仍由主任务根据实际Slurm状态核验。build超时默认1200秒、模拟每suite180秒，若触发保留实际退出/终止记录，不能当作功能通过。

## 复现入口

服务器checkout、脚本、合同、运行目录父目录和Slurm日志目录须先在本人目录准备好，再提交。生成器不会创建远程目录或提交作业。`--root`须为含正式RTL/TB/reference的checkout；`--output`必须新建或空目录，不复写任何旧尝试。脚本中的示例目标为：

```text
/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/a8-1d72247-20261102/
  integrated/                 # 正式输入副本
  server/                     # 两脚本和两合同、独立sbatch脚本
  runs/all-r01/               # runner创建；已有结果则换新编号
  logs/                       # sbatch前必须已存在
```

实际作业由当前正式preparer写完整绝对路径、full source ref、shared runtime位置和明确的资源配置。提交前读回内容并核验实际队列；主任务按REMOTE_RULES/AGENTS即时报告job ID、node或待分配、源码、命令、日志与结果目录及squeue/sacct/tail命令。r01的runtime路径127退出、r02的ROOT不一致、r03的warning默认fatal均保留为独立尝试；它们不产生RTL功能通过结论。

runner支持`--suite n`、`f8`、`a8`、`regression`（N+F8）和`all`（N+F8+A8）。`a8/all`缺独立冻结A8合同即拒绝，不能悄悄只运行旧54例。全部命令使用结构化argv，无`eval`或来源文本shell拼接；job生成器只对明确参数做shell quoting。

## 成功判据与保留输出

实际命令为`verilator --binary --timing --assert --threads 1 -j <allocated> --top-module <TB> --Mdir <owned-build> -o <TB> ...`，每suite单独构建。官方说明`--binary`提供timing可执行模拟器，构建仍需C++工具链，见[参数说明](https://verilator.org/guide/latest/exe_verilator.html)。默认warning fatal；正式runner现在提供显式`--nonfatal-warnings` opt-in，仅追加`-Wno-fatal`，保留全部warning原日志、类别计数和完整header，回执标注`lint_clean_claim=false`。这允许在已审阅warning下执行功能测试，不代表lint clean。无`Wno-width`、`bbox-unsup`、`no-assert`、`no-timing`或faultcase过滤；首次默认fatal失败和后续新run均须保留。

每suite同时要求进程exit0、精确终结PASS一次、`cases=`等于声明数、完整CASE集合无遗漏/新增/重复、无FAIL/Fatal/Error文本。解析兼容纯Verilator输出和旧ModelSim可选`# `前缀；合成日志验证包括非零退出、缺case、重复case、未知case、显式FAIL和伪summary六种拒绝情况。

`results/run-receipt.json`保存base commit及新源快照指纹、独立CASE合同、工具/二进制/容器SHA、实际argv/cwd/资源、阶段退出码、日志SHA、完整观察CASE和失败原因。输入快照、build可执行文件、日志及失败结果均留在本次目录；不上传大量build工件可由主任务另按项目交付索引处理。已接受RAM写/外部输出和reset/abort造成的在途丢弃由TB实际语义解释，不能仅用全程累计计数宣布守恒。

## 兼容性风险与验收边界

N TB使用显式gate背压；F8和A8还对恒定permit、native opcode等进行层级force/release，并直接预填S RAM。当前官方指南描述了force/release支持及部分语义限制；服务器5.042早于当前指南，不能从文档推断其所有条件force、重复force或release调度与ModelSim等价。见[Verilator语言支持说明](https://verilator.org/guide/latest/languages.html)。必须保留所有fault、reset和反压CASE实际编译/运行；不支持时记为工具兼容阻塞，再由主任务审查等价TB驱动方案，不能删case或修改native来求通过。

24项日志解析检查只验证Python判据，管理结构PASS只验证管理文件；80项是期望分母，尚无本作者执行的Verilator通过。正式通过也仅覆盖声明的A8单query/8key/D8 QK→Softmax→PV和N/F8回归；不是完整Attention、主线四整体、主线五、完整模型、MEM或PPA验收。
