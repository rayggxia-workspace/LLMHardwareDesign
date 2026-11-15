# PR273 接入：范围前沿与实际 RTL 合同

本次目标：将可独立提交的范围纳入 Algo1；按实际 SRAM 地址、覆盖和提交语义管理驻留；输出同计划的连线、MC/LC 指令和描述符。PR185 保持：只有功能宏是硬边界，无隐式 U/P 预接、无新增抽象部分和 bank。

## 前一轮清洁驻留基线（不等同于联合搜索）

- native_range_frontier.py 从原 operand recipe 的精确 source segments 与 output intervals 建立范围依赖。消费者只等待相交的已提交生产范围。完整 K 归约仍原子；同父任务工作区复用显式串行，未省略不可证明的依赖。
- Frontend 在原图布局和存储分配完成后展开范围，因此资产、权重及地址不变。CLI --range-tiles 控制每个动作的合法已有 tile 数；0 保留整算子基线。此轮未将 PR273 独立范围原型的任意分段 K/动态宽度选择冒充部署支持。
- native_range_residency.py 只保留已有 SRAM 的实际16B字地址，记录已提交 DDR 对应副本。新 SRAM 写使相交副本失效；未知服务清空该实例缓存；DDR覆盖使所有旧副本失效。仅当整个512B已在目标字位置时删除DRL1。所有输出store和提交事件保留，因而淘汰清洁副本不需要新增写回。
- native_resident_binding_search.py 在范围DP给出的合法顺序上，使用真实驻留状态比较绑定；保留原绑定序列为备选。保留哪些范围先进入前沿的原DP，第二阶段绑定beam默认最多4。不是联合搜索所有分块宽度/顺序的全局最优求解器。
- 不把不同资源池合并。实际宏、LC、adapter资源预约继续参与，范围和重编码沿用原端点准入、包封存和 TLM执行。

## 跨命令归约续接缺口——不是单删一个 WAIT

| 层 | 当前事实 | 要开放续接必须补的内容 |
|---|---|---|
| Algo1 描述符 | compiler/projection_local_descriptor.py 的 encode 明确要求 k_begin=0、k_end=full_k、ways=1 | 新能力版本、合法K区间、输出组/上下文身份、首次/续接/最后动作；不能放宽检查后仍发旧ABI |
| parent 描述符解码 | 上游 rtl/block_local_native/p_scope128_decode.sv：partial_scope=k_begin!=0或k_end!=full_k；stream_bad明确拒绝stream_scope的partial_scope | 定义并验证流式partial scope，保留输入长度、地址、snapshot及身份验证 |
| parent 局控 | rtl/services/projection_stream_controller.sv 按完整scope接范围服务；projection_local_service_controller.sv 仅在p_done且source_drained且owners=0时报告结束 | 增加“部分和已保留/已保存”与“最终输出提交”的不同终态；暂停要排空在途请求，保留或显式释放输入/结果所有权；取消和错误也要回收 |
| M 宏状态 | projection_context_s32.sv 已有16组S32 context及create/restore/step/snapshot-clear命令；当前 p_native_weight_overlap_candidate 明确拒绝 record_restore/record_spill | 查明可跨scope保留的命令序列及占用上限；若现有宏接口不能安全表达，则改M宏控制协议。不得在parent里隐藏新累加器 |
| 保存/恢复 | Attention的S80 snapshot是另一服务内部合同，不能直接赋予Down | 为Down明确实际状态位宽、字节布局、舍入位置、保存/恢复端口和ACK、地址容量、owner/version/next_k不匹配拒绝；不能默设S64/S80外部bank |
| Algo1 生命周期 | 未开放的partial K动作不生成 | 部分和租约跨动作保留；所有输出组读完前不释放输入；保存、恢复、溢出和竞争均计成本。读到partial-DONE不等于最终张量可见 |
| TLM | 当前projection服务按完整scope解释 | 对应新ABI逐命令模拟上述真实状态及终态；不能自行重排/续接/新增算术状态 |

当前可交付的范围动作是“完整归约后的输出范围”。跨命令K续接需要以上软件、parent控制和必要的M宏协议共同完成，不能只归责DP，也不能仅凭宏内有context就宣布支持。本轮对齐缺口，不擅自增加部分和宏、bank或宽口。

## 验证入口

- audits/verify_range_integration.py：完整36层prefill与decode候选/计划。
- audits/refine_range_plans.py：同图范围DP＋驻留状态绑定搜索。
- audits/package_range_plans.sbatch：同计划静态端点、实际九组/30宏装配elaboration及完整指令包。
- audits/run_range_request.sbatch：完整两token prefill→本次自产KV和token→一步decode，执行全部指令并与独立整数参考核对所有张量。
- 上述作业未完成前不报告通过。未运行P512/D128；TLM时序仍未校准。

## 本轮真正联合搜索

见 JOINT_FRONTIER_STATUS.md。native_joint_search 同时搜索ready范围、服务绑定和是否延后DDR提交；native_dirty_memory 按实际SRAM容量安放数据、生成必要spill，并在最后读者之后释放。不能把本轮状态与上述保留所有store的基线混写。完整图包/TLM结果尚待作业回执。
