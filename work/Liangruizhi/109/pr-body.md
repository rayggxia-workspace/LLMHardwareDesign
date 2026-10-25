106的唯一共享银行只接入M/A/Falcon R，104完整两头GDN仍是独立核。本任务抽离104控制器并增加第四profile，真实共用同一个16KiB128bit1RW、8S8、一个S32服务、SFU和外部桥；宽乘lowerer三次使用同一S32后一次RNE，GDN完整两head guard/重标/双metadata及root发布保持原数学。新增共享桥真实导出2048B候选、完整identity及pending排空；accept后commit-drain不可撤销，跨lease状态依赖有版本外存。

本人服务器两等待模式各13条真实混合和44条恢复命令独立全值通过；两路selected raw gate各8完整命令，包括native首步与真实legacy重标，actual行/完整状态/阶段/协议与RTL逐字节相同并通过独立整数oracle。8个数值协议与3个库存实际文件重SHA负例拒绝。43作业全终态：39COMPLETED、2首轮2400s门级FAILED、2依赖reader取消；唯一6000s重放41:43/50:46完成，原失败未覆盖。104.92MB完整证据留授权服务器，356685B/229成员精选入仓；服务器双包、本机精选和8phase233原Git源字节全部接收。

实际唯一库存logic-only163901.220µm²、109574cells、12767DFF；候选2048B需128事务、10240B wire、1024B generation sideband。比106增加第四profile及控制器约30.11%逻辑面积，不是同函数PPA优化。环境最多6KiB provisional sink与320bit+control responseFIFO单列，真实下游事务buffer尚未实现。原10441项、10652项源码/工件Gitblob保持不变；抽离源码静态审计不是形式证明。SCP重试及43cmd早期receiver依赖录入错误完整留档，最终44cmd与gate依赖以实际producer为准。

新增电路候选v2：固定完整K/RQ/scale、R整head guard/trial/shadow/原子root、响应所有权和scratch/持久外存生命周期；不冻结制造宏或M9–M10拓扑。下一最小门槛为真实事务消费者缓冲、宏/drive/PG/PVT及新top物理。README阶段已纠正，引用98/PR111的97有限研究logic-island资格；109不继承旧时序、预算或固定层证据。110仅为独立等价微优化候选，尚未合入。

限制：非完整Block库、整模型数据链、通用V ISA/GEMM、attention online/append或GDN gatednorm。结果前缀provisional，DONE ACK释放旧bank引用；原子128bitroot/effect-onceACK及协调reset为fabric义务。selected门级不含全部恢复、RTL-only Q注入、真实宏或物理时序。真实S reset只清响应valid/dout，内容不初始化；cfg/canary setup不冒充核心计算。

Refs #109

规则版本：rayggxia-project-collab 1.0.0
项目/任务：rayggxia-workspace/LLMHardwareDesign；llm-hardware-design；Issue109；Liangruizhi
成果：本任务分支；报告docs/experiments/issue-109-shared-gdn.md、电路候选v2、个人进度和交接；实际RTL4b69d43、44cmd driver fe14c02、接收phase6、成本phase7、后处理phase8@33f7a46；最终发布HEAD以PR为准
验证：实际argv/43作业/完整整数/恢复/selected gate/库存/负例/字节回执随仓库；项目结构与12Python AST通过；最终LF/累计diff审计见work109/local-checks.json
登记：pending，management-hub PR5尚待合并
看板：unverified（配置/read:project缺项）；同步pending，管理员待处理
审查与状态：本地证据完成，root核验发布后再in_review；独立审查人待指定，未合并/done
下一步：root发布并读回report/index/cost/gate；按电路候选v2继续真实消费者及宏/drive/PG/PVT/newtop物理门槛
