# R2 原生 U stateless relative EXP：测试与测量

Issue247 / PR243；2026-11-10。正式建议目录 `project/experiments/rtl_iterations/round2`。本目录是独立实验，不修改冻结R1。RTL由 `iterations-research/feed/round2` 提供，测试/runner由本目录提供。未在本机执行EDA；当前只有Python AST、准备生成和既有日志parser检查，真实周期待父代理Slurm运行。

正式目录需同时放：feed/round2的四个flat候选、`baseline/`四源与source.json、把其generate.py改名`generate_rtl.py`；再放本目录明确文件。不要上传本地`preview/`或`__pycache__/`。服务只编译实际 `project/rtl/...` 四个已集成候选，generator严格要求其逐字节等于冻结patch；R1对照独立使用baseline/四份旧源。旧bench直接取run16生成原件，四SHA在prepare.py硬锁。

运行目录：

```text
RUN/source/               # 已上传且源码SHA核验的Git快照
RUN/inputs.json           # source_commit / code_sha256 / input_sha256
RUN/source-files.sha256
RUN/input-files.sha256
RUN/run16-result.json     # 原始R1 actual RTL回执
RUN/job.sh
RUN/results/              # 不得预先存在
```

run16输入SHA固定 `78c57febe43f2a114a8a21ca9b5992b465d7b7589f05c83eb68e5f97923d4ef7`。外部真实bank SHA固定 `6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7`。其路径沿用R1；Verilator固定repro02路径、实际版本及GCC/Python/container SHA留回执。server入口：

```sh
python3 -B source/project/experiments/rtl_iterations/round2/run.py --root "$RUN"
```

父代理使用`job.sh`提交，mdt任务名、c64/c96、单task4核、time0；runner拒绝非Slurm/超4核，各variant顺序编译且-j不超过实际分配。不得在登录节点或Windows启动EDA。

## 测试和公平对照

13个build，各三种原初始化配置1:143、2:143、2:144：

- R1 legacy对R2默认0：完整COMPAT命令、S、回应与绝对周期相同。
- R1 BATCH1对R2 BATCH1/DIRECT0：完整COMPAT相同；DIRECT1的普通N命令逐事务元数据/接受到完成间隔/结果相同。
- R1四命令compute/fullU、R2 DIRECT0 compute/fullU、R2 DIRECT1 compute/fullU：前两者完整带时间的SRAM事件、计时行、功能计数相同；baseline费用另外精确重现run16。
- compute继承R1原scalar五命令oracle，穷举全部65536个S16值；NX32覆盖INT32极值/随机、各count、零padding、错误、背压和reset。reference N仅存在于testbench，不是新生产资源。
- fullU继承NX32真实读S/执行/写ACK后逐字读回、错误目的哨兵不变、描述符S前拒绝、真实IO占S阻塞到写请求再hold6拍、reset等。DIRECT1另在不夹入golden scalar的snapshot之间测试normal统计保持；DIRECT0原clobber例原样保留。
- `stateless`单native N：4096位快照覆盖统计、factor、exp计数、replay游标、top数组及持久控制；在无context、softmax部分/完整统计、部分exp、factor、部分/完整replay、RMS、top加载及选择后插op12，之后继续原合法程序。非法count/param/aux/padding保持状态；12个reset时点覆盖运行和held response。
- `group_gate`的四个U实例仅为参数组合testbench，验证只有BATCH1/DIRECT1允许新native op12。生产每U仍一个N、原两EXP lane与同一LUT，无新SRAM/乘法器/EXP表。

新bench打印实际native请求计数 `NEXP_NATIVE_PATH`，DIRECT1 compute必须op12_commands>0且other_commands=0；fullU因scalar准备存在普通指令，但必须实际出现op12。不能只凭profile mode标签把R1费用充作R2。DIRECT0也输出marker，要求op12_commands=0。

## profile 接口

保留R1 fields：`commands/runs/measurements.compute_s32/full_U`，每项绑定实际exit0命令、log SHA、初始化mode/seed；active measurement和run新增direct_mode=1，run.native_path保存上述原始日志字段。

profile的scope/payload边界与R1相同，新增：

```text
implementation = native_stateless_relative_exp_op12
row.mode = legacy_s32_low16_zeroextend_stateless_op12
gates.stateless_context_preservation = true
gates.old_batch_compatibility = true
```

其余六个R1 gates继续必需。stateless gate绑定`runs[label=stateless].checks`，含cases>=10/checks>0/reset_cases=12；old_batch gate绑定三个disabled labels、三个seed的exact_old_batch_match=true。

费用从三个seed一致的NX32 count1..4实际 `accepted_to_next_accept_cycles` 生成。count5..8按`[4,count-4]`加和，完整U读算写费用分开记录；全部计时在done首次出现时结束，后续人为hold不进headline。没有预填任何预计费用。

NX32仍是signed low16提取、U16零扩至S32的既有别名合同，不是无损S32转换。模型只替换原NExp额外补充compute服务，原vector_region E/S/cache/DDR保持，S16输入fallback原费用。每block S保持16KiB；旧体系300MHz条件频率不是本RTL STA资格。相同native数值、功能/周期、完整LLM、量化质量及物理资格分别报告。

## 源码清单

本目录11个明确文件：`prepare.py,run.py,job.sh,README.md,delivery.json`，两个`tb_nexp_*.sv`新bench，四个`r1_tb_*.sv`冻结bench。生成/EDA输出全部写RUN/results。最终delivery.json保存本目录除自身外文件SHA；RTL源由feed交付清单另锁。最终服务器输入/输出SHA及源码commit由父代理回收与发布。
