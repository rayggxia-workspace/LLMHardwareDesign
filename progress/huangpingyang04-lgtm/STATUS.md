# huangpingyang04-lgtm 的进度

- 更新时间：2026-10-23 17:13（Asia/Shanghai）。
- 当前任务：[#48 ≤4B INT8输入规范与轻量资源估算](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/48)，负责人本人，审查人/优先级待指定；待PR审查/合并，不done。
- PR：[PR50](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/50)已创建；最新head及两项线上CI读回保存在Issue48/PR回执，未自动合并。
- 成果：[输入合同与使用](../../docs/LLM_RESOURCE_INPUT.md)、`project/analysis/llm_resources/`的schema、标准库CLI、PR44固定候选配置快照、四个精选示例及单元/CLI测试；增加专用CI。复用候选格式，不改PR44代码、原始参考或其他成员进度。
- 已完成：总参数≤4,000,000,000（包含全部专家/aux），W8A8/INT32、参数分区/shape/场景校验；未知量保留null；权重/scale、KV/状态、tile、六类库存/FIFO、指定路径打包、线性块数及带宽记账。报告始终是部分解析估算，没有完整模型通过结论。
- 隔离：`C:/Users/86188/Documents/ChatGPT/2026DAC/LLMHardwareDesign-resource-estimator`，`task/48-int8-resource-estimator`，起点main `0cc36f3238c7084d7126d94c314fe7d8bf0f9c5d`；不是PR44派生分支。固定候选来源PR44@3fa0b45，完整commit和字节绑定见文档/报告；PR/最新commit/CI以Issue48交付回执为准。
- 验证：本机Python3.13.5，管理检查通过；31项已知值/负例/容量/带宽/prefill/窗口/打包/CLI/确定性测试通过。源码提交后的冻结重跑、检查命令及摘要见本任务交付记录；准备运行的source_bound=false不冒称冻结结果。
- 冻结记录：[validation.json](../../work/huangpingyang04-lgtm/48/validation.json)，源码commit b21112bb1ce311db4ec22155f4b1ce23ffbcb5b1；四示例各两次逐字节一致，输入/源码/schema/候选全部source_bound=true。全部搬运未知时带宽/时间返回null；已指定传输按参考边及共享TX单独记账，不外推到扩展库存。
- 下一步：Block同学/团队填写真实频率、服务率、RQ通道/II、外存/布局预算和整数合同；算法侧提供生命周期与完整传输/映射，再评估库存。布局、死锁、周期仿真、数值质量及PPA尚未验证。
- 并行任务：[PR26/#25](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/26)为功能benchmark；[PR45/#42](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/45)为控制锥检查；[PR46/#43](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/46)为资源调研。本PR仅增加#48交付；并行个人进度文件合并时保留各任务记录，不覆盖其他分支。
- 协作回执：rayggxia-project-collab1.0.0；project_id=llm-hardware-design，认证身份huangpingyang04-lgtm。登记沿用[management-hub PR5](https://github.com/rayggxia-workspace/management-hub/pull/5) pending；本轮无模型/训练/GPU/远程/EDA作业、无软件安装或权重下载。
- 看板交接：仓库无board.json、当前工具无Projects字段读写，实际条目unverified/同步pending，不推断账号权限。具能力/权限管理员待指定：确认组织看板#1受众/字段，复用或加入Issue48，设置Project ID=llm-hardware-design、提交后Status=In review，核对assignee并读回条目ID/状态/时间；Priority/日期待指定。恢复先读Issue48、PR及本文件。

## 2026-10-25 Block v2 字段与合成图 Draft PR

- 用户明确授权将此前离线成果总结并提交Draft PR，并指定使用`huangpingyang04-lgtm`成员身份；Git凭据账户列表、Git作者配置及浏览器GitHub用户菜单均与之匹配。原10月24日离线禁push/PR为历史范围，当前只开放本批发布，服务器/EDA/模型/合并仍不执行。
- 分支`codex/block-v2-offline-prep`，基线`b06d85a801a87c07f9745ccae6950dc7e4cbd0d2`；远端读取确认PR50基础分支`task/48-int8-resource-estimator`仍指向该基线，main仍为0cc36f3。[Draft PR #78](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/78)已使用该基础分支为base，避免混入PR50既有17文件改动；不合并或重写依赖分支。
- 成果：[字段对照](../../docs/BLOCK_V2_FIELD_MAPPING.md)、[两图输入/独立expected/标准库验证器](../../project/analysis/block_v2_offline/README.md)。图1完整归约/RQ/残差，图2guard/shadow/原子提交/失败重试/保存恢复，含通信与proposal/metadata存储账。固定v2源88e9c4b不替换，旧估算器/快照不修改。
- 离线证据run01/run02保留原字节和当时未提交状态；本次发布前run04-pr-preflight再次实际通过管理检查、32新测试、31旧回归及两图确定性/保护检查。run03行尾检查失败及修复记录保留；最终暂存差异检查通过，固定fixture/来源字节与Git索引一致。不据此宣称真实模型、全整数硬件或PPA通过。
- 本批没有新Issue；Refs [#63](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/63)只作为接续，API读回其仍open/status:blocked、负责人本人，不改变其状态。实现提交`3b1fc28fb6b733e0bcf3decc0aae20ba21196f1c`已推送并由[PR78](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/78)交付；PR后续HEAD/发布回执以[交接追加节](../../docs/handoffs/2026-10-24-pending-block-v2-offline-prep.md)及线上记录为准。待指定审查人，未合并/未done。
- 登记沿用management-hub PR5 pending，最新登记事实未重读；无board.json，Issue63页面无Projects关联，适用看板/条目unverified、同步pending，管理员待指定。GitHub连接器仍Unknown tool，最终以现有Git凭据管理器认证的GitHub API发布，/user读回本人`huangpingyang04-lgtm`、ID239819021，仓库push权限true；不写盘/输出凭据，未修改全局账号/作者设置或其他成员已有进度。

## Issue #63 — 本机适配器续接（2026-10-25 Asia/Shanghai）

- Issue: https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/63；状态in_progress，PR首阶段准备中。
- 独立目录LLMHardwareDesign-workload-adapter-63，分支task/63-workload-layout-adapter；接续PR78固定a5ff0c5，服务器未访问/未比较/未修改。
- 已恢复通用core/CLI/consumer/resource bridge和例子；本轮32上游小图+31估算器+42核心+23资源桥通过，最小build/verify通过。
- 下一步：同一Draft PR持续接入v2两图、真实端口、完整独立复跑。C缺M8固定接入/同版冻结底座保持blocked。
- 登记pending、Projects unverified/同步pending，审查人待指定；不标done。

### #63 本机软件提交待审查（2026-10-25 Asia/Shanghai）

- 持续Draft PR #79：https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/79，Refs #63；依赖PR78。
- 正式干净执行源 aa6f096695af45e9898090ce4f8006b8c9265029；195 tests/0skip，10场景独立源码目录/进程重放科学SHA一致，固定输入不变。
- A选定软件范围pass；B三真实LEF/3032旧bit对照pass，协议未验；C同版M8/冻结底座缺项blocked。服务器未连接、未比较、未覆盖。
- 代码/说明/精选receipt见work/huangpingyang04-lgtm/63；CI和最终远端head待本次push读回。软件in_review，不标done、不合并；审查人待指定。看板unverified/同步pending。

#63最新正式复跑：源fee9ca211fcfa1440a2a4f2a3607762129957e00，197 tests/0skip，10场景独立重放，旧科学结果SHA不变。PR79持续交付，CI基线修复后的run40114765442通过，最终head CI读回见PR；本机/上传/CI与未审查/未合并状态区分。A/B选定范围pass，C仍blocked，Issue in_review，不done。


2026-10-25 生命周期复核：干净源 `10cd3d97d3b8ca9cbb242b1eee0078c2d708f577` 在全新 `.local/runs/formal-04` 实际通过 **200 tests / 0 skip**（原32+31、适配器137，其中核心48），10场景独立源码副本/进程重放，科学SHA仍为 `f2ec30e28966be33888cf314bd5e93a0bb24378d4147d79cbdd9ad9971efbbdc`。修复显式复制后源槽复用的误拒绝，按实际驻留字节范围处理部分覆盖与多个view复制；独立consumer采用另一个范围覆盖算法，并重查alias/接口宽度/FIFO。新增3个合法/非法成对回归；最初负例因残留旧transfer源导致错误提前触发，保留本机失败和修正记录，未改原fixture。旧正式回执不覆盖，最新见 `work/huangpingyang04-lgtm/63/formal-04/receipt.json`。A/B选定范围pass、C仍blocked；软件in_review。

用户再次明确要求重试SSH后，仅执行一次BatchMode连接，结果为 `Connection closed by 10.129.166.172 port 22`，未建立远程会话、未读取或修改服务器文件；未改网络配置。旧服务器版本仍未比较，后续只读比较后在新目录整合，不能覆盖原件。


## 2026-10-26 服务器验收补充

用户重新授权服务器操作后，已只读比较旧目录8文件：core/resource_bridge/test_resource_bridge与发布版SHA不同；5个vendor资料仍保留，当前发布版改用固定的兄弟llm_resources。旧目录实际上缺少consumer.py、cli.py、__init__.py；旧记录的“曾实存CLI/consumer”未由本次观察支持。旧目录未修改、未移动或覆盖。

在全新 `/public/home/yuzelu/PingyangHuang/issue-63/server-validation-20261026T0100/repo` 核验发布源 `d07abaeef16049da199f0efa96acffc95bd487dd`，通过Slurm作业91622（hpy-adapter63、debug/node27、1CPU、23秒、COMPLETED/0:0）实际200项/0skip、10场景独立源码与新进程重放通过；科学SHA仍f2ec30e28966be33888cf314bd5e93a0bb24378d4147d79cbdd9ad9971efbbdc，与Windows逐字节相同。仅传输本任务Git对象、固定参考输入；未传凭据/配置/环境，未读#55活动文件或干扰作业。最初2G内存请求被Slurm拒绝（节点公布内存1MB），保留失败，命令覆盖--mem=0后提交成功，未改集群配置。

精选证据在 `work/huangpingyang04-lgtm/63/server-20261026/`；原始日志与完整输出留新服务器目录。receipt中的server_access=false表示离线验收器自身不发SSH，不代表本轮未在服务器执行，执行平台由execution.json和Slurm记录明确区分。A/B选定范围pass；C仍缺同版实例/真实M8引出/冻结底座等证据。软件实现、离线验证与服务器复跑均完成；正式结项仍待PR79审查/合并，当前零reviews、Issue in_review，不能宣称done。看板仍unverified/同步pending。


### #63 通信优化研究扩展（2026-10-26 Asia/Shanghai）

- 用户授权新增较大图、greedy/beam和服务器对比；保留原两图/expected和#48依赖，继续同一PR79。冻结源38bd3094afeda09c5219f4bfa22068b1ecc35ac3。
- 新增形状DAG、容量约束搜索、独立回放及正式合同导出。仅合成资源下的串行通信优化，不冒称真实Block能力/模型质量/端到端性能。
- 独立服务器 `/public/home/yuzelu/PingyangHuang/issue-63/search-20261026-v1/`，Slurm91643/hpy-search63/4CPU；221回归和CI smoke已过，19格全实验及独立源码副本重放运行中。#55活动文件/作业未访问或改动。
- 软件扩展in_progress，C保持blocked；登记pending、看板unverified/同步pending，最终结果与交付head待正式双轮完成后追加。


### 2026-10-26 优化实验完成回执

Slurm91643（debug/node27、4CPU、22:44）和91646（c64/node3、2CPU、4:18）均COMPLETED/0:0。主实验19格（12主表+4分块+3搜索消融）及更强贪心追加12格，各在独立源码工作区/新进程完整跑两轮，science逐字节相同。最大13,120任务；12个6任务小图穷举给出真实最优差距，保留beam退化。最终223项/0skip，原两图/expected/来源和原#48字节不变，旧10场景独立复跑通过。

12主表格的线上字节总量：fixed10,119,300,544；greedy9,135,129,664（减少9.7257%）；beam9,012,513,536（减少10.9374%，较greedy再少1.3422%，7胜5负）。发现greedy在tie时总选M0后，追加相同12格的live-eviction tie策略：8,673,527,488（比fixed少14.2873%，比beam少3.7613%），不能将原较弱tie偏差包装成束搜索优势。推荐显式使用solve_tie，保留原solve(method='greedy')基线不变。收益主要来自减少权重重读、保护未来驻留、利用已存在M1；不增加硬件数量。主表beam权重加载下降11.5193%，非权重加载（含scale）增加5.7622%，所有方法输出写回payload相同。

束宽/深度更大不保证更优：第一格width4/depth3比greedy差0.1628%；去掉初始值未来读取下界时差2.0545%。长prefill512、1MiB案例beam比greedy多7.1658%线上字节。row64/col128在512KiB时必要工作集631,328B超过524,288B，明确infeasible。主表第一轮算法walltime中位数fixed0.890s、greedy5.113s、beam127.961s（同node27四worker下观测，非芯片时间）；更强贪心在不同node3/两worker单列，禁止据跨节点秒数推断CPU加速。

主表源38bd3094afeda09c5219f4bfa22068b1ecc35ac3；追加及223回归源b68f060ca5212bfc35d6beb58080d83007ad2427。主科学SHA d7f6c3d847e3865493fff01a10b2f459f86f328e6f46bc5df93d7616efcdc14c，追加SHA b0219fc13eb1b3410d430a5aa40be4ac0683a410dc9ae7776c1fd43a1cbdccb6。精选证据work/huangpingyang04-lgtm/63/search-20261026；大DAG/计划/日志仅留search-20261026-v1和search-20261026-tie新服务器目录。未触碰#55及旧版本。主模型/搜索/checker/driver当前字节与已验收源一致。

本轮是形状DAG与合成资源上的串行通信优化，不是完整Qwen数值执行、真实Block功能、并行吞吐或PPA证明；真实实例还需确定RQ位置，不能把合成fused kernel当已实现M/V。C依然blocked。软件/研究交付in_review，PR79持续更新，审查人待指定，不合并、不关闭、不done；登记pending、看板unverified/同步pending。
