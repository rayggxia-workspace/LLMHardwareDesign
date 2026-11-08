# 实际后端接入与产品输入边界

任务 [#230](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/230)，叠加
#227/#229。目标为 main 五类 `_64` 独立叶宏＋局控的九组产品，前置 #220；
不使用 #206 的旧组合硬块替代该对象。`_64` 是指令宽度，不改变数据端口宽度。

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

以上工件仍然 `physical_qualified=false`。互联视图不是已经 stitch 的产品 ODB；
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

## #220 到实际产品仍缺什么

`audit_product_input.py` 读取 #220 实际 IR/plan，先运行原独立调度检查，再保留每项
需求及 task/binding 身份生成 #227 合同。当前没有经验证的产品信号目录，状态保持
unbound，而不是猜出128根数据线或只丢掉无法绑定的束。该检查是输入审计，不是布线
不可行性证明，也不说明五类独立交付失效。

main 提供五类独立 `_64` 夹具及当前母控，不等于存在九组共同 ODB。完整产品需要：

1. 九组资源实际共同放置、原生网和局控身份绑定、PG/CTS及局控PM的明确实现。
   不能把五种夹具的外框作为新组合硬宏。
2. #220 原生命令/私有S服务到真实预连或晚接端点的逐项目录；已有固定数据路径如实
   登记，不能因综合输入使用“零预连”就把它们当成可任意改线。
3. 取代 #182 虚拟外存的实际 gateway/端口/信用和确认合同。当前已验收母控只提供
   两个驻留目标；九组控制分发、局控PM和全部算子服务需分别核对，不能由布线补出RTL。

这些实现冻结后，才有完整产品逐位网表及真实驱动/接收端供全网布线与STA使用。

## RC 方法必须保留的限制

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
