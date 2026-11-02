# A8服务器Verilator执行与验证回执

本次只接受固定8key/D8 QK–Softmax–PV切片的下列功能证据，完整A/F/L4、模型质量、MEM与物理未接受。新源运行时尚未提交，以逐文件SHA/快照绑定；交付commit必须与PR读回的新RTL/TB/脚本SHA核对，不把parent1d72247当作已含A8。

## 环境与真实执行

- 登录：用户提供可信服务器公钥后，以电脑既有SSH身份登录yuzelu；未读取/复制私钥或密码，不依赖MobaXterm窗口，不新增远程认证。
- 本人任务根：`/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/a8-1d72247-20261102`；源码input-r01..r04、编译/日志/results在runs/对应子目录，Slurm日志在slurm；所有主要输出均在本人目录。软件和容器只读复用，未安装软件。
- 实际计算节点入口：`/public/software/singularity-ce-4.3.4/bin/singularity`，不是仅登录节点可见的`/usr/bin/singularity`。
- Verilator5.042 2025-11-02 rev UNKNOWN.REV；C++ Ubuntu11.4.0；GNU Make4.3；容器Python3.10.12。版本未知rev如实保留，wrapper及18,824,040B核心二进制前后SHA相同，完整指纹见run receipt。
- 容器：orfs-26Q1-repacked.sif，1,522,868,224B，SHA256 c742bf99ea498fb4da5135bc83fd1677abcebe0e64470e6a115f2baecb3905df；镜像SHA在Slurm allocation中计算。
- Job95116：zenanyan-a8-all，c64/node1，单task8CPU/30分钟上限；顺序三suite，build-jobs8、simulation threads1，真实Elapsed00:01:51/COMPLETED/0:0。没有操作其他成员作业。

| 尝试 | 真实结果 | 处置 |
| --- | --- | --- |
| r01 /95111 | FAILED127，1秒，计算节点缺/usr/bin/singularity；未compile/sim | 保留脚本/Slurm日志，查本人旧E实验实际shared入口 |
| env-compute-02 /95112 | COMPLETED0，探测计算节点；direct Verilator有glibc不兼容、默认GCC8.5 | 仅环境探测，不计RTL功能通过；改用既有shared容器入口 |
| r02 /95114 | FAILED1，7秒，手设VERILATOR_ROOT与实际安装布局不一致；未compile/sim | 保留receipt，取消手设ROOT；HOME改明确挂载本人bootstrap |
| r03 /95115 | 工具版本0，build-n exit1，由33条warning默认fatal中断；未sim | 全部警告保留审阅，不改叶宏/TB消警；功能测试显式-Wno-fatal |
| r04 /95116 | 三次compile和三次simulate均exit0，80项完整CASE+PASS | authoritative功能证据；仍不是lint clean |

## 最终结果

| 测试 | 独立声明的CASE数 | 周期 | 结论 |
| --- | --- | --- | --- |
| N单组RMS/L2/Softmax服务 | 29 | 20336 | 与既有完整CASE集合一致；服务器Verilator通过 |
| RMS-preNorm F8回归 | 25 | 16323 | 旧RTL/TB字节不变；force/时序在本次工具实际可运行 |
| A8 QK–Softmax–PV | 26 | 9687 | 8组独立数值输入、逐score/EXP/prob/output以及故障/背压/恢复通过 |

CASE集合来自运行前冻结合同；不能从本次日志反推期望集合。runner要求exit0、唯一终结PASS及cases计数、全部CASE无缺失/新增/重复、无FAIL/Fatal，再判通过。原生N15/QK EXEC/PV EXEC错误注入、等待prob ACK等检查均保留。Verilator为两态/事件实现的有限证据，不代替四态/形式或全活性验证。

成功正常帧S23req/23ACK=19W4R、M10cmd/rsp、N6cmd/rsp、2loader、T1take+RELEASE。A8全测试总S741req/738ACK及M302cmd/301rsp包含故意reset/abort的在途差额，不能宣称跨reset全局无条件守恒；正常帧逐项守恒由TB核对，差额见交叉审阅。输出已消费前缀不支持回滚。

警告保留：N33（TIMESCALEMOD18/WIDTHEXPAND13/WIDTHTRUNC2），F829（18/8/3），A836（18/16/2）。没有禁用任何warning类别，-Wno-fatal仅允许功能执行；日志原字节、每类计数与源码审阅归档，未作为lint/PPA门通过。不得因80项通过扩大原生R资格或任何真实模型质量结论。

## 文件与复现

[执行索引](../work/Melodydt/151/a8-execution-index.json)记录固定源、归档文件/下载SHA、作业和工具配置；[最终原始receipt](../work/Melodydt/151/a8-rtl-evidence/runs/r04/results/run-receipt.json)记录完整命令和源码快照。全部55份下载文本已逐SHA与大小校验，原始日志不清理空白。编译目录/二进制留服务器，未开trace，没有生成波形，不捏造波形路径。

重新执行必须使用新的本人run/input目录，先逐SHA绑定源文件，再生成sbatch并提交；具体命令见ARCHITECTURE的A8章节。无需重跑已通过的同源RTL来验证文档修改。本次独立Python参考、结构检查和静态复核单列，不替代服务器RTL。
