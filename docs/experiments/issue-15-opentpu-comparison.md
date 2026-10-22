# openTPU ACT/MXU 同资源物理对照

关联 [Issue #15](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/15)、[草稿 PR #17](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/17)，依赖 [PR #10](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/10)。2026-10-22 起，所有新作业均 `--time=0` 且提交后读回 `UNLIMITED`。未设置完成截止或基于耗时的取消条件。

## 对照定义

使用原 openTPU `f237dab2f196855a59a083b1454786df8f01291f` small 参数：D32、MCOLS2、ROWS2、ACT_BLOCKS32、LANES4、DEPTH64、IMPL2、CL16、E0、SID0。SRAM 仍是原 synthetic fakeram，不能用于制造签核。

从根06 ACT20/MXU20的冻结 `1_2_yosys.v` 开始，不重新跨块综合。合并组把相同两份已映射网表直接接线、展开层级，不执行逻辑优化；拆分组各自实现。共同起点 ACT3167＋MXU165942＝169109 个映射单元，包含同一套12个SRAM实例：32x128×4、32x64×2、64x72×3、64x40×1、64x96×1、64x64×1。后续物理缓冲、时钟树、驱动升级和填充另报，不能伪称终态所有单元型号／数量完全一致。

两组保持40个外部端口、1662bit、2.5ns时钟、0.5ns输入／输出预算；本轮增加统一且明确的 BUF_X4/Z 输入驱动、5fF 输出负载、50ps 时钟输入转换。拆分边界为684bit地址数据＋1bit computing反馈，无串行化、额外缓存或寄存器。实际宏模型内部周期约束不足，顶层完成后须以真实块网表和分层 SPEF 拼接 STA，不能只看父层黑盒宏时序。

正式父层对照使用同一外部 die 和逐bit固定引脚坐标，分别放置 ACT/MXU 两宏和一个合并宏；块内实际限制M1–M9，为父层共同M10 PG网保留资源并接入M7供电。原详细 OBS 保留，每个宏的实际坐标、PG端子、通孔落点与严格原生连通性单独核验。该实验是允许新增有源缓冲和M10供电资源的H1工程对照，尚不代表H2预制底座或受限掩模定制。仅导出实际ODB／DEF／SPEF；没有SRAM GDS，不能报告制造版GDS完成。

## 已查实的修正

1. 旧根17的89558两路均FAILED，89559仅产物审计COMPLETED。CAP_MARGIN30/40实际执行，但升级BUF的 `dont_touch` 使 InsertBufferBeforeLoads 被拒绝，报RSZ-3006。不是超时。新 `repair-01` 去掉冲突冻结，并将3个BUF升级为X4；原2.5ns/0.5ns预算不变。
2. `probe-01` 因计算节点PATH未指定Singularity而127退出；补上项目已有运行时路径后 `probe-02` 完成。保留失败目录和提交身份。
3. 第一版拼装使用了Tcl式路径引用，Yosys拒绝；改为Yosys文件引用后继续。层级展开产生的2条 `$scopeinfo` 是元数据，移除后初始物理单元库存逐型号完全相同。
4. `matched-merged-03` 的物理导入 `eliminate_dead_logic` 又删除135个单元，包括9个DFF；ACT/MXU各删除0。该结果仅为优化诊断，不进入严格同资源主表。新 `matched-merged-04` 在导入时关闭该优化，并实际核对ODB库存169109一致。关闭的是资源优化，保留网表检查和所有物理质量门槛。
5. 原块有M10信号金属，与父层M10供电策略冲突。仅写配置、甚至传make参数均不足以清除CTS数据库保存的旧路由范围；`m9-*-01/02`因此不具备层资源资格。第三轮在实际GRT前显式执行 `set_routing_layers`，先确认日志 `Max routing layer: metal9` 再进入详细布线，终态再审查详细LEF无M10几何。取消的是已证实无效的尝试及尚未运行的依赖父层，原因不是耗时。
6. OpenROAD内部STA需要技术LEF和 `link_design -hier`。透明ACT包装的实测SPEF拼接自检已通过：setup 1.257897ns、hold 0.031897ns，相对源结果误差均小于1ps。不能将各块WNS相加当作完整路径时序。

## 当前实际进度

截至2026-10-22 17:30（Asia/Shanghai）：

- 未预留M10的对照起点 `matched-act-02`／89641、`matched-mxu-02`／89642、固定资源 `matched-merged-04`／89647 均通过严格电气、setup／hold、DRC和天线检查。`matched-merged-03`库存改变且真实电容余量为负，只保留诊断。
- `repair-01`／89631 已严格通过，独立 `repair-audit-01`／89650 核对34个复制输入与原冻结清单一致；旧修复回执中的聚合输入JSON为空，未重写旧目录，也未把独立审计冒充原运行回执。
- 正式候选ACT `m9-act-03`／89671通过：面积36109.5µm²，setup +1.27562ns，hold +0.0361168ns，最差电容余量+3.025779486fF，信号线272215µm、通孔37627，DRC／天线0；实际GRT上限M9，最终详细LEF没有M10几何。
- 正式候选 `m9-mxu-03`／89677、`m9-merged-03`／89678已严格通过；同源CTS、时钟、IO预算不变，电容修复margin30。三块终态均DRC／天线／cap／slew／fanout计数0，setup／hold TNS0，真实最差电容余量为正，实际路由M9上限且LEF无M10几何。
- 正式父层 `top-split-03`／89682、`top-merged-03`／89683已启动详细布线，实读UNLIMITED；runner为 `6e5552b2140f69ea378cb33b305dffb24d349041`。宏存储／状态库存核对及初始VDD／VSS原生连通性均通过；顶层提取后的严格门槛和完整STA尚待验证。
- 映射网表到物理修复网表的精确逻辑锥核对 `structural-m9-01`／89687 已通过：ACT612状态／存储实例、3210逻辑锥；MXU36423实例、74399锥；合并37035实例、76925锥，差异均0。归一化缓冲、反相器抵消和同功能驱动规格，逐个核对状态输入和外部输出；ACT状态输入突变负例检出。合并锥数较拆分合计少684，是内部化读数据／地址边界输出，所有状态输入仍检查。该证书只证明本轮共同映射网表到物理修复网表；上游RTL等价、真实SRAM和制造签核仍未完成。

| 正式M9候选 | 叶面积µm² | setup WNS/ns | hold WNS/ns | 最差cap余量/fF | 块内信号线/µm | 信号通孔 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ACT | 36109.5 | +1.275620 | +0.0361168 | +3.025779486 | 272215 | 37627 |
| MXU | 432496 | +0.210635 | +0.0386703 | +3.090818167 | 3013817 | 1210709 |
| 合并 | 465542 | +0.525250 | +0.0136278 | +2.119797468 | 3535985 | 1226927 |

该表是块内分解，不能据此直接判断整机拆分代价：拆分尚有685bit跨块接口的父层连线。各块WNS不能相加；完整时序须使用父层与真实子块SPEF拼接。叶面积包含同一批SRAM面积和非填充标准单元；硬宏占地另列，不能重复相加。

轻量回执在 `project/experiments/opentpu_compare/results/`；原始输出在 `yuzelu@10.129.166.172:/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-15/`。最终面积将区分叶单元面积、父层单元面积和硬宏占地，避免把宏占地与宏内单元面积重复相加。布线代价分别报告块内、父层及总信号线／通孔；PG采用几何审计单独记录。

## 恢复与验证

```powershell
python scripts/check_project.py
python project/experiments/opentpu_compare/collect.py
python project/experiments/opentpu_compare/launch.py <全新尝试名> matched --cores 16 --spec project/experiments/opentpu_compare/matched-merged.json
```

提交脚本先要求代码已提交，上传每次独立runner，记录实际commit和逐文件SHA；计算节点核对容器SHA、输入和实际资源。`collect.py`只读远端，终态首次归档后不覆盖。不得修改旧尝试或把后续commit倒填成已执行runner。原VECTOR／89448不属于本次实验，继续保留。
