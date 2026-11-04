# Issue179：局部Block接续研究与协作欠项

2026-11-04，Asia/Shanghai。仓库rayggxia-workspace/LLMHardwareDesign，project_id=llm-hardware-design；[Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179)，负责人Melodydt。优先级/审查人/Projects处理管理员待指定。

## 分支、版本与位置

- 来源PR176未合并，固定设计commit `08f2ea20a11dfdd09892a67599163e32b7237edb`、tree `70d56e60b162ce3ef17e6f0ffdd55b570ec5d4d7`。
- 新任务分支`task/179-local-block-continuation`，[Draft PR180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)以`task/175-local-block-design`为base；首交付commit `8513c23d70ac6156a9735f04da271cf6764a1f7c`，最终HEAD在Issue179/PR180在线回执读回。PR176合并后先核差异再考虑改base，不自动合并。
- 独立本地API包`D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/delivery`，管理/来源快照与本任务白名单文件；无.git/HEAD/index/暂存，因此无“本地已提交”状态，未提交资料指发布前本目录的新文件。远端通过Git tree API继承固定父树，仅上传白名单。
- 根参考资料副本和work/Melodydt/151旧包不覆盖；main仍为`4b1df2c7cbdaa0fa6f9f468f2b5b854cec875609`（本轮读回）。本任务未改服务器或原作业。

## 成果与验证

[研究报告](../local-blocks/CONTINUATION_RESEARCH.md)、[8项容量下界](../local-blocks/continuation-capacity.json)、[核算输入/程序/来源和验证入口](../../work/Melodydt/179/README.md)、[个人进度](../../progress/Melodydt/STATUS.md)。实际发布SHA和验证结果见Issue/PR回执与work/Melodydt/179/validation.json；本地资料与远端每个上传blob逐字核验后才报告上传完成。

管理结构不是业务验收；容量算术不是完整生存期/调度证明。没有新增RTL/模型/EDA/服务器实验；作业号、节点、日志、服务器结果目录均不适用（未启动），没有自动监测。

## 未完成项与恢复第一步

负责人Melodydt先读取Issue179及PR最新头、PR176和PR178/167/152/163最新状态，确认无并行更新；保留其他任务及其作业。然后在本目录运行：

```powershell
python -X utf8 -B scripts/check_project.py
python -X utf8 -B work/Melodydt/179/analyze_capacity.py --check
```

接着从Qwen dense FFN起，给出16/32KiB候选的对象地址、紧凑打包、bank、M单上下文、down端完整Mid重放位置与成本及真实ACK/释放顺序。先形成可检查合同/轨迹，再落地新仿真；Falcon数值、系数表、Granite质量和最后同资源物理对照仍待接续。完整三模型能力未验收，不标done。

## 登记与看板交接

本轮读回management-hub PR5 open/unmerged，登记pending；复用该登记不重复建PR。PR176基线config/board.json返回404，status-mapping.json已读取；当前连接器没有Projects条目/字段读写工具，因此本任务实际看板/条目ID/status未核验，并非已证明Melodydt缺read:project权限。状态unverified、同步pending。

管理员待指定：确认正确看板及受众，补配置，查Issue179是否已有卡片，复用或添加；同步Project ID=llm-hardware-design、Status=In progress，Priority待指定不猜测；读回条目ID、字段及时间并写回本Issue/PR。未完成前不报告synced，不修改权限或另建看板。
