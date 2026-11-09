# Issue247速度迭代接续

2026-11-10，Asia/Shanghai；负责人Melodydt；状态in_progress。

- 仓库：rayggxia-workspace/LLMHardwareDesign；[Issue247](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/247) / [PR243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)，现有分支 `task/242-r-load-bounds`。PR未合并，不宣称已进入main。
- 起点源码：`a22e199c1dce7d1037995a26f71f8b1358d038e0`；已创建并读回完整备份分支 `task/247-speed-base-a22e199c`。
- 本地主目录：`D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/242/r-load-bounds/repo`，非Git快照，通过Melodydt本人GitHub连接、精确文件清单和租约更新远程分支；不要在外层管理快照假称git提交。
- 独立研究目录：外层 `work/Melodydt/247/iterations-research/{feed,model,rtl,upstream241}`。子代理仅改各自研究目录，正式目录由根会话集成。upstream241冻结PR241@189e43c77a6277955c1be54281b0d6b0b0d55c1f，13文件Git blobSHA已校验。
- 当前本地变更：迭代总入口、此交接、本人进度/项目阶段摘要；R1模块/测试在独立目录形成，尚无本轮已通过仿真。管理结构检查PASS，只是结构检查。
- 目标：最多四轮，每轮研究→方案→RTL→旧评价体系服务器评估→详细PDF，主W8 decode512达5 token/s或满四轮时停止。当前0/4轮完成。SRAM扩容仍不实装，巨大面积方案独立备份。
- 评价：固定run15原trace、S32/S96条件模型、2P/1U、300MHz、17.1GB/s，16KiB、八上下文，共享口/理想1R1W分列。起点3.23081074122/3.49616888299 token/s。仅在实际RTL证据支持下替换局部成本，禁止把原生S64/四1RW资格等同旧S96/理想端口。
- 首轮：正式U新增默认关闭NExp批处理，共享唯一原N。S32容器低16有符号映射和输出U16零扩为S32保持旧候选合同；op15显式破坏原N统计会话，普通统计需重新op0。prefill实际S16输入不适配NX32，保持完整旧路径费用。
- 下一步第一动作：核对远程分支仍是已知head及其他会话改动，再审查独立候选、集成正式RTL和运行器，提交代码后才打包仿真。先RTL功能/数值/握手/U实际S读写ACK，再把实际profile绑定旧SystemC评估；每轮PDF完成视觉QA和证据上传后计入已完成轮次。
- 服务器：`yuzelu@10.129.166.172`，本人目录 `/public/home/yuzelu/Melodydt/issue247-area-speed`。既有run01–15保留；本轮尚未提交，拟从run16开始。所有EDA/SystemC用Slurm c64/c96、4核、mdt前缀、time=0及既有容器，禁止本机/登录节点执行。每次提交立即补充实际job/node/日志/结果/追踪命令；现在无新作业，未配置自动监测。
- 工具辅助：外层 `work/Melodydt/247/iterations-tools/` 为显式清单打包、Git tree准备、不可变证据策展和PDF转换。首次新PDF操作marker已成功执行一次（05153f），无需重复；期望最多4份。每份最终PDF均需逐页渲染和目视核验。
- 审查/登记/看板：独立审查人待指定；登记management-hub PR5 pending；缺config/board.json及Projects工具，看板unverified、同步pending，管理员待处理。未标done，不自行合并。
