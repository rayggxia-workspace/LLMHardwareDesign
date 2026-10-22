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
7. 原父层03／04轮因导出的引脚命令显示M5／M6差异，被操作者误判为实际几何不一致而停止。随后 `pin-checkpoint-old-01`／89705直接读取旧CTS ODB，证明两组原本均为M2／M3、实际完整几何完全一致；`write_pin_placement`使用了旧IO放置器缓存，不能作为实际数据库证据。该停止是分析误判，与耗时无关；原始取消回执不改写，更正在 `correct-cached-pin-export-diagnosis.json`。新05轮从同样的实际引脚几何继续，改为完成CTS后直接导出ODB盒形、层号，并强制两组1662bit的几何哈希相同后才进入布线；BPin重建已执行但未改变最终几何。

## 当前实际进度

截至2026-10-22 18:20（Asia/Shanghai）：

- 未预留M10的对照起点 `matched-act-02`／89641、`matched-mxu-02`／89642、固定资源 `matched-merged-04`／89647 均通过严格电气、setup／hold、DRC和天线检查。`matched-merged-03`库存改变且真实电容余量为负，只保留诊断。
- `repair-01`／89631 已严格通过，独立 `repair-audit-01`／89650 核对34个复制输入与原冻结清单一致；旧修复回执中的聚合输入JSON为空，未重写旧目录，也未把独立审计冒充原运行回执。
- 正式候选ACT `m9-act-03`／89671通过：面积36109.5µm²，setup +1.27562ns，hold +0.0361168ns，最差电容余量+3.025779486fF，信号线272215µm、通孔37627，DRC／天线0；实际GRT上限M9，最终详细LEF没有M10几何。
- 正式候选 `m9-mxu-03`／89677、`m9-merged-03`／89678已严格通过；同源CTS、时钟、IO预算不变，电容修复margin30。三块终态均DRC／天线／cap／slew／fanout计数0，setup／hold TNS0，真实最差电容余量为正，实际路由M9上限且LEF无M10几何。
- 原父层03及追加电气修复04轮因上述缓存误判被停止，未完成最终布线，保留诊断证据及更正。此前GRT约-46ps setup和残余电气违例仍是估计结果，不能当作完整提取结论。
- `top-split-place-05`／89700、`top-merged-place-05`／89701已完成布局与CTS，PG通过，实际引脚M3×832／M2×830，逐bit完整几何哈希均为 `8c1e5da591ece5cefdd142408f1431bc5c82cb1fb91ebd075d1f3f4dfb19cdb7`。原03 ODB也有同一哈希。05父层补充标准电气修复后，合法化／重布线使新增弱缓冲重新过载，真实余量门槛使两组在DRT前失败；不以cap计数0代替实际余量。
- 06轮基于真实GRT负余量，定向升级BUF／INV驱动并逐轮合法化、增量重布线。`top-merged-06`／89711完成10次升级后通过电气门槛，正在详细布线；`top-split-06`／89710完成25次升级后，剩余违例集中于冻结宏输出，最差 `u_mxu/t_waddr[105]` 电容余量−17.890644fF，故停止在GRT并保留诊断。
- `top-split-07`／89722从同一封存CTS继续，在真实负电容余量的宏输出最近边缘外约2µm处插入BUF_X2，隔离长父层网络；保持子块网表、端口、状态和SRAM不变，新增缓冲计入物理开销。API探针89721已确认实际插入及位置，正式轮仍需路由后重新验收，不能把插入成功当作违例收敛。所有新轮UNLIMITED，完整提取、PG终态和分层STA仍未完成。
- 18:23后拆分07已插入16个宏输出近端BUF，通过GRT电气门槛并进入DRT。合并06也继续DRT。`stitch-selftest-05`／89731进一步核对父／子共享边界RC：缓冲＋DFF受控网络的分层SPEF与手工显式拼接的平坦RC参考，setup／hold分别为2.255283594／0.190321565ns，两者在报告精度内完全一致；故意漏掉父层RC的负例变化31.129837ps，并出现3个部分未标注驱动。该自检补充透明包装测试，不能替代实际大网表的标注覆盖检查。
- 映射网表到物理修复网表的精确逻辑锥核对 `structural-m9-01`／89687 已通过：ACT612状态／存储实例、3210逻辑锥；MXU36423实例、74399锥；合并37035实例、76925锥，差异均0。归一化缓冲、反相器抵消和同功能驱动规格，逐个核对状态输入和外部输出；ACT状态输入突变负例检出。合并锥数较拆分合计少684，是内部化读数据／地址边界输出，所有状态输入仍检查。该证书只证明本轮共同映射网表到物理修复网表；上游RTL等价、真实SRAM和制造签核仍未完成。
- `inventory-m9-02`／89733对上述封存证明中的映射／终态网表逐型号族复核：除BUF／INV／CLKBUF、常量tie和填充／tap支持单元外，全部计算逻辑、状态和SRAM数量保持一致，拆分两块合计与合并块也一致。物理新增tie为拆分LOGIC1×550、LOGIC0×67，合并也为550／67；支持单元完整数量单列，没有当作计算资源或从总面积中扣除。

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

