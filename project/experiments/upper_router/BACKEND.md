# 实际后端接入与产品输入边界

任务 [#230](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/230)，叠加
#227/#229。实现参数化通用物理EDA；首个输入为 main 五类 `_64` 独立叶宏＋局控的九组资源，前置 #220；
不使用 #206 的旧组合硬块替代该对象。`_64` 是指令宽度，不改变数据端口宽度。

2026-11-09，九组690条实际晚接网的完整工程门及便携包回放已通过，
见[交付与复跑说明](../../../work/YUZE-LU/230/HANDOFF.md)。该资格不扩展到未执行的整模型/控制程序。

## 已实现的入口

- `stage_package.py ARCHIVE SHA256 DEST`：原包只读，解包到新任务目录并核对清单。
- `native_inventory.tcl` 从实际 ODB 导出端口、层/矩形、原生网、真实驱动/负载、
  独立宏与标准单元。`native_inventory.py --tsv TSV PACKAGE OUTPUT` 转成机器索引。
  不把独立夹具 BTerm 自动升级为九组产品的全局端点。
- `backend.py SPEC ROUTES NEW_OUTPUT --dbu-per-micron 2000 --via-resistance-ohm 0.08`：
  对已完成路线重新检查后生成 `upper.def`、`upper-vias.lef`、`bindings.json`。
  DEF 使用生成的安全名称，原始逻辑网络、driver/sink 与绑定指纹保存在 identity map。
  合并共线重叠段；保留每一条分支和通孔；部分路线、过期输入或单位不一致直接拒绝。
  通孔电阻显式输入；不是 RC 提取结果。
- `ingest.tcl` 以真实研究技术 LEF 读入 DEF，核对层宽，生成 `upper.odb`、读回 DEF
  和 OpenDB 实际矩形。该 ODB 是上层互联视图，没有虚构的功能宏或控制标准单元。
- `physical_readback.py` 用 KLayout 将**实际 OpenDB 矩形**写入 GDS，逐网/逐层对照
  所需几何；重新读回，检查宽度、间距、切孔、包围、跨网短接和真实原生 M10 覆盖。
  与源 GDS 合成后再核对上层，并对全部原生层做几何 XOR。
  ODB/GDS 可以采用不同精确单位，不能通过坐标取整掩盖不匹配。
- `native_drc.sbatch` 对合成 GDS 运行原版完整 FreePDK45 规则，固定规则 SHA。
  原版规则只覆盖原生层；M11/M12 几何另按声明的研究规则核验。

以上单步导出仍然 `physical_qualified=false`；最终装配由`qualify.py`逐项核验后授予声明范围资格。互联视图不是已经 stitch 的产品 ODB；
几何通过不会自动产生原生网表绑定、分布 RC、Liberty 电气或 300MHz 时序资格。

## 真实接口回归及资源

`fixture_case.py` 从合格包的连接合同和本轮 ODB 索引建立回归输入，算法不读模型名。
五类分别包含 P 34、U 130、C 34、F 34、J 130 条真实晚接信号，共362条；
这不是 #220 整网需求，也不是九组联合布局。沿用真实 pin 的8µm格点子集，
保持2µm线宽、2µm金属间距和2.2µm切孔间距；没有放宽4µm轨距以满足大通孔。
不同的候选底座若没有该格点接入，仍可能需要更一般的局部逃逸算法，不能宣布无解。

服务器入口 `inventory.sbatch`、`inventory_resume.sbatch`、`fixture.sbatch`、
`product_audit.sbatch` 和 `native_drc.sbatch`。每项10核、数组最多6项；依赖阶段不
重叠超过60核。所有工作在 Issue230 独立目录；源包、失败候选和日志分别保留。
集群 Slurm 的每节点 memory 字段登记为1MB，不能提交60GB内存声明；使用其默认策略，
不独占CPU节点。不存在的 OpenROAD Python API 已改用已验证的 Tcl 接口。

## #220 输入与通用物理后端（范围纠正）

用户明确：底座/资源库是工具输入；不能将“先有已验收九组产品”当作开发布线的前置。
#220 `full_plan.py::replicated_inventory()` 已提供九组资源，实际IR和计划均有版本/SHA。
九组不是算法常量。此前把控制PM、九目标母控和实际gateway开发列为本任务先决条件的
判断撤回；完整系统RTL资格仍可独立核对，但不阻止开发、运行通用路由EDA。

新增入口：

- `resource_library.py INPUTS INVENTORIES PACKAGES OUTPUT`：登记并校验实际物理视图。
- `resource_base.py IR_OR_HARDWARE LIBRARY NEW_BASE --gap-dbu N --alignment-dbu N`：
  从leaf_inventory匹配资源能力，生成共同候选放置、独立叶宏身份和实际M10端点坐标。
  源视图组合及平移显式记录；不伪造合并ODB，也不把控制组变成硬宏/上层禁布矩形。
  当前保留源视图的局部预连几何，采用对齐的shelf初始布局；不是自由移动已有预连内的叶宏。
- `flow.py IR PLAN LIBRARY RULES NEW_OUTPUT --gap-dbu N --via-resistance-ohm R`：
  运行原独立计划检查、资源装配、库合同展开、逐位绑定、通用路由与DEF/通孔LEF导出。
  接口定义从资源库capabilities.interfaces中的`{group}`模板展开，或显式`--catalog`输入；
  缺项保存具体需求诊断，搜索失败保存反馈，均不导出伪完成几何。

实际#220九组IR已装配得到9组/28独立叶宏/1380个M10端点（100559）。这证明资源输入接入，
不是完整18逻辑束物理闭合。资源接口描述的降低、实际公共几何和电气验收继续由后端推进。

## 物理接口描述的当前状态

`audit_product_input.py`是刻意省略接口目录的旧诊断入口，不是硬件实施前置检查。
正式入口`flow.py`使用提供的资源合同，将每项需求分成逐位新连线、已有`native_service`，
或`external_boundary`。原有S/适配器路径不重复布线；外部接口保留实际原生层，
不能因BTerm位于M5便凭空宣称有M10接点。接口身份、资源inventory SHA和三种源视图共同绑定。

`resource_library.py --services work/YUZE-LU/230/resource-services.json`可登记当前五类
已提供资源的物理附件合同。该文件只声明原生物理服务及外部边界，不认证完整#220
算子数值/局控程序语义。EDA运行不要求先开发母控或外存gateway；系统功能资格单独记录。
690条真实晚接通路的算法物理回归、#220的逻辑服务绑定及完整模型系统验证分开列证据。

## RC 方法必须保留的限制

便携交付由`package_delivery.py`补齐六文件所引用的技术/上层通孔LEF及全部别名LEF/Liberty，
生成相对路径加载脚本。包内各依赖保持原始字节和SHA，源目录同名文件分别保存。
`package_delivery.sbatch`实际重读ODB/DEF并比较计数、重跑名义STA并与原裕量核对，
全部通过后才归档；其资格仍限于原交付声明的输入与研究RC口径。

- [#202](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/202) 的查表提取
  会漏掉跨层正交互容；场解修复保留电阻图并重新求电容。路线变化必须重提取，不能
  把旧 SPEF 的电容套到新 DEF 上。
- [#218](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/218) 主铜参数为
  `Rs=0.0102 Ω/□`、via10/via11仍为研究假设`0.08 Ω`；不是工厂标定角。
  低/高电阻率及理想通孔只能作为分别列出的敏感性实验。
- [#225](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/225) 证明原生层
  耦合会改变负载；其数据仍属于旧 #206 版图，不能转移到新五类底座。它也没有取得
  新耦合后整版 STA 资格。新产品需采用真实原生导体重新求解并核对器件/宏模型边界。

最终须保存实际布线/连接/几何、原生层不变或重新验收、分布耦合 SPEF 及读回、
原 Liberty 电气与 TT300MHz setup/hold、规定的功能/PG/CTS记录；失败按实际端点、
路线或底座版本回改。缺这些输入或证据时不把“362条几何回归”改称系统通过。
