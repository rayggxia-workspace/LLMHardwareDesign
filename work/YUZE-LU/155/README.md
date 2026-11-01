# S SRAM 独立物理版本

任务：[Issue #155](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/155)。负责人：YUZE-LU。

本次验收包含完整 S 的远程布局布线及最终物理结果，不能以本地接口仿真结束。
保留标准单元 S、原供数器和其他宏的现有结果与任务；四个256×128bit真实1RW SRAM替换16KiB有效载荷存储。

原始本地接口证据位于[143/s-sram-variant](../143/s-sram-variant/README.md)：严格lint及三初态存储/完整供数测试通过。原S接口源在本地基线`9a248b38`与PR144远端基线`d1f26884`逐路径比较无差异；本分支仅重放独立SRAM修改，不向远端发布未关联的主线本地提交。

## 远程执行记录

根目录：`/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155`。
固定ORFS镜像SHA256：`49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a`。
EDA仅在Slurm分配中执行；任务名为`yzl-sram-*`。单个SRAM银行生成一次、实例化四次；在真实视图产生前不启动依赖它的P&R。

| 目录 | 作业 | 实际结果 |
| --- | --- | --- |
| probe-002 | 94535 | COMPLETED0:0：Python3.10.12/KLayout0.30.12/Yosys0.68+post；无OpenRAM/ngspice；平台SRAM GDS列表为空 |
| generate-001 | 94536 | FAILED2:0：归档导出CRLF使bash拒绝pipefail；已新增s_sram目录LF属性 |
| generate-002 | 94537 | FAILED1:0：计算节点DNS不能解析软件源；改用离线包 |
| generate-003 | 94538 | FAILED1:0：跨平台下载未带Python3.10条件依赖exceptiongroup；已补齐并重新封存离线包 |
| generate-004 | 94540 | 工具准备阶段CANCELLED：在进入SRAM编译前补齐显式OPENRAM_TMP/TMPDIR目录约束；已安装Python依赖复用，未取消其他任务或已运行的SRAM编译 |
| generate-005 | 94543 | 独立c64/16CPU；离线依赖哈希与精确版本检查通过、ngspice45实际编译成功，真实SRAM编译已开始；最终结果待接收 |

离线包v2：`/public/home/yuzelu/opt/eda/issue155-offline-v2/offline.tar`，SHA256=`8cbdf1046ed3c101429de04790caba6184e92fe32d7b624020cd6dee2e63d886`。
OpenRAM1.2.48、numpy1.26.4、scipy1.13.1、scikit-learn1.5.2、coverage7.6.1及官方ngspice45源码，使用包内逐文件SHA256SUMS核验。
工具目录：`/public/home/yuzelu/opt/eda/issue155-sram`；不修改公共镜像或其他任务的工具。

## 当前验收边界

真实宏配置为FreePDK45、TT/1.1V/25℃、`analytical_delay=False`、显式ngspice/KLayout、保留临时日志。
准备阶段原始回执、日志与Slurm终态已实收至[remote-preparation](remote-preparation/receipt.json)，逐文件SHA256保留。尚无真实SRAM完整视图、宏DRC/LVS、完整S P&R或300MHz物理通过结论。工具安装、宏生成、完整宏物理验证分别记录，不能相互替代。

完整S物理入口为`project/experiments/s_sram/physical.py`，需在分配内提供真实`generation.json`且五种实际视图哈希一致。它排除仿真替身，检查四个真实银行实例，固定银行与M10内部接口，沿用300MHz边界/原生输入保护/电气修复预算，执行新综合、PG/布局/CTS/布线/RCX、完整GDS合图、完整GDS DRC和版图渲染。当前仅完成Python语法检查，尚未运行该流程，不代表物理通过。原生独立检查、最终功能和严格等价仍为单独验收项。

完成后需要接收真实宏V/Liberty/LEF/GDS/SPICE、完整S最终V/SDC/DEF/ODB/GDS/SPEF、版图图像、面积/时序/电气/DRC/连接证据、SHA256及最终功能/等价检查；若失败保留原始报告并说明具体障碍。

## 已提交的后继及中间几何

- 完整S物理作业94551，`physical-001`，源码`9f026931`，`afterok:94543`；真实银行生成成功后才分配CPU。
- 实际生成模型功能作业94555，`actual-model-001`，归档源码`2af5282d`，`afterok:94543`；使用生成器实际Verilog，保留默认3ns读延迟/1ns输出保持，并显式推进仿真时间。较慢时钟下检查协议与数据，不能作为300MHz通过证据；可与P&R并行。
- Git HTTPS push连续reset后，已通过本人GitHub API发布相同源码树`4e062cd8`，与归档源码`2af5282d`整树严格一致，见[publish-functional-tree.json](publish-functional-tree.json)。仅对齐本独立分支，未改主工作树。
- 检查点`checkpoint-002/intermediate.gds`位于本任务远程根，14,826,244B，SHA256=`8976d2910679b46cc4866f8a65fbc0ad934800426bef52550f8528f038542e2d`，140层次单元、0.0005μm数据库单位。读取前后源文件与快照SHA完全相同、GDS ENDLIB完整，KLayout可读并渲染。当前外包框`(-44.055,-9.85;405.47,108.225)`μm，为最终坐标平移/电源完成之前的中间布局，不作为最终宏边界或合格GDS。

![SRAM中间布局，仅过程证据](intermediate-bank/intermediate.png)

读回元数据与图片哈希见[checkpoint.json](intermediate-bank/checkpoint.json)。真实几何已存在；当前仍在宏内布线，不能因此宣称宏DRC/LVS、表征或完整S P&R通过。

草稿：[PR #158](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/158)，base为PR144分支。侧会话调用应用附件挂载返回`thread not found`，在线PR可用；未改其他线程附件。最终审查仍待指定。

规则版本：rayggxia-project-collab1.0.0。项目登记复用已有pending证据；本地未配置config/board.json，看板事实unverified、同步pending，管理员及审查人待指定。PR158保持Draft，Issue保持in_progress，不标done。
