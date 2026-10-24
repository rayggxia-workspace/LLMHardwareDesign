# Issue #63 本机续接与物理接入交接

仓库：https://github.com/rayggxia-workspace/LLMHardwareDesign；负责人huangpingyang04-lgtm。
持续PR：https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/79，Refs #63，base为PR78的codex/block-v2-offline-prep。
分支task/63-workload-layout-adapter。本机独立目录：C:/Users/86188/Documents/ChatGPT/2026DAC/LLMHardwareDesign-workload-adapter-63。

## 恢复与来源边界

旧任务目录仅为历史记录：`/public/home/yuzelu/PingyangHuang/issue-63/workload-layout-adapter-20261023T134541Z/`。
本轮没有SSH/SCP/SFTP/Slurm或任何服务器命令，也没有VPN/路由/防火墙/SSH配置变更。
此前已写core.py、consumer.py、CLI、resource_bridge、部分测试和固定依赖的服务器版本没有读取、比较或覆盖。

聊天工具store已失效。core/consumer/CLI依据原聊天完整文本在本机续接，未声称字节等同；examples/test_core和assets/test_assets的恢复字节与聊天记录的历史SHA核对一致，但同样没有与服务器比较。resource bridge恢复并补已准备的hardening，改为复用现有llm_resources，未再次复制估算器。新v2桥/typed sidecar/消费端加强/完整复跑为本机续接实现。逐文件当前SHA、来源和验证见work/huangpingyang04-lgtm/63/source_inventory.json。

PR78依赖固定a5ff0c5af973ffeafa441712cd3f6e491da5a2fd，文档基准88e9c4b2c3bb1b93b7155ba87ad11853e6c15512，原fixture/expected/sources和历史记录不改写。服务器版本只有历史功能记录，本机未取得其原文件；同名函数不构成来源同一证明。

## 运行与验证

正式代码project/analysis/workload_mapping；主要合同docs/WORKLOAD_MAPPING_INPUT.md。
完整入口：`python -B -m project.analysis.workload_mapping.validate_delivery --output-dir .local/runs/formal-new --reference-root .local/dependencies/reference_assets`。
本机原ZIP/LEF在.local/dependencies/reference_assets，原始stdout/stderr、开发失败、全部输出和独立源码复制留.local/runs；仓库只保留精选science/receipt索引。

首阶段commit f8d2dcdaab21b9aec243d53f43fea6f11ff205a3已由本人Git HTTPS上传；后续源码冻结commit、正式运行及最终提交身份以精选receipt和PR head实际读回为准。开发预检195项、10场景独立进程/独立源码目录重放通过，source_clean=false明确不当正式冻结验收；正式干净源码复跑另存新目录，不覆盖该预检。

第一轮discovery相对import错误已保留可取得的截断输出/摘要，修复后通过。没有伪造未保存的完整日志。缺信息返回blocked，负例被拒绝不表示被拒映射通过。

## A/B/C与准确缺项

A为选定静态图/有限事件的声明条件检查，typed unit/group/owner/epoch/version/guard/abort/commit、分域容量、FIFO和串行bank访问检查；不证明任意LLM、通用宽算术或最优调度。
B实际取得PR18三宏LEF：ACT860、MXU2172、GEMM3753信号pin，PG/PORT/OBS/DBU保留。PR20原ZIP本轮已取得并独立核对3032位Yosys/CSV/旧LEF，不能再称未取得。一个真实ACT clk引用已检查；真实协议、完整RTL/Liberty timing、其他块和GEMM逻辑bit顺序没有资格证据。
C缺同版完整实例/放置/朝向、固定M8 escape/landing、冻结底座及source hash、技术合法via和固定PG/clock连通性，保持blocked。主方案M1–M8固定，M9/M10及技术允许的8↔9/9↔10定制，M11/M12另列后备。M5/M6 pin不构成M8接入。

#55当前固定PR58@09f1876dd8eaaf0cb77005a4c094527d9ed5d9b0的flow只是阶段执行；无mapping_request读入口。本任务consumer是拟议布局合同独立读取，不是实际布线联调。任何将来新增physical checker需独立证据，不接受caller的true代替原始资格。

## 后续接续

服务器操作必须另获授权；第一步只读比较旧目录源码与输入SHA，明确差异后在全新目录整合，保护旧未提交代码、失败和输入。不能自动把本机版本覆盖旧服务器，也不能接管#55。
物理任务/资产提供方（具体处理人待指定）需提供同版冻结实例/端口/固定M8引出/技术via/PG与clock资格。收到后先固定commit和SHA，再实现明确的物理绑定合同检查。

看板未配置config/board.json，当前工具没有Projects能力：实际条目unverified、同步pending。管理员待指定，需要核验本Issue条目、Project ID=llm-hardware-design、实际Status/Priority并读回，不创建新看板或扩大权限。登记沿用management-hub PR5 pending，最终以读回为准。审查人待指定；PR不合并，Issue不提前done或关闭。

## 2026-10-25 正式本机复跑回执

干净执行源 `aa6f096695af45e9898090ce4f8006b8c9265029`，实际195项测试（32原小图、31原估算器、132适配器），0跳过；10个场景在独立源码副本/新进程/新cwd中重放，四个科学JSON逐字节及SHA一致。原fixture/expected/来源快照前后不变。真实导入/3032bit audit与bind/verify/replay独立重放一致，显式physical请求退出3。科学摘要SHA `f2ec30e28966be33888cf314bd5e93a0bb24378d4147d79cbdd9ad9971efbbdc`。原始日志和完整结果为 `.local/runs/formal-01/`；精选[回执](../../work/huangpingyang04-lgtm/63/receipt.json)与[科学摘要](../../work/huangpingyang04-lgtm/63/science.json)。C保持blocked，远端上传/CI/审查/看板另行核验。

首次CI run40114649385在fixed-dependency-diff返回128，因浅克隆没有固定PR78基线commit。原失败保留work/.../63/ci_first_failure.json及GitHub job日志；获取步骤加入该精确commit，原Git差异审计门槛不变。整体CI仍待后续真实终态，不能用本机通过替代。
