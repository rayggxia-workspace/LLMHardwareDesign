# openTPU ACT/MXU 同资源物理对照

关联 [Issue #15](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/15)，依赖 [PR #10](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/10)。2026-10-22 起，所有新作业均 `--time=0` 且提交后读回 `UNLIMITED`。未设置完成截止或基于耗时的取消条件。

## 对照定义

使用原 openTPU `f237dab2f196855a59a083b1454786df8f01291f` small 参数：D32、MCOLS2、ROWS2、ACT_BLOCKS32、LANES4、DEPTH64、IMPL2、CL16、E0、SID0。SRAM 仍是原 synthetic fakeram，不能用于制造签核。

从根06 ACT20/MXU20的冻结 `1_2_yosys.v` 开始，不重新跨块综合。合并组把相同两份已映射网表直接接线、展开层级，不执行逻辑优化；拆分组各自实现。共同起点 ACT3167＋MXU165942＝169109 个映射单元，包含同一套12个SRAM实例：32x128×4、32x64×2、64x72×3、64x40×1、64x96×1、64x64×1。后续物理缓冲、时钟树、驱动升级和填充另报，不能伪称终态所有单元型号／数量完全一致。

两组保持40个外部端口、1662bit、2.5ns时钟、0.5ns输入／输出预算；本轮增加统一且明确的 BUF_X4/Z 输入驱动、5fF 输出负载、50ps 时钟输入转换。拆分边界为684bit地址数据＋1bit computing反馈，无串行化、额外缓存或寄存器。实际宏模型内部周期约束不足，顶层完成后须以真实块网表和分层 SPEF 拼接 STA，不能只看父层黑盒宏时序。

正式父层对照使用同一外部 die 和逐bit固定引脚坐标，分别放置 ACT/MXU 两宏和一个合并宏；原详细 OBS 保留，以共同 M10 父层PG网接入M7供电。每个宏的实际坐标、PG端子、通孔落点与严格原生连通性单独核验。该实验是允许新增有源缓冲和M10供电资源的H1工程对照，尚不代表H2预制底座或受限掩模定制。

## 已查实的修正

1. 旧根17的89558两路均FAILED，89559仅产物审计COMPLETED。CAP_MARGIN30/40实际执行，但升级BUF的 `dont_touch` 使 InsertBufferBeforeLoads 被拒绝，报RSZ-3006。不是超时。新 `repair-01` 去掉冲突冻结，并将3个BUF升级为X4；原2.5ns/0.5ns预算不变。
2. `probe-01` 因计算节点PATH未指定Singularity而127退出；补上项目已有运行时路径后 `probe-02` 完成。保留失败目录和提交身份。
3. 第一版拼装使用了Tcl式路径引用，Yosys拒绝；改为Yosys文件引用后继续。层级展开产生的2条 `$scopeinfo` 是元数据，移除后初始物理单元库存逐型号完全相同。
4. `matched-merged-03` 的物理导入 `eliminate_dead_logic` 又删除135个单元，包括9个DFF；ACT/MXU各删除0。该结果仅为优化诊断，不进入严格同资源主表。新 `matched-merged-04` 在导入时关闭该优化，并实际核对ODB库存169109一致。关闭的是资源优化，保留网表检查和所有物理质量门槛。

## 当前实际进度

- `matched-act-02`／89641 已完成4:29：面积35985.5µm²，setup +1.25790ns，hold +0.0326128ns，setup/hold TNS0，cap/slew/fanout计数0，最差电容余量+2.540644884fF。DRC、天线及候选宏资格以冻结终态和后续审计为准，不只据进程退出判断。
- `matched-mxu-02`／89642 与固定资源 `matched-merged-04`／89647 正在执行；`matched-merged-03`保留诊断用途。
- `repair-01`／89631 已越过原阻塞并进入最终提取／报告，尚未在此写为严格通过。
- 正式两组父层布线尚未执行；运行脚本正在补齐。轻量回执在 `project/experiments/opentpu_compare/results/`；原始输出在 `yuzelu@10.129.166.172:/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-15/`。

## 恢复与验证

```powershell
python scripts/check_project.py
python project/experiments/opentpu_compare/collect.py
python project/experiments/opentpu_compare/launch.py <全新尝试名> matched --cores 16 --spec project/experiments/opentpu_compare/matched-merged.json
```

提交脚本先要求代码已提交，上传每次独立runner，记录实际commit和逐文件SHA；计算节点核对容器SHA、输入和实际资源。`collect.py`只读远端，终态首次归档后不覆盖。不得修改旧尝试或把后续commit倒填成已执行runner。原VECTOR／89448不属于本次实验，继续保留。