父层现采用两阶段：`top-*-place-m9-05.json`只运行到CTS并核验实际引脚；`top-*-route-m9-05.json`指定本组检查点与另一组参考，验证封存SHA和共同几何后继续GRT／DRT。后续电气调整可从同一封存CTS开始，使用全新尝试目录，避免重做或改写已核对的布局。`compare.py`仅接受五份严格物理终态以及三块、两父层的功能证书；未全部通过不会输出完整PPA对照。

`stitch-selftest.json`运行共享边界RC的独立自检；比较还要求该证书通过。采集器对轻量指标、资格、STA及功能证据逐个验证其SHA属于封存输出清单；最终1662bit的实际BPin盒形还必须与共同CTS起点完全相同。五份外部SDC除设计名称外的规范文本SHA均为 `b08d83cc225c1753aee3027d6c97e296bc25d4cf9d5cdd7ffd0b4efc6694f044`。

提交脚本先要求代码已提交，上传每次独立runner，记录实际commit和逐文件SHA；计算节点核对容器SHA、输入和实际资源。`collect.py`只读远端，终态首次归档后不覆盖。不得修改旧尝试或把后续commit倒填成已执行runner。原VECTOR／89448不属于本次实验，继续保留。

## 19:12 后的收敛诊断（仍在执行）

合并父层06／89711已完成真实DRT，迭代违例4796→263→168→16→5→5→0，最终DRC／天线为0，父层信号线2660913µm、通孔62185。原生PG终态通过；提取后宏模型setup −0.0784699ns，真实分层STA setup −0.053027ns、hold +0.013229ns、TNS −0.063750ns，且电容余量仍负，故严格失败，不能纳入合格PPA。最差输出t_waddr[25]的末级BUF_X4驱动较长父层连线，需继续改善驱动／缓冲。拆分07／89722仍在DRT，未按耗时停止。

89750对合并06完整分层STA的40846个未标注驱动逐一用本机原生get_fanout（flat、all arcs、pin depth 2）核对：全部可解析且无连接负载，部分未标注驱动0；连接时钟正控制通过。说明这批未标注提示属于空载端，不能抵消实际时序／电容失败。正式选择的新父层仍须重新审计。

08／09两组尝试均在新增联合修复时出现EST-0104，不进入正式DRT；保留全部失败。依据[官方估算器实现](https://raw.githubusercontent.com/The-OpenROAD-Project/OpenROAD/master/src/est/src/EstimateParasitics.cpp)推断手工ECO回调留下待更新队列，完整estimate本身不清队列；官方master不是当前未知版本二进制的精确来源，故以实际下一轮验证为准。新的joint_repair.py改为真实ODB检查点和独立进程交替：重新全局布线／估算RC，原生setup／hold修复，再独立进程电气增驱和宏输出近端隔离，最后新进程独立审计。保留全部中间检查点，不清空错误队列，不跳过真实检查，外部SDC不变。流程尚待计算节点验证，不能预称收敛。
