# 母控双格式物理实现与 Block 一致性

Issue #223 / PR #224，工程门已通过，独立审查待指定。先64位后128位，报告见 [双格式验收](../../../docs/experiments/mother-control-dual-format.md)，轻量证据见 [执行索引](../../../work/YUZE-LU/223/acceptance-index.json)。

固定 #180 `81663a1e6586602d2a02748db1c488d2d0ba0233` 原始 MC、消息端口、紧凑取指和 PM 源；原始字节及上游 SHA 见 `project/rtl/mother_control_v1/upstream-lock.json`，不修改原 ISA。绑定原生 ABI `0x01930001`。两个驻留目标、八 token、每端单在途，不宣称九局控或完整 ISA。

`mother_control_64` 包含母控和独立16KiB真实四-bank程序SRAM；不将它算作Block私有S，复位不清SRAM。硬件按镜像版本选择 v2/64位或v1/128位指令，PM口均128位。两格式共用同一组未改六文件，物理cell名仍为 `mother_control_64`；128位另行验证对应局控和程序。

已接收候选1104×768µm，Nangate45原生M1–M10、TT1.1V/25°C、300MHz。setup/hold +374.917/+7.629ps，原版完整GDS DRC0，原Liberty电气、完整RC、PG、SRAM周期/脉宽、所有端点检查通过。2446个2µm原生M10接点，六排、6.4µm间距；只证明实际GDS铜存在，不含全位M11/M12逃逸。I/O max/min0.5/0.05ns，输入转换0.05ns，输出5fF，setup/hold uncertainty0.05/0.02ns；无false/multicycle/case约束。ORFS读回周期3.3333ns略严格，不能降频过验。

## 实际控制覆盖

两格式各54项RTL、54项母控最终网表、69项真实Block/LC RTL组合。包括P、C/F G/E、J、C的R状态/五场景往返、U五场景往返、CF双向以及U双向/三源FMA双向。三种初始化/种子组合，不回标SDF，提取STA独立判定。

P/U保留#195派生局控，64位使用其紧凑取指适配；CFJ64使用逐文件锁定的#180原紧凑源，CFJ128保留原生旧profile。U绑定#221硬件提交 `17ba807d69dda5415b34e531af016ab47b8e17b0` 的31文件锁，未替换对方源码。C往返用#195参考U，U往返用#195参考C；不宣称最新C与最新U的完整联合产品通过。

组合中的母控是最终物理网表，Block/LC是RTL，私有S是真实SRAM模型；局控PM仍为外部行为夹具。因此不是全系统最终门级、联合P&R或完整ISA资格。联合顶层需重新核对ID、负载、时钟、接入与实际布线。

## 运行入口

所有EDA在获授权Slurm计算任务中执行，c64/c96共享节点；P&R/ECO每项10核、回归4核、完整审计6核、封包2核。新目录重跑，不覆盖候选或终止其他人的作业。

```bash
# SOURCE含project子树、锁定control180 / control180-cfj64和u221参考。
# P&R入口需数组0–1及已核对银行视图；每项10核。
bash SOURCE/project/experiments/mother_control_v1/physical.sh NEW_PHYSICAL SOURCE
bash SOURCE/project/experiments/mother_control_v1/regression.sh NEW_RTL SOURCE 64
bash SOURCE/project/experiments/mother_control_v1/audit.sh NEW_AUDIT SOURCE CANDIDATE full
bash SOURCE/project/experiments/mother_control_v1/gate.sh NEW_GATE SOURCE CANDIDATE 64
# KIND: P/U/C/F/J/C-roundtrip/CF-duplex/U-duplex/U-fma-duplex。
bash SOURCE/project/experiments/mother_control_v1/consistency.sh NEW_BIND SOURCE AUDIT_JSON GATE_JSON CELLS_SV KIND 64
# 必须先有完整合格64位清单；验证完全相同六文件的128位profile。
bash SOURCE/project/experiments/mother_control_v1/regression.sh NEW_RTL128 SOURCE 128
bash SOURCE/project/experiments/mother_control_v1/gate.sh NEW_GATE128 SOURCE CANDIDATE 128 QUALIFIED64_MANIFEST
bash SOURCE/project/experiments/mother_control_v1/consistency.sh NEW_BIND128 SOURCE AUDIT_JSON GATE128_JSON CELLS_SV KIND 128
```

真实银行generation路径及版本固定在执行源。只有输入RTL散列完全相同时才可显式复用映射。`audit.sh ... preflight`不赋予物理资格；`full`必须跑未改原版完整规则。先读标准单元fF库、后读银行pF库，并强制核对UI单位，保留原上限及负裕量拒绝。

实际候选通过临时bank-front放置保留、真实接收器位置锁定以及单根M10主干ECO修复；全部临时保留/避让均移除。`eco_m10.py`仅适用于锁定的原候选，逐项比较所有其他网、实例和原下层线路，并在新目录重新提取。`reroute_guarded.py`保留重布尝试工具；它产生候选而非资格。构建`inputs.json`的`qualified=false`是当时生成状态，最终资格来源为独立`audit.json`及程序回执，不回写历史记录。

fresh报告14项同网标记原样保留，不能称路线报告0。`native_marker_shapes.tcl`及`native_marker_gds.py`逐项证明整区被同一原网的真实ODB线段与实际GDS铜完全覆盖。多网/缺线/其他规则拒绝；缺任一侧证据的反向控制亦拒绝。完整原版GDS规则必须另外0项，不作waiver。失败的补线/DEF导入原型及日志保留在远端，不计入验收。

`package64.py`默认封装64位，`--instruction-bits 128`要求先前64位清单、本地回收回执及128位RTL结果。实际封包源自身入包并校验，运行期间不修改。`verify64.py ARCHIVE SHA256 --receipt NEW_JSON`自动识别格式，流式核对全部文件、六文件、原规则、完整DRC、程序版本及实际日志，不解包执行归档内容。64/128包分别3860/3148文件，本地均已通过。归档、源SHA和复核入口见正式报告；Issue待审，不自合并。
