# 在已验证原生目标上统一任务描述，独立核对完整镜像

Issue179 / PR180；Melodydt；2026-11-07 Asia/Shanghai。

新增bounded-native-tasks/1，不直接接收任意模型图。五类同型目标和四条U/F/C/J→P链复用既有ABI、拓扑、可综合PM与管理口；母控双CALL/共同WAIT、局控串行EXEC/WAIT，固定两任务。命名缓冲区和有限语义服务先校验能力、地址/生命周期、原生上下文和展开容量，再编码；不开放裸native参数逃逸口。J保留片段/T提交输出，RAW128不提供数值转换。

跨块源原生操作后追加SEND，目的先RESERVE/RECEIVE再消费；预约expected service_sequence由源操作数推导，与START序号区分。资源槽0是整组适配器，不改变物理宏组成。执行ISA仍64 bit，旧45个SV（含测试）不变。

独立audit不导入编译器/编码器，另行构造完整规范字节；数值参考另列有限示例域。软件1218/1218检查点，实际主机装载和原生数据路径回放162/162。r001执行RTL，r002补验导出工具/合同/CLI，八个核心生成/参考/回放文件SHA相同。场景通过率不是覆盖率，新增组合STA/CDC/RDC/物理资格不由该结果授予。下一步8扩展完整矩阵和覆盖，9冻结综合交付；完整LLM图导入及任意规模调度留在本有界编译器之外。

接口、复现与证据见project/control_task_compiler_v1/README.md和work/Melodydt/179/control-compiler-validation.json。
