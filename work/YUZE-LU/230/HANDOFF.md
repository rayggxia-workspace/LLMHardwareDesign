# 通用布局布线后端交付

任务 [#230](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/230)，交付 [PR #231](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/231)，前置 #220/#227/#229。2026-11-09 CST 工程验收通过，待独立审查。

## 算法与输入

`project/experiments/upper_router/flow.py`读取综合IR/plan、物理资源库、接口catalog及规则；实例数来自输入。
执行能力匹配、通信相关放置、静态逐位需求展开、真实M10接入、多源A*及fanout树、历史拥塞拆线重布，输出实际DEF/通孔LEF及身份映射。
独立检查、真实ODB/GDS装配、共同场RC、原约束STA和严格交付门继续验证工件。模型名不进入布线算法。

```powershell
python project/experiments/upper_router/flow.py IR.json PLAN.json LIBRARY.json RULES.json NEW_OUTPUT --catalog CATALOG.json --gap-dbu GAP --via-resistance-ohm VIA_R
python -m unittest discover -s project/experiments/upper_router -p 'test_*.py'
```

参数须采用所选资源库的实际单位、端点及规则；图导出结果本身不授予物理资格。
运行器、原始输入、工具SHA及所有失败/修复见[工作记录](README.md)及[后端说明](../../../project/experiments/upper_router/BACKEND.md)。

## 本次实际验收

| 检查 | 结果 |
| --- | --- |
| 输入资源 | P×3/U×2/C/F/J×2；28独立叶宏；1380个实际M10端点；690条晚接网 |
| 平坦物理身份/连接 | 1698914实例、678871网、2070个新网ITerm归属一致；原生导体/pin和新增几何XOR为0 |
| GDS原生身份 | 1293 cells、40083 cell-layer、12402850层级实例/变换全部保持 |
| 完整原版FreePDK45 DRC | 0；另有声明M11/M12研究几何与真实M10落地检查 |
| 共同场RC | 113006927矩形；690/690行通过；62行提高采样重算，原失败保留 |
| 原约束TT300MHz | 9档节点/Miller敏感性均0 setup/hold/capacitance/slew/fanout违规；最差+73.082209/+0.211775ps |
| 便携包实际回放 | ODB/DEF计数一致，名义STA复现原结果；101473 COMPLETED0:0 |
| 本地回收 | 808854594字节，40项包内文件及全部六文件SHA匹配 |
| 业务检查 | 57项后端与119项上游综合器回归通过；管理结构和diff检查通过 |

## 后端工件与加载

服务器根：`/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-230-backend-router/`。

- `attempt84/delivery/`：严格合格六文件及资格回执。
- `attempt85/delivery-index.json`：物理证据、执行源及工具索引。
- `attempt88/handoff.tar.gz`：最终便携包，含六文件、实际技术/通孔LEF、所有别名LEF/Liberty、加载脚本和证据。
- `attempt86/`、`attempt87/`：未通过回放的原始失败，不作为交付。

本地：`D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-230-artifacts\backend-handoff-230.tar.gz`；
已核验解包目录为同级`backend-handoff-230`，回收记录为同级`backend-local-readback.json`。

压缩包SHA-256：`c53b79eaf89c185307d9d29472de10ec65ad6c699fbd8bc544162b948c7fda4c`。

使用记录的ORFS容器/OpenROAD，在解包目录执行：

```bash
openroad -no_init -threads 10 -exit load_odb.tcl
openroad -no_init -threads 10 -exit load_def.tcl
openroad -no_init -threads 10 -exit load_timing.tcl
```

脚本只引用包内相对路径。LEF basename全局唯一；OpenDB以文件名识别库，不能仅靠目录隔离。
实际回放与本地回收证据见[最终机器索引](evidence/final-handoff.json)。

## 资格边界与审查

本次是声明资源网表/晚接接口的通用算法物理验收。#220真实计划18项原生服务/外部边界绑定（0条新增网）另有回执，未将其换称690条模型新连线。
原生M1–M10不变；M11/M12采用#218/#225参考的明确研究RC栈，原生内部RC保留，新增上层电容在共同真实原生导体上下文重新求解。
资格限原始TT300MHz约束；全模型数值/控制程序、统一顶层CTS/PG、其他PVT、动态SI及工厂标定12层签核需要各自证据。
保留8µm合法格点子集及有限搜索的算法边界；候选失败不宣称不可布。

独立审查人待指定；Issue进入待审查，不自合并或标done。项目登记PR5 pending；缺board配置，Projects unverified/同步pending，沿用Issue7交接。
