# Issue68 R范围与V/R/S服务交接

2026-10-24 Asia/Shanghai；负责人Liangruizhi/182389313/2663955430@qq.com；仓库https://github.com/rayggxia-workspace/LLMHardwareDesign，[Issue68](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/68)/[PR69](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/69)。规则rayggxia-project-collab1.0.0；插件及HTTPS实际身份均核，未借其他账号。

## 分支、实际版本与入口

根D:/Projects/LLMHardwareDesign-range-service，task/68-range-service，base task/66-scale-state@8bde3bf2309c2b41b68c081e9dbbe8be42d2ee19。独立range/service/audit子worktree分别-68-range/-68-service/-68-audit，root整合及所有服务器/GitHub操作，不覆盖他人。最终文档commit读PR69 head；恢复必须git status核尚未提交文件，不能假定本文件描述以后的工作区。

实际算术phase2源@7ea68a4、range83ef2b0...；phase5兼容resume扩展@b650cc4、db92865...，原默认数组/统计逐码兼容，未覆写旧run。service phase6@ae9d26b/SHA0fa2cc07...不变；最终接收phase9@ff53f65/SHA325a3668...。聚合、并行接收合并、分析、精选、归档均独立phase/commit/SHA见[统一索引](../../project/experiments/range_service/results/issue-68/index.json)与work68/phase*-binding.json，不用最终HEAD代替已执行代码。

## 已执行及数据位置

[报告](../experiments/issue-68-range-service.md)、[Block v2第10节](../BLOCK_PARTITION_V2.md)、[决策](../decisions/2026-10-24-r-range-and-finite-service.md)记录实际条件。R每轮native12、legacy72条件两轮；各6预先固定条件独立数学全步接收，其余两轮SHA。4checkpoint及实际重写SHA负例通过。28服务分片，两套各56配置/112witness，两轮科学SHA一致；native全112串行独立接收，legacy7×16并行独立接收后source-bound合并覆盖。每套48轨迹级同资源标签对照0差。

Slurm90083–90151共69个本人job：61 COMPLETED、7 FAILED、1 CANCELLED，最终ledger已读回。7个失败分别为输入脚本词法错误1、接收器pilot子集假设4、root接收repeat路径误填2；均保留原source/log/命令，不是篡改后的数值成功。90137本人串行接收尚pending时取消，替换7并行接收，其他成员89448/node3未动。所有真实计算node13/c96本人lrz-i68-*，没有新模型下载/完整模型加载/其他机器任务，Phi封存。

服务器/public/home/yuzelu/RuizhiLiang/issue68-range-service-20261024；delivery01/full-results01.zip **8024664381B**、SHA **745968df14258e0984028a3d6d5626753196f4082dea1591719c9235ee51b8ea**，1919成员逐SHA/大小读回及ZIP CRC通过，归档自身最终log外置。旧Issue66输入包仍独立依赖，SHA cf07db65cb9207bd1aea0efd50b2338fa535edee6f2cae760a116df912dfb548；未重复下载8GB到本机，未在C盘放任务数据。

仓库精选约18.17MB（不含索引）：portable-r.zip 2424317B，SHA9c9fda0bb30f0d514a4679353852df9f4d109063c4e3bc9c9c04fc38f24a32f5；真实t[2,14)完整2head128×128，两种state格式，两次重定标。4份原服务gzip及完整回执、分析/metrics索引在同results目录。服务器与本机独立精选接收均PASS；R精选不重新证明省略的前2步/剩余242步/原浮点编译，服务精选只重放调度/容量/元数据，不重做原NPZ算术。全量原捕获、旧输入及全窗口需按索引取得授权服务器数据。

实际管理检查、69项新增边界/聚合/接收/分析测试和本轮原164研究回归通过。work68保存命令/日志/验证JSON及源SHA；本机测试日志仅为仓库LF去CR，raw与仓库SHA映射单列，不改科学数据。临时D:/Projects/Codex/range-service-20261024-1238保留仍有用途的回执/核验输入；任务重复副本移出仓库保留，未删除他人数据。

## 结论、限制与恢复第一步

先重读最新AGENTS/Skill/README/状态、Issue68/PR69及评论、成员Issue55/63/相关PR/交接，再核Git身份/origin/worktree和服务器squeue/sacct。现有28分片与所有数值/接收/归档已完成，不重跑历史launch脚本或覆盖输出。按module README先核本索引与精选SHA，再用新D盘receipt路径离线接收。

本轮因果重定标让固定S32旧窗256步无发布sat，原193sat保留在static诊断。它额外需要fulltrial clone、坏head重编码和失败重试，S16误差略退化；不能称质量通过或全生命周期安全。下一轮以tile16本地old/new+aux为条件工作基线，S32完整state分页、owner/epoch/共同提交义务可收敛，独立R宏/V-R合宏/近M RQ/全图收益仍未定。

剩余真正改变决策的第一步：冻结独立初态/校准生命周期和错误预算；或先把当前S8宽乘/checked merge、SFU、1RW/FIFO及合法M阵列复用映射为可校准实现，再在相同issue粒度、恢复语义和真实端点下比较。norm32:R256为人为独立流配比，一次性布局计入cold成本，不是完整LLM。q/k norm、gate、SiLU/GatedNorm等FP桥仍在；全模型质量、目标RTL/EDA/时序/PPA和端到端收益未执行。研究接续Liangruizhi，Issue55/63物理/适配器沿原负责人，不自行接管。

## 协作交付未完成项

成果通过任务分支/PR69交付，待指定审查人与合并，Issue in_review而非done；PR69以PR67任务分支为base，依赖链未合并，不能直接改base绕过。登记management-hub PR5 open/unmerged为pending；没有board.json及可用Projects字段能力，看板事实unverified、同步pending待管理员配置/核卡/字段并读回。提交状态以PR最终head和Issue读回为准，不将本地文件改动说成在线设置生效。
