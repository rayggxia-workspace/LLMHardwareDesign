# Issue230：综合后通用物理后端的范围纠正与接续

仓库rayggxia-workspace/LLMHardwareDesign；[Issue230](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/230)、[草稿PR231](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/231)，分支task/230-backend-router，负责人YUZE-LU。

用户明确要求通用EDA。底座/资源库属于输入；此前“需用户先补九组已验收芯片、母控、PM、gateway硬件”的开发前提已撤回。没有待用户批准的新硬件范围问题，不要重复提出。

## 九组输入与当前实际成果

PR220 head f23a6d93448849b6f7b15edccce7e996d1092e7d。
project/experiments/block_synthesis/full_plan.py::replicated_inventory()提供P×3/U×2/C/F/J×2。
真实IR：/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/algorithm-fix-112-reuse-fast-plan/generated/nine-groups-count-experiment-ir.json，
144229730B、SHA6aa273e57057dcd000e44218ec4229672f82b8b0251a51a882ef21541753395f；计划在同目录。

resource_base/library读取该IR并匹配物理资源模板，100559及100560均成功：9组、28独立叶宏、1380个真实M10端点。源视图SHA核对；保存组合变换，不虚构合并ODB。flow.py已接计划独立检查、资源装配、库接口展开、逐位绑定、路由、DEF导出，36项本地及服务器检查通过；原合同/DP/缓存40项通过。

五类362网实际读回、研究上层几何及全原生层XOR通过。100406五项完整原版DRC均0违规。
100555证据收集通过；包SHA504e672d45770edbb2adcc761f6e4fa5cf15fb5ba4d7aaee006b9fd07abc6159。
这不是#220完整18束布线或九组RC/STA资格。

attempt14漏带inputs配置，attempt15独立CLI导入路径缺失，均保留失败；attempt16修复后通过。
attempt17包含完整flow测试，作业100560 COMPLETED0:0，源包SHA253cdeb30a45c1f3355b22a0cc016b65b313a095030fb8bdaa796673a4701e21。
源视图当前按固定局部布线整体平移，leaf_instances逐个登记；放置是shelf基线，尚非通信感知布局。源envelope不是上层障碍或大硬宏边界。

## 继续工作

继续把资源接口/预连语义降低到#220 binding所需的逐位实际端点，推进共同物理视图、完整路由及RC/电气/时序反馈。缺资源描述时报告具体条目，不以尚无完整系统RTL资格停止EDA开发；不猜宽度/造接点，不将362网回归冒称完整18束闭合。

工具、证据和复现入口见project/experiments/upper_router/BACKEND.md及work/YUZE-LU/230/README.md。
服务器所有工作在本人issue-230-backend-router目录；每项10核、最多6并发，所有attempt不可覆盖。
不移植旧#206的物理资格；新路线重提上下层寄生。独立审查人待指定，不自合并/关闭。
登记management-hub PR5 pending；无board配置，Projects unverified/同步pending，沿用Issue7。
