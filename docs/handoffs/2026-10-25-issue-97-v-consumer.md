# Issue97交接：专用SiLU→动态A8→真实M→norm

- 仓库：rayggxia-workspace/LLMHardwareDesign；[Issue97](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/97)，负责人Liangruizhi；分支task/97-v-consumer，目录D:/Projects/LLMHardwareDesign-v-consumer。依赖93最终4b70b6a已merge；文档整理前head `03eef3e4dadb7fef6763c417b5a501847695a935`，最终head由交付git log/PR确认，不用这段自引用代替提交。
- 实际源码：RTL phase8@40491d1，map phase2@064995e，严格receiver phase9@2ba64aa，汇总/归档phase10@a9e91390。所有RTL未因后续文档/换行改写；7个文本末尾CRLF→LF仅规范，旧Git/SHA照存于work97/line-ending-receipt.json。
- 完成：两路各50accepted/29成功输出（27完整链+2V边界）、11错误/20恢复/7阶段abort，独立原74oracle、22个实际文件重SHA负例；4路门级8输出全字段/原74一致，4重SHA负例。门级不含RTL的Q注入/错误恢复，行为SRAM零延迟，不是STA。
- 资源：8S8+1S32+normSFU，一块16KiB128bit1RW；70,102.970µm²、47499cell、5344DFF_X1，未含存储宏/外部ROM/tag/FIFO/物理时钟与布线。至少320bit+控制外部恢复FIFO另计。当前M仍K512/8expert/H1536；通用80V ISA未整合。
- 全包：`/public/home/yuzelu/RuizhiLiang/issue97-v-consumer-20261025/delivery01/full-results.zip`，750458058B/1085，SHA ccdda33ea2df686b4ce2493ab3efc241e58f9be570344bea33e52cb41e5be604。精选220674B/178，SHA c2d553d09cb6107b230b881c7def1322c8744e6796ef9afc7089eefa4e477c2d。两包server/精选PC与10phase153原Git字节PASS。
- 失败：1构建gamma命名冲突、4旧metadata注入时机回归失败，均保留；5自有失效/旧版依赖取消。最终50作业全部终态，原输出不覆盖。
- 98复用接口：map01/mapped.json，gateprep01原Liberty导出；phase6 sim.cpp无Q注入，input02/vectors.tsv，argv `vectors.tsv actual.jsonl stall(0/1) pilot(1/2)`。pilot1=L0T0、pilot2=L13T71，每路V-only后full，不能把qualification.cpp的top输出赋值搬到gate。`gatereceive02/receipt.json` SHA 932a267391e62d8a23bda0e214b67daea187082fa52bb4c6004866818d024ebd。
- 下一步：98只重放新物理变换后的gate，不重复本raw图；99 R in_progress不能预判。完整在线GQA A、通用V/M/D、真实宏/时序/多工作负载端到端仍需后续任务。
- 恢复第一步：指定Liangruizhi身份读最新AGENTS/Issue97/98/99、PR和成员55/63；核results/issue-97/index.json、selected.zip、source-byte-receipt，再按原phase源码新out恢复。源码/元数据在本机，实际张量/RTL/map接收仅本人服务器；无需下载模型或动其他机器。
- 交付状态：本地已整理、主会话待push/PR与Issue in_review同步。PR尚未由本分代理创建；不自合并、不done。登记PR5 pending；board配置/read:project缺失，未核/待管理员同步。主会话发PR后补实际链接/读回，不把本地完成称远端完成。
- 暂停时无未归档运行作业；当前有用临时文件保留D:/Projects/Codex/issue97-v-consumer-20261025-01供复查。最终改动和检查见work97/local-validation.json及最终commit。
