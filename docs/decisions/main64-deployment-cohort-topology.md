# main64部署整组topology与端口能力（R8.1）

Issue179 / PR180；2026-11-08；Melodydt。main c4d7b960，分支起点f087c3c8。

main MC call_word[192+:32]直接使用母控已装载topology；LC task_ready要求任务包[192+:32]等于本端topology。类型不是topology。候选选整组0x01938000+KIND0*16+KIND1，三份镜像、两端task记录和物理LC参数共同绑定；主机BEGIN错拓扑返回3，不能让已接受的部署随后永久等TASK。

U没有普通主机S_READ；只能通过main已有SEND返回真实S数据。CF对部署后的未预约RX有硬件限制，因此候选统一禁止部署后普通S_WRITE，避免管理器挂起；J专属片段可在空闲、输出清空后补充，每次join重新提供片段。CF读口通过main group_top的verify_read选项形成新候选封装，不继承旧物理验收。

main生成控制/服务仅作可逆模块名重命名，解决U三源adapter与CF两源adapter的全局名字冲突；原始main源及产生器不改。64位保持，共同集成资格先限G_CALL/G_WAIT/G_END、L_EXEC/L_WAIT/L_END；其余原生能力和后续编译目标在contract.json分别列出，不能从取指位宽推导全部指令可用。

规格/接口证据与R8.2功能、结构、时序分开记录。完整编译、恢复、覆盖和新综合冻结分别留后续阶段。


R8.2补充：P/U未使用close输入固定0、trace输出显式空接；J生成器十个未用输出作可逆显式空接，保持main原始源不变。严格PINMISSING检查保留；主矩阵189、同DUT保护27、九结构通过。完整对象close程序仍不在本轮三指令局控子集内。
