# 第一版五宏：V 最终时序与剩余间距修复

Refs #121 / PR #122。M/V/R/S/T每种一个基础宏，M1–M10固定、未来M11/M12，不扩展阵列或产品。M/S/T已接收的证据不重跑，V/R最终结果尚未齐。

V423六阶段实际完成，最终setup仍−0.0875939ns/TNS−1.35826ns、37项，hold+0.0700393ns、max_cap2。完整路径定位function_sent→函数输入寄存器；[原始23文件/309归档源](v-423-finish-diagnosis/README.md)。424独立门继续。新唯一基础V仅在回放选择与S33减max之间加寄存，两lane有效mask与元数据对齐；8元素函数预期9拍、Softmax138+10B+P、N256586，RMS/L2不改。见[功能流水取舍](../../../../docs/decisions/2026-10-30-block-v1-v-function-fetch-pipeline.md)。458数值/映射/延迟等八检查尚待部署；所有最终P&R门必须新做，不能继承423。

| 隔离诊断 | 实际结果 | 结论 |
| --- | --- | --- |
| [447](v-410-residual-def-447/index.json) | 445剩余196标记的192网精确DEF记录与哈希 | 只绑定旧410→445，不可用于423坐标 |
| [448/449](v-410-residual-jog-449/index.json) | 88网M3沿现有腿移动过孔，196→215，删除90/新增109 | 拒收 |
| [450](v-410-pruned-jog-450/index.json) | 回退55个新增标记涉及网，保留33网，196→163，删33/增0；全DEF/网表/连通通过 | 仍163项，不合格 |
| [451](v-410-via-enclosure-451/index.json) | 相同via矩形clone的原生196报告逐字节相同；仅沿已有同网线延伸一个via pad，实际全层金属/切孔并集相同，196→195、删1/增0 | 有界单点证据，完整GDS452仍运行 |
| [453/457](v-410-enclosure-bulk-453-457/index.json) | 191网/194个显式via定义；完整DEF结构、所有191网前后全栈连通与全部金属/切孔并集相同。clone196逐字节相同，merge196→1、删195/增0 | 非生产资格；没有豁免原生DRC |
| [411最终DRC](v-411-final-drc/index.json) | 旧410原生487；完整未修改GDS deck另2项METAL9.2 | 两门均需通过，保持拒收 |

453的原始EDA自然完成一次，未重跑。454只读检查误把“还导出完整上层网”的集合等同191目标网而失败；455保留所有其他导出网不变的检查后，已通过完整结构/union/连通，却被300kB展示diff大小上限拒绝。457保持完整结构比较与几何/连通检查，仅把展示diff大小记录为描述项，重新只读核验通过；两次失败原样归档。标准readback本身没有放宽：新via定义只在另一个明确命名的结构审计副本中精确核验后移除，真实after.DEF/ODB完整保留自含定义，未拿审计副本做EDA或交付。

剩余唯一M2标记是net104114的小折返。456只在453merge隔离副本提出三段换一段的局部直连，保留全部via/anchor/M1，仍在实际全芯片native检查；不得预称清零。完整GDS452用于单点451的真实全层递归XOR与原deck，尚未完成，不以ODB并集代替完整GDS证据。所有probe没有RC/STA/最终功能/LEC资格，未修改当前V/R或原ODB。

诊断复用R404既有allocation，每任务16CPU、即完成即补位；曾与R和两个GDS后继形成六个独立16CPU槽。仅真实数据依赖限制后继；使用实际MemAvailable及预测RAM×1.2+16GiB保护，无新增诊断allocation、无取消/重启EDA。458会通过原Issue级最大8准入器另分配一个c96运行新源必要检查。

RAW-0451-VERIFICATION.json记录前一组86语义文件；所有原始报告按-text保留字节，压缩副本保留原始字节SHA，生成Python cache仅远端索引，大DEF/V/ODB保留授权存储及SHA。文件上传、登记、看板、最终业务验收分开：登记pending（management-hub PR5未合并）；board.json未配置，看板unverified/同步pending；管理员/独立审查人待指定。Issue121=in_progress、PR122=draft、目标active。
